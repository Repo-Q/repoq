from __future__ import annotations

from .analyzers.ci_qm import CIQualityAnalyzer
from .analyzers.complexity import ComplexityAnalyzer
from .analyzers.history import HistoryAnalyzer
from .analyzers.hotspots import HotspotsAnalyzer
from .analyzers.structure import StructureAnalyzer
from .analyzers.weakness import WeaknessAnalyzer
from .config import AnalyzeConfig
from .core.model import Project


def run_pipeline(project: Project, repo_dir: str, cfg: AnalyzeConfig) -> None:
    if cfg.mode in ("structure", "full"):
        StructureAnalyzer().run(project, repo_dir, cfg)
        ComplexityAnalyzer().run(project, repo_dir, cfg)
        WeaknessAnalyzer().run(project, repo_dir, cfg)
        CIQualityAnalyzer().run(project, repo_dir, cfg)
    if cfg.mode in ("history", "full"):
        HistoryAnalyzer().run(project, repo_dir, cfg)
    if cfg.mode in ("full",):
        HotspotsAnalyzer().run(project, repo_dir, cfg)
