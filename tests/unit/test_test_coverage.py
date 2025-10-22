"""
Tests for test coverage RDF export.
"""

import json
from pathlib import Path

import pytest
from rdflib import Graph

from repoq.core.test_coverage import (
    TestCase,
    TestCoverage,
    _extract_tested_concept,
    enrich_graph_with_test_coverage,
    export_test_coverage_rdf,
    parse_coverage_json,
    parse_pytest_collection,
)


def test_extract_tested_concept_from_class():
    """Test extracting concept from test class name."""
    assert _extract_tested_concept("TestComplexityAnalyzer") == "ComplexityAnalyzer"
    assert _extract_tested_concept("TestSelfAnalysis") == "SelfAnalysis"
    assert _extract_tested_concept("TestFoo") == "Foo"


def test_extract_tested_concept_from_function():
    """Test extracting concept from test function name."""
    assert _extract_tested_concept("test_shacl_validation") == "shacl_validation"
    assert _extract_tested_concept("test_rdf_export") == "rdf_export"
    assert _extract_tested_concept("test_foo_bar_baz") == "foo_bar_baz"


def test_extract_tested_concept_none():
    """Test that non-test names return None."""
    assert _extract_tested_concept("ComplexityAnalyzer") is None
    assert _extract_tested_concept("foo") is None


def test_parse_pytest_collection():
    """Test parsing pytest --collect-only output."""
    collect_output = """
tests/analyzers/test_complexity.py::TestComplexityAnalyzer::test_init
tests/analyzers/test_complexity.py::TestComplexityAnalyzer::test_run
tests/test_utils.py::test_helper_function
"""

    tests = parse_pytest_collection(collect_output)

    assert len(tests) == 3

    # Check class test
    assert tests[0].test_class == "TestComplexityAnalyzer"
    assert tests[0].name == "test_init"
    assert tests[0].tested_concept == "ComplexityAnalyzer"

    # Check function test
    assert tests[2].test_class is None
    assert tests[2].name == "test_helper_function"
    assert tests[2].tested_concept == "helper_function"


def test_parse_coverage_json(tmp_path):
    """Test parsing coverage.json file."""
    coverage_data = {
        "meta": {"format": 3, "version": "7.0.0"},
        "files": {
            "repoq/foo.py": {"summary": {"percent_covered": 80.0}},
            "repoq/bar.py": {"summary": {"percent_covered": 0.0}},
            "repoq/baz.py": {"summary": {"percent_covered": 50.0}},
        },
        "totals": {
            "percent_covered": 65.5,
            "covered_lines": 100,
            "num_statements": 152,
        },
    }

    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(json.dumps(coverage_data))

    coverage = parse_coverage_json(coverage_path)

    assert float(coverage.coverage_percentage) == 65.5
    assert coverage.covered_lines == 100
    assert coverage.total_lines == 152
    assert coverage.files_covered == 2  # foo and baz have coverage > 0
    assert coverage.total_files == 3


def test_parse_coverage_json_not_found():
    """Test that FileNotFoundError is raised for missing file."""
    with pytest.raises(FileNotFoundError):
        parse_coverage_json("nonexistent.json")


def test_export_test_coverage_rdf():
    """Test exporting test coverage to RDF graph."""
    g = Graph()

    coverage = TestCoverage(
        coverage_percentage=65.5,
        covered_lines=100,
        total_lines=152,
        files_covered=2,
        total_files=3,
    )

    tests = [
        TestCase(
            id="test:tests/test_foo.py//test_bar",
            name="test_bar",
            file_path="tests/test_foo.py",
            tested_concept="bar",
            status="passed",
        ),
    ]

    export_test_coverage_rdf(g, coverage, tests, "repo:test_project")

    # Verify coverage triple
    query_coverage = """
    PREFIX test: <http://example.org/vocab/test#>
    SELECT ?coverage ?percentage WHERE {
        ?coverage a test:Coverage ;
                  test:coveragePercentage ?percentage .
    }
    """
    results = list(g.query(query_coverage))
    assert len(results) == 1
    assert float(results[0][1]) == 65.5

    # Verify test case triple
    query_test = """
    PREFIX test: <http://example.org/vocab/test#>
    SELECT ?test ?name ?concept WHERE {
        ?test a test:TestCase ;
              test:testName ?name ;
              test:testedConcept ?concept .
    }
    """
    results = list(g.query(query_test))
    assert len(results) == 1
    assert str(results[0][1]) == "test_bar"
    assert str(results[0][2]) == "bar"


