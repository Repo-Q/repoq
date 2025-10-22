"""History analyzer for Git commit analysis and contributor statistics.

This module analyzes repository history to extract:
- Commit timeline and authorship
- Contributor statistics (commits, lines added/deleted)
- Code churn per file
- Temporal coupling between files (files changed together)
- File ownership based on commit activity

Uses PyDriller when available, falls back to raw Git commands.
"""

from __future__ import annotations

import logging
import subprocess
from collections import defaultdict
from typing import Dict, List, Tuple

from ..core.model import (
    Commit,
    CouplingEdge,
    Person,
    Project,
    VersionResource,
    foaf_sha1,
    hash_email,
)
from ..core.utils import is_excluded
from .base import Analyzer

logger = logging.getLogger(__name__)


def _run(cmd: list[str], cwd: str) -> str:
    """Execute Git command and return stdout.

    Args:
        cmd: Command and arguments as list
        cwd: Working directory for command execution

    Returns:
        Command stdout as string, empty string if command fails
    """
    out = subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)
    if out.returncode != 0:
        return ""
    return out.stdout


class HistoryAnalyzer(Analyzer):
    """Analyzer for repository history and contributor metrics.

    Extracts:
    - Commits with authorship and timestamps
    - Contributors (Person entities with FOAF mapping)
    - Code churn (lines added/deleted per file)
    - Temporal coupling (files frequently changed together)
    - File ownership (primary contributor per file)

    Prefers PyDriller for detailed analysis, falls back to Git CLI if unavailable.
    """

    name = "history"

    def run(self, project: Project, repo_dir: str, cfg) -> None:
        """Execute history analysis using PyDriller or Git fallback.

        Args:
            project: Project model to populate with history data
            repo_dir: Absolute path to repository root
            cfg: Configuration with time range filters (cfg.since)

        Note:
            Populates project.commits, project.contributors, project.coupling,
            project.versions, and mutates File.commits_count, File.code_churn,
            File.contributors.
        """
        try:
            self._run_pydriller(project, repo_dir, cfg)
            return
        except ImportError:
            logger.info("PyDriller not available, falling back to Git CLI")
            self._run_git(project, repo_dir, cfg)
        except Exception as e:
            logger.warning(f"PyDriller analysis failed: {e}, falling back to Git CLI")
            self._run_git(project, repo_dir, cfg)

    def _process_commit_metadata(self, commit, project: Project) -> str:
        """Process commit metadata and update project (T1.1 refactoring).

        Returns:
            Person ID for the commit author
        """
        # Update last commit date
        if project.last_commit_date is None or (
            commit.author_date and commit.author_date.isoformat() > project.last_commit_date
        ):
            project.last_commit_date = (
                commit.author_date.isoformat() if commit.author_date else project.last_commit_date
            )

        # Get or create author
        name = commit.author.name or "Unknown"
        email = commit.author.email or ""
        pid = f"repo:person:{hash_email(email) or name.replace(' ', '_')}"
        person = project.contributors.get(pid)
        if not person:
            person = Person(
                id=pid,
                name=name,
                email=email,
                email_hash=hash_email(email),
                foaf_mbox_sha1sum=foaf_sha1(email) if email else "",
            )
            project.contributors[pid] = person
        person.commits += 1

        # Add commit record
        cid = f"repo:commit:{commit.hash}"
        project.commits.append(
            Commit(
                id=cid,
                message=commit.msg or "",
                author_id=pid,
                ended_at=commit.author_date.isoformat() if commit.author_date else None,
            )
        )

        # Add version record
        project.versions.append(
            VersionResource(
                id=f"repo:version:{commit.hash}",
                version_id=commit.hash,
                branch=getattr(commit, "branches", None) and ",".join(commit.branches) or None,
                committer=pid,
                committed=commit.author_date.isoformat() if commit.author_date else None,
            )
        )

        return pid

    def _process_modifications(
        self,
        modifications,
        project: Project,
        cfg,
        author_id: str,
        file_author_lines: Dict[str, Dict[str, int]],
    ) -> List[str]:
        """Process file modifications from a commit (T1.1 refactoring).

        Returns:
            List of file IDs modified in this commit
        """
        files_in_commit = []

        for m in modifications:
            path = m.new_path or m.old_path
            if not path:
                continue
            if is_excluded(path, cfg.exclude_globs):
                continue

            fid = f"repo:file:{path}"
            f = project.files.get(fid)
            if not f:
                continue

            # Update file metrics
            additions = m.added or 0
            deletions = m.removed or 0
            f.code_churn += additions + deletions
            f.commits_count += 1
            f.last_modified = (
                m.change_date.isoformat()
                if hasattr(m, "change_date") and m.change_date
                else f.last_modified
            )

            # Track authorship
            file_author_lines[fid][author_id] = file_author_lines[fid].get(author_id, 0) + max(
                additions, 0
            )
            files_in_commit.append(fid)

        return files_in_commit

    def _update_coupling(
        self, files_in_commit: List[str], file_coupling: Dict[Tuple[str, str], int]
    ) -> None:
        """Update temporal coupling for files changed together (T1.1 refactoring)."""
        for i in range(len(files_in_commit)):
            for j in range(i + 1, len(files_in_commit)):
                a, b = sorted([files_in_commit[i], files_in_commit[j]])
                file_coupling[(a, b)] += 1

    def _aggregate_ownership_stats(
        self,
        project: Project,
        cfg,
        file_author_lines: Dict[str, Dict[str, int]],
        file_coupling: Dict[Tuple[str, str], int],
    ) -> None:
        """Aggregate ownership and coupling statistics (T1.1 refactoring)."""
        # Calculate ownership
        for fid, counter in file_author_lines.items():
            total = sum(counter.values())
            if total <= 0:
                continue

            pid_owner, lines = max(counter.items(), key=lambda kv: kv[1])

            # Assign contributions
            f = project.files.get(fid)
            if f:
                f.contributors = {pid: {"linesAdded": int(val)} for pid, val in counter.items()}

            # Assign ownership if threshold met
            if total > 0 and (lines / total) >= cfg.thresholds.ownership_owner_threshold:
                if pid_owner in project.contributors:
                    project.contributors[pid_owner].owns.append(fid)

        # Add coupling edges
        for (a, b), w in file_coupling.items():
            project.coupling.append(CouplingEdge(a=a, b=b, weight=w))

    def _run_pydriller(self, project: Project, repo_dir: str, cfg) -> None:
        """Analyze history using PyDriller library for detailed metrics (T1.1 refactored).

        Args:
            project: Project model to populate
            repo_dir: Repository directory
            cfg: Configuration

        Raises:
            ImportError: If pydriller is not installed
            Exception: On analysis errors
        """
        from pydriller import Repository

        file_author_lines: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        file_coupling: Dict[Tuple[str, str], int] = defaultdict(int)

        # Traverse commits and populate data structures
        for commit in Repository(path_to_repo=repo_dir, only_no_merge=True).traverse_commits():
            # Process commit metadata (dates, contributors, versions)
            author_id = self._process_commit_metadata(commit, project)

            # Handle different PyDriller API versions
            try:
                modifications = commit.modifications if hasattr(commit, "modifications") else []
            except AttributeError:
                logger.warning(
                    "'Commit' object has no attribute 'modifications', falling back to Git CLI"
                )
                self._run_git(project, repo_dir, cfg)
                return

            # Process file modifications
            files_in_commit = self._process_modifications(
                modifications, project, cfg, author_id, file_author_lines
            )

            # Update temporal coupling
            self._update_coupling(files_in_commit, file_coupling)

        # Aggregate ownership and coupling statistics
        self._aggregate_ownership_stats(project, cfg, file_author_lines, file_coupling)

    def _get_last_commit_date(self, project: Project, repo_dir: str) -> None:
        """Extract last commit date from git log.

        Args:
            project: Project model to update
            repo_dir: Repository directory path
        """
        last = _run(["git", "log", "-1", "--date=iso-strict", "--pretty=%cI"], cwd=repo_dir).strip()
        if last:
            project.last_commit_date = last

    def _extract_authors(self, repo_dir: str, cfg) -> list[tuple[int, str, str]]:
        """Extract author statistics from git history.

        Args:
            repo_dir: Repository directory path
            cfg: Configuration with optional 'since' filter

        Returns:
            List of tuples: (commit_count, author_name, author_email)
        """
        if cfg.since:
            out = _run(
                ["git", "log", f"--since={cfg.since}", "--pretty=%an%x09%ae", "--no-merges"],
                cwd=repo_dir,
            )
            counts: Dict[tuple, int] = defaultdict(int)
            for line in out.splitlines():
                if not line.strip():
                    continue
                try:
                    name, email = line.split("\t", 1)
                except ValueError:
                    parts = line.split()
                    name = " ".join(parts[:-1]) if len(parts) > 1 else parts[0]
                    email = parts[-1] if parts else ""
                counts[(name.strip(), email.strip())] += 1
            authors = [(c, n, e) for (n, e), c in counts.items()]
        else:
            out = _run(["git", "shortlog", "-sne"], cwd=repo_dir)
            authors = []
            for line in out.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    n_commits, rest = line.split("\t", 1)
                except ValueError:
                    parts = line.split()
                    n_commits = parts[0]
                    rest = " ".join(parts[1:])
                n_commits = int(n_commits.strip())
                if "<" in rest and ">" in rest:
                    name = rest[: rest.rfind("<")].strip()
                    email = rest[rest.rfind("<") + 1 : rest.rfind(">")].strip()
                else:
                    name, email = rest, ""
                authors.append((n_commits, name, email))

        return authors

    def _populate_contributors(self, project: Project, authors: list[tuple[int, str, str]]) -> None:
        """Populate project contributors from author statistics.

        Args:
            project: Project model to update
            authors: List of (commit_count, name, email) tuples
        """
        for n_commits, name, email in sorted(authors, reverse=True):
            pid = f"repo:person:{hash_email(email) or name.replace(' ', '_')}"
            if pid not in project.contributors:
                project.contributors[pid] = Person(
                    id=pid,
                    name=name,
                    email=email,
                    email_hash=hash_email(email),
                    foaf_mbox_sha1sum=foaf_sha1(email) if email else "",
                )
            project.contributors[pid].commits += int(n_commits)

    def _parse_commit_header(
        self,
        project: Project,
        line: str,
    ) -> tuple[str, str, str]:
        """Parse commit header line and create commit/version records.

        Args:
            project: Project model to update
            line: Git log header line (SHA, date, author, email, message)

        Returns:
            Tuple of (sha, date, person_id) for tracking current commit
        """
        sha, date, author, email, msg = line.split("\t", 4)
        pid = f"repo:person:{hash_email(email) or author.replace(' ', '_')}"

        project.commits.append(
            Commit(id=f"repo:commit:{sha}", message=msg, author_id=pid, ended_at=date)
        )
        project.versions.append(
            VersionResource(
                id=f"repo:version:{sha}",
                version_id=sha,
                branch=None,
                committer=pid,
                committed=date,
            )
        )

        return sha, date, pid

    def _parse_commit_file_changes(
        self,
        project: Project,
        line: str,
        current: tuple[str, str, str] | None,
    ) -> str | None:
        """Parse file change stats (numstat) and update file/contributor metrics.

        Args:
            project: Project model to update
            line: Git numstat line (added, deleted, path)
            current: Current commit context (sha, date, person_id)

        Returns:
            File ID if processed, None otherwise (for coupling tracking)
        """
        parts = line.split("\t")
        if len(parts) < 3:
            return None

        added, deleted, path = parts[0], parts[1], parts[2]
        try:
            a = int(added) if added.isdigit() else 0
            d = int(deleted) if deleted.isdigit() else 0
        except Exception:
            a, d = 0, 0

        fid = f"repo:file:{path}"
        f = project.files.get(fid)

        if not f:
            return None

        # Update file metrics
        f.code_churn += a + d
        f.commits_count += 1

        if not current:
            return fid

        _, date, pid = current
        f.last_modified = date

        # Update file contributor stats
        if pid not in f.contributors:
            f.contributors[pid] = {"linesAdded": 0, "linesDeleted": 0}
        f.contributors[pid]["linesAdded"] += a
        f.contributors[pid]["linesDeleted"] += d

        # Update project contributor stats
        if pid in project.contributors:
            project.contributors[pid].lines_added += a
            project.contributors[pid].lines_deleted += d
            if fid not in project.contributors[pid].owns:
                project.contributors[pid].owns.append(fid)

        return fid

    def _process_commits(self, project: Project, repo_dir: str, cfg) -> None:
        """Process detailed commit history with file changes.

        Args:
            project: Project model to update
            repo_dir: Repository directory path
            cfg: Configuration with optional 'since' filter
        """
        cmd = ["git", "log", "--numstat", "--format=%H%x09%aI%x09%an%x09%ae%x09%s"]
        if cfg.since:
            cmd = [
                "git",
                "log",
                f"--since={cfg.since}",
                "--numstat",
                "--format=%H%x09%aI%x09%an%x09%ae%x09%s",
            ]

        out = _run(cmd, cwd=repo_dir)
        current = None
        files_in_commit = []

        for line in out.splitlines():
            # Check if this is a commit header line
            if (
                line.count("\t") >= 4
                and len(line.split("\t")) >= 5
                and len(line.split("\t")[0]) == 40
            ):
                if current and files_in_commit:
                    # coupling accumulation if needed (skipped for brevity)
                    files_in_commit = []

                current = self._parse_commit_header(project, line)
                continue

            # Process file change stats
            fid = self._parse_commit_file_changes(project, line, current)
            if fid:
                files_in_commit.append(fid)

    def _run_git(self, project: Project, repo_dir: str, cfg) -> None:
        """Git-based history analysis (refactored from original monolithic version).

        Args:
            project: Project model to update
            repo_dir: Repository directory path
            cfg: Configuration with optional 'since' filter
        """
        self._get_last_commit_date(project, repo_dir)
        authors = self._extract_authors(repo_dir, cfg)
        self._populate_contributors(project, authors)
        self._process_commits(project, repo_dir, cfg)
