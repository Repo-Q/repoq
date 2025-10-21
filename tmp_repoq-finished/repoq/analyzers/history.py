from __future__ import annotations
import subprocess, os, itertools, datetime
from collections import defaultdict
from ..core.model import Project, CouplingEdge

class HistoryAnalyzer:
    def run(self, p: Project, repo_dir: str, cfg):
        # Use git log --numstat to aggregate churn + authors + coupling
        cmd = ["git","-C", repo_dir, "log","--date=iso","--numstat","--pretty=format:%H%x09%an%x09%ae%x09%ad"]
        if cfg.since:
            cmd.insert(4, f"--since={cfg.since}")
        out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.splitlines()
        cur_commit = None; cur_files = []
        for line in out:
            if line and not line[0].isdigit() and "\t" in line and line.count("\t")==3:
                # new commit header
                if cur_commit and len(cur_files)>1:
                    # add coupling
                    for a,b in itertools.combinations(cur_files, 2):
                        p.coupling.append(CouplingEdge(a=a,b=b,weight=1.0))
                h, an, ae, ad = line.split("\t")
                cur_commit = {"hash":h,"author":an,"email":ae,"date":ad}; cur_files = []
                p.contributors.setdefault(an, {"commits":0,"linesAdded":0,"linesDeleted":0})
                p.contributors[an]["commits"] += 1
            elif "\t" in line and cur_commit:
                add, dele, path = line.split("\t")
                try:
                    add = int(add); dele = int(dele)
                except:
                    add = dele = 0
                fid = f"repo:file:{path}"
                if fid not in p.files:
                    # if file filtered by structure, skip stats
                    continue
                f = p.files[fid]
                f.commits_count += 1
                f.code_churn += (add + dele)
                f.last_modified = cur_commit["date"]
                f.contributors.setdefault(cur_commit["author"], {"linesAdded":0,"linesDeleted":0,"commits":0})
                f.contributors[cur_commit["author"]]["linesAdded"] += add
                f.contributors[cur_commit["author"]]["linesDeleted"] += dele
                f.contributors[cur_commit["author"]]["commits"] += 1
                p.contributors[cur_commit["author"]]["linesAdded"] += add
                p.contributors[cur_commit["author"]]["linesDeleted"] += dele
                cur_files.append(fid)
        # squash coupling weights
        weights = defaultdict(float)
        for e in p.coupling:
            key = tuple(sorted((e.a,e.b)))
            weights[key] += e.weight
        p.coupling = [CouplingEdge(a=a,b=b,weight=w) for (a,b),w in weights.items()]
