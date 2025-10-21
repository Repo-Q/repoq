from __future__ import annotations
import subprocess, json, os, sys
from ..core.model import Project

class ComplexityAnalyzer:
    def run(self, p: Project, repo_dir: str, cfg):
        # try call lizard -j for JSON output
        try:
            res = subprocess.run(["lizard","-j",repo_dir], capture_output=True, text=True, check=True)
        except Exception:
            # fallback: simple heuristic complexity = sqrt(LOC)/2
            import math
            for f in p.files.values():
                f.complexity = round(min(20.0, (f.lines_of_code ** 0.5)/2), 2)
            return
        try:
            data = json.loads(res.stdout)
            # lizard groups files with average complexity; we'll map by file path
            for entry in data.get("files", []):
                path = os.path.relpath(entry.get("filename",""), repo_dir).replace("\\","/")
                fid = f"repo:file:{path}"
                if fid in p.files:
                    cc = entry.get("average_cyclomatic_complexity") or entry.get("cyclomatic_complexity")
                    try:
                        p.files[fid].complexity = float(cc)
                    except Exception:
                        p.files[fid].complexity = None
        except Exception:
            pass
