"""Incremental analyzer for changed files only.

This module implements git diff-based incremental analysis to achieve
<2 min performance (NFR-01) for large repositories.

Architecture:
    1. Parse git diff (BASE..HEAD)
    2. Identify changed files (Added/Modified/Deleted)
    3. For unchanged files: use MetricCache
    4. For changed files: analyze with cache update
    5. Aggregate results

Performance:
    - Without cache: O(n) where n = total files
    - With cache + incremental: O(Δn) where Δn = changed files
    - Target: ≤2 min (P90) for <1K files

Example:
    >>> analyzer = IncrementalAnalyzer(repo_path=".")
    >>> changed_files = analyzer.get_changed_files("main", "HEAD")
    >>> # Only analyze changed_files (not all files)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set

import git

from ..core.metric_cache import MetricCache, get_global_cache


class ChangeType(Enum):
    """Type of file change in git diff."""

    ADDED = "A"
    MODIFIED = "M"
    DELETED = "D"
    RENAMED = "R"
    COPIED = "C"


@dataclass
class FileChange:
    """Represents a single file change from git diff.

    Attributes:
        path: File path relative to repository root
        change_type: Type of change (A/M/D/R/C)
        old_path: Old path if renamed (None otherwise)
    """

    path: str
    change_type: ChangeType
    old_path: Optional[str] = None


class IncrementalAnalyzer:
    """Incremental analyzer using git diff + MetricCache.

    This analyzer identifies changed files between BASE and HEAD
    revisions and only re-analyzes those files, using cached metrics
    for unchanged files.

    Attributes:
        repo_path: Path to git repository
        cache: MetricCache instance
        repo: GitPython Repo instance

    Example:
        >>> analyzer = IncrementalAnalyzer(Path("."))
        >>> changes = analyzer.get_changed_files("main", "HEAD")
        >>> # Analyze only changes
        >>> for change in changes:
        ...     if change.change_type != ChangeType.DELETED:
        ...         analyze_file(change.path)
    """

    def __init__(
        self,
        repo_path: Path,
        cache: Optional[MetricCache] = None,
    ):
        """Initialize incremental analyzer.

        Args:
            repo_path: Path to git repository
            cache: MetricCache instance (uses global if None)
        """
        self.repo_path = Path(repo_path).resolve()
        self.cache = cache or get_global_cache()

        try:
            self.repo = git.Repo(self.repo_path)
        except git.InvalidGitRepositoryError as e:
            raise ValueError(f"Not a git repository: {self.repo_path}") from e

    def get_changed_files(
        self,
        base_ref: str = "HEAD~1",
        head_ref: str = "HEAD",
        include_untracked: bool = False,
    ) -> List[FileChange]:
        """Get list of changed files between two refs.

        Args:
            base_ref: Base git reference (e.g., "main", "HEAD~1", SHA)
            head_ref: Head git reference (default: "HEAD")
            include_untracked: Whether to include untracked files

        Returns:
            List of FileChange objects

        Example:
            >>> changes = analyzer.get_changed_files("main", "HEAD")
            >>> added = [c for c in changes if c.change_type == ChangeType.ADDED]
            >>> modified = [c for c in changes if c.change_type == ChangeType.MODIFIED]
        """
        changes: List[FileChange] = []

        try:
            # Get diff between base and head
            if base_ref == "HEAD" and head_ref == "HEAD":
                # Working tree changes (unstaged + staged)
                diff_index = self.repo.head.commit.diff(None)
            else:
                # Compare two refs
                base_commit = self.repo.commit(base_ref)
                if head_ref == "HEAD":
                    head_commit = self.repo.head.commit
                else:
                    head_commit = self.repo.commit(head_ref)

                diff_index = base_commit.diff(head_commit)

            # Parse diff results
            for diff_item in diff_index:
                change_type = ChangeType(diff_item.change_type)

                if change_type == ChangeType.RENAMED:
                    changes.append(
                        FileChange(
                            path=diff_item.b_path,
                            change_type=change_type,
                            old_path=diff_item.a_path,
                        )
                    )
                elif change_type == ChangeType.DELETED:
                    changes.append(
                        FileChange(
                            path=diff_item.a_path,
                            change_type=change_type,
                        )
                    )
                else:  # ADDED, MODIFIED, COPIED
                    changes.append(
                        FileChange(
                            path=diff_item.b_path,
                            change_type=change_type,
                        )
                    )

            # Include untracked files if requested
            if include_untracked:
                for untracked_path in self.repo.untracked_files:
                    changes.append(
                        FileChange(
                            path=untracked_path,
                            change_type=ChangeType.ADDED,
                        )
                    )

        except git.GitCommandError as e:
            raise ValueError(f"Git diff failed: {e}") from e

        return changes

    def filter_python_files(self, changes: List[FileChange]) -> List[FileChange]:
        """Filter for Python files only.

        Args:
            changes: List of file changes

        Returns:
            Filtered list containing only .py files
        """
        return [change for change in changes if change.path.endswith(".py")]

    def get_all_python_files(self) -> Set[str]:
        """Get all Python files in repository (for full analysis).

        Returns:
            Set of Python file paths relative to repo root
        """
        python_files = set()

        for path in self.repo_path.rglob("*.py"):
            if ".git" not in path.parts:
                rel_path = path.relative_to(self.repo_path)
                python_files.add(str(rel_path))

        return python_files

    def should_use_incremental(
        self,
        base_ref: str,
        head_ref: str,
        threshold: float = 0.3,
    ) -> bool:
        """Determine if incremental analysis is beneficial.

        Incremental analysis is worth it if changed files < threshold * total files.

        Args:
            base_ref: Base git reference
            head_ref: Head git reference
            threshold: Threshold ratio (default: 0.3 = 30%)

        Returns:
            True if incremental analysis should be used

        Example:
            >>> if analyzer.should_use_incremental("main", "HEAD"):
            ...     # Use incremental (fast)
            ...     changes = analyzer.get_changed_files("main", "HEAD")
            ... else:
            ...     # Use full analysis (too many changes)
            ...     all_files = analyzer.get_all_python_files()
        """
        changes = self.get_changed_files(base_ref, head_ref)
        python_changes = self.filter_python_files(changes)

        all_python_files = self.get_all_python_files()

        if len(all_python_files) == 0:
            return False

        ratio = len(python_changes) / len(all_python_files)
        return ratio < threshold

    def analyze_with_cache(
        self,
        file_path: str,
        policy_version: str,
        analyzer_fn: callable,
    ) -> Dict[str, any]:
        """Analyze file with cache lookup.

        Args:
            file_path: Path to file relative to repo root
            policy_version: Quality policy version
            analyzer_fn: Function to analyze file (called on cache miss)

        Returns:
            Dictionary of metrics (from cache or computed)

        Example:
            >>> metrics = incremental.analyze_with_cache(
            ...     file_path="src/main.py",
            ...     policy_version="v1.0",
            ...     analyzer_fn=lambda: analyze_complexity("src/main.py")
            ... )
        """
        abs_path = self.repo_path / file_path

        if not abs_path.exists():
            return {}

        # Read file content
        content = abs_path.read_bytes()

        # Use cache
        return self.cache.get_or_compute(
            file_path=file_path,
            file_content=content,
            policy_version=policy_version,
            compute_fn=analyzer_fn,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache size, hit rate, etc.
        """
        return {
            "size": self.cache.size(),
            "max_size": self.cache.max_size,
            "hit_rate": self.cache.hit_rate(),
        }

    def invalidate_cache(self, policy_version: Optional[str] = None) -> int:
        """Invalidate cache entries.

        Args:
            policy_version: If provided, only invalidate this policy version

        Returns:
            Number of invalidated entries
        """
        return self.cache.invalidate(policy_version)

    def save_cache(self, cache_path: Path) -> None:
        """Save cache to disk.

        Args:
            cache_path: Path to save cache file
        """
        self.cache.save(cache_path)

    def load_cache(self, cache_path: Path) -> int:
        """Load cache from disk.

        Args:
            cache_path: Path to cache file

        Returns:
            Number of loaded entries
        """
        return self.cache.load(cache_path)


def create_incremental_analyzer(
    repo_path: Path,
    cache: Optional[MetricCache] = None,
) -> IncrementalAnalyzer:
    """Factory function to create IncrementalAnalyzer.

    Args:
        repo_path: Path to git repository
        cache: MetricCache instance (uses global if None)

    Returns:
        IncrementalAnalyzer instance
    """
    return IncrementalAnalyzer(repo_path, cache)
