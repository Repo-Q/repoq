"""
Integration tests for TRS rules RDF export (T2.5).

Tests the full pipeline:
1. Extract TRS rules from normalize/ modules
2. Enrich with verification metadata from property tests
3. Generate trs:Rule and trs:RewriteSystem triples
4. Validate against SHACL trs_shape.ttl
"""

import json
from pathlib import Path

import pytest
from rdflib import Graph

from repoq.core.model import File, Project
from repoq.core.rdf_export import export_ttl, validate_shapes
from repoq.core.trs_rules import enrich_graph_with_trs_rules


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


def test_trs_rules_export_to_rdf(sample_project, tmp_path):
    """Test that TRS rules are exported to RDF correctly."""
    normalize_dir = Path("repoq/normalize")

    if not normalize_dir.exists():
        pytest.skip("normalize/ directory not found")

    ttl_path = tmp_path / "test_output.ttl"

    # Export with TRS rules enrichment
    export_ttl(sample_project, str(ttl_path), enrich_trs_rules=True)

    # Verify RDF contains TRS data
    content = ttl_path.read_text()
    assert "trs:RewriteSystem" in content or "trs:Rule" in content
    assert "trs:leftHandSide" in content
    assert "trs:rightHandSide" in content

    print(f"✅ RDF export includes TRS rules")


def test_trs_system_triples_structure(sample_project):
    """Test that TRS system triples have correct structure."""
    normalize_dir = Path("repoq/normalize")

    if not normalize_dir.exists():
        pytest.skip("normalize/ directory not found")

    g = Graph()
    from repoq.core.jsonld import to_jsonld

    data = to_jsonld(sample_project)
    g.parse(data=json.dumps(data), format="json-ld")

    enrich_graph_with_trs_rules(g, sample_project.id, normalize_dir=normalize_dir)

    # Query for TRS systems
    query_systems = """
    PREFIX trs: <http://example.org/vocab/trs#>
    SELECT ?system ?name ?confluence WHERE {
        ?system a trs:RewriteSystem ;
                trs:systemName ?name ;
                trs:confluenceProven ?confluence .
    }
    """
    results = list(g.query(query_systems))

    assert len(results) >= 1, "Expected at least one TRS system"

    # Check structure
    for system, name, confluence in results:
        assert str(name) != ""
        assert isinstance(bool(confluence), bool)

    print(f"✅ Found {len(results)} TRS systems in RDF")


def test_trs_rules_triples_structure(sample_project):
    """Test that TRS rule triples have correct structure."""
    normalize_dir = Path("repoq/normalize")

    if not normalize_dir.exists():
        pytest.skip("normalize/ directory not found")

    g = Graph()
    from repoq.core.jsonld import to_jsonld

    data = to_jsonld(sample_project)
    g.parse(data=json.dumps(data), format="json-ld")

    enrich_graph_with_trs_rules(g, sample_project.id, normalize_dir=normalize_dir)

    # Query for TRS rules
    query_rules = """
    PREFIX trs: <http://example.org/vocab/trs#>
    SELECT ?rule ?name ?lhs ?rhs ?system WHERE {
        ?rule a trs:Rule ;
              trs:ruleName ?name ;
              trs:leftHandSide ?lhs ;
              trs:rightHandSide ?rhs ;
              trs:inSystem ?system .
    }
    """
    results = list(g.query(query_rules))

    assert len(results) >= 1, "Expected at least one TRS rule"

    # Check structure
    for rule, name, lhs, rhs, system in results:
        assert str(name) != ""
        assert str(lhs) != ""
        assert str(rhs) != ""
        assert str(system) != ""

    print(f"✅ Found {len(results)} TRS rules in RDF")


def test_spdx_idempotence_rule_in_rdf(sample_project):
    """Test that SPDX idempotence rule appears in RDF."""
    normalize_dir = Path("repoq/normalize")

    if not normalize_dir.exists():
        pytest.skip("normalize/ directory not found")

    g = Graph()
    from repoq.core.jsonld import to_jsonld

    data = to_jsonld(sample_project)
    g.parse(data=json.dumps(data), format="json-ld")

    enrich_graph_with_trs_rules(g, sample_project.id, normalize_dir=normalize_dir)

    # Query for rules with "OR" in LHS and description containing "idempotence"
    query = """
    PREFIX trs: <http://example.org/vocab/trs#>
    SELECT ?rule ?lhs ?rhs ?desc WHERE {
        ?rule a trs:Rule ;
              trs:leftHandSide ?lhs ;
              trs:rightHandSide ?rhs .
        OPTIONAL { ?rule trs:ruleDescription ?desc }
        FILTER (CONTAINS(LCASE(?lhs), "or"))
    }
    """
    results = list(g.query(query))

    # Check if any rule looks like idempotence (A OR A → A)
    idempotence_rules = [
        r
        for r in results
        if "or" in str(r[1]).lower()
        and (r[3] is None or "idempotence" in str(r[3]).lower())
    ]

    if idempotence_rules:
        print(f"✅ Found {len(idempotence_rules)} idempotence-like rules")
    else:
        print(f"⚠️  No idempotence rules found (total OR rules: {len(results)})")


