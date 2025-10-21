"""Hotspots analyzer for identifying high-risk files requiring attention.

This module calculates hotspot scores by combining:
- Code churn (frequency of changes)
- File size (lines of code)
- Complexity (cyclomatic complexity)

High hotspot scores indicate files that are frequently changed and complex,
making them prime candidates for refactoring and technical debt reduction.
"""

from __future__ import annotations

import logging

from ..core.model import Issue, Project
from .base import Analyzer

logger = logging.getLogger(__name__)


def _norm(x: float, maxv: float) -> float:
    """Normalize value to 0-1 range.

    Args:
        x: Value to normalize
        maxv: Maximum value in dataset

    Returns:
        Normalized value between 0.0 and 1.0
    """
    return (x / maxv) if maxv > 0 else 0.0


class HotspotsAnalyzer(Analyzer):
    """Analyzer for identifying code hotspots (high-risk files).

    Calculates hotspot score combining:
    - Code churn (70% of LOC weight + 30% of complexity weight)
    - Normalized by maximum values across all files

    Files with high scores are flagged as hotspot issues with severity
    based on score thresholds (high: >=0.66, medium: >=0.33, low: <0.33).

    Top N hotspots (cfg.thresholds.hotspot_top_n) are reported as issues.
    """

    name = "hotspots"

    def run(self, project: Project, repo_dir: str, cfg) -> None:
        """Calculate hotspot scores and create issues for top files.

        Args:
            project: Project model with files containing churn and complexity data
            repo_dir: Repository directory (unused)
            cfg: Configuration with hotspot_top_n threshold

        Note:
            Populates File.hotness and creates Issue entities for top hotspots.
        """
        max_loc = max((f.lines_of_code for f in project.files.values()), default=0)
        max_churn = max((f.code_churn for f in project.files.values()), default=0)
        max_cplx = max((f.complexity or 0.0 for f in project.files.values()), default=0.0)

        scores = []
        for fid, f in project.files.items():
            s = _norm(f.code_churn, max_churn) * (
                0.7 * _norm(f.lines_of_code, max_loc)
                + 0.3 * _norm(float(f.complexity or 0.0), max_cplx)
            )
            project.files[fid].hotness = float(s)
            scores.append((s, fid))

        scores.sort(reverse=True)
        top_n = cfg.thresholds.hotspot_top_n
        for i, (s, fid) in enumerate(scores[:top_n]):
            severity = "high" if s >= 0.66 else "medium" if s >= 0.33 else "low"
            iid = f"repo:issue:hotspot:{fid.split(':', 2)[-1].replace('/', '_')}"
            if iid not in project.issues:
                project.issues[iid] = Issue(
                    id=iid,
                    type="repo:HotspotIssue",
                    file_id=fid,
                    description=f"Hotspot score={s:.3f}",
                    severity=severity,
                    status="Open",
                    title="Hotspot",
                )
            if iid not in project.files[fid].issues:
                project.files[fid].issues.append(iid)
