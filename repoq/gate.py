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

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import AnalyzeConfig
from .core.model import Project
from .quality import QualityMetrics, compare_metrics, compute_quality_score


@dataclass
class GateResult:
    """Result of Quality Gate check.
    
    Attributes:
        passed: True if all hard constraints passed
        base_metrics: QualityMetrics for BASE revision
        head_metrics: QualityMetrics for HEAD revision
        deltas: Dict of metric deltas (HEAD - BASE)
        violations: List of constraint violation messages
    """

    passed: bool
    base_metrics: QualityMetrics
    head_metrics: QualityMetrics
    deltas: dict[str, float]
    violations: list[str]


def run_quality_gate(
    repo_path: Path,
    base_ref: str,
    head_ref: str = ".",
    strict: bool = True,
) -> GateResult:
    """Run Quality Gate comparing BASE vs HEAD.
    
    Algorithm:
        1. Checkout BASE revision to temp directory
        2. Run analysis pipeline on BASE
        3. Run analysis pipeline on HEAD (working tree)
        4. Compute Q-metrics for both
        5. Check hard constraints on HEAD
        6. Return GateResult with pass/fail status
    
    Args:
        repo_path: Path to Git repository
        base_ref: Git reference for baseline (e.g., "main", "origin/main", SHA)
        head_ref: Git reference for current (default "." = working tree)
        strict: If True, fail on any constraint violation; if False, warn only
        
    Returns:
        GateResult with metrics, deltas, and gate status
        
    Raises:
        subprocess.CalledProcessError: If git checkout fails
        FileNotFoundError: If repository not found
        
    Example:
        >>> result = run_quality_gate(Path("."), "main", ".")
        >>> if not result.passed:
        ...     print(f"Gate FAILED: {result.violations}")
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

    # 4. Check hard constraints on HEAD
    violations = []
    if not head_metrics.constraints_passed["tests_coverage_ge_80"]:
        violations.append(
            f"Tests coverage {head_metrics.tests_coverage:.1%} < 80% (required)"
        )
    if not head_metrics.constraints_passed["todos_le_100"]:
        violations.append(f"TODOs count {head_metrics.todos} > 100 (max allowed)")
    if not head_metrics.constraints_passed["hotspots_le_20"]:
        violations.append(
            f"Hotspots count {head_metrics.hotspots} > 20 (max allowed)"
        )

    # 5. Additional delta checks (score degradation)
    if deltas["score_delta"] < -5.0:
        violations.append(
            f"Quality score degraded by {-deltas['score_delta']:.1f} points (max -5.0)"
        )

    passed = len(violations) == 0 if strict else True

    return GateResult(
        passed=passed,
        base_metrics=base_metrics,
        head_metrics=head_metrics,
        deltas=deltas,
        violations=violations,
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
    """Format GateResult as human-readable report.
    
    Args:
        result: GateResult from run_quality_gate
        
    Returns:
        Multi-line formatted report string
        
    Example:
        >>> report = format_gate_report(result)
        >>> print(report)
        Quality Gate: PASS
        ==================
        BASE: Q=85.0 (B)
        HEAD: Q=90.0 (A) [+5.0]
        ...
    """
    status = "✅ PASS" if result.passed else "❌ FAIL"
    lines = [
        f"Quality Gate: {status}",
        "=" * 40,
        "",
        "BASE Metrics:",
        f"  Score: {result.base_metrics.score:.1f} ({result.base_metrics.grade})",
        f"  Complexity: {result.base_metrics.complexity:.2f}",
        f"  Hotspots: {result.base_metrics.hotspots}",
        f"  TODOs: {result.base_metrics.todos}",
        f"  Tests: {result.base_metrics.tests_coverage:.1%}",
        "",
        "HEAD Metrics:",
        f"  Score: {result.head_metrics.score:.1f} ({result.head_metrics.grade})",
        f"  Complexity: {result.head_metrics.complexity:.2f}",
        f"  Hotspots: {result.head_metrics.hotspots}",
        f"  TODOs: {result.head_metrics.todos}",
        f"  Tests: {result.head_metrics.tests_coverage:.1%}",
        "",
        "Deltas (HEAD - BASE):",
        f"  Score: {result.deltas['score_delta']:+.1f}",
        f"  Complexity: {result.deltas['complexity_delta']:+.2f}",
        f"  Hotspots: {result.deltas['hotspots_delta']:+d}",
        f"  TODOs: {result.deltas['todos_delta']:+d}",
        f"  Tests: {result.deltas['tests_coverage_delta']:+.1%}",
    ]

    if result.violations:
        lines.extend(
            [
                "",
                "Constraint Violations:",
                *[f"  ❌ {v}" for v in result.violations],
            ]
        )

    return "\n".join(lines)
