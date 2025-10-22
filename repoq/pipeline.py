"""Analysis pipeline orchestration.

This module coordinates the execution of multiple analyzers in the correct
sequence based on analysis mode (structure/history/full). Analyzers mutate
the shared Project model progressively.
"""

from __future__ import annotations

import logging

from .analyzers.architecture import ArchitectureAnalyzer
from .analyzers.ci_qm import CIQualityAnalyzer
from .analyzers.complexity import ComplexityAnalyzer
from .analyzers.history import HistoryAnalyzer
from .analyzers.hotspots import HotspotsAnalyzer
from .analyzers.structure import StructureAnalyzer
from .analyzers.weakness import WeaknessAnalyzer
from .config import AnalyzeConfig
from .core.model import Project

logger = logging.getLogger(__name__)


def run_pipeline(project: Project, repo_dir: str, cfg: AnalyzeConfig) -> None:
    """Execute analysis pipeline based on configuration mode.

    Orchestrates analyzer execution in dependency order:
    - structure mode: StructureAnalyzer → ComplexityAnalyzer → WeaknessAnalyzer → CIQualityAnalyzer
    - history mode: HistoryAnalyzer
    - full mode: All of the above + HotspotsAnalyzer (requires both structure and history data)

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
    if cfg.mode in ("structure", "full"):
        StructureAnalyzer().run(project, repo_dir, cfg)
        ComplexityAnalyzer().run(project, repo_dir, cfg)
        WeaknessAnalyzer().run(project, repo_dir, cfg)
        CIQualityAnalyzer().run(project, repo_dir, cfg)
        ArchitectureAnalyzer().run(project, repo_dir, cfg)  # Architecture analysis
    if cfg.mode in ("history", "full"):
        HistoryAnalyzer().run(project, repo_dir, cfg)
    if cfg.mode in ("full",):
        HotspotsAnalyzer().run(project, repo_dir, cfg)