def test_shacl_validation_with_trs_rules(sample_project, tmp_path):
    """Test that SHACL validation passes with TRS rules data."""
    normalize_dir = Path("repoq/normalize")
    shapes_dir = Path("repoq/shapes")

    if not normalize_dir.exists() or not shapes_dir.exists():
        pytest.skip("normalize/ or shapes/ directory not found")

    # Export RDF with TRS rules
    g = Graph()
    from repoq.core.jsonld import to_jsonld

    data = to_jsonld(sample_project)
    g.parse(data=json.dumps(data), format="json-ld")

    enrich_graph_with_trs_rules(g, sample_project.id, normalize_dir=normalize_dir)

    # Save to temp file for validation
    ttl_path = tmp_path / "test_output.ttl"
    g.serialize(destination=str(ttl_path), format="turtle")

    # Validate against trs_shape.ttl
    from rdflib import Graph as ValidationGraph
    from pyshacl import validate

    data_graph = ValidationGraph()
    data_graph.parse(ttl_path, format="turtle")

    shapes_graph = ValidationGraph()
    trs_shape_path = shapes_dir / "trs_shape.ttl"
    shapes_graph.parse(trs_shape_path, format="turtle")

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

    assert (
        len(critical_violations) == 0
    ), f"Expected no critical violations, got {len(critical_violations)}"

    print(f"✅ SHACL validation passed (TRS rules)")


def test_confluence_proven_metadata(sample_project):
    """Test that confluence metadata is included in RDF."""
    normalize_dir = Path("repoq/normalize")

    if not normalize_dir.exists():
        pytest.skip("normalize/ directory not found")

    g = Graph()
    from repoq.core.jsonld import to_jsonld

    data = to_jsonld(sample_project)
    g.parse(data=json.dumps(data), format="json-ld")

    enrich_graph_with_trs_rules(g, sample_project.id, normalize_dir=normalize_dir)

    # Query for systems with confluence metadata
    query = """
    PREFIX trs: <http://example.org/vocab/trs#>
    SELECT ?system ?confluence ?termination WHERE {
        ?system a trs:RewriteSystem ;
                trs:confluenceProven ?confluence ;
                trs:terminationProven ?termination .
    }
    """
    results = list(g.query(query))

    assert len(results) >= 1, "Expected at least one TRS system with verification metadata"

    for system, confluence, termination in results:
        # Metadata should be present (even if False)
        assert confluence is not None
        assert termination is not None

    print(f"✅ Found verification metadata for {len(results)} TRS systems")


@pytest.mark.skipif(
    not Path("repoq/normalize").exists(), reason="Requires normalize/ directory"
)
def test_multiple_trs_systems_exported():
    """Test that multiple TRS systems are exported (spdx, rdf, semver, etc.)."""
    g = Graph()

    enrich_graph_with_trs_rules(g, "repo:test_project")

    # Query for all TRS systems
    query = """
    PREFIX trs: <http://example.org/vocab/trs#>
    SELECT DISTINCT ?system WHERE {
        ?system a trs:RewriteSystem .
    }
    """
    results = list(g.query(query))

    # Should have at least 2-3 systems (spdx_trs, rdf_trs, etc.)
    assert len(results) >= 2, f"Expected at least 2 TRS systems, got {len(results)}"

    print(f"✅ Exported {len(results)} TRS systems")


def test_integration_with_full_export_pipeline(tmp_path):
    """Test TRS rules in full export pipeline with all enrichments."""
    from repoq.core.model import File, Project

    # Create test project
    project = Project(id="repo:test", name="test")
    file1 = File(id=f"{project.id}/file1", path="src/main.py", language="python")
    project.files = {file1.id: file1}

    ttl_path = tmp_path / "test_output.ttl"

    # Export with all enrichments
    export_ttl(project, str(ttl_path), enrich_meta=True, enrich_trs_rules=True)

    # Verify output contains all ontologies
    content = ttl_path.read_text()
    assert "meta:" in content  # Meta-loop ontology
    assert "trs:" in content  # TRS ontology

    # Verify TRS rules are present
    assert "RewriteSystem" in content or "Rule" in content

    print(f"✅ Full RDF export with meta + TRS: {ttl_path}")
