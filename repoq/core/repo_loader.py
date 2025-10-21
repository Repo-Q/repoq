from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Optional, Tuple


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://") or s.startswith("git@")


def prepare_repo(
    path_or_url: str, depth: Optional[int] = None, branch: Optional[str] = None
) -> Tuple[str, Optional[str]]:
    # Check if URL first (URLs don't need path resolution)
    if is_url(path_or_url):
        tmpdir = tempfile.mkdtemp(prefix="repoq_")
        cmd = ["git", "clone"]
        if depth:
            cmd += ["--depth", str(depth)]
        if branch:
            cmd += ["--branch", branch]
        cmd += [path_or_url, tmpdir]
        subprocess.run(cmd, check=True)
        return tmpdir, tmpdir

    # For local paths, resolve to absolute path
    abs_path = os.path.abspath(path_or_url)

    if os.path.isdir(abs_path) and os.path.isdir(os.path.join(abs_path, ".git")):
        return abs_path, None

    raise RuntimeError(f"Not a git repo path or URL: {path_or_url}")


def get_head(path: str) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except Exception:
        return ""
