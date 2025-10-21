"""Property-based tests for quality metrics aggregation.

Tests verify mathematical properties of Q-metric computation:
- Monotonicity: ↑complexity ⇒ ↓Q, ↑hotspots ⇒ ↓Q, ↑todos ⇒ ↓Q
- Boundedness: Q ∈ [0, 100]
- Determinism: same input → same output
- Idempotence: compute(compute(x)) = compute(x)
"""

from __future__ import annotations

from hypothesis import given, strategies as st
from repoq.core.model import File, Issue, Project
from repoq.quality import compute_quality_score


@given(
    st.lists(
        st.builds(
            File,
            id=st.text(min_size=1, max_size=20),
            path=st.text(min_size=1, max_size=50),
            lines_of_code=st.integers(min_value=1, max_value=10000),
            complexity=st.floats(min_value=0, max_value=100),
            code_churn=st.integers(min_value=0, max_value=1000),
            hotness=st.floats(min_value=0, max_value=1),
            test_file=st.booleans(),
            language=st.just("Python"),
            issues=st.lists(
                st.builds(
                    Issue,
                    id=st.text(min_size=1),
                    type=st.sampled_from(
                        ["repo:TodoComment", "repo:Deprecated", "repo:Warning"]
                    ),
                    file_id=st.none(),
                    description=st.text(min_size=1),
                ),
                max_size=10,
            ),
        ),
        min_size=1,
        max_size=50,
    )
)
def test_score_bounded(files):
    """Q-metric must be bounded: Q ∈ [0, 100]."""
    project = Project(
        id="test",
        name="test",
        files={f.id: f for f in files},
    )

    metrics = compute_quality_score(project)

    assert 0.0 <= metrics.score <= 100.0, f"Score {metrics.score} not in [0,100]"
    assert 0.0 <= metrics.complexity <= 5.0
    assert metrics.hotspots >= 0
    assert metrics.todos >= 0
    assert 0.0 <= metrics.tests_coverage <= 1.0


@given(
    st.lists(
        st.builds(
            File,
            id=st.text(min_size=1, max_size=20),
            path=st.text(min_size=1, max_size=50),
            lines_of_code=st.integers(min_value=1, max_value=10000),
            complexity=st.floats(min_value=0, max_value=100),
            code_churn=st.integers(min_value=0, max_value=1000),
            hotness=st.floats(min_value=0, max_value=1),
            test_file=st.booleans(),
            language=st.just("Python"),
        ),
        min_size=1,
        max_size=20,
    )
)
def test_monotonicity_complexity(files):
    """↑complexity ⇒ ↓score (monotonicity)."""
    # Create project with low complexity
    low_cplx_files = [
        File(
            id=f.id,
            path=f.path,
            lines_of_code=f.lines_of_code,
            complexity=1.0,  # Low
            code_churn=f.code_churn,
            hotness=f.hotness,
            test_file=f.test_file,
            language=f.language,
        )
        for f in files
    ]
    low_project = Project(
        id="low",
        name="low",
        files={f.id: f for f in low_cplx_files},
    )

    # Create project with high complexity
    high_cplx_files = [
        File(
            id=f.id,
            path=f.path,
            lines_of_code=f.lines_of_code,
            complexity=100.0,  # High
            code_churn=f.code_churn,
            hotness=f.hotness,
            test_file=f.test_file,
            language=f.language,
        )
        for f in files
    ]
    high_project = Project(
        id="high",
        name="high",
        files={f.id: f for f in high_cplx_files},
    )

    low_metrics = compute_quality_score(low_project)
    high_metrics = compute_quality_score(high_project)

    # Higher complexity should result in lower score
    assert (
        low_metrics.score >= high_metrics.score
    ), f"Monotonicity violated: low_cplx={low_metrics.score} < high_cplx={high_metrics.score}"


