"""Analysis pipeline orchestration.

This module coordinates the execution of multiple analyzers in the correct
sequence based on analysis mode (structure/history/full). Analyzers mutate
the shared Project model progressively.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .analyzers.architecture import ArchitectureAnalyzer
from .analyzers.ci_qm import CIQualityAnalyzer
from .analyzers.complexity import ComplexityAnalyzer
from .analyzers.doc_code_sync import DocCodeSyncAnalyzer
from .analyzers.git_status import GitStatusAnalyzer
from .analyzers.history import HistoryAnalyzer
from .analyzers.hotspots import HotspotsAnalyzer
from .analyzers.structure import StructureAnalyzer
from .analyzers.weakness import WeaknessAnalyzer
from .config import AnalyzeConfig
from .core.model import Project
from .core.workspace import RepoQWorkspace, compute_ontology_checksums

logger = logging.getLogger(__name__)


def run_pipeline(project: Project, repo_dir: str, cfg: AnalyzeConfig) -> None:
    """Execute analysis pipeline based on configuration mode.

    Orchestrates analyzer execution in dependency order:
    - structure mode: StructureAnalyzer → ComplexityAnalyzer → WeaknessAnalyzer → CIQualityAnalyzer
    - history mode: HistoryAnalyzer
    - full mode: All of the above + HotspotsAnalyzer (requires both structure and history data)

    **Phase 5.1 Integration**: Workspace initialization and manifest generation.
    - Creates .repoq/ structure at start
    - Generates manifest.json at end with checksums (FR-10, Theorem A)

    Args:
        project: Project model to populate with analysis results
        repo_dir: Absolute path to repository root
        cfg: Configuration with mode and parameters

    Note:
        Each analyzer mutates the project object in-place. The pipeline
        ensures analyzers run in the correct order to satisfy dependencies
        (e.g., HotspotsAnalyzer needs both complexity and history data).

    Example:
        >>> project = Project(id="repo:test", name="Test")
        >>> cfg = AnalyzeConfig(mode="full")
        >>> run_pipeline(project, "/path/to/repo", cfg)
        >>> print(len(project.files))
        42
    """
    # Phase 5.1: Initialize workspace at start (FR-10, ADR-008)
    repo_path = Path(repo_dir)
    workspace = RepoQWorkspace(repo_path)
    workspace.initialize()
    logger.info(f"Workspace initialized: {workspace.root}")

    # Run analyzers
    if cfg.mode in ("structure", "full"):
        StructureAnalyzer().run(project, repo_dir, cfg)
        GitStatusAnalyzer().run(project, repo_dir, cfg)  # Git working directory status
        ComplexityAnalyzer().run(project, repo_dir, cfg)
        WeaknessAnalyzer().run(project, repo_dir, cfg)
        CIQualityAnalyzer().run(project, repo_dir, cfg)
        ArchitectureAnalyzer().run(project, repo_dir, cfg)  # Architecture analysis
        DocCodeSyncAnalyzer().run(project, repo_dir, cfg)  # Documentation-code sync
    if cfg.mode in ("history", "full"):
        HistoryAnalyzer().run(project, repo_dir, cfg)
    if cfg.mode in ("full",):
        HotspotsAnalyzer().run(project, repo_dir, cfg)

    # Phase 5.1: Generate manifest at end (Theorem A - reproducibility)
    try:
        import subprocess  # nosec B404  # Safe: only git command

        commit_sha = subprocess.run(  # nosec B603,B607  # Safe: git with fixed args
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError:
        commit_sha = "unknown"

    ontology_dir = Path(__file__).parent / "ontologies"
    checksums = compute_ontology_checksums(ontology_dir)

    workspace.save_manifest(
        commit_sha=commit_sha,
        policy_version="2.0.0-alpha",  # Phase 5 pre-release
        ontology_checksums=checksums,
    )
    logger.info(f"Manifest saved: {workspace.root / 'manifest.json'}")
