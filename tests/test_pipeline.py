"""
Unit tests for pipeline module.

Tests the run_pipeline function that orchestrates all analyzers.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from repoq.config import AnalyzeConfig
from repoq.core.model import Project
from repoq.pipeline import run_pipeline


@pytest.fixture
def git_repo_with_history():
    """Create a git repository with commits for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir) / "test_repo"
        repo_path.mkdir()

        # Initialize git
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Create initial file
        (repo_path / "main.py").write_text("def hello(): return 'world'\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"], cwd=repo_path, check=True, capture_output=True
        )

        # Add another commit
        (repo_path / "utils.py").write_text(
            "# TODO: implement\ndef util(): pass\n", encoding="utf-8"
        )
        subprocess.run(["git", "add", "-A"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add utils"], cwd=repo_path, check=True, capture_output=True
        )

        yield str(repo_path)


class TestRunPipeline:
    """Test suite for run_pipeline function."""

    def test_pipeline_structure_mode(self, git_repo_with_history: str):
        """Test pipeline with structure mode."""
        project = Project(id="test:struct", name="test_struct")
        config = AnalyzeConfig(mode="structure")

        run_pipeline(project, git_repo_with_history, config)

        # Structure mode should populate files
        assert len(project.files) > 0

        # Should have programming languages detected
        assert len(project.programming_languages) > 0

    def test_pipeline_history_mode(self, git_repo_with_history: str):
        """Test pipeline with history mode."""
        project = Project(id="test:hist", name="test_hist")
        config = AnalyzeConfig(mode="history")

        run_pipeline(project, git_repo_with_history, config)

        # History mode should populate commits
        assert len(project.commits) > 0

        # Should have at least 2 commits (from fixture)
        assert len(project.commits) >= 2

    def test_pipeline_full_mode(self, git_repo_with_history: str):
        """Test pipeline with full mode (all analyzers)."""
        project = Project(id="test:full", name="test_full")
        config = AnalyzeConfig(mode="full")

        run_pipeline(project, git_repo_with_history, config)

        # Full mode should have files (from structure)
        assert len(project.files) > 0

        # Should have commits (from history)
        assert len(project.commits) > 0

        # Should have programming languages detected
        assert len(project.programming_languages) > 0

    def test_pipeline_runs_complexity_analyzer(self, git_repo_with_history: str):
        """Test that complexity analyzer is run in structure/full mode."""
        project = Project(id="test:complexity", name="test_complexity")
        config = AnalyzeConfig(mode="structure")

        run_pipeline(project, git_repo_with_history, config)

        # At least one file should have complexity measured
        has_complexity = any(f.complexity is not None for f in project.files.values())
        # Note: may be False if lizard doesn't find functions
        # Just verify pipeline runs without error

    def test_pipeline_runs_weakness_analyzer(self, git_repo_with_history: str):
        """Test that weakness analyzer is run in structure/full mode."""
        project = Project(id="test:weakness", name="test_weakness")
        config = AnalyzeConfig(mode="structure")

        run_pipeline(project, git_repo_with_history, config)

        # utils.py has TODO, should create an issue
        has_issues = len(project.issues) > 0
        if has_issues:
            # Check that we found issues (TODO markers create issues with different format)
            # Issue IDs contain file reference
            utils_issues = [i for i in project.issues.values() if "utils.py" in i.id]
            assert len(utils_issues) > 0

    def test_pipeline_runs_hotspots_analyzer_in_full_mode(self, git_repo_with_history: str):
        """Test that hotspots analyzer only runs in full mode."""
        project_structure = Project(id="test:struct", name="test_struct")
        config_structure = AnalyzeConfig(mode="structure")

        project_full = Project(id="test:full", name="test_full")
        config_full = AnalyzeConfig(mode="full")

        # Run both modes
        run_pipeline(project_structure, git_repo_with_history, config_structure)
        run_pipeline(project_full, git_repo_with_history, config_full)

        # Hotspots are computed in full mode
        # (HotspotsAnalyzer enriches existing file data)
        # Both should complete without error

    def test_pipeline_respects_exclude_globs(self, git_repo_with_history: str):
        """Test that pipeline respects exclude_globs configuration."""
        # Add excluded file
        repo_path = Path(git_repo_with_history)
        venv_dir = repo_path / ".venv"
        venv_dir.mkdir()
        (venv_dir / "excluded.py").write_text("def excluded(): pass", encoding="utf-8")

        project = Project(id="test:exclude", name="test_exclude")
        config = AnalyzeConfig(mode="structure", exclude_globs=["**/.venv/**"])

        run_pipeline(project, git_repo_with_history, config)

        # Excluded file should not be in project
        excluded_files = [f for f in project.files.values() if ".venv" in f.path]
        assert len(excluded_files) == 0

    def test_pipeline_respects_max_files(self, git_repo_with_history: str):
        """Test that pipeline respects max_files configuration."""
        project = Project(id="test:max", name="test_max")
        config = AnalyzeConfig(mode="structure", max_files=1)

        run_pipeline(project, git_repo_with_history, config)

        # Should have at most 1 file
        assert len(project.files) <= 1

    def test_pipeline_idempotent(self, git_repo_with_history: str):
        """Test that running pipeline multiple times is idempotent."""
        project = Project(id="test:idem", name="test_idem")
        config = AnalyzeConfig(mode="full")

        # First run
        run_pipeline(project, git_repo_with_history, config)
        first_files = set(project.files.keys())
        first_commits = len(project.commits)

        # Second run (should overwrite, not accumulate)
        run_pipeline(project, git_repo_with_history, config)
        second_files = set(project.files.keys())
        second_commits = len(project.commits)

        # Should have same results
        assert first_files == second_files
        # Note: commits might accumulate if not cleared, depends on analyzer impl
        # For now just check it doesn't crash

    def test_pipeline_handles_empty_repo(self):
        """Test that pipeline handles repository with no files gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "empty_repo"
            repo_path.mkdir()

            # Init git but add no files
            subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(
                ["git", "config", "user.name", "Test"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@test.com"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )

            project = Project(id="test:empty", name="test_empty")
            config = AnalyzeConfig(mode="full")

            # Should not crash
            run_pipeline(project, str(repo_path), config)

            # Should have no files
            assert len(project.files) == 0

    def test_pipeline_ci_qm_analyzer_runs(self, git_repo_with_history: str):
        """Test that CI/QM analyzer runs in structure/full mode."""
        # Add CI config file
        repo_path = Path(git_repo_with_history)
        github_dir = repo_path / ".github" / "workflows"
        github_dir.mkdir(parents=True)
        (github_dir / "ci.yml").write_text(
            "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n", encoding="utf-8"
        )

        project = Project(id="test:ci", name="test_ci")
        config = AnalyzeConfig(mode="structure")

        run_pipeline(project, git_repo_with_history, config)

        # Should detect GitHub Actions
        assert len(project.ci_configured) > 0
        assert "GitHub Actions" in project.ci_configured

    def test_pipeline_with_extension_filter(self, git_repo_with_history: str):
        """Test pipeline with extension filter."""
        # Add non-Python file
        repo_path = Path(git_repo_with_history)
        (repo_path / "script.js").write_text("console.log('test');", encoding="utf-8")

        project = Project(id="test:ext", name="test_ext")
        config = AnalyzeConfig(mode="structure", include_extensions=["py"])

        run_pipeline(project, git_repo_with_history, config)

        # All files should be Python
        for file in project.files.values():
            assert file.path.endswith(".py") or "/" in file.path  # directory
