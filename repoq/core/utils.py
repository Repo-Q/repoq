from __future__ import annotations

import fnmatch
import hashlib
import os

EXT2LANG = {
    "py": "Python",
    "js": "JavaScript",
    "ts": "TypeScript",
    "java": "Java",
    "c": "C",
    "h": "C/C++ Header",
    "hpp": "C++ Header",
    "hh": "C++ Header",
    "cc": "C++",
    "cpp": "C++",
    "cxx": "C++",
    "go": "Go",
    "rb": "Ruby",
    "rs": "Rust",
    "kt": "Kotlin",
    "swift": "Swift",
    "php": "PHP",
    "cs": "C#",
    "m": "Objective-C",
    "mm": "Objective-C++",
    "scala": "Scala",
    "sh": "Shell",
    "ps1": "PowerShell",
    "yaml": "YAML",
    "yml": "YAML",
    "toml": "TOML",
    "json": "JSON",
    "md": "Markdown",
    "rst": "reStructuredText",
    "txt": "Text",
    "xml": "XML",
}


def guess_language(path: str) -> str | None:
    base, ext = os.path.splitext(path)
    if ext.startswith("."):
        ext = ext[1:]
    return EXT2LANG.get(ext.lower())


def is_excluded(relpath: str, patterns: list[str]) -> bool:
    for p in patterns:
        if fnmatch.fnmatch(relpath, p):
            return True
    return False


def checksum_file(path: str, algo: str) -> str:
    h = hashlib.sha1() if algo.lower() == "sha1" else hashlib.sha256()  # nosec B324
    with open(path, "rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()
