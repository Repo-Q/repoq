from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import AnalyzeConfig
from ..core.model import Project


class Analyzer(ABC):
    name: str = "base"

    @abstractmethod
    def run(self, project: Project, repo_dir: str, cfg: AnalyzeConfig) -> None: ...
