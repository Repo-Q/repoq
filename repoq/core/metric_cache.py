"""Metric cache with SHA-based keys and LRU eviction.

This module implements caching for analysis metrics to enable incremental
analysis. Cache keys are based on file content SHA, policy version, and
RepoQ version to ensure correctness.

Key Features:
- SHA-based keys (content-addressable)
- LRU eviction (max 10K entries)
- Policy version tracking (invalidate on policy change)
- Thread-safe operations

Architecture:
    cache_key = f"{file_sha}_{policy_version}_{repoq_version}"

    if cache_key in cache:
        return cached_metrics  # Cache hit
    else:
        metrics = calculate_metrics(file)
        cache[cache_key] = metrics  # Store for future
        return metrics

Example:
    >>> cache = MetricCache(max_size=1000)
    >>> metrics = cache.get("abc123_v1.0_2.0.0")
    >>> if metrics is None:
    ...     metrics = analyze_file(...)
    ...     cache.set("abc123_v1.0_2.0.0", metrics)
"""

from __future__ import annotations

import hashlib
import json
import threading
from collections import OrderedDict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .. import __version__


@dataclass
class CachedMetrics:
    """Cached metrics for a single file.

    Attributes:
        file_path: Path to analyzed file
        file_sha: SHA256 of file content
        policy_version: Version of quality policy used
        repoq_version: Version of RepoQ tool used
        metrics: Dictionary of metric name -> value
        timestamp: ISO 8601 timestamp of analysis
    """

    file_path: str
    file_sha: str
    policy_version: str
    repoq_version: str
    metrics: Dict[str, Any]
    timestamp: str


