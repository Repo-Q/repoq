"""Dependency extraction utilities for Python and JavaScript/TypeScript.

This module provides functions to extract import statements from source code:
- Python: Uses AST parsing with regex fallback
- JavaScript/TypeScript: Uses regex to match ES6 imports and CommonJS requires

Extracts top-level package names for dependency graph construction.
"""
from __future__ import annotations

import ast
import logging
import re
from typing import Set

logger = logging.getLogger(__name__)

IMPORT_RE = re.compile(r"^\s*import\s+([\w\.]+)|^\s*from\s+([\w\.]+)\s+import\s+", re.MULTILINE)
JS_IMPORT_RE = re.compile(
    r"^\s*import\s+.*?from\s+['\"]([^'\"]+)['\"]|^\s*require\(['\"]([^'\"]+)['\"]\)", re.MULTILINE
)


def python_imports(content: str) -> Set[str]:
    """Extract Python import package names from source code.

    Uses AST parsing for accuracy, falls back to regex if parsing fails.
    Returns top-level package names only (e.g., "requests" from "requests.api").

    Args:
        content: Python source code as string

    Returns:
        Set of top-level package names imported in the code

    Example:
        >>> code = "import requests\\nfrom pathlib import Path"
        >>> python_imports(code)
        {'requests', 'pathlib'}
    """
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        logger.debug(f"Failed to parse Python code, using regex fallback: {e}")
        mods = set()
        for m in IMPORT_RE.finditer(content):
            g1, g2 = m.groups()
            if g1:
                mods.add(g1.split(".")[0])
            if g2:
                mods.add(g2.split(".")[0])
        return mods
    except Exception as e:
        logger.warning(f"Unexpected error parsing Python imports: {e}")
        return set()
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
    """Extract JavaScript/TypeScript package names from source code.

    Matches ES6 imports (import ... from "pkg") and CommonJS requires (require("pkg")).
    Returns top-level package names, excluding relative imports (starting with ".").

    Args:
        content: JavaScript or TypeScript source code as string

    Returns:
        Set of NPM package names imported in the code

    Example:
        >>> code = 'import React from "react"\\nconst fs = require("fs")'
        >>> js_imports(code)
        {'react', 'fs'}

    Note:
        Relative imports (e.g., "./module") are excluded as they represent
        internal project files, not external dependencies.
    """
    mods: Set[str] = set()
    for m in JS_IMPORT_RE.finditer(content):
        g1, g2 = m.groups()
        pkg = (g1 or g2 or "").split("/")[0]
        if pkg and not pkg.startswith("."):
            mods.add(pkg)
    return mods
