"""Incremental Analysis with SHA-based caching and git diff.

This module implements smart incremental analysis that:
- Skips unchanged files using SHA256-based cache keys
- Parses git diff to detect changed files
- Invalidates cache on policy/version changes
- Provides 2500x speedup for typical PRs (2 changed / 5000 total files)

Key Features:
- SHA-based content addressing (deterministic)
- Policy version tracking (cache invalidation)
- Git diff integration (changed files detection)
- Thread-safe caching (via MetricCache)
- O(K) analysis time where K = changed files

Architecture:
    compute_cache_key(content, policy_version) → str
    needs_analysis(content, policy_version, cache) → bool

    DiffAnalyzer:
        get_changed_files(base_ref, head_ref) → List[str]

    IncrementalAnalyzer:
        filter_unchanged_files(files: Dict[str, bytes]) → Dict[str, bytes]
        get_cached_metrics(content) → CachedMetrics | None
        store_metrics(path, content, metrics) → None

Example:
    >>> cache = MetricCache()
    >>> analyzer = IncrementalAnalyzer(cache, policy_version="v1.0")
    >>>
    >>> # Filter unchanged files
    >>> files = {"test.py": b"def foo(): pass"}
    >>> to_analyze = analyzer.filter_unchanged_files(files)
    >>>
    >>> # Analyze only changed files
    >>> for path, content in to_analyze.items():
    ...     metrics = analyze_file(path, content)
    ...     analyzer.store_metrics(path, content, metrics)
"""

from __future__ import annotations

import hashlib
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .. import __version__
from .metric_cache import CachedMetrics, MetricCache

logger = logging.getLogger(__name__)


def compute_cache_key(file_content: bytes, policy_version: str) -> str:
    """Compute cache key from file content SHA, policy version, and repoq version.

    Cache key format: {file_sha}_{policy_version}_{repoq_version}
    (Uses FULL SHA256, matching MetricCache._make_key)

    Args:
        file_content: File content as bytes
        policy_version: Quality policy version (e.g., "v1.0")

    Returns:
        Cache key string (deterministic)

    Example:
        >>> content = b"def foo(): pass"
        >>> compute_cache_key(content, "v1.0")
        'a1b2c3...full_sha..._v1.0_2.0.0'
    """
    file_sha = hashlib.sha256(file_content).hexdigest()  # FULL SHA, not [:16]
    repoq_version = __version__
    return f"{file_sha}_{policy_version}_{repoq_version}"


def needs_analysis(file_content: bytes, policy_version: str, cache: MetricCache) -> bool:
    """Determine if file needs analysis based on cache.

    Returns True if:
    - File not in cache (new file)
    - Policy version changed (invalidated)
    - RepoQ version changed (invalidated)

    Args:
        file_content: File content as bytes
        policy_version: Quality policy version
        cache: MetricCache instance

    Returns:
        True if analysis needed, False if cached

    Example:
        >>> cache = MetricCache()
        >>> needs_analysis(b"def foo(): pass", "v1.0", cache)
        True  # First time, not cached
        >>> # ... after storing metrics ...
        >>> needs_analysis(b"def foo(): pass", "v1.0", cache)
        False  # Cache hit
    """
    file_sha = hashlib.sha256(file_content).hexdigest()
    return cache.get(file_sha, policy_version) is None


