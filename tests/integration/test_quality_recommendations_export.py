"""
Integration tests for quality recommendations RDF export.

Tests end-to-end workflow: Project → Recommendations → RDF → SHACL validation.
"""

from decimal import Decimal
from pathlib import Path

import pytest

from repoq.core.model import File, Project
from repoq.core.quality_recommendations import (
    enrich_graph_with_quality_recommendations,
    generate_recommendations_from_project,
)
from repoq.core.rdf_export import export_ttl, validate_shapes


@pytest.fixture
def sample_project():
    """Create a sample project with complexity/hotspot issues."""
    project = Project(
        id="repo:sample",
        name="Sample Project",
        repository_url="https://github.com/test/sample",
        programming_languages={"Python": 1.0},
    )

    # File with high complexity (should trigger recommendation)
    file1 = File(
        id="repo:sample/src/complex.py",
        path="src/complex.py",
        complexity=35.0,  # High complexity
        lines_of_code=500,
    )

    # File with moderate complexity
    file2 = File(
        id="repo:sample/src/moderate.py",
        path="src/moderate.py",
        complexity=12.0,
        lines_of_code=180,
    )

    # Low complexity file (should not trigger recommendation)
    file3 = File(
        id="repo:sample/src/simple.py",
        path="src/simple.py",
        complexity=3.0,
        lines_of_code=50,
    )

    project.files["src/complex.py"] = file1
    project.files["src/moderate.py"] = file2
    project.files["src/simple.py"] = file3

    return project


def test_generate_recommendations_integration(sample_project):
    """Test recommendation generation from project with quality issues."""
    recommendations = generate_recommendations_from_project(
        sample_project, top_k=10, min_delta_q=3.0
    )

    assert len(recommendations) > 0
    assert all(rec.delta_q >= Decimal("3.0") for rec in recommendations)

    # Verify sorted by ΔQ descending
    delta_q_values = [float(rec.delta_q) for rec in recommendations]
    assert delta_q_values == sorted(delta_q_values, reverse=True)

    # Verify high-complexity file is prioritized
    top_rec = recommendations[0]
    assert "complex.py" in top_rec.target_file


def test_export_recommendations_to_rdf(sample_project, tmp_path):
    """Test RDF export of quality recommendations."""
    ttl_path = tmp_path / "recommendations.ttl"

    export_ttl(
        sample_project,
        str(ttl_path),
        enrich_quality_recommendations=True,
        top_k_recommendations=5,
        min_delta_q=2.0,
    )

    assert ttl_path.exists()
    content = ttl_path.read_text()

    # Verify recommendation triples exist
    assert "quality:Recommendation" in content
    assert "quality:deltaQ" in content
    assert "quality:priority" in content
    assert "quality:recommendationTitle" in content


def test_enrich_graph_with_recommendations(sample_project):
    """Test graph enrichment with recommendations."""
    from rdflib import Graph, Namespace
    from rdflib.namespace import RDF

    g = Graph()
    QUALITY = Namespace("http://example.org/vocab/quality#")
    g.bind("quality", QUALITY)

    enrich_graph_with_quality_recommendations(g, sample_project, top_k=3, min_delta_q=5.0)

    # Verify Recommendation nodes exist
    recommendations = list(g.subjects(RDF.type, QUALITY.Recommendation))
    assert len(recommendations) > 0

    # Verify deltaQ properties exist and are non-negative
    for rec_uri in recommendations:
        delta_q = g.value(rec_uri, QUALITY.deltaQ)
        assert delta_q is not None
        assert float(delta_q) >= 0.0


def test_shacl_validation_with_recommendations(sample_project, tmp_path):
    """Test SHACL validation of recommendations (quality_shape.ttl constraints)."""
    shapes_dir = Path(__file__).parent.parent.parent / "repoq" / "shapes"

    if not shapes_dir.exists():
        pytest.skip("SHACL shapes directory not found")

    result = validate_shapes(
        sample_project,
        str(shapes_dir),
        enrich_quality_recommendations=True,
        top_k_recommendations=5,
        min_delta_q=1.0,
    )

    # Check for SHACL violations related to quality:Recommendation
    if not result["conforms"]:
        violations = result.get("violations", [])
        quality_violations = [
            v for v in violations if "quality:Recommendation" in str(v) or "deltaQ" in str(v)
        ]

        if quality_violations:
            pytest.fail(f"SHACL violations for recommendations: {quality_violations}")


def test_top_k_recommendations_limit(sample_project):
    """Test that top_k parameter limits recommendation count."""
    recommendations_k3 = generate_recommendations_from_project(sample_project, top_k=3)
    recommendations_k1 = generate_recommendations_from_project(sample_project, top_k=1)

    assert len(recommendations_k3) <= 3
    assert len(recommendations_k1) <= 1

    # First recommendation in k3 should match recommendation in k1 (highest ΔQ)
    if recommendations_k1 and recommendations_k3:
        assert recommendations_k1[0].id == recommendations_k3[0].id


def test_min_delta_q_threshold(sample_project):
    """Test that min_delta_q filters low-priority recommendations."""
    recommendations_low = generate_recommendations_from_project(
        sample_project, top_k=10, min_delta_q=1.0
    )
    recommendations_high = generate_recommendations_from_project(
        sample_project, top_k=10, min_delta_q=10.0
    )

    # High threshold should filter out more recommendations
    assert len(recommendations_high) <= len(recommendations_low)

    # All high-threshold recommendations should have ΔQ >= 10.0
    for rec in recommendations_high:
        assert rec.delta_q >= Decimal("10.0")


def test_recommendation_properties_completeness(sample_project):
    """Test that all required properties are exported to RDF."""
    from rdflib import Graph, Namespace
    from rdflib.namespace import RDF

    g = Graph()
    QUALITY = Namespace("http://example.org/vocab/quality#")
    g.bind("quality", QUALITY)

    enrich_graph_with_quality_recommendations(g, sample_project, top_k=1, min_delta_q=1.0)

    recommendations = list(g.subjects(RDF.type, QUALITY.Recommendation))
    if not recommendations:
        pytest.skip("No recommendations generated for test project")

    rec_uri = recommendations[0]

    # Check required properties (from quality_shape.ttl)
    required_properties = [
        QUALITY.deltaQ,
        QUALITY.priority,
        QUALITY.recommendationTitle,
        QUALITY.recommendationDescription,
    ]

    for prop in required_properties:
        value = g.value(rec_uri, prop)
        assert value is not None, f"Missing required property: {prop}"


def test_recommendations_link_to_files(sample_project):
    """Test that recommendations link to target files via quality:targetsFile."""
    from rdflib import Graph, Namespace
    from rdflib.namespace import RDF

    g = Graph()
    QUALITY = Namespace("http://example.org/vocab/quality#")
    g.bind("quality", QUALITY)

    enrich_graph_with_quality_recommendations(g, sample_project, top_k=5, min_delta_q=1.0)

    recommendations = list(g.subjects(RDF.type, QUALITY.Recommendation))
    if not recommendations:
        pytest.skip("No recommendations generated")

    # At least one recommendation should link to a file
    files_linked = []
    for rec_uri in recommendations:
        target_file = g.value(rec_uri, QUALITY.targetsFile)
        if target_file:
            files_linked.append(str(target_file))

    assert len(files_linked) > 0, "No recommendations linked to files"

    # Verify file paths are valid
    for file_uri in files_linked:
        assert "src/" in file_uri or "repoq/" in file_uri
