"""
Integration tests for test coverage RDF export (T2.4).

Tests the full pipeline:
1. Parse pytest coverage.json
2. Parse pytest --collect-only output
3. Generate test:TestCase and test:Coverage triples
4. Validate against SHACL test_shape.ttl
"""

import json
from pathlib import Path

import pytest
from rdflib import Graph

from repoq.core.model import File, Project
from repoq.core.rdf_export import export_ttl, validate_shapes
from repoq.core.test_coverage import enrich_graph_with_test_coverage


@pytest.fixture
def sample_project():
    """Create sample project for testing."""
    project = Project(
        id="repo:test_project",
        name="test_project",
        repository_url="https://github.com/test/test_project",
    )

    file1 = File(
        id=f"{project.id}/file1",
        path="src/main.py",
        language="python",
        lines_of_code=80,
        complexity=5.0,
    )

    project.files = {file1.id: file1}
    return project


@pytest.fixture
def mock_coverage_json(tmp_path):
    """Create mock coverage.json file."""
    coverage_data = {
        "meta": {"format": 3, "version": "7.0.0"},
        "files": {
            "src/main.py": {"summary": {"percent_covered": 85.5}},
            "src/utils.py": {"summary": {"percent_covered": 92.0}},
        },
        "totals": {
            "percent_covered": 88.2,
            "covered_lines": 150,
            "num_statements": 170,
        },
    }

    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(json.dumps(coverage_data))
    return coverage_path


@pytest.fixture
def mock_pytest_collection():
    """Mock pytest --collect-only output."""
    return """
tests/test_main.py::TestMainFeature::test_initialization
tests/test_main.py::TestMainFeature::test_run
tests/test_utils.py::test_helper_function
tests/integration/test_e2e.py::test_full_pipeline
"""


def test_coverage_export_to_rdf(sample_project, tmp_path, mock_coverage_json, mock_pytest_collection):
    """Test that coverage data is exported to RDF correctly."""
    ttl_path = tmp_path / "test_output.ttl"

    # Export with test coverage enrichment
    g = Graph()
    from repoq.core.jsonld import to_jsonld

    data = to_jsonld(sample_project)
    g.parse(data=json.dumps(data), format="json-ld")

    enrich_graph_with_test_coverage(
        g,
        sample_project.id,
        coverage_path=str(mock_coverage_json),
        pytest_collect_output=mock_pytest_collection,
    )

    g.serialize(destination=str(ttl_path), format="turtle")

    # Verify RDF contains coverage
    content = ttl_path.read_text()
    assert "test:Coverage" in content
    assert "test:TestCase" in content
    assert "test:coveragePercentage" in content

    print(f"✅ RDF export includes test coverage")


def test_coverage_triples_structure(mock_coverage_json, mock_pytest_collection):
    """Test that coverage triples have correct structure."""
    g = Graph()

    enrich_graph_with_test_coverage(
        g,
        "repo:test_project",
        coverage_path=str(mock_coverage_json),
        pytest_collect_output=mock_pytest_collection,
    )

    # Query for coverage
    query_coverage = """
    PREFIX test: <http://example.org/vocab/test#>
    SELECT ?coverage ?percentage ?covered ?total WHERE {
        ?coverage a test:Coverage ;
                  test:coveragePercentage ?percentage ;
                  test:coveredLines ?covered ;
                  test:totalLines ?total .
    }
    """
    results = list(g.query(query_coverage))

    assert len(results) == 1
    coverage, percentage, covered, total = results[0]

    assert float(percentage) == 88.2
    assert int(covered) == 150
    assert int(total) == 170

    print(f"✅ Coverage: {float(percentage):.1f}% ({int(covered)}/{int(total)} lines)")


def test_testcase_triples_structure(mock_coverage_json, mock_pytest_collection):
    """Test that test case triples have correct structure."""
    g = Graph()

    enrich_graph_with_test_coverage(
        g,
        "repo:test_project",
        coverage_path=str(mock_coverage_json),
        pytest_collect_output=mock_pytest_collection,
    )

    # Query for test cases
    query_tests = """
    PREFIX test: <http://example.org/vocab/test#>
    SELECT ?test ?name ?filePath ?concept WHERE {
        ?test a test:TestCase ;
              test:testName ?name ;
              test:testFilePath ?filePath ;
              test:testedConcept ?concept .
    }
    """
    results = list(g.query(query_tests))

    assert len(results) >= 3  # At least 3 tests from mock collection

    # Check first test
    test, name, file_path, concept = results[0]
    assert str(name) in ["test_initialization", "test_run", "test_helper_function"]
    assert "tests/" in str(file_path)
    assert str(concept) != ""

    print(f"✅ Found {len(results)} test cases in RDF")


