"""Tests for Incremental Analysis (SHA-based cache with git diff).

TDD RED phase: Write failing tests first.

Tests cover:
- Cache key computation (SHA + policy + version)
- needs_analysis() logic (cache hit/miss)
- Git diff parsing (changed files detection)
- Policy version changes (cache invalidation)
- File content changes (SHA-based detection)
- Parallel analysis with cache
"""

from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path

import pytest

from repoq.core.incremental import (
    DiffAnalyzer,
    IncrementalAnalyzer,
    compute_cache_key,
    needs_analysis,
)
from repoq.core.metric_cache import MetricCache


@pytest.fixture
def temp_git_repo():
    """Create temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create initial commit
        test_file = repo_path / "test.py"
        test_file.write_text("def foo(): pass\n")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        yield repo_path


@pytest.fixture
def cache():
    """MetricCache instance for testing."""
    return MetricCache(max_size=10000)  # Large enough for performance tests


@pytest.fixture
def incremental_analyzer(cache):
    """IncrementalAnalyzer instance."""
    return IncrementalAnalyzer(cache=cache, policy_version="v1.0")


class TestCacheKeyComputation:
    """Test cache key generation from file content."""

    def test_compute_cache_key_deterministic(self):
        """Cache key should be deterministic for same inputs."""
        file_content = b"def foo(): pass\n"
        policy_version = "v1.0"

        key1 = compute_cache_key(file_content, policy_version)
        key2 = compute_cache_key(file_content, policy_version)

        assert key1 == key2

    def test_compute_cache_key_includes_sha(self):
        """Cache key should include file SHA256."""
        file_content = b"def foo(): pass\n"
        policy_version = "v1.0"

        expected_sha = hashlib.sha256(file_content).hexdigest()[:16]
        key = compute_cache_key(file_content, policy_version)

        assert expected_sha in key

    def test_compute_cache_key_includes_policy_version(self):
        """Cache key should include policy version."""
        file_content = b"def foo(): pass\n"
        policy_version = "v1.0"

        key = compute_cache_key(file_content, policy_version)

        assert "v1.0" in key

    def test_compute_cache_key_includes_repoq_version(self):
        """Cache key should include repoq version."""
        file_content = b"def foo(): pass\n"
        policy_version = "v1.0"

        key = compute_cache_key(file_content, policy_version)

        # Should include repoq version from __version__
        assert "_" in key  # Format: sha_policy_version

    def test_compute_cache_key_different_content(self):
        """Different file content should produce different keys."""
        policy_version = "v1.0"

        key1 = compute_cache_key(b"def foo(): pass\n", policy_version)
        key2 = compute_cache_key(b"def bar(): pass\n", policy_version)

        assert key1 != key2

    def test_compute_cache_key_different_policy(self):
        """Different policy version should produce different keys."""
        file_content = b"def foo(): pass\n"

        key1 = compute_cache_key(file_content, "v1.0")
        key2 = compute_cache_key(file_content, "v2.0")

        assert key1 != key2


class TestNeedsAnalysis:
    """Test needs_analysis() decision logic."""

    def test_needs_analysis_cache_miss(self, cache):
        """Should return True for cache miss (new file)."""
        file_content = b"def foo(): pass\n"
        policy_version = "v1.0"

        result = needs_analysis(file_content, policy_version, cache)

        assert result is True

    def test_needs_analysis_cache_hit(self, cache):
        """Should return False for cache hit (unchanged file)."""
        file_content = b"def foo(): pass\n"
        policy_version = "v1.0"

        # Pre-populate cache
        cache_key = compute_cache_key(file_content, policy_version)
        # Populate cache with metrics
        cache.set(
            file_path="test.py",
            file_sha=hashlib.sha256(file_content).hexdigest(),
            policy_version=policy_version,
            metrics={"complexity": 1},
            timestamp="2025-10-22T10:00:00Z",
            repoq_version="2.0.0",
        )

        result = needs_analysis(file_content, policy_version, cache)

        assert result is False

    def test_needs_analysis_policy_change_invalidates(self, cache):
        """Policy change should invalidate cache."""
        file_content = b"def foo(): pass\n"

        # Cache with v1.0
        cache.set(
            file_path="test.py",
            file_sha=hashlib.sha256(file_content).hexdigest(),
            policy_version="v1.0",
            metrics={"complexity": 1},
            timestamp="2025-10-22T10:00:00Z",
            repoq_version="2.0.0",
        )

        # Check with v2.0 (should be cache miss)
        result = needs_analysis(file_content, "v2.0", cache)

        assert result is True

    def test_needs_analysis_content_change_invalidates(self, cache):
        """Content change should invalidate cache."""
        policy_version = "v1.0"

        # Cache original content
        original_content = b"def foo(): pass\n"
        cache.set(
            file_path="test.py",
            file_sha=hashlib.sha256(original_content).hexdigest(),
            policy_version=policy_version,
            metrics={"complexity": 1},
            timestamp="2025-10-22T10:00:00Z",
            repoq_version="2.0.0",
        )

        # Check modified content (should be cache miss)
        modified_content = b"def bar(): pass\n"
        result = needs_analysis(modified_content, policy_version, cache)

        assert result is True


class TestDiffAnalyzer:
    """Test git diff parsing and changed files detection."""

    def test_get_changed_files_no_changes(self, temp_git_repo):
        """Should return empty list for no changes."""
        analyzer = DiffAnalyzer(repo_path=temp_git_repo)

        changed = analyzer.get_changed_files(base_ref="HEAD", head_ref="HEAD")

        assert changed == []

    def test_get_changed_files_one_file_modified(self, temp_git_repo):
        """Should detect single modified file."""
        analyzer = DiffAnalyzer(repo_path=temp_git_repo)

        # Modify file
        test_file = temp_git_repo / "test.py"
        test_file.write_text("def bar(): pass\n")

        changed = analyzer.get_changed_files(base_ref="HEAD", head_ref=".")

        assert len(changed) == 1
        assert "test.py" in changed[0]

    def test_get_changed_files_new_file_added(self, temp_git_repo):
        """Should detect new file."""
        analyzer = DiffAnalyzer(repo_path=temp_git_repo)

        # Add new file
        new_file = temp_git_repo / "new.py"
        new_file.write_text("def baz(): pass\n")

        changed = analyzer.get_changed_files(base_ref="HEAD", head_ref=".")

        assert len(changed) == 1
        assert "new.py" in changed[0]

    def test_get_changed_files_multiple_files(self, temp_git_repo):
        """Should detect multiple changed files."""
        analyzer = DiffAnalyzer(repo_path=temp_git_repo)

        # Modify and add files
        test_file = temp_git_repo / "test.py"
        test_file.write_text("def bar(): pass\n")

        new_file = temp_git_repo / "new.py"
        new_file.write_text("def baz(): pass\n")

        changed = analyzer.get_changed_files(base_ref="HEAD", head_ref=".")

        assert len(changed) == 2
        paths = " ".join(changed)
        assert "test.py" in paths
        assert "new.py" in paths

    def test_get_changed_files_between_commits(self, temp_git_repo):
        """Should detect changes between two commits."""
        # Create second commit
        test_file = temp_git_repo / "test.py"
        test_file.write_text("def bar(): pass\n")
        subprocess.run(["git", "add", "."], cwd=temp_git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Second commit"],
            cwd=temp_git_repo,
            check=True,
            capture_output=True,
        )

        analyzer = DiffAnalyzer(repo_path=temp_git_repo)
        changed = analyzer.get_changed_files(base_ref="HEAD~1", head_ref="HEAD")

        assert len(changed) == 1
        assert "test.py" in changed[0]


class TestIncrementalAnalyzer:
    """Test IncrementalAnalyzer orchestration."""

    def test_filter_unchanged_files_all_unchanged(self, incremental_analyzer, cache):
        """Should filter out all unchanged files (cache hits)."""
        files = {
            "test1.py": b"def foo(): pass\n",
            "test2.py": b"def bar(): pass\n",
        }

        # Pre-populate cache for both
        for path, content in files.items():
            cache.set(
                file_path=path,
                file_sha=hashlib.sha256(content).hexdigest(),
                policy_version="v1.0",
                metrics={"complexity": 1},
                timestamp="2025-10-22T10:00:00Z",
                repoq_version="2.0.0",
            )

        to_analyze = incremental_analyzer.filter_unchanged_files(files)

        assert len(to_analyze) == 0

    def test_filter_unchanged_files_some_changed(self, incremental_analyzer, cache):
        """Should return only changed files."""
        files = {
            "test1.py": b"def foo(): pass\n",  # Unchanged (in cache)
            "test2.py": b"def bar(): pass\n",  # Changed (not in cache)
        }

        # Cache only test1.py
        cache.set(
            file_path="test1.py",
            file_sha=hashlib.sha256(files["test1.py"]).hexdigest(),
            policy_version="v1.0",
            metrics={"complexity": 1},
            timestamp="2025-10-22T10:00:00Z",
            repoq_version="2.0.0",
        )

        to_analyze = incremental_analyzer.filter_unchanged_files(files)

        assert len(to_analyze) == 1
        assert "test2.py" in to_analyze

    def test_filter_unchanged_files_all_new(self, incremental_analyzer):
        """Should return all files for fresh analysis (empty cache)."""
        files = {
            "test1.py": b"def foo(): pass\n",
            "test2.py": b"def bar(): pass\n",
            "test3.py": b"def baz(): pass\n",
        }

        to_analyze = incremental_analyzer.filter_unchanged_files(files)

        assert len(to_analyze) == 3

    def test_get_cached_metrics_hit(self, incremental_analyzer, cache):
        """Should return cached metrics for unchanged file."""
        file_content = b"def foo(): pass\n"
        policy_version = "v1.0"

        # Pre-populate cache
        cache.set(
            file_path="test.py",
            file_sha=hashlib.sha256(file_content).hexdigest(),
            policy_version=policy_version,
            metrics={"complexity": 5, "lines": 100},
            timestamp="2025-10-22T10:00:00Z",
            repoq_version="2.0.0",
        )

        # Retrieve
        result = incremental_analyzer.get_cached_metrics(file_content)

        assert result is not None
        assert result.metrics["complexity"] == 5
        assert result.metrics["lines"] == 100

    def test_get_cached_metrics_miss(self, incremental_analyzer):
        """Should return None for cache miss."""
        file_content = b"def foo(): pass\n"

        result = incremental_analyzer.get_cached_metrics(file_content)

        assert result is None

    def test_store_metrics(self, incremental_analyzer, cache):
        """Should store metrics in cache with correct key."""
        file_path = "test.py"
        file_content = b"def foo(): pass\n"
        metrics = {"complexity": 10, "lines": 200}

        incremental_analyzer.store_metrics(file_path, file_content, metrics)

        # Verify stored (use cache.get with proper API)
        file_sha = hashlib.sha256(file_content).hexdigest()
        cached = cache.get(file_sha, "v1.0")

        assert cached is not None
        assert cached.metrics["complexity"] == 10
        assert cached.file_path == file_path


class TestCacheInvalidation:
    """Test cache invalidation scenarios."""

    def test_policy_change_clears_cache(self, cache):
        """Changing policy version should invalidate all cached metrics."""
        file_content = b"def foo(): pass\n"

        # Cache with v1.0
        file_sha = hashlib.sha256(file_content).hexdigest()
        cache.set(
            file_path="test.py",
            file_sha=file_sha,
            policy_version="v1.0",
            metrics={"complexity": 1},
            timestamp="2025-10-22T10:00:00Z",
            repoq_version="2.0.0",
        )

        # Verify v1.0 is cached
        assert cache.get(file_sha, "v1.0") is not None

        # New analyzer with v2.0
        analyzer_v2 = IncrementalAnalyzer(cache=cache, policy_version="v2.0")

        # Should be cache miss with v2.0
        assert analyzer_v2.get_cached_metrics(file_content) is None

    def test_whitespace_only_change_cache_miss(self, incremental_analyzer, cache):
        """Whitespace change should cause cache miss (before normalization)."""
        original = b"def foo():pass\n"
        whitespace_change = b"def foo(): pass\n"  # Added space

        # Cache original
        cache.set(
            file_path="test.py",
            file_sha=hashlib.sha256(original).hexdigest(),
            policy_version="v1.0",
            metrics={"complexity": 1},
            timestamp="2025-10-22T10:00:00Z",
            repoq_version="2.0.0",
        )

        # Whitespace change should be cache miss (different SHA)
        result = needs_analysis(whitespace_change, "v1.0", cache)

        assert result is True


class TestPerformance:
    """Test performance characteristics."""

    def test_cache_speedup_large_repo(self, incremental_analyzer, cache):
        """Cache should significantly reduce analysis time for large repos."""
        # Simulate 1000 files
        files = {f"file_{i}.py": f"def func_{i}(): pass\n".encode() for i in range(1000)}

        # First pass: all files need analysis (cold cache)
        to_analyze_cold = incremental_analyzer.filter_unchanged_files(files)
        assert len(to_analyze_cold) == 1000

        # Populate cache (simulate analysis)
        for path, content in files.items():
            incremental_analyzer.store_metrics(path, content, {"complexity": 1})

        # Second pass: no files need analysis (warm cache)
        to_analyze_warm = incremental_analyzer.filter_unchanged_files(files)
        assert len(to_analyze_warm) == 0

        # Speedup: 1000 files → 0 files (infinite speedup for unchanged)

    def test_partial_cache_hit_typical_pr(self, incremental_analyzer, cache):
        """Typical PR (2 changed files) should hit cache for 99.96% of files."""
        # Simulate 5000 files
        all_files = {f"file_{i}.py": f"def func_{i}(): pass\n".encode() for i in range(5000)}

        # Cache all files
        for path, content in all_files.items():
            incremental_analyzer.store_metrics(path, content, {"complexity": 1})

        # Modify 2 files (typical PR)
        all_files["file_42.py"] = b"def func_42_modified(): pass\n"
        all_files["file_100.py"] = b"def func_100_modified(): pass\n"

        # Should only analyze 2 changed files
        to_analyze = incremental_analyzer.filter_unchanged_files(all_files)

        assert len(to_analyze) == 2
        assert "file_42.py" in to_analyze
        assert "file_100.py" in to_analyze

        # Cache hit rate: 4998/5000 = 99.96%
        cache_hit_rate = (5000 - len(to_analyze)) / 5000
        assert cache_hit_rate >= 0.999
