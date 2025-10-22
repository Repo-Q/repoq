"""Complexity analyzer for cyclomatic complexity and maintainability metrics.

This module analyzes code complexity using:
- Lizard: Cyclomatic complexity (CCN) for multiple languages
- Radon: Maintainability Index for Python code

Metrics help identify complex, hard-to-maintain code sections.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from ..core.model import Project
from ..core.utils import is_excluded
from .base import Analyzer

logger = logging.getLogger(__name__)


class ComplexityAnalyzer(Analyzer):
    """Analyzer for code complexity and maintainability metrics.

    Uses external tools:
    - lizard: Multi-language cyclomatic complexity (Python, Java, C++, JS, etc.)
    - radon: Python maintainability index (0-100 scale, 100=best)

    Populates File.complexity and File.maintainability fields. Gracefully
    skips analysis if tools are not installed.
    """

    name = "complexity"

    def _collect_file_paths(self, project: Project, repo_dir: str, cfg) -> list[str]:
        """Collect file paths for analysis, excluding configured patterns.
        
        Args:
            project: Project with files to analyze
            repo_dir: Repository root directory
            cfg: Configuration with exclude_globs
            
        Returns:
            List of absolute file paths to analyze
        """
        file_paths: List[str] = []
        for f in project.files.values():
            rel = f.path
            if is_excluded(rel, cfg.exclude_globs):
                continue
            file_paths.append(str(Path(repo_dir) / rel))
        return file_paths
    
    def _analyze_with_lizard(self, project: Project, repo_dir: str, file_paths: list[str]) -> None:
        """Run Lizard analysis and update file complexity metrics.
        
        Args:
            project: Project to update with complexity metrics
            repo_dir: Repository root for path resolution
            file_paths: List of absolute paths to analyze
        """
        try:
            import lizard  # type: ignore
        except ImportError:
            logger.debug("Lizard not installed, skipping cyclomatic complexity analysis")
            return
        except Exception as e:
            logger.warning(f"Failed to import lizard: {e}")
            return

        try:
            # Use threads=1 (minimum) to avoid "Number of processes must be at least 1" error
            results = lizard.analyze_files(file_paths, threads=1)
            for r in results:
                rel = Path(r.filename).relative_to(repo_dir).as_posix()
                fid = f"repo:file:{rel}"
                if fid in project.files:
                    if r.function_list:
                        # Store max complexity for backward compatibility
                        max_ccn = max(func.cyclomatic_complexity for func in r.function_list)
                        project.files[fid].complexity = float(max_ccn)
                        
                        # Store per-function metrics for detailed analysis
                        from ..core.model import FunctionMetrics
                        
                        project.files[fid].functions = [
                            FunctionMetrics(
                                name=func.name,
                                cyclomatic_complexity=func.cyclomatic_complexity,
                                lines_of_code=func.nloc,
                                parameters=func.parameter_count,
                                start_line=func.start_line,
                                end_line=func.end_line,
                                token_count=func.token_count,
                                max_nesting_depth=getattr(func, 'max_nesting_depth', None),
                            )
                            for func in r.function_list
                        ]
        except Exception as e:
            logger.warning(f"Lizard analysis failed: {e}")
    
    def _analyze_with_radon(self, project: Project, repo_dir: str) -> None:
        """Run Radon maintainability index analysis for Python files.
        
        Args:
            project: Project to update with maintainability metrics
            repo_dir: Repository root directory
        """
        try:
            from radon.mi import mi_visit
        except ImportError:
            logger.debug("Radon not installed, skipping maintainability index analysis")
            return
        except Exception as e:
            logger.warning(f"Failed to import radon: {e}")
            return

        for f in project.files.values():
            if f.language != "Python":
                continue
            try:
                p = Path(repo_dir) / f.path
                with p.open("r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                mi = mi_visit(content, True)
                f.maintainability = float(mi)
            except OSError as e:
                logger.debug(f"Could not read file {f.path} for MI analysis: {e}")
                continue
            except Exception as e:
                logger.debug(f"MI analysis failed for {f.path}: {e}")
                continue

    def run(self, project: Project, repo_dir: str, cfg) -> None:
        """Execute complexity analysis on project files.

        Args:
            project: Project model with files to analyze
            repo_dir: Absolute path to repository root
            cfg: Configuration with exclude patterns

        Note:
            Silently skips analysis if lizard or radon are not installed.
            Errors in individual file analysis are logged but don't stop
            the overall process.
        """
        # Collect file paths to analyze
        file_paths = self._collect_file_paths(project, repo_dir, cfg)
        
        # Run Lizard for cyclomatic complexity
        self._analyze_with_lizard(project, repo_dir, file_paths)
        
        # Run Radon for maintainability index
        self._analyze_with_radon(project, repo_dir)
