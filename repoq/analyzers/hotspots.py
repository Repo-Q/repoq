from __future__ import annotations

from ..core.model import Issue, Project
from .base import Analyzer


def _norm(x: float, maxv: float) -> float:
    return (x / maxv) if maxv > 0 else 0.0


class HotspotsAnalyzer(Analyzer):
    name = "hotspots"

    def run(self, project: Project, repo_dir: str, cfg) -> None:
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
            iid = f"repo:issue:hotspot:{fid.split(':',2)[-1].replace('/','_')}"
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
