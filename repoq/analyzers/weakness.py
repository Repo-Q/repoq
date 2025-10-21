"""Weakness analyzer for detecting code quality markers and technical debt.

This module scans source code for patterns indicating potential issues:
- TODO/FIXME/HACK comments (technical debt markers)
- Deprecated code markers
- Bug/fix-related comments

These markers help identify areas requiring attention, refactoring, or removal.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from ..core.model import Issue, Project
from .base import Analyzer

logger = logging.getLogger(__name__)

PATTERNS = [
    ("repo:TodoComment", re.compile(r"\b(TODO|FIXME|@todo|HACK)\b", re.IGNORECASE)),
    ("repo:Deprecated", re.compile(r"\bdeprecated\b", re.IGNORECASE)),
    ("repo:Bugfix", re.compile(r"\bfix(e[ds])?|bug|error\b", re.IGNORECASE)),
]


def _severity_for(match_type: str) -> str:
    """Determine issue severity based on marker type.

    Args:
        match_type: Issue type identifier (e.g., "repo:Deprecated")

    Returns:
        Severity level: "medium" for Deprecated/Bugfix, "low" for others
    """
    if "Deprecated" in match_type:
        return "medium"
    if "Bugfix" in match_type:
        return "medium"
    return "low"


class WeaknessAnalyzer(Analyzer):
    """Analyzer for code weakness patterns and technical debt markers.

    Scans source files for regex patterns indicating:
    - TODO/FIXME/HACK comments (low severity)
    - Deprecated code markers (medium severity)
    - Bug/fix-related comments (medium severity)

    Creates Issue entities for each detected pattern and links them to files.
    """

    name = "weakness"

    def run(self, project: Project, repo_dir: str, cfg) -> None:
        """Scan files for weakness patterns and create issues.

        Args:
            project: Project model with files to scan
            repo_dir: Absolute path to repository root
            cfg: Configuration (unused)

        Note:
            Populates project.issues and File.issues lists. Errors reading
            individual files are logged but don't stop the analysis.
        """
        for fid, f in project.files.items():
            try:
                path = Path(repo_dir) / f.path
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
            except OSError as e:
                logger.debug(f"Could not read file {f.path} for weakness analysis: {e}")
                continue
            except Exception as e:
                logger.warning(f"Unexpected error reading {f.path}: {e}")
                continue
            for typ, rx in PATTERNS:
                if rx.search(content):
                    iid = f"repo:issue:{f.path.replace('/', '_')}:{typ.split(':')[-1]}"
                    issue = project.issues.get(iid)
                    if not issue:
                        issue = Issue(
                            id=iid,
                            type=typ,
                            file_id=fid,
                            description=f"Found {typ} markers in {f.path}",
                            severity=_severity_for(typ),
                            status="Open",
                            title=f"{typ} in {f.path}",
                        )
                        project.issues[iid] = issue
                    if iid not in f.issues:
                        f.issues.append(iid)