class MetricCache:
    """Thread-safe LRU cache for analysis metrics.

    The cache uses SHA-based keys to ensure correctness:
    - File content change → new SHA → cache miss
    - Policy version change → new key → cache miss
    - RepoQ version change → new key → cache miss

    LRU eviction ensures bounded memory usage (max_size entries).

    Thread Safety:
        All operations are protected by a lock for safe concurrent access.

    Attributes:
        max_size: Maximum number of cache entries (default: 10000)
        _cache: OrderedDict for LRU semantics
        _lock: Threading lock for safe concurrent access

    Example:
        >>> cache = MetricCache(max_size=5000)
        >>> cache.get_or_compute(
        ...     file_path="src/main.py",
        ...     file_content=b"def main(): pass",
        ...     policy_version="v1.0",
        ...     compute_fn=lambda: {"complexity": 1}
        ... )
        {"complexity": 1}
    """

    def __init__(self, max_size: int = 10000):
        """Initialize cache with max size.

        Args:
            max_size: Maximum cache entries (default: 10K)
        """
        self.max_size = max_size
        self._cache: OrderedDict[str, CachedMetrics] = OrderedDict()
        self._lock = threading.Lock()

    def _make_key(
        self,
        file_sha: str,
        policy_version: str,
        repoq_version: str | None = None,
    ) -> str:
        """Generate cache key from SHA + versions.

        Args:
            file_sha: SHA256 of file content
            policy_version: Quality policy version
            repoq_version: RepoQ version (defaults to current)

        Returns:
            Cache key string: "{file_sha}_{policy_ver}_{repoq_ver}"
        """
        repoq_ver = repoq_version or __version__
        return f"{file_sha}_{policy_version}_{repoq_ver}"

    def _compute_file_sha(self, content: bytes) -> str:
        """Compute SHA256 of file content.

        Args:
            content: File content as bytes

        Returns:
            Hexadecimal SHA256 digest
        """
        return hashlib.sha256(content).hexdigest()

    def get(
        self,
        file_sha: str,
        policy_version: str,
        repoq_version: str | None = None,
    ) -> Optional[CachedMetrics]:
        """Get cached metrics by key.

        Args:
            file_sha: SHA256 of file content
            policy_version: Quality policy version
            repoq_version: RepoQ version (optional)

        Returns:
            CachedMetrics if found, None otherwise
        """
        key = self._make_key(file_sha, policy_version, repoq_version)

        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                return self._cache[key]
            return None

    def set(
        self,
        file_path: str,
        file_sha: str,
        policy_version: str,
        metrics: Dict[str, Any],
        timestamp: str,
        repoq_version: str | None = None,
    ) -> None:
        """Store metrics in cache.

        Args:
            file_path: Path to analyzed file
            file_sha: SHA256 of file content
            policy_version: Quality policy version
            metrics: Dictionary of metric name -> value
            timestamp: ISO 8601 timestamp
            repoq_version: RepoQ version (optional)
        """
        key = self._make_key(file_sha, policy_version, repoq_version)
        repoq_ver = repoq_version or __version__

        cached = CachedMetrics(
            file_path=file_path,
            file_sha=file_sha,
            policy_version=policy_version,
            repoq_version=repoq_ver,
            metrics=metrics,
            timestamp=timestamp,
        )

        with self._lock:
            # Add to cache (or update if exists)
            self._cache[key] = cached
            self._cache.move_to_end(key)

            # LRU eviction if over max_size
            if len(self._cache) > self.max_size:
                # Remove oldest (first item)
                self._cache.popitem(last=False)

    def get_or_compute(
        self,
        file_path: str,
        file_content: bytes,
        policy_version: str,
        compute_fn: callable,
        timestamp: str,
        repoq_version: str | None = None,
    ) -> Dict[str, Any]:
        """Get cached metrics or compute if missing.

        This is the main entry point for cache-aware analysis.

        Args:
            file_path: Path to file being analyzed
            file_content: File content as bytes
            policy_version: Quality policy version
            compute_fn: Function to compute metrics if cache miss
            timestamp: ISO 8601 timestamp
            repoq_version: RepoQ version (optional)

        Returns:
            Dictionary of metrics (from cache or computed)

        Example:
            >>> metrics = cache.get_or_compute(
            ...     file_path="src/main.py",
            ...     file_content=b"def main(): pass",
            ...     policy_version="v1.0",
            ...     compute_fn=lambda: analyze_file("src/main.py"),
            ...     timestamp="2025-01-21T10:30:00Z"
            ... )
        """
        file_sha = self._compute_file_sha(file_content)

        # Try cache first
        cached = self.get(file_sha, policy_version, repoq_version)
        if cached is not None:
            return cached.metrics

        # Cache miss: compute metrics
        metrics = compute_fn()

        # Store in cache
        self.set(
            file_path=file_path,
            file_sha=file_sha,
            policy_version=policy_version,
            metrics=metrics,
            timestamp=timestamp,
            repoq_version=repoq_version,
        )

        return metrics

    def invalidate(self, policy_version: str | None = None) -> int:
        """Invalidate cache entries.

        Args:
            policy_version: If provided, only invalidate entries with this policy version.
                           If None, clear entire cache.

        Returns:
            Number of invalidated entries
        """
        with self._lock:
            if policy_version is None:
                # Clear entire cache
                count = len(self._cache)
                self._cache.clear()
                return count
            else:
                # Invalidate entries with matching policy version
                to_remove = [
                    key
                    for key, cached in self._cache.items()
                    if cached.policy_version == policy_version
                ]
                for key in to_remove:
                    del self._cache[key]
                return len(to_remove)

    def size(self) -> int:
        """Get current cache size (number of entries)."""
        with self._lock:
            return len(self._cache)

    def hit_rate(self, reset: bool = False) -> float:
        """Calculate cache hit rate (requires statistics tracking).

        Note: This is a placeholder. Implement hit/miss counters if needed.

        Args:
            reset: Whether to reset counters after calculating

        Returns:
            Hit rate as float (0.0 to 1.0)
        """
        # TODO: Implement hit/miss tracking if needed
        return 0.0

    def save(self, path: Path) -> None:
        """Save cache to disk (JSON format).

        Args:
            path: Path to save cache file
        """
        with self._lock:
            data = {
                "version": "1.0",
                "max_size": self.max_size,
                "entries": [asdict(cached) for cached in self._cache.values()],
            }

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    def load(self, path: Path) -> int:
        """Load cache from disk (JSON format).

        Args:
            path: Path to cache file

        Returns:
            Number of loaded entries
        """
        if not path.exists():
            return 0

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        with self._lock:
            self._cache.clear()

            for entry in data.get("entries", []):
                cached = CachedMetrics(**entry)
                key = self._make_key(
                    cached.file_sha,
                    cached.policy_version,
                    cached.repoq_version,
                )
                self._cache[key] = cached

            return len(self._cache)


# Global cache instance (singleton pattern)
_global_cache: Optional[MetricCache] = None


def get_global_cache() -> MetricCache:
    """Get or create global cache instance.

    Returns:
        Global MetricCache singleton
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = MetricCache(max_size=10000)
    return _global_cache