class DiffAnalyzer:
    """Git diff parser for detecting changed files.

    Analyzes git diff between two refs to determine which files changed.
    Supports:
    - Branch comparisons (main vs feature-branch)
    - Commit comparisons (SHA1 vs SHA2)
    - Working directory (base vs .)

    Attributes:
        repo_path: Path to git repository

    Example:
        >>> analyzer = DiffAnalyzer(repo_path=Path("."))
        >>> changed = analyzer.get_changed_files(base_ref="main", head_ref=".")
        >>> print(f"Changed files: {changed}")
        ['src/foo.py', 'tests/test_foo.py']
    """

    def __init__(self, repo_path: Path):
        """Initialize DiffAnalyzer.

        Args:
            repo_path: Path to git repository root
        """
        self.repo_path = repo_path

    def get_changed_files(self, base_ref: str, head_ref: str) -> List[str]:
        """Get list of changed files between two refs.

        Args:
            base_ref: Base reference (e.g., "main", "HEAD~1", SHA)
            head_ref: Head reference (e.g., ".", "feature-branch", SHA)

        Returns:
            List of changed file paths (relative to repo root)

        Raises:
            subprocess.CalledProcessError: If git command fails

        Example:
            >>> analyzer.get_changed_files("HEAD~1", "HEAD")
            ['src/modified.py', 'tests/test_new.py']
        """
        # Handle working directory (".")
        if head_ref == ".":
            # git diff --name-only HEAD (shows modified/deleted files)
            cmd_diff = ["git", "diff", "--name-only", base_ref]
            result_diff = subprocess.run(  # nosec B603 - safe git command with validated args
                cmd_diff,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            changed = [f for f in result_diff.stdout.strip().split("\n") if f]

            # git ls-files --others --exclude-standard (shows untracked files)
            cmd_untracked = ["git", "ls-files", "--others", "--exclude-standard"]
            result_untracked = subprocess.run(  # nosec B603 - safe git command
                cmd_untracked,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            untracked = [f for f in result_untracked.stdout.strip().split("\n") if f]

            return changed + untracked
        else:
            # git diff --name-only base_ref..head_ref
            cmd = ["git", "diff", "--name-only", f"{base_ref}..{head_ref}"]

        result = subprocess.run(  # nosec B603 B607
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse output (one file per line)
        changed_files = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]

        logger.info(
            f"Detected {len(changed_files)} changed files between {base_ref} and {head_ref}"
        )
        return changed_files


class IncrementalAnalyzer:
    """Orchestrates incremental analysis with cache.

    Provides high-level API for:
    - Filtering unchanged files (cache hits)
    - Retrieving cached metrics
    - Storing new metrics

    Attributes:
        cache: MetricCache instance
        policy_version: Current quality policy version

    Example:
        >>> cache = MetricCache()
        >>> analyzer = IncrementalAnalyzer(cache, policy_version="v1.0")
        >>>
        >>> files = {
        ...     "test1.py": b"def foo(): pass",
        ...     "test2.py": b"def bar(): pass",
        ... }
        >>>
        >>> to_analyze = analyzer.filter_unchanged_files(files)
        >>> print(f"Need to analyze: {len(to_analyze)} / {len(files)}")
    """

    def __init__(self, cache: MetricCache, policy_version: str):
        """Initialize IncrementalAnalyzer.

        Args:
            cache: MetricCache instance
            policy_version: Quality policy version (e.g., "v1.0")
        """
        self.cache = cache
        self.policy_version = policy_version

    def filter_unchanged_files(self, files: Dict[str, bytes]) -> Dict[str, bytes]:
        """Filter out unchanged files (cache hits).

        Args:
            files: Dict of {file_path: file_content}

        Returns:
            Dict of files that need analysis (cache misses)

        Example:
            >>> files = {"test1.py": b"...", "test2.py": b"..."}
            >>> to_analyze = analyzer.filter_unchanged_files(files)
            >>> # Only returns files not in cache
        """
        to_analyze = {}

        for file_path, file_content in files.items():
            if needs_analysis(file_content, self.policy_version, self.cache):
                to_analyze[file_path] = file_content
                logger.debug(f"Cache miss: {file_path} needs analysis")
            else:
                logger.debug(f"Cache hit: {file_path} skipped")

        cache_hits = len(files) - len(to_analyze)
        cache_hit_rate = cache_hits / len(files) if files else 0.0

        logger.info(
            f"Cache: {cache_hits}/{len(files)} hits ({cache_hit_rate:.1%}), "
            f"{len(to_analyze)} files need analysis"
        )

        return to_analyze

    def get_cached_metrics(self, file_content: bytes) -> Optional[CachedMetrics]:
        """Retrieve cached metrics for file.

        Args:
            file_content: File content as bytes

        Returns:
            CachedMetrics if cache hit, None if miss

        Example:
            >>> cached = analyzer.get_cached_metrics(b"def foo(): pass")
            >>> if cached:
            ...     print(cached.metrics["complexity"])
        """
        file_sha = hashlib.sha256(file_content).hexdigest()
        return self.cache.get(file_sha, self.policy_version)

    def store_metrics(self, file_path: str, file_content: bytes, metrics: Dict[str, Any]) -> None:
        """Store metrics in cache.

        Args:
            file_path: Path to file (relative to repo root)
            file_content: File content as bytes
            metrics: Dict of metric name → value

        Example:
            >>> analyzer.store_metrics(
            ...     "test.py",
            ...     b"def foo(): pass",
            ...     {"complexity": 1, "lines": 10}
            ... )
        """
        file_sha = hashlib.sha256(file_content).hexdigest()
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        self.cache.set(
            file_path=file_path,
            file_sha=file_sha,
            policy_version=self.policy_version,
            metrics=metrics,
            timestamp=timestamp,
        )
        logger.debug(f"Cached metrics for {file_path}")
