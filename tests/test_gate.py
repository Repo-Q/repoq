"""Integration tests for quality gate command.

Tests the full gate workflow:
1. Create test repository with BASE and HEAD revisions
2. Run gate command
3. Verify metrics, deltas, and constraint checking
"""

import pytest

from repoq.gate import GateResult
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


class TestFormatGateReport:
    """Tests for format_gate_report function (coverage expansion)."""

    def test_format_passed_gate(self):
        """Format report for PASSED gate with all metrics."""
        from repoq.gate import format_gate_report

        base_metrics = QualityMetrics(
            score=85.0,
            grade="B",
            complexity=2.5,
            hotspots=5,
            todos=20,
            tests_coverage=0.75,
            constraints_passed={
                "tests_coverage_ge_80": False,
                "todos_le_100": True,
                "hotspots_le_20": True,
            },
        )
        head_metrics = QualityMetrics(
            score=90.0,
            grade="A",
            complexity=2.0,
            hotspots=3,
            todos=15,
            tests_coverage=0.85,
            constraints_passed={
                "tests_coverage_ge_80": True,
                "todos_le_100": True,
                "hotspots_le_20": True,
            },
        )
        deltas = {
            "score_delta": 5.0,
            "complexity_delta": -0.5,
            "hotspots_delta": -2,
            "todos_delta": -5,
            "tests_coverage_delta": 0.10,
        }
        result = GateResult(
            passed=True,
            base_metrics=base_metrics,
            head_metrics=head_metrics,
            deltas=deltas,
            violations=[],
        )

        report = format_gate_report(result)

        assert "PASS ✓" in report
        assert "Q=85.0 (B)" in report  # BASE
        assert "Q=90.0 (A)" in report  # HEAD
        assert "+5.00" in report  # score delta
        assert "-2" in report  # hotspots delta (negative is good)
        assert "Complexity" in report
        assert "Hotspots" in report
        assert "TODOs" in report
        assert "Coverage" in report

    def test_format_failed_gate_with_violations(self):
        """Format report for FAILED gate with multiple violations."""
        from repoq.gate import format_gate_report

        base_metrics = QualityMetrics(
            score=85.0,
            grade="B",
            complexity=2.0,
            hotspots=10,
            todos=50,
            tests_coverage=0.82,
            constraints_passed={
                "tests_coverage_ge_80": True,
                "todos_le_100": True,
                "hotspots_le_20": True,
            },
        )
        head_metrics = QualityMetrics(
            score=70.0,
            grade="C",
            complexity=3.5,
            hotspots=25,
            todos=120,
            tests_coverage=0.75,
            constraints_passed={
                "tests_coverage_ge_80": False,
                "todos_le_100": False,
                "hotspots_le_20": False,
            },
        )
        deltas = {
            "score_delta": -15.0,
            "complexity_delta": 1.5,
            "hotspots_delta": 15,
            "todos_delta": 70,
            "tests_coverage_delta": -0.07,
        }
        result = GateResult(
            passed=False,
            base_metrics=base_metrics,
            head_metrics=head_metrics,
            deltas=deltas,
            violations=[
                "Tests coverage 75.0% < 80% (required)",
                "TODOs count 120 > 100 (max allowed)",
                "Hotspots count 25 > 20 (max allowed)",
                "Quality score degraded by 15.0 points (max -5.0)",
            ],
        )

        report = format_gate_report(result)

        assert "FAIL ✗" in report
        assert "Q=70.0 (C)" in report  # HEAD (degraded)
        assert "Constraint Violations" in report
        assert "Tests coverage 75.0% < 80%" in report
        assert "TODOs count 120 > 100" in report
        assert "Hotspots count 25 > 20" in report
        assert "Quality score degraded by 15.0 points" in report

    def test_format_report_includes_deltas_section(self):
        """Ensure report includes Deltas section with all metrics."""
        from repoq.gate import format_gate_report

        base_metrics = QualityMetrics(
            score=80.0,
            grade="B",
            complexity=2.5,
            hotspots=8,
            todos=30,
            tests_coverage=0.85,
            constraints_passed={
                "tests_coverage_ge_80": True,
                "todos_le_100": True,
                "hotspots_le_20": True,
            },
        )
        head_metrics = QualityMetrics(
            score=82.0,
            grade="B",
            complexity=2.7,
            hotspots=9,
            todos=32,
            tests_coverage=0.87,
            constraints_passed={
                "tests_coverage_ge_80": True,
                "todos_le_100": True,
                "hotspots_le_20": True,
            },
        )
        deltas = {
            "score_delta": 2.0,
            "complexity_delta": 0.2,
            "hotspots_delta": 1,
            "todos_delta": 2,
            "tests_coverage_delta": 0.02,
        }
        result = GateResult(
            passed=True,
            base_metrics=base_metrics,
            head_metrics=head_metrics,
            deltas=deltas,
            violations=[],
        )

        report = format_gate_report(result)

        assert "Deltas (HEAD - BASE)" in report
        assert "+2.00" in report  # score delta
        assert "+0.20" in report  # complexity delta
        assert "+1" in report  # hotspots delta
        assert "+2" in report  # todos delta (appears multiple times, but at least once in deltas)
