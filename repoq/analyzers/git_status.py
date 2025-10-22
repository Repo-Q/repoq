"""Git working directory status analyzer.

STRATIFICATION_LEVEL: 0 (base repository analysis, no self-reference)

This analyzer detects "dirty" repository state that may affect analysis quality:
- Uncommitted changes (staged/unstaged)
- Untracked files
- Merge conflicts
- Detached HEAD state
- Diverged branches

These indicators help ensure analysis reproducibility and warn about
uncommitted work that may skew metrics.

Algorithm:
    1. Run `git status --porcelain=v2` for machine-readable output
    2. Parse status codes (M=modified, A=added, D=deleted, U=unmerged, ?=untracked)
    3. Check for detached HEAD (`git symbolic-ref HEAD`)
    4. Check branch tracking status (`git rev-list --left-right --count`)
    5. Generate warnings/issues for dirty state

Safety:
- Read-only (no git operations modify state)
- Deterministic (same git state → same output)
- Terminating (fixed set of git commands)
"""

from __future__ import annotations

import logging
import subprocess  # nosec B404 # Required for git commands
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from ..config import AnalyzeConfig
from ..core.model import Issue, Project
from .base import Analyzer

logger = logging.getLogger(__name__)


@dataclass
class GitStatusReport:
    """Git working directory status summary.

    Attributes:
        is_clean: True if no uncommitted changes or untracked files
        staged_files: List of file paths with staged changes
        unstaged_files: List of file paths with unstaged changes
        untracked_files: List of untracked file paths
        conflicted_files: List of files with merge conflicts
        detached_head: True if HEAD is detached
        branch: Current branch name (or None if detached)
        ahead: Commits ahead of remote (or None if no tracking)
        behind: Commits behind remote (or None if no tracking)
    """

    is_clean: bool
    staged_files: List[str]
    unstaged_files: List[str]
    untracked_files: List[str]
    conflicted_files: List[str]
    detached_head: bool
    branch: Optional[str]
    ahead: Optional[int]
    behind: Optional[int]

    @property
    def total_dirty_files(self) -> int:
        """Total number of files in dirty state."""
        return len(self.staged_files) + len(self.unstaged_files) + len(self.untracked_files)


