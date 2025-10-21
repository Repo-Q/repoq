from __future__ import annotations

import ast
import re
from typing import Set

IMPORT_RE = re.compile(r"^\s*import\s+([\w\.]+)|^\s*from\s+([\w\.]+)\s+import\s+", re.MULTILINE)
JS_IMPORT_RE = re.compile(
    r"^\s*import\s+.*?from\s+['\"]([^'\"]+)['\"]|^\s*require\(['\"]([^'\"]+)['\"]\)", re.MULTILINE
)


def python_imports(content: str) -> Set[str]:
    try:
        tree = ast.parse(content)
    except Exception:
        mods = set()
        for m in IMPORT_RE.finditer(content):
            g1, g2 = m.groups()
            if g1:
                mods.add(g1.split(".")[0])
            if g2:
                mods.add(g2.split(".")[0])
        return mods
    mods: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mods.add(node.module.split(".")[0])
    return mods


def js_imports(content: str) -> Set[str]:
    mods: Set[str] = set()
    for m in JS_IMPORT_RE.finditer(content):
        g1, g2 = m.groups()
        pkg = (g1 or g2 or "").split("/")[0]
        if pkg and not pkg.startswith("."):
            mods.add(pkg)
    return mods
