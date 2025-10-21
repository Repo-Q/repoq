from __future__ import annotations
import re, os
from ..core.model import Project, Issue

TODO_RE = re.compile(r"\b(TODO|FIXME|BUG)\b", re.IGNORECASE)

class WeaknessAnalyzer:
    def run(self, p: Project, repo_dir: str, cfg):
        for f in p.files.values():
            try:
                with open(os.path.join(repo_dir, f.path), "r", encoding="utf-8", errors="ignore") as fh:
                    for i, line in enumerate(fh, start=1):
                        if TODO_RE.search(line):
                            iid = f"repo:issue:todo:{f.path}:{i}"
                            p.issues[iid] = Issue(id=iid, type="TodoComment", file=f.id, description=line.strip(), severity="low")
                            f.issues.append(iid)
            except Exception:
                continue
