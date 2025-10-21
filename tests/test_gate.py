"""Integration tests for quality gate command.

Tests the full gate workflow:
1. Create test repository with BASE and HEAD revisions
2. Run gate command
3. Verify metrics, deltas, and constraint checking
"""

import tempfile
from pathlib import Path

import pytest

from repoq.core.model import File, Issue, Project
from repoq.gate import GateResult, run_quality_gate
from repoq.quality import QualityMetrics


def test_gate_result_dataclass():
    """GateResult should properly store gate execution results."""
    base_metrics = QualityMetrics(
        score=85.0,
        complexity=2.0,
        hotspots=5,
        todos=20,
        tests_coverage=0.8,
        grade="B",
        constraints_passed={
            "tests_coverage_ge_80": True,
            "todos_le_100": True,
            "hotspots_le_20": True,
        },
    )

    head_metrics = QualityMetrics(
        score=90.0,
        complexity=1.5,
        hotspots=3,
        todos=10,
        tests_coverage=0.9,
        grade="A",
        constraints_passed={
            "tests_coverage_ge_80": True,
            "todos_le_100": True,
            "hotspots_le_20": True,
        },
    )

    result = GateResult(
        passed=True,
        base_metrics=base_metrics,
        head_metrics=head_metrics,
        deltas={
            "score_delta": 5.0,
            "complexity_delta": -0.5,
            "hotspots_delta": -2,
            "todos_delta": -10,
            "tests_coverage_delta": 0.1,
        },
        violations=[],
    )

    assert result.passed
    assert result.base_metrics.score == 85.0
    assert result.head_metrics.score == 90.0
    assert result.deltas["score_delta"] == 5.0
    assert len(result.violations) == 0


def test_quality_metrics_validation():
    """QualityMetrics should validate invariants in __post_init__."""
    # Valid metrics
    metrics = QualityMetrics(
        score=85.0,
        complexity=2.0,
        hotspots=5,
        todos=20,
        tests_coverage=0.8,
        grade="B",
        constraints_passed={"test": True},
    )
    assert metrics.score == 85.0

    # Invalid score (out of bounds)
    with pytest.raises(AssertionError, match="Score.*not in"):
        QualityMetrics(
            score=150.0,  # > 100
            complexity=2.0,
            hotspots=5,
            todos=20,
            tests_coverage=0.8,
            grade="B",
            constraints_passed={"test": True},
        )

    # Invalid complexity
    with pytest.raises(AssertionError, match="Complexity.*not in"):
        QualityMetrics(
            score=85.0,
            complexity=10.0,  # > 5
            hotspots=5,
            todos=20,
            tests_coverage=0.8,
            grade="B",
            constraints_passed={"test": True},
        )

    # Invalid grade
    with pytest.raises(AssertionError, match="Invalid grade"):
        QualityMetrics(
            score=85.0,
            complexity=2.0,
            hotspots=5,
            todos=20,
            tests_coverage=0.8,
            grade="Z",  # Invalid
            constraints_passed={"test": True},
        )


# Note: Full integration test requires Git repository setup
# This would be added in a separate test file with pytest fixtures
# for creating temporary Git repos with different revisions.
#
# Example structure:
# @pytest.fixture
# def test_repo(tmp_path):
#     """Create test Git repository with BASE and HEAD commits."""
#     repo_path = tmp_path / "test_repo"
#     repo_path.mkdir()
#     # Initialize git, create commits, etc.
#     return repo_path
#
# def test_gate_integration(test_repo):
#     """Full integration test of quality gate."""
#     result = run_quality_gate(test_repo, "HEAD~1", "HEAD")
#     assert isinstance(result, GateResult)
