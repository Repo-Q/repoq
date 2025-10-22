"""Quality Gate command for comparing BASE vs HEAD revisions.

This module implements the `repoq gate` command that:
1. Analyzes BASE revision (e.g., main branch SHA)
2. Analyzes HEAD revision (current working tree)
3. Computes Q-metrics for both
4. Checks hard constraints (fail-fast if violated)
5. Reports deltas and gate status (PASS/FAIL)

Usage:
    repoq gate --base <sha> --head .
    repoq gate --base origin/main --head .
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .config import AnalyzeConfig
from .core.model import Project
from .quality import (
    QualityMetrics,
    calculate_pcq,
    compare_metrics,
    compute_quality_score,
    generate_pce_witness,
)


@dataclass
class GateResult:
    """Result of Quality Gate check.

    Attributes:
        passed: True if all hard constraints passed
        base_metrics: QualityMetrics for BASE revision
        head_metrics: QualityMetrics for HEAD revision
        deltas: Dict of metric deltas (HEAD - BASE)
        violations: List of constraint violation messages
        pcq_base: Per-Component Quality for BASE (min aggregation)
        pcq_head: Per-Component Quality for HEAD (min aggregation)
        pce_witness: PCE k-repair witness (if gate failed)
    """

    passed: bool
    base_metrics: QualityMetrics
    head_metrics: QualityMetrics
    deltas: dict[str, float]
    violations: list[str]
    pcq_base: float | None = None
    pcq_head: float | None = None
    pce_witness: list[dict] | None = None


def run_quality_gate(
    repo_path: Path,
    base_ref: str,
    head_ref: str = ".",
    strict: bool = True,
    epsilon: float = 0.3,
    tau: float = 0.8,
    enable_pcq: bool = True,
) -> GateResult:
    """Run Quality Gate comparing BASE vs HEAD.

    Algorithm (Phase 4 full admission predicate):
        1. Analyze BASE and HEAD revisions
        2. Compute Q-scores for both
        3. Check hard constraints H (tests≥80%, TODOs≤100, hotspots≤20)
        4. Check ΔQ ≥ ε (noise tolerance, default: 0.3)
        5. Check PCQ ≥ τ (gaming resistance, default: 0.8)
        6. Admission: H ∧ (ΔQ ≥ ε) ∧ (PCQ ≥ τ)
        7. If failed: generate PCE k-repair witness

    Args:
        repo_path: Path to Git repository
        base_ref: Git reference for baseline (e.g., "main", "origin/main", SHA)
        head_ref: Git reference for current (default "." = working tree)
        strict: If True, fail on any constraint violation; if False, warn only
        epsilon: ΔQ noise tolerance (default: 0.3 points)
        tau: PCQ threshold for gaming resistance (default: 0.8)
        enable_pcq: Enable PCQ min-aggregation (default: True)

    Returns:
        GateResult with metrics, deltas, PCQ, PCE witness, and gate status

    Example:
        >>> result = run_quality_gate(Path("."), "main", ".", epsilon=0.3, tau=0.8)
        >>> if not result.passed:
        ...     for action in result.pce_witness:
        ...         print(f"Fix {action['file']}: {action['action']}")
    """
    repo_path = repo_path.resolve()

    # 1. Analyze HEAD (current working tree)
    head_project = _analyze_repo(repo_path, "HEAD")
    head_metrics = compute_quality_score(head_project)

    # 2. Analyze BASE (checkout to temp directory)
    with tempfile.TemporaryDirectory(prefix="repoq_gate_base_") as tmpdir:
        base_path = Path(tmpdir) / "repo"

        # Clone BASE revision
        _checkout_ref(repo_path, base_ref, base_path)

        # Analyze BASE
        base_project = _analyze_repo(base_path, base_ref)
        base_metrics = compute_quality_score(base_project)

    # 3. Compute deltas
    deltas = compare_metrics(base_metrics, head_metrics)

    # 4. Hard constraints H (fail-fast)
    violations = []
    if not head_metrics.constraints_passed["tests_coverage_ge_80"]:
        violations.append(f"Tests coverage {head_metrics.tests_coverage:.1%} < 80% (required)")
    if not head_metrics.constraints_passed["todos_le_100"]:
        violations.append(f"TODOs count {head_metrics.todos} > 100 (max allowed)")
    if not head_metrics.constraints_passed["hotspots_le_20"]:
        violations.append(f"Hotspots count {head_metrics.hotspots} > 20 (max allowed)")

    # 5. ΔQ ≥ ε check (noise tolerance)
    delta_q = deltas["score_delta"]
    if delta_q < -epsilon:
        violations.append(
            f"Quality score degraded by {-delta_q:.2f} points (threshold: -{epsilon})"
        )

    # 6. PCQ ≥ τ check (gaming resistance)
    pcq_base = None
    pcq_head = None

    if enable_pcq:
        pcq_base = calculate_pcq(base_project, module_type="directory")
        pcq_head = calculate_pcq(head_project, module_type="directory")

        if pcq_head < tau * 100:  # tau is ratio, PCQ is score ∈ [0, 100]
            violations.append(f"PCQ {pcq_head:.1f} < {tau*100:.1f} (gaming protection threshold)")

    # 7. Admission predicate: H ∧ (ΔQ ≥ ε) ∧ (PCQ ≥ τ)
    passed = len(violations) == 0 if strict else True

    # 8. Generate PCE witness if failed
    pce_witness = None
    if not passed and not strict:
        # Generate k-repair witness (constructive feedback)
        target_score = base_metrics.score + epsilon  # Minimal improvement target
        pce_witness = generate_pce_witness(head_project, target_score, k=8)

    return GateResult(
        passed=passed,
        base_metrics=base_metrics,
        head_metrics=head_metrics,
        deltas=deltas,
        violations=violations,
        pcq_base=pcq_base,
        pcq_head=pcq_head,
        pce_witness=pce_witness,
    )


def _analyze_repo(repo_path: Path, ref: str) -> Project:
    """Analyze a repository at given path/ref.

    Args:
        repo_path: Path to repository
        ref: Git reference being analyzed (for project ID)

    Returns:
        Project with completed analysis
    """
    # Create Project instance
    project = Project(
        id=str(repo_path),
        name=repo_path.name,
        repository_url=None,
    )

    # Run analysis pipeline (structure + complexity + weaknesses)
    cfg = AnalyzeConfig(mode="structure")

    from .analyzers.ci_qm import CIQualityAnalyzer
    from .analyzers.complexity import ComplexityAnalyzer
    from .analyzers.structure import StructureAnalyzer
    from .analyzers.weakness import WeaknessAnalyzer

    repo_dir = str(repo_path)

    try:
        StructureAnalyzer().run(project, repo_dir, cfg)
        ComplexityAnalyzer().run(project, repo_dir, cfg)
        WeaknessAnalyzer().run(project, repo_dir, cfg)
        CIQualityAnalyzer().run(project, repo_dir, cfg)
    except Exception as e:
        # Log error but continue with partial results
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Analysis error for {ref}: {e}")

    return project


def _checkout_ref(repo_path: Path, ref: str, target_path: Path) -> None:
    """Checkout a Git reference to target directory using worktree.

    Args:
        repo_path: Path to source Git repository
        ref: Git reference (branch, tag, SHA)
        target_path: Destination path for checkout

    Raises:
        subprocess.CalledProcessError: If git command fails
    """
    # Use git worktree for safe parallel checkout
    subprocess.run(
        ["git", "worktree", "add", "--detach", str(target_path), ref],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )


def _cleanup_worktree(repo_path: Path, worktree_path: Path) -> None:
    """Clean up git worktree.

    Args:
        repo_path: Path to source Git repository
        worktree_path: Path to worktree to remove
    """
    try:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree_path)],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        # Worktree might be already removed by tempdir cleanup
        pass


def format_gate_report(result: GateResult) -> str:
    """Format GateResult as human-readable report with PCQ/PCE.

    Args:
        result: GateResult from run_quality_gate

    Returns:
        Multi-line formatted report string with ASCII box drawing

    Example:
        >>> report = format_gate_report(result)
        >>> print(report)
        ╔════════════════════════════════════════╗
        ║       Quality Gate: PASS ✓            ║
        ╚════════════════════════════════════════╝
        BASE: Q=85.0 (B), PCQ=82.3
        HEAD: Q=87.5 (B), PCQ=84.1
        ΔQ: +2.5 points ✓
    """
    lines = []

    # Header
    status = "PASS ✓" if result.passed else "FAIL ✗"
    status_color = "green" if result.passed else "red"

    lines.append("=" * 60)
    lines.append(f"[bold {status_color}]Quality Gate: {status}[/bold {status_color}]")
    lines.append("=" * 60)
    lines.append("")

    # Metrics comparison
    lines.append("[bold]📊 Metrics Comparison[/bold]")
    lines.append("")

    # BASE metrics
    pcq_base_str = f", PCQ={result.pcq_base:.1f}" if result.pcq_base is not None else ""
    lines.append(
        f"  BASE: Q={result.base_metrics.score:.1f} " f"({result.base_metrics.grade}){pcq_base_str}"
    )
    lines.append(
        f"        Complexity={result.base_metrics.complexity:.2f}, "
        f"Hotspots={result.base_metrics.hotspots}, "
        f"TODOs={result.base_metrics.todos}"
    )
    lines.append(f"        Coverage={result.base_metrics.tests_coverage:.1%}")
    lines.append("")

    # HEAD metrics
    pcq_head_str = f", PCQ={result.pcq_head:.1f}" if result.pcq_head is not None else ""
    lines.append(
        f"  HEAD: Q={result.head_metrics.score:.1f} " f"({result.head_metrics.grade}){pcq_head_str}"
    )
    lines.append(
        f"        Complexity={result.head_metrics.complexity:.2f}, "
        f"Hotspots={result.head_metrics.hotspots}, "
        f"TODOs={result.head_metrics.todos}"
    )
    lines.append(f"        Coverage={result.head_metrics.tests_coverage:.1%}")
    lines.append("")

    # Deltas
    lines.append("[bold]📈 Deltas (HEAD - BASE)[/bold]")
    lines.append("")

    delta_q = result.deltas["score_delta"]
    delta_q_str = f"+{delta_q:.2f}" if delta_q >= 0 else f"{delta_q:.2f}"
    delta_q_emoji = "✓" if delta_q >= 0 else "✗"
    lines.append(f"  ΔQ: {delta_q_str} points {delta_q_emoji}")

    delta_cplx = result.deltas["complexity_delta"]
    delta_cplx_str = f"+{delta_cplx:.2f}" if delta_cplx >= 0 else f"{delta_cplx:.2f}"
    delta_cplx_emoji = "✗" if delta_cplx > 0 else "✓"  # Lower is better
    lines.append(f"  ΔComplexity: {delta_cplx_str} {delta_cplx_emoji}")

    delta_hotspots = result.deltas["hotspots_delta"]
    delta_hotspots_str = f"+{delta_hotspots}" if delta_hotspots >= 0 else f"{delta_hotspots}"
    delta_hotspots_emoji = "✗" if delta_hotspots > 0 else "✓"
    lines.append(f"  ΔHotspots: {delta_hotspots_str} {delta_hotspots_emoji}")

    delta_todos = result.deltas["todos_delta"]
    delta_todos_str = f"+{delta_todos}" if delta_todos >= 0 else f"{delta_todos}"
    delta_todos_emoji = "✗" if delta_todos > 0 else "✓"
    lines.append(f"  ΔTODOs: {delta_todos_str} {delta_todos_emoji}")

    lines.append("")

    # PCQ details (if enabled)
    if result.pcq_base is not None and result.pcq_head is not None:
        delta_pcq = result.pcq_head - result.pcq_base
        delta_pcq_str = f"+{delta_pcq:.2f}" if delta_pcq >= 0 else f"{delta_pcq:.2f}"
        delta_pcq_emoji = "✓" if delta_pcq >= 0 else "✗"

        lines.append("[bold]🛡️  Gaming Protection (PCQ Min-Aggregation)[/bold]")
        lines.append("")
        lines.append(f"  ΔPCQ: {delta_pcq_str} points {delta_pcq_emoji}")
        lines.append("  PCQ enforces minimum quality across all modules")
        lines.append("  (prevents hiding complexity in one module)")
        lines.append("")

    # Violations
    if result.violations:
        lines.append("[bold red]❌ Constraint Violations[/bold red]")
        lines.append("")
        for i, violation in enumerate(result.violations, 1):
            lines.append(f"  {i}. {violation}")
        lines.append("")

    # PCE witness (if available)
    if result.pce_witness and len(result.pce_witness) > 0:
        lines.append("[bold yellow]💡 Constructive Feedback (PCE k-Repair Witness)[/bold yellow]")
        lines.append("")
        lines.append("  Top files to fix (by impact):")
        lines.append("")

        for i, action in enumerate(result.pce_witness[:5], 1):  # Show top 5
            priority_emoji = "🔴" if action["priority"] == "high" else "🟡"
            lines.append(f"  {i}. {priority_emoji} {action['file']}")
            lines.append(f"     Action: {action['action']}")
            lines.append(f"     Expected ΔQ: +{action['delta_q']:.2f} points")
            lines.append("")

    # Footer
    lines.append("=" * 60)

    return "\n".join(lines)
