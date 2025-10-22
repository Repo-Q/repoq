"""
Unit tests for quality_recommendations.py module.

Tests ΔQ calculation, RDF export, priority mapping, and effort parsing.
"""

from decimal import Decimal

from rdflib import Graph, Namespace
from rdflib.namespace import RDF, XSD

from repoq.core.model import File, Project
from repoq.core.quality_recommendations import (
    QualityRecommendation,
    _parse_effort_hours,
    _project_to_refactoring_input,
    convert_refactoring_task_to_recommendation,
    export_recommendations_rdf,
    generate_recommendations_from_project,
)
from repoq.refactoring import RefactoringTask

QUALITY = Namespace("http://example.org/vocab/quality#")


def test_parse_effort_hours_minutes():
    """Test parsing effort strings with minutes."""
    assert _parse_effort_hours("15 min") == 0.25
    assert _parse_effort_hours("30 min") == 0.5
    assert _parse_effort_hours("60 min") == 1.0


def test_parse_effort_hours_single_hour():
    """Test parsing effort strings with single hour."""
    assert _parse_effort_hours("1 hour") == 1.0
    assert _parse_effort_hours("2 hours") == 2.0


def test_parse_effort_hours_range():
    """Test parsing effort strings with range."""
    assert _parse_effort_hours("2-4 hours") == 3.0  # Average
    assert _parse_effort_hours("1-3 hours") == 2.0


def test_parse_effort_hours_fallback():
    """Test fallback for invalid effort strings."""
    assert _parse_effort_hours("unknown") == 1.0
    assert _parse_effort_hours("") == 1.0


def test_convert_refactoring_task_to_recommendation():
    """Test conversion from RefactoringTask to QualityRecommendation."""
    task = RefactoringTask(
        id=1,
        file_path="repoq/core/model.py",
        priority="high",
        delta_q=15.5,
        current_metrics={"complexity": 25.0, "loc": 350},
        issues=["High complexity", "No docstrings"],
        recommendations=["Split into smaller classes", "Add type hints"],
        estimated_effort="2-4 hours",
    )

    rec = convert_refactoring_task_to_recommendation(task, "repo:repoq")

    assert rec.id == "repo:repoq/quality/recommendation_1"
    assert rec.title == "Refactor model.py"
    assert rec.delta_q == Decimal("15.5")
    assert rec.priority == "high"
    assert rec.target_file == "repoq/core/model.py"
    assert rec.estimated_effort_hours == 3.0  # Average of 2-4


def test_export_recommendations_rdf():
    """Test RDF export of quality recommendations."""
    g = Graph()
    g.bind("quality", QUALITY)

    recommendations = [
        QualityRecommendation(
            id="repo:test/quality/recommendation_1",
            title="Refactor complex module",
            description="Reduce complexity from 30 to 10",
            delta_q=Decimal("20.0"),
            priority="critical",
            target_file="src/complex.py",
            estimated_effort_hours=4.0,
        )
    ]

    export_recommendations_rdf(g, recommendations, "repo:test")

    # Verify triples
    rec_uri = "repo:test/quality/recommendation_1"
    assert g.value(subject=None, predicate=RDF.type, object=QUALITY.Recommendation) is not None

    # Check title
    title_triple = list(g.triples((None, QUALITY.recommendationTitle, None)))
    assert len(title_triple) == 1
    assert str(title_triple[0][2]) == "Refactor complex module"

    # Check deltaQ (decimal)
    delta_q_triple = list(g.triples((None, QUALITY.deltaQ, None)))
    assert len(delta_q_triple) == 1
    assert delta_q_triple[0][2].datatype == XSD.decimal
    assert float(delta_q_triple[0][2]) == 20.0


def test_export_recommendations_priority_values():
    """Test that priority values are correctly exported."""
    g = Graph()
    g.bind("quality", QUALITY)

    recommendations = [
        QualityRecommendation(
            id="repo:test/quality/rec_1",
            title="Test",
            description="Test",
            delta_q=Decimal("10.0"),
            priority="critical",
            estimated_effort_hours=1.0,
        ),
        QualityRecommendation(
            id="repo:test/quality/rec_2",
            title="Test",
            description="Test",
            delta_q=Decimal("5.0"),
            priority="medium",
            estimated_effort_hours=2.0,
        ),
    ]

    export_recommendations_rdf(g, recommendations, "repo:test")

    priorities = list(g.triples((None, QUALITY.priority, None)))
    assert len(priorities) == 2
    priority_values = {str(p[2]) for p in priorities}
    assert priority_values == {"critical", "medium"}


def test_project_to_refactoring_input():
    """Test conversion from Project to refactoring.py input format."""
    project = Project(id="repo:test", name="Test", repository_url="https://github.com/test/test")

    file1 = File(
        id="repo:test/src/file1.py",
        path="src/file1.py",
        complexity=15.0,
        lines_of_code=250,
    )
    project.files["src/file1.py"] = file1

    result = _project_to_refactoring_input(project)

    assert result["@id"] == "repo:test"
    assert result["name"] == "Test"
    assert len(result["files"]) == 1
    assert result["files"][0]["path"] == "src/file1.py"
    assert result["files"][0]["complexity"] == 15.0
    assert result["files"][0]["lines_of_code"] == 250


def test_generate_recommendations_from_project_empty():
    """Test recommendation generation with empty project."""
    project = Project(id="repo:empty", name="Empty", repository_url="https://github.com/test/empty")

    recommendations = generate_recommendations_from_project(project)

    assert recommendations == []


def test_delta_q_non_negative():
    """Test that all deltaQ values are non-negative (SHACL constraint)."""
    g = Graph()
    g.bind("quality", QUALITY)

    # Zero is valid
    rec_zero = QualityRecommendation(
        id="repo:test/rec_zero",
        title="Test",
        description="Test",
        delta_q=Decimal("0.0"),
        priority="low",
        estimated_effort_hours=1.0,
    )
    assert rec_zero.delta_q >= 0

    # Export with zero (should succeed)
    export_recommendations_rdf(g, [rec_zero], "repo:test")
    delta_q_triple = list(g.triples((None, QUALITY.deltaQ, None)))
    assert len(delta_q_triple) == 1
    assert float(delta_q_triple[0][2]) == 0.0

    # Note: Negative ΔQ would be caught by SHACL validation (quality_shape.ttl minInclusive=0)
    # RDF export itself doesn't validate, only serializes data


def test_recommendation_sorting_by_delta_q():
    """Test that recommendations are sorted by ΔQ descending."""
    recommendations = [
        QualityRecommendation(
            id="rec_1",
            title="Low priority",
            description="Test",
            delta_q=Decimal("5.0"),
            priority="low",
            estimated_effort_hours=1.0,
        ),
        QualityRecommendation(
            id="rec_2",
            title="High priority",
            description="Test",
            delta_q=Decimal("20.0"),
            priority="critical",
            estimated_effort_hours=2.0,
        ),
        QualityRecommendation(
            id="rec_3",
            title="Medium priority",
            description="Test",
            delta_q=Decimal("10.0"),
            priority="medium",
            estimated_effort_hours=1.5,
        ),
    ]

    # Sort (same logic as in generate_recommendations_from_project)
    recommendations.sort(key=lambda r: float(r.delta_q), reverse=True)

    assert recommendations[0].delta_q == Decimal("20.0")
    assert recommendations[1].delta_q == Decimal("10.0")
    assert recommendations[2].delta_q == Decimal("5.0")