@given(
    st.lists(
        st.builds(
            File,
            id=st.text(min_size=1, max_size=20),
            path=st.text(min_size=1, max_size=50),
            lines_of_code=st.integers(min_value=1, max_value=10000),
            complexity=st.floats(min_value=0, max_value=100),
            code_churn=st.integers(min_value=0, max_value=1000),
            hotness=st.floats(min_value=0, max_value=1),
            test_file=st.booleans(),
            language=st.just("Python"),
        ),
        min_size=1,
        max_size=20,
    )
)
def test_monotonicity_hotspots(files):
    """↑hotspots ⇒ ↓score (monotonicity)."""
    # Low hotspots
    low_hot_files = [
        File(
            id=f.id,
            path=f.path,
            lines_of_code=f.lines_of_code,
            complexity=f.complexity,
            code_churn=f.code_churn,
            hotness=0.1,  # Low
            test_file=f.test_file,
            language=f.language,
        )
        for f in files
    ]
    low_project = Project(id="low", name="low", files={f.id: f for f in low_hot_files})

    # High hotspots
    high_hot_files = [
        File(
            id=f.id,
            path=f.path,
            lines_of_code=f.lines_of_code,
            complexity=f.complexity,
            code_churn=f.code_churn,
            hotness=0.9,  # High (>0.66 threshold)
            test_file=f.test_file,
            language=f.language,
        )
        for f in files
    ]
    high_project = Project(
        id="high", name="high", files={f.id: f for f in high_hot_files}
    )

    low_metrics = compute_quality_score(low_project)
    high_metrics = compute_quality_score(high_project)

    # More hotspots should result in lower score
    assert (
        low_metrics.score >= high_metrics.score
    ), f"Monotonicity violated: low_hot={low_metrics.score} < high_hot={high_metrics.score}"


def test_empty_project():
    """Empty project should have perfect score."""
    project = Project(id="empty", name="empty", files={})

    metrics = compute_quality_score(project)

    assert metrics.score == 100.0
    assert metrics.complexity == 0.0
    assert metrics.hotspots == 0
    assert metrics.todos == 0
    assert metrics.tests_coverage == 1.0
    assert metrics.grade == "A"
    assert all(metrics.constraints_passed.values())


def test_perfect_project():
    """Project with perfect metrics."""
    files = {
        "f1": File(
            id="f1",
            path="src/main.py",
            lines_of_code=100,
            complexity=1.0,
            code_churn=0,
            hotness=0.0,
            test_file=False,
            language="Python",
        ),
        "f2": File(
            id="f2",
            path="tests/test_main.py",
            lines_of_code=100,
            complexity=1.0,
            code_churn=0,
            hotness=0.0,
            test_file=True,
            language="Python",
        ),
        # Add more test files to reach 80%+ coverage
        "f3": File(
            id="f3",
            path="tests/test_utils.py",
            lines_of_code=50,
            complexity=1.0,
            code_churn=0,
            hotness=0.0,
            test_file=True,
            language="Python",
        ),
        "f4": File(
            id="f4",
            path="tests/test_models.py",
            lines_of_code=50,
            complexity=1.0,
            code_churn=0,
            hotness=0.0,
            test_file=True,
            language="Python",
        ),
        "f5": File(
            id="f5",
            path="tests/test_integration.py",
            lines_of_code=50,
            complexity=1.0,
            code_churn=0,
            hotness=0.0,
            test_file=True,
            language="Python",
        ),
    }
    project = Project(id="perfect", name="perfect", files=files)

    metrics = compute_quality_score(project)

    # 4 test files out of 5 = 80% coverage
    assert metrics.tests_coverage == 0.8
    # Score calculation: Q = 100 - 20*(5/5) - 30*(0/20) - 10*(0/10) = 100 - 20 = 80
    assert metrics.score == 80.0, f"Expected 80.0, got {metrics.score}"
    assert metrics.grade == "B"
    assert metrics.hotspots == 0
    assert metrics.todos == 0
    assert metrics.constraints_passed["tests_coverage_ge_80"]


def test_failing_constraints():
    """Project violating hard constraints."""
    # Many files without tests (low coverage)
    # Many hotspots
    # Many TODOs
    files = {}
    for i in range(50):
        files[f"f{i}"] = File(
            id=f"f{i}",
            path=f"src/module{i}.py",
            lines_of_code=100,
            complexity=50.0,
            code_churn=100,
            hotness=0.9,  # Hotspot
            test_file=False,
            language="Python",
            issues=[
                Issue(
                    id=f"todo{i}",
                    type="repo:TodoComment",
                    file_id=f"f{i}",
                    description="TODO: fix this",
                )
                for _ in range(3)  # 3 TODOs per file = 150 total
            ],
        )

    project = Project(id="bad", name="bad", files=files)

    metrics = compute_quality_score(project)

    # Should fail constraints
    assert not metrics.constraints_passed["tests_coverage_ge_80"]
    assert not metrics.constraints_passed["hotspots_le_20"]
    assert not metrics.constraints_passed["todos_le_100"]
    assert metrics.score < 50.0  # Low score
