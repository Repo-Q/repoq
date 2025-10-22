"""Tests for GitStatusAnalyzer."""

import tempfile
from pathlib import Path
from subprocess import run

import pytest

from repoq.analyzers.git_status import GitStatusAnalyzer
from repoq.config import AnalyzeConfig
from repoq.core.model import Project


@pytest.fixture
def git_repo():
    """Create temporary git repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Initialize git repo
        run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)
        run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True)

        # Create initial commit
        (repo_path / "file1.py").write_text("print('hello')")
        run(["git", "add", "."], cwd=repo_path, check=True)
        run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, check=True)

        yield repo_path


def test_clean_repository(git_repo):
    """Test clean repository (no uncommitted changes)."""
    analyzer = GitStatusAnalyzer()
    report = analyzer._analyze_git_status(git_repo)

    assert report.is_clean
    assert len(report.staged_files) == 0
    assert len(report.unstaged_files) == 0
    assert len(report.untracked_files) == 0
    assert len(report.conflicted_files) == 0
    assert not report.detached_head


def test_uncommitted_changes_staged(git_repo):
    """Test staged changes."""
    # Modify file and stage
    (git_repo / "file1.py").write_text("print('world')")
    run(["git", "add", "file1.py"], cwd=git_repo, check=True)

    analyzer = GitStatusAnalyzer()
    report = analyzer._analyze_git_status(git_repo)

    assert not report.is_clean
    assert "file1.py" in report.staged_files
    assert len(report.unstaged_files) == 0


def test_uncommitted_changes_unstaged(git_repo):
    """Test unstaged changes."""
    # Modify file without staging
    (git_repo / "file1.py").write_text("print('world')")

    analyzer = GitStatusAnalyzer()
    report = analyzer._analyze_git_status(git_repo)

    assert not report.is_clean
    assert len(report.staged_files) == 0
    assert "file1.py" in report.unstaged_files


def test_untracked_files(git_repo):
    """Test untracked files."""
    # Create new file
    (git_repo / "file2.py").write_text("print('new')")

    analyzer = GitStatusAnalyzer()
    report = analyzer._analyze_git_status(git_repo)

    assert not report.is_clean
    assert "file2.py" in report.untracked_files


def test_generate_issues(git_repo):
    """Test issue generation for dirty state."""
    # Create uncommitted changes
    (git_repo / "file1.py").write_text("print('world')")
    run(["git", "add", "file1.py"], cwd=git_repo, check=True)

    # Create untracked file
    (git_repo / "file2.py").write_text("print('new')")

    # Run analyzer
    project = Project(id="repo:test", name="test")
    cfg = AnalyzeConfig(mode="full")
    analyzer = GitStatusAnalyzer()
    analyzer.run(project, str(git_repo), cfg)

    # Check issues generated
    assert len(project.issues) >= 2  # At least uncommitted + untracked

    # Check uncommitted issue
    uncommitted_issues = [
        i for i in project.issues.values() if i.type == "repo:GitUncommittedChanges"
    ]
    assert len(uncommitted_issues) == 1
    assert uncommitted_issues[0].severity == "medium"

    # Check untracked issue
    untracked_issues = [i for i in project.issues.values() if i.type == "repo:GitUntrackedFiles"]
    assert len(untracked_issues) == 1
    assert untracked_issues[0].severity == "low"


def test_detached_head(git_repo):
    """Test detached HEAD detection."""
    # Checkout specific commit (detaches HEAD)
    result = run(
        ["git", "rev-parse", "HEAD"], cwd=git_repo, check=True, capture_output=True, text=True
    )
    commit_sha = result.stdout.strip()
    run(["git", "checkout", commit_sha], cwd=git_repo, check=True, capture_output=True)

    analyzer = GitStatusAnalyzer()
    report = analyzer._analyze_git_status(git_repo)

    assert report.detached_head
    assert report.branch is None


def test_branch_tracking(git_repo):
    """Test branch ahead/behind detection."""
    # Setup requires remote, skip if not in CI
    # This is a placeholder for full integration test
    analyzer = GitStatusAnalyzer()
    report = analyzer._analyze_git_status(git_repo)

    # In local repo without remote, ahead/behind should be None
    assert report.ahead is None
    assert report.behind is None


def test_total_dirty_files(git_repo):
    """Test total_dirty_files property."""
    # Create mixed dirty state
    (git_repo / "file1.py").write_text("print('world')")  # Unstaged
    run(["git", "add", "file1.py"], cwd=git_repo, check=True)  # Now staged

    (git_repo / "file2.py").write_text("print('new')")  # Untracked

    analyzer = GitStatusAnalyzer()
    report = analyzer._analyze_git_status(git_repo)

    assert report.total_dirty_files == 2  # 1 staged + 1 untracked
