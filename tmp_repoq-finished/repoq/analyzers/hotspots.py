from __future__ import annotations
from ..core.model import Project

class HotspotsAnalyzer:
    def run(self, p: Project, repo_dir: str, cfg):
        max_churn = max((f.code_churn for f in p.files.values()), default=1) or 1
        max_cplx = max((f.complexity or 0.0 for f in p.files.values()), default=1.0) or 1.0
        for f in p.files.values():
            cplx = (f.complexity or 0.0) / max_cplx
            churn = f.code_churn / max_churn
            f.hotness = round(0.5*cplx + 0.5*churn, 4)
