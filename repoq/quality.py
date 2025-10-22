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


def _compute_complexity_metric(files: list) -> float:
    """Compute normalized complexity metric ∈ [0, 5].

    Args:
        files: List of File objects

    Returns:
        Normalized complexity score
    """
    complexities = [f.complexity or 0.0 for f in files]
    max_cplx = max(complexities) if complexities else 1.0
    avg_cplx = sum(complexities) / len(files)
    return (avg_cplx / max_cplx * 5.0) if max_cplx > 0 else 0.0


def _count_quality_issues(project: Project) -> tuple[int, int]:
    """Count hotspots and TODOs across all files.

    Args:
        project: Project with files and issues

    Returns:
        Tuple of (hotspots_count, todos_count)
    """
    files = list(project.files.values())
    hotspots_count = sum(1 for f in files if (f.hotness or 0.0) > 0.66)

    # Project.issues is Dict[str, Issue], not List[Issue]
    issues_by_id = project.issues if project.issues else {}

    # Count TODOs by checking issue types
    todos_count = 0
    for f in files:
        for issue_id in getattr(f, "issues", []):
            issue = issues_by_id.get(issue_id)
            if issue and "todo" in issue.type.lower():
                todos_count += 1

    return hotspots_count, todos_count


def _calculate_q_score(
    normalized_complexity: float,
    hotspots_count: int,
    todos_count: int,
) -> float:
    """Calculate Q-score using weighted formula.

    Formula: Q = 100 - 20×complexity - 30×hotspots - 10×todos

    Args:
        normalized_complexity: Complexity metric ∈ [0, 5]
        hotspots_count: Number of hotspot files
        todos_count: Number of TODO items

    Returns:
        Quality score ∈ [0, 100]
    """
    # Normalize hotspots and todos to [0, 1] range
    hotspots_norm = min(1.0, hotspots_count / 20.0)  # Cap at 20
    todos_norm = min(1.0, todos_count / 10.0)  # Cap at 10

    score = 100.0
    score -= 20.0 * (normalized_complexity / 5.0)  # Max penalty 20
    score -= 30.0 * hotspots_norm  # Max penalty 30
    score -= 10.0 * todos_norm  # Max penalty 10

    # Clamp to [0, 100]
    return max(0.0, min(100.0, score))


def _check_quality_constraints(
    tests_coverage: float, todos_count: int, hotspots_count: int
) -> dict[str, bool]:
    """Check hard quality constraints.

    Args:
        tests_coverage: Test coverage ratio
        todos_count: Total TODOs
        hotspots_count: Total hotspots

    Returns:
        Dict of constraint name → passed boolean
    """
    return {
        "tests_coverage_ge_80": tests_coverage >= 0.8,
        "todos_le_100": todos_count <= 100,
        "hotspots_le_20": hotspots_count <= 20,
    }


def _calculate_architecture_adjustment(arch_model) -> float:
    """Calculate architecture quality adjustment for Q-score.

    Bonuses/Penalties:
    - +10 for clean architecture (no layering violations, no circular deps)
    - -5 per layering violation (max -15)
    - -5 per circular dependency (max -10)

    Args:
        arch_model: ArchitectureModel from ArchitectureAnalyzer

    Returns:
        Adjustment value (can be positive or negative)
    """
    adjustment = 0.0

    # Check for clean architecture
    has_violations = len(arch_model.layering_violations) > 0
    has_circular = len(arch_model.circular_dependencies) > 0

    if not has_violations and not has_circular:
        # Bonus for clean architecture
        adjustment += 10.0
    else:
        # Penalties for violations
        # -5 per layering violation (max -15)
        violation_penalty = min(len(arch_model.layering_violations) * 5.0, 15.0)
        adjustment -= violation_penalty

        # -5 per circular dependency (max -10)
        circular_penalty = min(len(arch_model.circular_dependencies) * 5.0, 10.0)
        adjustment -= circular_penalty

    return adjustment


def compute_quality_score(project: Project, arch_model=None) -> QualityMetrics:
    """Compute overall quality score Q for project.

    Algorithm:
        1. Normalize complexity (cyclomatic + maintainability)
        2. Count hotspots (files with hotness > 0.66)
        3. Count TODOs from issues
        4. Calculate Q = 100 - 20×complexity - 30×hotspots - 10×todos
        5. Apply architecture adjustment (+10 bonus or up to -25 penalty)
        6. Check hard constraints (tests ≥ 80%, todos ≤ 100, hotspots ≤ 20)

    Args:
        project: Project model with analysis results
        arch_model: Optional ArchitectureModel with violations/metrics

    Returns:
        QualityMetrics with score, grade, and constraint results
    """
    files = list(project.files.values())

    # 1. Normalize complexity
    normalized_complexity = _compute_complexity_metric(files)

    # 2. Count quality issues
    hotspots_count, todos_count = _count_quality_issues(project)  # Pass project, not files

    # Tests coverage (heuristic: test_files / total_files)
    test_files = sum(1 for f in files if f.test_file)
    tests_coverage = test_files / len(files) if files else 0.0

    # Calculate base Q-score
    score = _calculate_q_score(normalized_complexity, hotspots_count, todos_count)

    # Apply architecture bonuses/penalties (NEW!)
    if arch_model:
        arch_adjustment = _calculate_architecture_adjustment(arch_model)
        score = max(0.0, min(100.0, score + arch_adjustment))

    # Grade and constraints
    grade = _compute_grade(score)
    constraints = _check_quality_constraints(tests_coverage, todos_count, hotspots_count)

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
        complexity = file_obj.complexity or 0.0
        if complexity > 10:
            delta_q = (complexity - 10) * 0.5  # Heuristic
            actions.append(
                {
                    "file": file_obj.path,
                    "action": f"Reduce complexity from {complexity:.1f} to 10",
                    "delta_q": min(delta_q, gap),
                    "priority": "high" if complexity > 20 else "medium",
                }
            )

        # Action 2: Resolve TODOs
        # NOTE: File.issues are string IDs, need to resolve from project.issues
        issues_by_id = project.issues if project.issues else {}
        todo_count = sum(
            1
            for issue_id in getattr(file_obj, "issues", [])
            if (issue := issues_by_id.get(issue_id)) and "todo" in issue.type.lower()
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
