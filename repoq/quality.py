"""Quality metrics aggregation for Quality Gate MVP.

This module implements the Q-metric aggregator:
    Q = 100 - 20×complexity - 30×hotspots - 10×todos

Constraints:
- Q ∈ [0, 100] (bounded)
- Monotonic: ↑complexity ⇒ ↓Q, ↑hotspots ⇒ ↓Q, ↑todos ⇒ ↓Q
- Deterministic: same input → same output

Hard constraints (fail-fast):
- tests_coverage ≥ 80%
- todos_count ≤ 100
- hotspots_count ≤ 20
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from .core.model import Project


@dataclass
class QualityMetrics:
    """Aggregated quality metrics for a project revision.

    Attributes:
        score: Overall quality score Q ∈ [0, 100]
        complexity: Normalized complexity score ∈ [0, 5]
        hotspots: Number of hotspot files (hotness > 0.66)
        todos: Total TODO count across all files
        tests_coverage: Test coverage ratio ∈ [0, 1]
        grade: Letter grade A-F based on score
        constraints_passed: Dict of hard constraint results
    """

    score: float
    complexity: float
    hotspots: int
    todos: int
    tests_coverage: float
    grade: str
    constraints_passed: Dict[str, bool]

    def __post_init__(self) -> None:
        """Validate invariants."""
        assert 0.0 <= self.score <= 100.0, f"Score {self.score} not in [0,100]"
        assert 0.0 <= self.complexity <= 5.0, f"Complexity {self.complexity} not in [0,5]"
        assert self.hotspots >= 0, f"Hotspots {self.hotspots} < 0"
        assert self.todos >= 0, f"TODOs {self.todos} < 0"
        assert 0.0 <= self.tests_coverage <= 1.0, f"Coverage {self.tests_coverage} not in [0,1]"
        assert self.grade in {"A", "B", "C", "D", "E", "F"}, f"Invalid grade {self.grade}"


def compute_quality_score(project: Project) -> QualityMetrics:
    """Compute Q-metric for a project.

    Algorithm:
        1. Normalize complexity: avg(file.complexity) / max(file.complexity) * 5
        2. Count hotspots: files with hotness > 0.66
        3. Count TODOs: sum(file.issues with type TodoComment)
        4. Compute Q = 100 - 20×complexity - 30×(hotspots/20) - 10×(todos/10)
        5. Check hard constraints

    Args:
        project: Project model with files and analysis results

    Returns:
        QualityMetrics with score, components, and constraint status

    Example:
        >>> from repoq.core.model import Project, File
        >>> p = Project(id="test", files={"f1": File(...)})
        >>> metrics = compute_quality_score(p)
        >>> assert 0 <= metrics.score <= 100
    """
    files = list(project.files.values())

    if not files:
        # Empty project: perfect score
        return QualityMetrics(
            score=100.0,
            complexity=0.0,
            hotspots=0,
            todos=0,
            tests_coverage=1.0,
            grade="A",
            constraints_passed={
                "tests_coverage_ge_80": True,
                "todos_le_100": True,
                "hotspots_le_20": True,
            },
        )

    # 1. Normalize complexity ∈ [0, 5]
    complexities = [f.complexity or 0.0 for f in files]
    max_cplx = max(complexities) if complexities else 1.0
    avg_cplx = sum(complexities) / len(files)
    normalized_complexity = (avg_cplx / max_cplx * 5.0) if max_cplx > 0 else 0.0

    # 2. Count hotspots (hotness > 0.66)
    hotspots_count = sum(1 for f in files if (f.hotness or 0.0) > 0.66)

    # 3. Count TODOs
    todos_count = sum(
        1 for f in files for issue in getattr(f, "issues", []) if "todo" in issue.type.lower()
    )

    # 4. Tests coverage (heuristic: test_files / total_files)
    test_files = sum(1 for f in files if f.test_file)
    tests_coverage = test_files / len(files) if files else 0.0

    # 5. Compute Q = 100 - 20×complexity - 30×hotspots - 10×todos
    #    Normalize hotspots and todos to [0, 1] range
    hotspots_norm = min(1.0, hotspots_count / 20.0)  # Cap at 20
    todos_norm = min(1.0, todos_count / 10.0)  # Cap at 10

    score = 100.0
    score -= 20.0 * (normalized_complexity / 5.0)  # Max penalty 20
    score -= 30.0 * hotspots_norm  # Max penalty 30
    score -= 10.0 * todos_norm  # Max penalty 10

    # Clamp to [0, 100]
    score = max(0.0, min(100.0, score))

    # 6. Grade
    grade = _compute_grade(score)

    # 7. Hard constraints
    constraints = {
        "tests_coverage_ge_80": tests_coverage >= 0.8,
        "todos_le_100": todos_count <= 100,
        "hotspots_le_20": hotspots_count <= 20,
    }

    return QualityMetrics(
        score=score,
        complexity=normalized_complexity,
        hotspots=hotspots_count,
        todos=todos_count,
        tests_coverage=tests_coverage,
        grade=grade,
        constraints_passed=constraints,
    )


def _compute_grade(score: float) -> str:
    """Map score to letter grade.

    Args:
        score: Quality score ∈ [0, 100]

    Returns:
        Letter grade A-F
    """
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    elif score >= 50:
        return "E"
    else:
        return "F"


def compare_metrics(base: QualityMetrics, head: QualityMetrics) -> Dict[str, float]:
    """Compare two QualityMetrics (BASE vs HEAD).

    Args:
        base: Baseline metrics (e.g., from main branch)
        head: Current metrics (e.g., from PR branch)

    Returns:
        Dict with deltas: {"score_delta": ..., "complexity_delta": ..., ...}
        Positive delta = improvement (for score), negative = degradation

    Example:
        >>> base = QualityMetrics(score=85, ...)
        >>> head = QualityMetrics(score=90, ...)
        >>> deltas = compare_metrics(base, head)
        >>> assert deltas["score_delta"] == 5.0  # Improvement
    """
    return {
        "score_delta": head.score - base.score,
        "complexity_delta": head.complexity - base.complexity,
        "hotspots_delta": head.hotspots - base.hotspots,
        "todos_delta": head.todos - base.todos,
        "tests_coverage_delta": head.tests_coverage - base.tests_coverage,
        "grade_delta": ord(base.grade) - ord(head.grade),  # Negative = better grade
    }


def calculate_pcq(project: Project, module_type: str = "directory") -> float:
    """Calculate Per-Component Quality (PCQ) with min-aggregation.

    PCQ implements gaming resistance through minimum aggregation:
        PCQ(S) = min_{m∈modules} Q(m)

    This prevents "compensation gaming" where developers hide complexity
    in one module while improving others.

    Args:
        project: Project with modules/files
        module_type: "directory", "layer", or "bounded_context"

    Returns:
        PCQ score ∈ [0, 100], the minimum quality across all modules

    Example:
        >>> pcq = calculate_pcq(project, module_type="directory")
        >>> assert 0 <= pcq <= 100
        >>> # If any module has low quality, PCQ reflects that
    """
    if not project.modules:
        # No modules: use global quality
        metrics = compute_quality_score(project)
        return metrics.score

    # Compute quality for each module
    module_scores = []

    for module_id, module in project.modules.items():
        # Create mini-project for this module
        module_project = Project(
            id=f"{project.id}/{module_id}",
            name=module.name,
        )

        # Filter files belonging to this module
        module_files = {}
        for file_id, file_obj in project.files.items():
            if file_obj.path.startswith(module.path):
                module_files[file_id] = file_obj

        module_project.files = module_files

        # Compute quality for this module
        if module_files:
            metrics = compute_quality_score(module_project)
            module_scores.append(metrics.score)

    if not module_scores:
        # No modules with files: return perfect score
        return 100.0

    # PCQ = minimum quality across modules (gaming-resistant)
    pcq = min(module_scores)

    return pcq


def generate_pce_witness(
    project: Project,
    target_score: float,
    k: int = 8,
) -> list[dict]:
    """Generate Per-Component Evidence (PCE) k-repair witness.

    PCE provides constructive feedback: which files to improve
    to reach the target quality score.

    Algorithm (greedy):
        1. Compute ΔQ_i = improvement potential for each file i
        2. Sort files by ΔQ_i descending (highest impact first)
        3. Select top-k files
        4. Return witness with file + action + expected Δ score

    Args:
        project: Project to analyze
        target_score: Target quality score (e.g., 80.0)
        k: Maximum number of repair actions (default: 8)

    Returns:
        List of repair actions sorted by impact:
        [{"file": path, "action": description, "delta_q": expected_improvement}]

    Example:
        >>> witness = generate_pce_witness(project, target_score=80.0, k=5)
        >>> # Top 5 files to fix with expected improvement
        >>> for action in witness:
        ...     print(f"{action['file']}: {action['action']} (+{action['delta_q']:.1f})")
    """
    current_metrics = compute_quality_score(project)
    current_score = current_metrics.score

    if current_score >= target_score:
        # Already at target: no repairs needed
        return []

    gap = target_score - current_score

    # Compute improvement potential for each file
    repair_candidates = []

    for file_id, file_obj in project.files.items():
        actions = []

        # Action 1: Reduce complexity
        if (file_obj.complexity or 0) > 10:
            delta_q = (file_obj.complexity - 10) * 0.5  # Heuristic
            actions.append(
                {
                    "file": file_obj.path,
                    "action": f"Reduce complexity from {file_obj.complexity:.1f} to 10",
                    "delta_q": min(delta_q, gap),
                    "priority": "high" if file_obj.complexity > 20 else "medium",
                }
            )

        # Action 2: Resolve TODOs
        todo_count = sum(
            1 for issue in getattr(file_obj, "issues", []) if "todo" in issue.type.lower()
        )
        if todo_count > 0:
            delta_q = todo_count * 0.1  # Heuristic: 0.1 point per TODO
            actions.append(
                {
                    "file": file_obj.path,
                    "action": f"Resolve {todo_count} TODO(s)",
                    "delta_q": min(delta_q, gap),
                    "priority": "low",
                }
            )

        # Action 3: Reduce hotspot (if applicable)
        if (file_obj.hotness or 0) > 0.66:
            delta_q = 1.5  # Heuristic: 1.5 points per hotspot resolved
            actions.append(
                {
                    "file": file_obj.path,
                    "action": f"Refactor hotspot (hotness={file_obj.hotness:.2f})",
                    "delta_q": min(delta_q, gap),
                    "priority": "high",
                }
            )

        repair_candidates.extend(actions)

    # Sort by delta_q descending (highest impact first)
    repair_candidates.sort(key=lambda x: x["delta_q"], reverse=True)

    # Select top-k actions
    witness = repair_candidates[:k]

    return witness
