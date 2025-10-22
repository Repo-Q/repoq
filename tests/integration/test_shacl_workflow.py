"""
Integration tests for CI/CD SHACL validation workflow.

Tests verify that the SHACL validation workflow correctly:
1. Exports RDF with meta-ontology enrichment
2. Validates against all SHACL shapes
3. Detects and reports violations
4. Blocks on critical violations
"""

import json
import subprocess
from pathlib import Path

import pytest
from rdflib import Graph

from repoq.core.model import File, Project
from repoq.core.rdf_export import export_ttl, validate_shapes


@pytest.fixture
def sample_project():
    """Create a sample project for testing."""
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

    file2 = File(
        id=f"{project.id}/file2",
        path="src/utils.py",
        language="python",
        lines_of_code=70,
        complexity=20.0,
    )

    project.files = {file1.id: file1, file2.id: file2}
    return project


def test_workflow_rdf_export_step(sample_project, tmp_path):
    """Test that the workflow's RDF export step produces valid RDF."""
    ttl_path = tmp_path / "repoq_analysis.ttl"

    # Simulate workflow step: repoq analyze with --ttl-output
    export_ttl(sample_project, str(ttl_path), enrich_meta=True)

    # Verify file exists
    assert ttl_path.exists()

    # Verify valid RDF
    g = Graph()
    g.parse(ttl_path, format="turtle")

    assert len(g) > 0, "RDF graph should not be empty"
    print(f"✅ Exported {len(g)} triples")


def test_workflow_shacl_validation_step(sample_project, tmp_path):
    """Test that the workflow's SHACL validation step works correctly."""
    shapes_dir = Path("repoq/shapes")

    # Simulate workflow step: SHACL validation
    result = validate_shapes(
        sample_project,
        shapes_dir=str(shapes_dir),
        context_file="repoq/ontologies/context_ext.jsonld",
        enrich_meta=True,
    )

    # Verify result structure
    assert "conforms" in result
    assert "report" in result
    assert "violations" in result

    print(f"✅ Conforms: {result['conforms']}")
    print(f"✅ Violations: {len(result['violations'])}")

    # For CI/CD, we expect no critical violations
    critical_violations = [
        v for v in result["violations"] if v.get("severity") == "Violation"
    ]

    assert (
        len(critical_violations) == 0
    ), f"Expected no critical violations, got {len(critical_violations)}"


def test_workflow_validation_report_format(sample_project, tmp_path):
    """Test that validation report has correct JSON format for CI/CD."""
    shapes_dir = Path("repoq/shapes")

    result = validate_shapes(
        sample_project,
        shapes_dir=str(shapes_dir),
        context_file="repoq/ontologies/context_ext.jsonld",
        enrich_meta=True,
    )

    # Write report as workflow would
    report_path = tmp_path / "validation-report.json"
    report_path.write_text(json.dumps(result, indent=2))

    # Verify report can be read
    loaded_report = json.loads(report_path.read_text())

    assert loaded_report["conforms"] == result["conforms"]
    assert len(loaded_report["violations"]) == len(result["violations"])

    print(f"✅ Report format valid: {report_path}")


def test_workflow_meta_loop_safety(sample_project, tmp_path):
    """Test that meta-loop self-analysis maintains safety guarantees."""
    ttl_path = tmp_path / "repoq_analysis.ttl"

    # Export with meta-enrichment
    export_ttl(sample_project, str(ttl_path), enrich_meta=True)

    # Parse and query for SelfAnalysis
    g = Graph()
    g.parse(ttl_path, format="turtle")

    query = """
    PREFIX meta: <http://example.org/vocab/meta#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    
    SELECT ?analysis ?level ?readOnly WHERE {
        ?analysis a meta:SelfAnalysis ;
                  meta:stratificationLevel ?level ;
                  meta:readOnlyMode ?readOnly .
    }
    """

    results = list(g.query(query))
    assert len(results) > 0, "Expected meta:SelfAnalysis to exist"

    # Verify safety properties
    for row in results:
        level = int(row[1])
        read_only = bool(row[2])

        assert level == 0, "Expected stratificationLevel = 0 (ground level)"
        assert read_only is True, "Expected readOnlyMode = true (no self-modification)"

    print("✅ Meta-loop safety guarantees maintained")


def test_workflow_quality_gate_computation(sample_project, tmp_path):
    """Test that quality gates are computed correctly in workflow."""
    ttl_path = tmp_path / "repoq_analysis.ttl"

    export_ttl(sample_project, str(ttl_path), enrich_meta=True)

    g = Graph()
    g.parse(ttl_path, format="turtle")

    query = """
    PREFIX quality: <http://example.org/vocab/quality#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    
    SELECT ?gate ?threshold ?actual ?status WHERE {
        ?gate a quality:ComplexityGate ;
              quality:threshold ?threshold ;
              quality:actualValue ?actual ;
              quality:gateStatus ?status .
    }
    """

    results = list(g.query(query))
    assert len(results) > 0, "Expected quality:ComplexityGate to exist"

    for row in results:
        threshold = float(row[1])
        actual = float(row[2])
        status = str(row[3])

        # Verify computation is correct
        expected_status = "passed" if actual <= threshold else "failed"
        assert status == expected_status, f"Expected {expected_status}, got {status}"

        print(f"✅ Quality gate: threshold={threshold}, actual={actual:.2f}, status={status}")


def test_workflow_docs_coverage_computation(sample_project, tmp_path):
    """Test that documentation coverage is computed correctly."""
    ttl_path = tmp_path / "repoq_analysis.ttl"

    export_ttl(sample_project, str(ttl_path), enrich_meta=True)

    g = Graph()
    g.parse(ttl_path, format="turtle")

    query = """
    PREFIX docs: <http://example.org/vocab/docs#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    
    SELECT ?coverage ?percentage WHERE {
        ?coverage a docs:Coverage ;
                  docs:coveragePercentage ?percentage .
    }
    """

    results = list(g.query(query))
    assert len(results) > 0, "Expected docs:Coverage to exist"

    for row in results:
        percentage = float(row[1])

        # Verify percentage is in valid range
        assert 0.0 <= percentage <= 100.0, f"Expected percentage in [0, 100], got {percentage}"

        print(f"✅ Docs coverage: {percentage:.1f}%")


@pytest.mark.skipif(
    not Path(".git").exists(), reason="Requires git repository for self-analysis"
)
def test_workflow_self_application():
    """Test that workflow can analyze repoq itself (meta-loop)."""
    # This would be run by the workflow's meta-loop-check job
    # For now, just verify the command exists
    result = subprocess.run(
        ["python", "-m", "repoq", "meta", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, "repoq meta command should exist"
    assert "meta-inspect" in result.stdout, "meta-inspect subcommand should exist"

    print("✅ Meta-loop self-application command exists")
