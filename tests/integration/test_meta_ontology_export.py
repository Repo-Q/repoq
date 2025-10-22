"""
Integration tests for meta-loop ontology export.

Tests that RDF export includes meta, test, trs, quality, docs ontology triples.
"""

from pathlib import Path

import pytest


@pytest.fixture
def sample_project():
    """Create sample project for testing."""
    from repoq.core.model import File, Project

    project = Project(
        id="repo:test_project",
        name="test_project",
        repository_url="https://github.com/test/test_project",
    )

    # Add sample files (files is Dict[str, File])
    file1 = File(
        id=f"{project.id}/file1",
        path="src/main.py",
        language="python",
        lines_of_code=100,
        complexity=5.0,
    )
    file2 = File(
        id=f"{project.id}/file2",
        path="src/utils.py",
        language="python",
        lines_of_code=50,
        complexity=20.0,  # High complexity
    )

    project.files = {file1.id: file1, file2.id: file2}

    return project


def test_rdf_export_includes_meta_ontology(sample_project, tmp_path):
    """Test that RDF export includes meta:SelfAnalysis triples."""
    from repoq.core.rdf_export import export_ttl

    ttl_path = tmp_path / "test_output.ttl"
    export_ttl(sample_project, str(ttl_path), enrich_meta=True)

    assert ttl_path.exists()
    content = ttl_path.read_text()

    # Check for meta ontology namespace
    assert "meta:" in content or META_NS in content

    # Check for SelfAnalysis instance
    assert "meta:SelfAnalysis" in content
    assert "meta:stratificationLevel" in content
    assert "meta:readOnlyMode" in content

    # Parse with rdflib and query
    try:
        from rdflib import Graph, Namespace

        g = Graph()
        g.parse(ttl_path, format="turtle")

        META = Namespace("http://example.org/vocab/meta#")

        # Query for SelfAnalysis
        query = f"""
        PREFIX meta: <{META}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?analysis ?level WHERE {{
            ?analysis rdf:type meta:SelfAnalysis .
            ?analysis meta:stratificationLevel ?level .
        }}
        """
        results = list(g.query(query))
        assert len(results) > 0, "No SelfAnalysis instances found"

        # Verify stratification level is 0
        level = int(results[0][1])
        assert level == 0, f"Expected stratification level 0, got {level}"

    except ImportError:
        pytest.skip("rdflib not installed")


def test_rdf_export_includes_quality_gate(sample_project, tmp_path):
    """Test that RDF export includes quality:Gate triples."""
    from repoq.core.rdf_export import export_ttl

    ttl_path = tmp_path / "test_output.ttl"
    export_ttl(sample_project, str(ttl_path), enrich_meta=True)

    content = ttl_path.read_text()

    # Check for quality ontology
    assert "quality:" in content or QUALITY_NS in content
    assert "quality:ComplexityGate" in content or "ComplexityGate" in content

    # Parse and query
    try:
        from rdflib import Graph, Namespace

        g = Graph()
        g.parse(ttl_path, format="turtle")

        QUALITY = Namespace("http://example.org/vocab/quality#")

        # Query for gates
        query = f"""
        PREFIX quality: <{QUALITY}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?gate ?status ?threshold ?actual WHERE {{
            ?gate rdf:type quality:ComplexityGate .
            ?gate quality:gateStatus ?status .
            ?gate quality:threshold ?threshold .
            ?gate quality:actualValue ?actual .
        }}
        """
        results = list(g.query(query))
        assert len(results) > 0, "No quality gates found"

        # Verify gate data
        status = str(results[0][1])
        threshold = float(results[0][2])
        actual = float(results[0][3])

        assert status in ["passed", "failed"], f"Invalid gate status: {status}"
        assert threshold > 0, f"Invalid threshold: {threshold}"
        assert actual >= 0, f"Invalid actual value: {actual}"

    except ImportError:
        pytest.skip("rdflib not installed")


def test_rdf_export_includes_docs_coverage(sample_project, tmp_path):
    """Test that RDF export includes docs:Coverage triples."""
    from repoq.core.rdf_export import export_ttl

    ttl_path = tmp_path / "test_output.ttl"
    export_ttl(sample_project, str(ttl_path), enrich_meta=True)

    content = ttl_path.read_text()

    # Check for docs ontology
    assert "docs:" in content or DOCS_NS in content

    # Parse and query
    try:
        from rdflib import Graph, Namespace

        g = Graph()
        g.parse(ttl_path, format="turtle")

        DOCS = Namespace("http://example.org/vocab/docs#")

        # Query for coverage
        query = f"""
        PREFIX docs: <{DOCS}>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?coverage ?percentage WHERE {{
            ?coverage rdf:type docs:Coverage .
            ?coverage docs:coveragePercentage ?percentage .
        }}
        """
        results = list(g.query(query))
        assert len(results) > 0, "No documentation coverage found"

        # Verify coverage is valid percentage
        percentage = float(results[0][1])
        assert 0.0 <= percentage <= 100.0, f"Invalid coverage percentage: {percentage}"

    except ImportError:
        pytest.skip("rdflib not installed")


def test_shacl_validation_with_meta_ontologies(sample_project, tmp_path):
    """Test SHACL validation includes meta-ontology constraints."""
    from repoq.core.rdf_export import validate_shapes

    # Create shapes directory
    shapes_dir = Path(__file__).parent.parent.parent / "repoq" / "shapes"

    if not shapes_dir.exists():
        pytest.skip("Shapes directory not found")

    try:
        result = validate_shapes(sample_project, str(shapes_dir), enrich_meta=True)

        assert "conforms" in result
        assert "report" in result
        assert "violations" in result

        # Log violations if any
        if not result["conforms"]:
            print(f"\nSHACL Violations ({len(result['violations'])}):")
            for v in result["violations"]:
                print(f"  {v['severity']}: {v['message']}")

        # Meta-ontology constraints should pass
        # (stratificationLevel=0, readOnlyMode=true)
        # We expect validation to pass or only have warnings
        if result["violations"]:
            critical_violations = [v for v in result["violations"] if v["severity"] == "Violation"]
            assert (
                len(critical_violations) == 0
            ), f"Expected no critical violations, got {len(critical_violations)}"

    except ImportError:
        pytest.skip("pyshacl not installed")


# Define namespace constants for assertions
META_NS = "http://example.org/vocab/meta#"
QUALITY_NS = "http://example.org/vocab/quality#"
DOCS_NS = "http://example.org/vocab/docs#"
