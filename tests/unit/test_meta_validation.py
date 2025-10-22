"""
Unit tests for meta_validation.py module.

Tests self-analysis, circular dependency detection, stratification checks, and RDF export.
"""

import pytest
from datetime import UTC, datetime
from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, XSD

from repoq.core.meta_validation import (
    SelfAnalysisResult,
    detect_circular_dependencies,
    _file_path_to_module,
    check_stratification_consistency,
    detect_universe_violations,
    perform_self_analysis,
    export_self_analysis_rdf,
)
from repoq.core.model import Project, File


META = Namespace("http://example.org/vocab/meta#")


def test_file_path_to_module():
    """Test conversion from file path to Python module name."""
    assert _file_path_to_module("repoq/core/model.py") == "repoq.core.model"
    assert _file_path_to_module("repoq/__init__.py") == "repoq"
    assert _file_path_to_module("tests/test_foo.py") is None  # Skip tests
    assert _file_path_to_module("setup.py") is None  # Skip setup
    assert _file_path_to_module("README.md") is None  # Non-Python


def test_detect_circular_dependencies_none():
    """Test circular dependency detection with no cycles."""
    project = Project(id="repo:test", name="Test", repository_url="https://github.com/test/test")

    file1 = File(id="repo:test/repoq/a.py", path="repoq/a.py")
    file2 = File(id="repo:test/repoq/b.py", path="repoq/b.py")
    file1.dependencies = ["repoq.b"]  # a → b (no cycle)

    project.files["repoq/a.py"] = file1
    project.files["repoq/b.py"] = file2

    cycles = detect_circular_dependencies(project)
    assert cycles == []


def test_detect_circular_dependencies_simple_cycle():
    """Test detection of simple circular dependency (A → B → A)."""
    project = Project(id="repo:test", name="Test", repository_url="https://github.com/test/test")

    file1 = File(id="repo:test/repoq/a.py", path="repoq/a.py")
    file2 = File(id="repo:test/repoq/b.py", path="repoq/b.py")
    file1.dependencies = ["repoq.b"]
    file2.dependencies = ["repoq.a"]

    project.files["repoq/a.py"] = file1
    project.files["repoq/b.py"] = file2

    cycles = detect_circular_dependencies(project)
    assert len(cycles) > 0
    assert "repoq.a" in cycles[0] and "repoq.b" in cycles[0]


def test_check_stratification_consistency_no_violations():
    """Test stratification consistency check with valid levels."""
    project = Project(id="repo:test", name="Test", repository_url="https://github.com/test/test")

    file1 = File(id="repo:test/repoq/meta.py", path="repoq/meta.py")
    file1.stratification_level = 1  # Valid level

    project.files["repoq/meta.py"] = file1

    violations = check_stratification_consistency(project)
    assert len(violations) == 0


def test_check_stratification_consistency_exceeds_max():
    """Test detection of stratification level > 2 (Russell's guard)."""
    project = Project(id="repo:test", name="Test", repository_url="https://github.com/test/test")

    file1 = File(id="repo:test/repoq/meta.py", path="repoq/meta.py")
    file1.stratification_level = 3  # Exceeds max (2)

    project.files["repoq/meta.py"] = file1

    violations = check_stratification_consistency(project)
    assert len(violations) == 1
    assert "stratificationLevel=3" in violations[0]
    assert "Russell's guard" in violations[0]


def test_detect_universe_violations():
    """Test detection of universe/type level violations."""
    project = Project(id="repo:test", name="Test", repository_url="https://github.com/test/test")

    # File that manages same concept it defines (potential universe collision)
    file1 = File(id="repo:test/repoq/ontology_manager.py", path="repoq/ontology_manager.py")
    project.files["repoq/ontology_manager.py"] = file1

    violations = detect_universe_violations(project)
    assert len(violations) > 0
    assert "universe collision" in violations[0].lower()