def test_shacl_validation_with_test_coverage(
    sample_project, mock_coverage_json, mock_pytest_collection, tmp_path
):
    """Test that SHACL validation passes with test coverage data."""
    # Export RDF with test coverage
    g = Graph()
    from repoq.core.jsonld import to_jsonld

    data = to_jsonld(sample_project)
    g.parse(data=json.dumps(data), format="json-ld")

    enrich_graph_with_test_coverage(
        g,
        sample_project.id,
        coverage_path=str(mock_coverage_json),
        pytest_collect_output=mock_pytest_collection,
    )

    # Save to temp file for validation
    ttl_path = tmp_path / "test_output.ttl"
    g.serialize(destination=str(ttl_path), format="turtle")

    # Validate against test_shape.ttl
    shapes_dir = Path("repoq/shapes")

    # Create a minimal project for validation
    # (actual RDF is already in graph)
    from rdflib import Graph as ValidationGraph
    from pyshacl import validate

    data_graph = ValidationGraph()
    data_graph.parse(ttl_path, format="turtle")

    shapes_graph = ValidationGraph()
    test_shape_path = shapes_dir / "test_shape.ttl"
    shapes_graph.parse(test_shape_path, format="turtle")

    conforms, report_graph, report_text = validate(
        data_graph, shacl_graph=shapes_graph, inference="rdfs", abort_on_first=False
    )

    # Extract violations
    violations = []
    if not conforms and report_graph:
        query = """
        PREFIX sh: <http://www.w3.org/ns/shacl#>
        SELECT ?focusNode ?message ?severity WHERE {
            ?result a sh:ValidationResult .
            ?result sh:focusNode ?focusNode .
            ?result sh:resultMessage ?message .
            ?result sh:resultSeverity ?severity .
        }
        """
        for row in report_graph.query(query):
            violations.append(
                {
                    "focusNode": str(row[0]),
                    "message": str(row[1]),
                    "severity": str(row[2]).split("#")[-1],
                }
            )

    # Check for critical violations
    critical_violations = [v for v in violations if v["severity"] == "Violation"]

    if critical_violations:
        print("\n❌ Critical SHACL violations:")
        for v in critical_violations:
            print(f"  - {v['focusNode']}: {v['message']}")

    assert len(critical_violations) == 0, f"Expected no critical violations, got {len(critical_violations)}"

    print(f"✅ SHACL validation passed (test coverage)")


def test_tested_concept_extraction(mock_coverage_json, mock_pytest_collection):
    """Test that tested concepts are correctly extracted from test names."""
    g = Graph()

    enrich_graph_with_test_coverage(
        g,
        "repo:test_project",
        coverage_path=str(mock_coverage_json),
        pytest_collect_output=mock_pytest_collection,
    )

    query = """
    PREFIX test: <http://example.org/vocab/test#>
    SELECT DISTINCT ?concept WHERE {
        ?test a test:TestCase ;
              test:testedConcept ?concept .
    }
    """
    results = list(g.query(query))

    concepts = [str(r[0]) for r in results]

    # From TestMainFeature → MainFeature
    assert "MainFeature" in concepts

    # From test_helper_function → helper_function
    assert "helper_function" in concepts

    print(f"✅ Extracted concepts: {concepts}")


@pytest.mark.skipif(
    not Path("coverage.json").exists(), reason="Requires coverage.json in project root"
)
def test_real_coverage_export():
    """Test export with real coverage.json from project."""
    g = Graph()

    # Use subset of real tests
    pytest_output = """
tests/unit/test_test_coverage.py::test_extract_tested_concept_from_class
tests/unit/test_test_coverage.py::test_parse_coverage_json
tests/integration/test_shacl_workflow.py::test_workflow_rdf_export_step
"""

    enrich_graph_with_test_coverage(
        g,
        "repo:repoq",
        coverage_path="coverage.json",
        pytest_collect_output=pytest_output,
    )

    # Query coverage
    query = """
    PREFIX test: <http://example.org/vocab/test#>
    SELECT ?percentage WHERE {
        ?coverage a test:Coverage ;
                  test:coveragePercentage ?percentage .
    }
    """
    results = list(g.query(query))

    assert len(results) == 1
    percentage = float(results[0][0])

    assert 0.0 <= percentage <= 100.0

    print(f"✅ Real project coverage: {percentage:.1f}%")
