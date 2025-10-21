"""Utility functions for file operations and language detection.

This module provides helper functions for:
- Programming language detection from file extensions
- File path filtering with glob patterns
- File checksum computation (SHA1/SHA256)
"""
from __future__ import annotations

import fnmatch
import hashlib
import logging
import os

logger = logging.getLogger(__name__)

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
    """Guess programming language from file extension.

    Args:
        path: File path (absolute or relative)

    Returns:
        Language name (e.g., "Python", "JavaScript") or None if unknown

    Example:
        >>> guess_language("src/main.py")
        'Python'
        >>> guess_language("app.js")
        'JavaScript'
    """
    base, ext = os.path.splitext(path)
    if ext.startswith("."):
        ext = ext[1:]
    return EXT2LANG.get(ext.lower())


def is_excluded(relpath: str, patterns: list[str]) -> bool:
    """Check if file path matches any exclusion pattern.

    Args:
        relpath: Relative file path to check
        patterns: List of glob patterns (e.g., ["*.pyc", "test_*", "*/node_modules/*"])

    Returns:
        True if path matches any pattern, False otherwise

    Example:
        >>> is_excluded("test_foo.py", ["test_*"])
        True
        >>> is_excluded("src/main.py", ["test_*"])
        False
    """
    for p in patterns:
        if fnmatch.fnmatch(relpath, p):
            return True
    return False


def checksum_file(path: str, algo: str) -> str:
    """Compute file checksum using SHA1 or SHA256.

    Args:
        path: Absolute path to file
        algo: Algorithm name ("sha1" or "sha256", case-insensitive)

    Returns:
        Hexadecimal checksum string

    Raises:
        OSError: If file cannot be read
        ValueError: If algorithm is not supported

    Note:
        SHA1 is used for compatibility with SPDX checksums despite being
        cryptographically weak. For security-critical checksums, use SHA256.

    Example:
        >>> checksum_file("/tmp/file.txt", "sha256")
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    """
    algo_lower = algo.lower()
    if algo_lower == "sha1":
        h = hashlib.sha1()  # nosec B324
    elif algo_lower == "sha256":
        h = hashlib.sha256()
    else:
        raise ValueError(f"Unsupported checksum algorithm: {algo}")

    try:
        with open(path, "rb") as f:
            while True:
                b = f.read(1024 * 1024)
                if not b:
                    break
                h.update(b)
        return h.hexdigest()
    except OSError as e:
        logger.error(f"Failed to read file {path} for checksum: {e}")
        raise