def test_perform_self_analysis_non_self():
    """Test self-analysis on non-RepoQ project (not self-referential)."""
    project = Project(id="repo:other", name="Other Project", repository_url="https://github.com/test/other")

    result = perform_self_analysis(project, stratification_level=1)

    assert result.project_id == "repo:other"
    assert result.stratification_level == 1
    assert result.read_only_mode is True
    assert result.self_reference_detected is False
    assert isinstance(result.performed_at, datetime)


def test_perform_self_analysis_self_referential():
    """Test self-analysis on RepoQ project (self-referential)."""
    project = Project(id="repo:repoq", name="RepoQ", repository_url="https://github.com/Repo-Q/repoq")

    result = perform_self_analysis(project, stratification_level=1)

    assert result.self_reference_detected is True  # "repoq" in name/id
    assert result.read_only_mode is True  # Always true


def test_perform_self_analysis_stratification_guard():
    """Test that stratification level > 2 raises ValueError (Russell's guard)."""
    project = Project(id="repo:test", name="Test", repository_url="https://github.com/test/test")

    with pytest.raises(ValueError) as exc_info:
        perform_self_analysis(project, stratification_level=3)

    assert "Russell's paradox" in str(exc_info.value)


def test_export_self_analysis_rdf():
    """Test RDF export of self-analysis result."""
    g = Graph()
    g.bind("meta", META)

    result = SelfAnalysisResult(
        project_id="repo:test",
        stratification_level=1,
        read_only_mode=True,
        self_reference_detected=False,
        circular_dependencies=[],
        universe_violations=[],
        safety_checks_passed=True,
        performed_at=datetime.now(UTC),
    )

    export_self_analysis_rdf(g, result)

    # Verify triples
    analysis_triples = list(g.triples((None, RDF.type, META.SelfAnalysis)))
    assert len(analysis_triples) == 1

    analysis_uri = analysis_triples[0][0]

    # Check stratificationLevel
    level = g.value(analysis_uri, META.stratificationLevel)
    assert level is not None
    assert int(level) == 1

    # Check readOnlyMode
    read_only = g.value(analysis_uri, META.readOnlyMode)
    assert read_only is not None
    assert bool(read_only) is True

    # Check safetyChecksPassed
    safety = g.value(analysis_uri, META.safetyChecksPassed)
    assert safety is not None
    assert bool(safety) is True


def test_export_self_analysis_with_violations():
    """Test RDF export with circular dependencies and violations."""
    g = Graph()
    g.bind("meta", META)

    result = SelfAnalysisResult(
        project_id="repo:test",
        stratification_level=1,
        read_only_mode=True,
        self_reference_detected=True,
        circular_dependencies=["repoq.a → repoq.b → repoq.a"],
        universe_violations=["File meta.py has stratificationLevel=3 (max: 2)"],
        safety_checks_passed=False,
        performed_at=datetime.now(UTC),
    )

    export_self_analysis_rdf(g, result)

    analysis_uri = list(g.subjects(RDF.type, META.SelfAnalysis))[0]

    # Check violations exported
    violations = list(g.objects(analysis_uri, META.universeViolation))
    assert len(violations) == 2  # 1 circular + 1 stratification
    assert any("Circular dependency" in str(v) for v in violations)
    assert any("stratificationLevel=3" in str(v) for v in violations)

    # Check safety status
    safety = g.value(analysis_uri, META.safetyChecksPassed)
    assert bool(safety) is False


def test_export_self_analysis_with_commit_sha():
    """Test RDF export includes commit SHA when provided."""
    g = Graph()
    g.bind("meta", META)

    result = SelfAnalysisResult(
        project_id="repo:test",
        stratification_level=1,
        read_only_mode=True,
        self_reference_detected=False,
        circular_dependencies=[],
        universe_violations=[],
        safety_checks_passed=True,
        performed_at=datetime.now(UTC),
        analyzed_commit="abc123def456",
    )

    export_self_analysis_rdf(g, result)

    analysis_uri = list(g.subjects(RDF.type, META.SelfAnalysis))[0]
    commit = g.value(analysis_uri, META.analyzedCommit)
    assert commit is not None
    assert str(commit) == "abc123def456"
