"""Base analyzer class defining the interface for all repository analyzers.

This module provides the abstract base class that all concrete analyzers must
implement, ensuring consistent interface and orchestration across the pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import AnalyzeConfig
from ..core.model import Project


class Analyzer(ABC):
    """Abstract base class for repository analyzers.

    All concrete analyzers (structure, history, complexity, etc.) must inherit
    from this class and implement the run() method. The analyzer pipeline
    orchestrates multiple analyzers sequentially, each mutating the shared
    Project model.

    Attributes:
        name: Identifier for this analyzer type (e.g., "structure", "history")

    Example:
        >>> class MyAnalyzer(Analyzer):
        ...     name = "my_analyzer"
        ...     def run(self, project, repo_dir, cfg):
        ...         project.description = "Analyzed by MyAnalyzer"
    """

    name: str = "base"

    @abstractmethod
    def run(self, project: Project, repo_dir: str, cfg: AnalyzeConfig) -> None:
        """Execute analysis and mutate the project model.

        Args:
            project: The Project model to populate with analysis results
            repo_dir: Absolute path to the repository directory
            cfg: Configuration object with analysis parameters

        Note:
            This method should mutate the project object in-place rather than
            returning a value. Analyzers should be idempotent when possible.
        """
        ...