def test_enrich_graph_with_test_coverage(tmp_path):
    """Test high-level enrichment function."""
    # Create mock coverage.json
    coverage_data = {
        "meta": {"format": 3},
        "files": {"repoq/foo.py": {"summary": {"percent_covered": 100.0}}},
        "totals": {
            "percent_covered": 80.0,
            "covered_lines": 80,
            "num_statements": 100,
        },
    }

    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(json.dumps(coverage_data))

    # Mock pytest collection output
    pytest_output = "tests/test_foo.py::test_bar"

    g = Graph()
    enrich_graph_with_test_coverage(
        g,
        "repo:test_project",
        coverage_path=str(coverage_path),
        pytest_collect_output=pytest_output,
    )

    # Verify graph has coverage data
    query = """
    PREFIX test: <http://example.org/vocab/test#>
    SELECT (COUNT(?s) as ?count) WHERE {
        ?s a test:Coverage .
    }
    """
    results = list(g.query(query))
    assert int(results[0][0]) >= 1  # At least one Coverage instance


def test_enrich_graph_with_actual_coverage():
    """Test with actual coverage.json from project root (if exists)."""
    coverage_path = Path("coverage.json")

    if not coverage_path.exists():
        pytest.skip("coverage.json not found in project root")

    g = Graph()

    # Use small subset of tests for speed
    pytest_output = """
tests/integration/test_shacl_workflow.py::test_workflow_rdf_export_step
tests/integration/test_shacl_workflow.py::test_workflow_shacl_validation_step
"""

    enrich_graph_with_test_coverage(
        g, "repo:repoq", coverage_path=str(coverage_path), pytest_collect_output=pytest_output
    )

    # Verify coverage exists
    query = """
    PREFIX test: <http://example.org/vocab/test#>
    SELECT ?coverage ?percentage WHERE {
        ?coverage a test:Coverage ;
                  test:coveragePercentage ?percentage .
    }
    """
    results = list(g.query(query))
    assert len(results) == 1

    percentage = float(results[0][1])
    assert 0.0 <= percentage <= 100.0

    print(f"✅ Test coverage: {percentage:.1f}%")


def test_integration_with_rdf_export(tmp_path):
    """Test integration with full RDF export pipeline."""
    from repoq.core.model import File, Project
    from repoq.core.rdf_export import export_ttl

    # Create test project
    project = Project(id="repo:test", name="test")
    file1 = File(id=f"{project.id}/file1", path="src/main.py", language="python")
    project.files = {file1.id: file1}

    # Create mock coverage
    coverage_data = {
        "meta": {"format": 3},
        "files": {"src/main.py": {"summary": {"percent_covered": 100.0}}},
        "totals": {
            "percent_covered": 90.0,
            "covered_lines": 90,
            "num_statements": 100,
        },
    }

    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(json.dumps(coverage_data))

    ttl_path = tmp_path / "test_output.ttl"

    # Mock pytest output
    pytest_output = "tests/test_main.py::test_foo"

    # Export with test coverage enrichment
    from repoq.core.test_coverage import enrich_graph_with_test_coverage
    from rdflib import Graph

    g = Graph()
    from repoq.core.jsonld import to_jsonld

    data = to_jsonld(project)
    g.parse(data=json.dumps(data), format="json-ld")

    enrich_graph_with_test_coverage(
        g, project.id, coverage_path=str(coverage_path), pytest_collect_output=pytest_output
    )

    g.serialize(destination=str(ttl_path), format="turtle")

    # Verify output contains test coverage
    content = ttl_path.read_text()
    assert "test:" in content
    assert "Coverage" in content

    print(f"✅ RDF export with test coverage: {ttl_path}")