class GitStatusAnalyzer(Analyzer):
    """Analyze Git working directory status for dirty state detection.

    Detects:
    - Uncommitted changes (staged/unstaged modifications)
    - Untracked files (not in .gitignore)
    - Merge conflicts (unmerged files)
    - Detached HEAD state
    - Branch divergence (ahead/behind remote)

    Generates warnings as Issue objects for non-clean state.
    """

    name = "git_status"

    def run(self, project: Project, repo_dir: str, cfg: AnalyzeConfig) -> None:
        """Run git status analysis.

        Args:
            project: Project model to populate
            repo_dir: Repository directory path
            cfg: Analysis configuration

        Note:
            Populates project.issues with git status warnings.
            Adds project.git_status (non-standard field) with GitStatusReport.
        """
        logger.info("Running git status analysis...")

        try:
            report = self._analyze_git_status(Path(repo_dir))

            # Attach report to project (for downstream consumers)
            project.__dict__["git_status"] = report

            # Generate issues for dirty state
            issues_count = self._generate_issues(project, report)

            logger.info(
                f"Git status analysis complete: "
                f"{'CLEAN' if report.is_clean else 'DIRTY'} "
                f"({report.total_dirty_files} dirty files, {issues_count} warnings)"
            )

        except Exception as e:
            logger.warning(f"Git status analysis failed: {e}")
            # Non-fatal: project may not be a git repo

    def _analyze_git_status(self, repo_dir: Path) -> GitStatusReport:
        """Analyze git working directory status.

        Args:
            repo_dir: Path to repository root

        Returns:
            GitStatusReport with current state
        """
        # 1. Parse git status --porcelain=v2
        staged, unstaged, untracked, conflicted = self._parse_git_status(repo_dir)

        # 2. Check for detached HEAD
        branch, detached_head = self._check_head_state(repo_dir)

        # 3. Check branch tracking status
        ahead, behind = self._check_tracking_status(repo_dir, branch)

        # Clean = no changes, no untracked, no conflicts
        is_clean = (
            len(staged) == 0 and len(unstaged) == 0 and len(untracked) == 0 and len(conflicted) == 0
        )

        return GitStatusReport(
            is_clean=is_clean,
            staged_files=staged,
            unstaged_files=unstaged,
            untracked_files=untracked,
            conflicted_files=conflicted,
            detached_head=detached_head,
            branch=branch,
            ahead=ahead,
            behind=behind,
        )

    def _parse_git_status(
        self, repo_dir: Path
    ) -> tuple[List[str], List[str], List[str], List[str]]:
        """Parse git status --porcelain=v2 output.

        Returns:
            Tuple of (staged_files, unstaged_files, untracked_files, conflicted_files)
        """
        try:
            result = subprocess.run(  # nosec B603, B607 # git command with fixed args
                ["git", "status", "--porcelain=v2"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                return [], [], [], []

            staged = []
            unstaged = []
            untracked = []
            conflicted = []

            for line in result.stdout.splitlines():
                if not line.strip():
                    continue

                # Porcelain v2 format:
                # 1 XY <sub> <mH> <mI> <mW> <hH> <hI> <path>
                # 2 XY <sub> <mH> <mI> <mW> <hH> <hI> X<score> <path><sep><origPath>
                # u XY <sub> <m1> <m2> <m3> <mW> <h1> <h2> <h3> <path>
                # ? <path>
                # ! <path>

                if line.startswith("1 ") or line.startswith("2 "):
                    # Changed entry
                    parts = line.split()
                    xy = parts[1]  # XY status code
                    path = parts[-1]

                    # X = staged, Y = unstaged
                    if xy[0] != ".":
                        staged.append(path)
                    if xy[1] != ".":
                        unstaged.append(path)

                elif line.startswith("u "):
                    # Unmerged (conflict)
                    parts = line.split()
                    path = parts[-1]
                    conflicted.append(path)

                elif line.startswith("? "):
                    # Untracked
                    path = line[2:].strip()
                    untracked.append(path)

            return staged, unstaged, untracked, conflicted

        except Exception as e:
            logger.debug(f"Failed to parse git status: {e}")
            return [], [], [], []

    def _check_head_state(self, repo_dir: Path) -> tuple[Optional[str], bool]:
        """Check if HEAD is detached and get current branch.

        Returns:
            Tuple of (branch_name, is_detached)
        """
        try:
            # Try to get symbolic ref (fails if detached)
            result = subprocess.run(  # nosec B603, B607 # git command with fixed args
                ["git", "symbolic-ref", "--short", "HEAD"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                # Not detached
                branch = result.stdout.strip()
                return branch, False
            else:
                # Detached HEAD
                return None, True

        except Exception as e:
            logger.debug(f"Failed to check HEAD state: {e}")
            return None, False

    def _check_tracking_status(
        self, repo_dir: Path, branch: Optional[str]
    ) -> tuple[Optional[int], Optional[int]]:
        """Check commits ahead/behind remote tracking branch.

        Returns:
            Tuple of (ahead_count, behind_count) or (None, None) if no tracking
        """
        if not branch:
            return None, None

        try:
            # Get remote tracking branch
            result = subprocess.run(  # nosec B603, B607 # git command with fixed args
                ["git", "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                # No tracking branch
                return None, None

            upstream = result.stdout.strip()

            # Count commits ahead/behind
            result = subprocess.run(  # nosec B603, B607 # git command with fixed args
                ["git", "rev-list", "--left-right", "--count", f"{branch}...{upstream}"],
                cwd=repo_dir,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                ahead_str, behind_str = result.stdout.strip().split()
                return int(ahead_str), int(behind_str)

            return None, None

        except Exception as e:
            logger.debug(f"Failed to check tracking status: {e}")
            return None, None

    def _generate_issues(self, project: Project, report: GitStatusReport) -> int:
        """Generate Issue objects for dirty git state.

        Args:
            project: Project to add issues to
            report: GitStatusReport

        Returns:
            Number of issues generated
        """
        issues_count = 0

        # Issue 1: Uncommitted changes
        if report.staged_files or report.unstaged_files:
            total = len(report.staged_files) + len(report.unstaged_files)
            issue = Issue(
                id=f"{project.id}:issue:git:uncommitted",
                type="repo:GitUncommittedChanges",
                file_id=None,
                description=(
                    f"Repository has {total} uncommitted changes "
                    f"({len(report.staged_files)} staged, {len(report.unstaged_files)} unstaged). "
                    "Commit changes before analysis for reproducible results."
                ),
                severity="medium",
                priority="medium",
                status="Open",
                title="Uncommitted changes detected",
                metadata={"analyzer": "GitStatusAnalyzer", "category": "repo_hygiene"},
            )
            project.issues[issue.id] = issue
            issues_count += 1

        # Issue 2: Untracked files
        if report.untracked_files:
            issue = Issue(
                id=f"{project.id}:issue:git:untracked",
                type="repo:GitUntrackedFiles",
                file_id=None,
                description=(
                    f"Repository has {len(report.untracked_files)} untracked files. "
                    "Add to .gitignore or commit them. "
                    f"Examples: {', '.join(report.untracked_files[:5])}"
                ),
                severity="low",
                priority="low",
                status="Open",
                title=f"{len(report.untracked_files)} untracked files",
                metadata={"analyzer": "GitStatusAnalyzer", "category": "repo_hygiene"},
            )
            project.issues[issue.id] = issue
            issues_count += 1

        # Issue 3: Merge conflicts
        if report.conflicted_files:
            issue = Issue(
                id=f"{project.id}:issue:git:conflicts",
                type="repo:GitMergeConflicts",
                file_id=None,
                description=(
                    f"Repository has {len(report.conflicted_files)} unresolved merge conflicts. "
                    f"Files: {', '.join(report.conflicted_files)}"
                ),
                severity="high",
                priority="high",
                status="Open",
                title="Merge conflicts detected",
                metadata={"analyzer": "GitStatusAnalyzer", "category": "repo_hygiene"},
            )
            project.issues[issue.id] = issue
            issues_count += 1

        # Issue 4: Detached HEAD
        if report.detached_head:
            issue = Issue(
                id=f"{project.id}:issue:git:detached_head",
                type="repo:GitDetachedHead",
                file_id=None,
                description=(
                    "Repository is in detached HEAD state. "
                    "Checkout a branch or create new one before committing."
                ),
                severity="medium",
                priority="medium",
                status="Open",
                title="Detached HEAD state",
                metadata={"analyzer": "GitStatusAnalyzer", "category": "repo_hygiene"},
            )
            project.issues[issue.id] = issue
            issues_count += 1

        # Issue 5: Branch diverged
        if report.ahead and report.ahead > 0:
            issue = Issue(
                id=f"{project.id}:issue:git:ahead",
                type="repo:GitBranchAhead",
                file_id=None,
                description=(
                    f"Branch '{report.branch}' is {report.ahead} commits ahead of remote. "
                    "Push changes to sync with remote."
                ),
                severity="low",
                priority="low",
                status="Open",
                title=f"Branch ahead by {report.ahead} commits",
                metadata={"analyzer": "GitStatusAnalyzer", "category": "repo_hygiene"},
            )
            project.issues[issue.id] = issue
            issues_count += 1

        if report.behind and report.behind > 0:
            issue = Issue(
                id=f"{project.id}:issue:git:behind",
                type="repo:GitBranchBehind",
                file_id=None,
                description=(
                    f"Branch '{report.branch}' is {report.behind} commits behind remote. "
                    "Pull changes to sync with remote."
                ),
                severity="low",
                priority="low",
                status="Open",
                title=f"Branch behind by {report.behind} commits",
                metadata={"analyzer": "GitStatusAnalyzer", "category": "repo_hygiene"},
            )
            project.issues[issue.id] = issue
            issues_count += 1

        return issues_count
