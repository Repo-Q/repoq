from __future__ import annotations

from pathlib import Path
from typing import List

from ..core.model import Project
from ..core.utils import is_excluded
from .base import Analyzer


class ComplexityAnalyzer(Analyzer):
    name = "complexity"

    def run(self, project: Project, repo_dir: str, cfg) -> None:
        try:
            import lizard  # type: ignore
        except Exception:
            return

        file_paths: List[str] = []
        for f in project.files.values():
            rel = f.path
            if is_excluded(rel, cfg.exclude_globs):
                continue
            file_paths.append(str(Path(repo_dir) / rel))

        try:
            results = lizard.analyze_files(file_paths, threads=0)
            for r in results:
                rel = Path(r.filename).relative_to(repo_dir).as_posix()
                fid = f"repo:file:{rel}"
                if fid in project.files:
                    if r.function_list:
                        max_ccn = max(func.cyclomatic_complexity for func in r.function_list)
                        project.files[fid].complexity = float(max_ccn)
        except Exception:
            pass

        try:
            from radon.mi import mi_visit
        except Exception:
            return

        for f in project.files.values():
            if f.language != "Python":
                continue
            try:
                p = Path(repo_dir) / f.path
                with p.open("r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                mi = mi_visit(content, True)
                f.maintainability = float(mi)
            except Exception:
                continue
