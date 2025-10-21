from __future__ import annotations
import os, shutil, subprocess, tempfile
from typing import Tuple

def is_url(path: str) -> bool:
    return path.startswith("http://") or path.startswith("https://") or path.endswith(".git")

def prepare_repo(src: str, depth: int | None = None, branch: str | None = None) -> tuple[str, str | None]:
    if os.path.isdir(src) and os.path.isdir(os.path.join(src, ".git")):
        return os.path.abspath(src), None
    # clone
    tmp = tempfile.mkdtemp(prefix="repoq_")
    cmd = ["git", "clone", src, tmp]
    if depth: cmd[2:2] = ["--depth", str(depth)]
    if branch: cmd[2:2] = ["--branch", branch]
    subprocess.run(cmd, check=True)
    return tmp, tmp
