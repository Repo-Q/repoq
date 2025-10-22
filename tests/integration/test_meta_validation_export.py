"""
Integration tests for meta-loop self-validation.

STRATIFICATION_LEVEL: 2 (testing meta-validation)

This test module operates at level 2:
- Level 0: Base repository (Project model)
- Level 1: Self-validation (perform_self_analysis)
- Level 2: Testing self-validation (this module)

Tests end-to-end workflow: Project → Self-Analysis → RDF → SHACL validation.
"""

import pytest
from pathlib import Path

from repoq.core.model import Project, File
from repoq.core.meta_validation import (
    perform_self_analysis,
    enrich_graph_with_self_analysis,
)
from repoq.core.rdf_export import export_ttl, validate_shapes


@pytest.fixture
def repoq_self_project():
    """Create a mock RepoQ project analyzing itself."""
    project = Project(
        id="repo:repoq",
        name="RepoQ",
        repository_url="https://github.com/Repo-Q/repoq",
        programming_languages={"Python": 1.0},
    )

    # Meta-level files
    file1 = File(
        id="repo:repoq/repoq/core/meta_validation.py",
        path="repoq/core/meta_validation.py",
        complexity=12.0,
        lines_of_code=250,
    )
    file1.stratification_level = 1

    file2 = File(
        id="repo:repoq/repoq/ontologies/meta.ttl",
        path="repoq/ontologies/meta.ttl",
        lines_of_code=252,
    )
    file2.stratification_level = 0

    # Regular analysis file
    file3 = File(
        id="repo:repoq/repoq/analyzers/complexity.py",
        path="repoq/analyzers/complexity.py",
        complexity=8.0,
        lines_of_code=180,
    )

    project.files["repoq/core/meta_validation.py"] = file1
    project.files["repoq/ontologies/meta.ttl"] = file2
    project.files["repoq/analyzers/complexity.py"] = file3

    return project


def test_self_analysis_detects_repoq():
    """Test that self-analysis correctly detects RepoQ analyzing itself."""
    project = Project(
        id="repo:repoq",
        name="RepoQ",
        repository_url="https://github.com/Repo-Q/repoq",
        programming_languages={"Python": 1.0},
    )

    result = perform_self_analysis(project, stratification_level=1)

    assert result.self_reference_detected is True
    assert result.stratification_level == 1
    assert result.read_only_mode is True


def test_self_analysis_safety_checks(repoq_self_project):
    """Test that safety checks validate stratification and dependencies."""
    result = perform_self_analysis(repoq_self_project, stratification_level=1)

    # Should pass safety checks (no circular deps, valid levels)
    assert result.safety_checks_passed is True
    assert len(result.circular_dependencies) == 0


def test_self_analysis_with_circular_dependency():
    """Test detection of circular dependencies in self-analysis."""
    project = Project(
        id="repo:test",
        name="Test",
        repository_url="https://github.com/test/test",
        programming_languages={"Python": 1.0},
    )

    file1 = File(id="repo:test/repoq/a.py", path="repoq/a.py")
    file2 = File(id="repo:test/repoq/b.py", path="repoq/b.py")
    file1.dependencies = ["repoq.b"]
    file2.dependencies = ["repoq.a"]

    project.files["repoq/a.py"] = file1
    project.files["repoq/b.py"] = file2

    result = perform_self_analysis(project, stratification_level=1)

    assert result.safety_checks_passed is False
    assert len(result.circular_dependencies) > 0


def test_export_self_analysis_to_rdf(repoq_self_project, tmp_path):
    """Test RDF export of self-analysis."""
    ttl_path = tmp_path / "self_analysis.ttl"

    export_ttl(
        repoq_self_project,
        str(ttl_path),
        enrich_self_analysis=True,
        stratification_level=1,
        analyzed_commit="abc123",
    )

    assert ttl_path.exists()
    content = ttl_path.read_text()

    # Verify meta:SelfAnalysis triples
    assert "meta:SelfAnalysis" in content
    assert "meta:stratificationLevel" in content
    assert "meta:readOnlyMode" in content
    assert "meta:safetyChecksPassed" in content


def test_enrich_graph_with_self_analysis(repoq_self_project):
    """Test graph enrichment with self-analysis."""
    from rdflib import Graph, Namespace
    from rdflib.namespace import RDF

    g = Graph()
    META = Namespace("http://example.org/vocab/meta#")
    g.bind("meta", META)

    enrich_graph_with_self_analysis(g, repoq_self_project, stratification_level=1)

    # Verify SelfAnalysis node exists
    analyses = list(g.subjects(RDF.type, META.SelfAnalysis))
    assert len(analyses) > 0

    # Verify properties
    analysis_uri = analyses[0]
    level = g.value(analysis_uri, META.stratificationLevel)
    assert level is not None
    assert int(level) == 1


def test_shacl_validation_with_self_analysis(repoq_self_project, tmp_path):
    """Test SHACL validation of self-analysis (meta_shape.ttl constraints)."""
    shapes_dir = Path(__file__).parent.parent.parent / "repoq" / "shapes"

    if not shapes_dir.exists():
        pytest.skip("SHACL shapes directory not found")

    result = validate_shapes(
        repoq_self_project,
        str(shapes_dir),
        enrich_self_analysis=True,
        stratification_level=1,
        analyzed_commit="test123",
    )

    # Check for SHACL violations related to meta:SelfAnalysis
    if not result["conforms"]:
        violations = result.get("violations", [])
        meta_violations = [
            v for v in violations if "meta:SelfAnalysis" in str(v) or "stratification" in str(v).lower()
        ]

        if meta_violations:
            pytest.fail(f"SHACL violations for self-analysis: {meta_violations}")


def test_stratification_level_max_constraint(repoq_self_project):
    """Test that stratification level > 2 is rejected (Russell's guard)."""
    with pytest.raises(ValueError) as exc_info:
        perform_self_analysis(repoq_self_project, stratification_level=3)

    assert "Russell's paradox" in str(exc_info.value)


def test_read_only_mode_always_true(repoq_self_project):
    """Test that self-analysis is always read-only."""
    result = perform_self_analysis(repoq_self_project, stratification_level=1)

    assert result.read_only_mode is True


def test_self_analysis_with_commit_sha(repoq_self_project):
    """Test that commit SHA is tracked in self-analysis."""
    result = perform_self_analysis(repoq_self_project, stratification_level=1, analyzed_commit="deadbeef")

    assert result.analyzed_commit == "deadbeef"


def test_self_analysis_timestamps(repoq_self_project):
    """Test that self-analysis records timestamp."""
    from datetime import datetime, UTC

    before = datetime.now(UTC)
    result = perform_self_analysis(repoq_self_project, stratification_level=1)
    after = datetime.now(UTC)

    assert before <= result.performed_at <= after


def test_stratification_level_0_allowed(repoq_self_project):
    """Test that stratification level 0 (base analysis) is allowed."""
    result = perform_self_analysis(repoq_self_project, stratification_level=0)

    assert result.stratification_level == 0
    assert result.safety_checks_passed is True


def test_stratification_level_2_allowed(repoq_self_project):
    """Test that stratification level 2 (max) is allowed."""
    result = perform_self_analysis(repoq_self_project, stratification_level=2)

    assert result.stratification_level == 2
    assert result.safety_checks_passed is True
