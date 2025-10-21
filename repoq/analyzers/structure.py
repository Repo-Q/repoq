"""Structure analyzer for repository organization and static metrics.

This module analyzes the static structure of a repository including:
- File and module organization
- Programming language detection and LOC counting
- Dependency extraction (Python, JavaScript/TypeScript)
- License and README detection
- CI/CD system detection
- File checksums for integrity verification
"""
from __future__ import annotations

import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict

from ..core.deps import js_imports, python_imports
from ..core.model import DependencyEdge, File, Module, Project
from ..core.utils import checksum_file, guess_language, is_excluded
from ..normalize import normalize_spdx
from .base import Analyzer

logger = logging.getLogger(__name__)

TEXT_LIKE = set(
    [
        "py",
        "js",
        "ts",
        "java",
        "c",
        "cc",
        "cpp",
        "cxx",
        "h",
        "hpp",
        "hh",
        "go",
        "rb",
        "rs",
        "kt",
        "swift",
        "php",
        "cs",
        "m",
        "mm",
        "scala",
        "sh",
        "ps1",
        "yaml",
        "yml",
        "toml",
        "json",
        "md",
        "rst",
        "txt",
        "xml",
    ]
)


def _is_textlike(path: Path) -> bool:
    """Check if file is likely a text file based on extension.

    Args:
        path: File path to check

    Returns:
        True if extension is in TEXT_LIKE set, False otherwise
    """
    return path.suffix[1:].lower() in TEXT_LIKE


def _detect_spdx_license(repo_path: Path) -> str | None:
    """Detect SPDX license identifier from LICENSE file.

    Args:
        repo_path: Repository root directory

    Returns:
        Normalized SPDX license expression or filename if detected, None otherwise

    Note:
        Uses simple text pattern matching for common licenses (MIT, Apache 2.0,
        GPL-3.0, BSD-3-Clause). Returns normalized canonical form.
        Falls back to filename if patterns don't match.
    """
    # naive but useful: look into LICENSE* file
    for name in ["LICENSE", "LICENSE.md", "LICENSE.txt"]:
        p = repo_path / name
        if p.exists():
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore").lower()
                
                # Detect license type and build SPDX expression
                detected_licenses = []
                
                if "mit license" in txt or "permission is hereby granted" in txt:
                    detected_licenses.append("MIT")
                if "apache license" in txt and "version 2.0" in txt:
                    detected_licenses.append("Apache-2.0")
                if "gnu general public license" in txt and "version 3" in txt:
                    detected_licenses.append("GPL-3.0-or-later")
                if "bsd" in txt and "3-clause" in txt:
                    detected_licenses.append("BSD-3-Clause")
                
                if detected_licenses:
                    # Build expression (multiple licenses = OR)
                    if len(detected_licenses) == 1:
                        expr = detected_licenses[0]
                    else:
                        expr = " OR ".join(detected_licenses)
                    
                    # Normalize to canonical form
                    normalized = normalize_spdx(expr)
                    logger.debug(f"License detected and normalized: {expr} → {normalized}")
                    return normalized
                
                # Fallback to filename
                return name
            except Exception as e:
                logger.warning(f"Error reading license file {p}: {e}")
                return name
    return None


class StructureAnalyzer(Analyzer):
    """Analyzer for repository structure and static code metrics.

    Analyzes:
    - File tree and module hierarchy
    - Programming languages and LOC distribution
    - Dependencies (Python imports, JavaScript/TypeScript requires)
    - License detection (SPDX)
    - README description extraction
    - CI/CD system detection (GitHub Actions, GitLab CI, etc.)
    - File checksums (SHA1/SHA256)

    The analyzer respects cfg.include_extensions, cfg.exclude_globs, and
    cfg.max_files for filtering.
    """

    name = "structure"

    def run(self, project: Project, repo_dir: str, cfg) -> None:
        """Execute structure analysis and populate project model.

        Args:
            project: Project model to populate with structure data
            repo_dir: Absolute path to repository root
            cfg: Configuration with filters and options

        Note:
            Mutates project.files, project.modules, project.dependencies,
            project.license, project.ci_configured, and
            project.programming_languages in-place.
        """
        repo_path = Path(repo_dir)
        language_loc: Dict[str, int] = defaultdict(int)

        # top-level modules
        for entry in sorted(repo_path.iterdir()):
            if (
                entry.is_dir()
                and not entry.name.startswith(".")
                and not is_excluded(entry.name, cfg.exclude_globs)
            ):
                mid = f"repo:module:{entry.name}"
                project.modules[mid] = Module(id=mid, name=entry.name, path=entry.as_posix())

        count = 0
        for root, dirs, files in os.walk(repo_path.as_posix()):
            relroot = Path(root).relative_to(repo_path).as_posix()
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and not is_excluded(f"{relroot}/{d}" if relroot != "." else d, cfg.exclude_globs)
            ]
            for fname in files:
                fpath = Path(root) / fname
                rel = fpath.relative_to(repo_path).as_posix()
                if is_excluded(rel, cfg.exclude_globs):
                    continue
                if rel.startswith(".git/"):
                    continue
                if cfg.max_files and count >= cfg.max_files:
                    break

                ext = fpath.suffix[1:].lower()
                if cfg.include_extensions and ext not in cfg.include_extensions:
                    continue

                language = guess_language(rel)
                loc = 0
                if _is_textlike(fpath):
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                            loc = sum(1 for _ in fh)
                    except Exception:
                        loc = 0

                fid = f"repo:file:{rel}"
                file_obj = File(id=fid, path=rel, language=language, lines_of_code=loc)
                if "/tests/" in f"/{rel}/" or rel.endswith("_test.py") or rel.endswith("Test.java"):
                    file_obj.test_file = True

                # checksum
                if cfg.hash_algo:
                    try:
                        file_obj.checksum_algo = cfg.hash_algo.lower()
                        file_obj.checksum_value = checksum_file(str(fpath), cfg.hash_algo)
                    except Exception:
                        file_obj.checksum_algo = None
                        file_obj.checksum_value = None

                # attach to module (top-level dir)
                parts = rel.split("/")
                if len(parts) > 1:
                    top = parts[0]
                    mid = f"repo:module:{top}"
                    if mid in project.modules:
                        file_obj.module = mid
                        m = project.modules[mid]
                        m.contains_files.append(fid)
                        m.total_loc += loc

                project.files[fid] = file_obj
                if language:
                    language_loc[language] += loc
                count += 1

                # dependencies (Python/JS)
                try:
                    if language == "Python" and _is_textlike(fpath):
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                            imps = python_imports(fh.read())
                        for mod in imps:
                            if file_obj.module:
                                project.dependencies.append(
                                    DependencyEdge(
                                        source=file_obj.module,
                                        target=f"pkg:{mod}",
                                        weight=1,
                                        type="import",
                                    )
                                )
                    elif language in ("JavaScript", "TypeScript") and _is_textlike(fpath):
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                            imps = js_imports(fh.read())
                        for pkg in imps:
                            if file_obj.module:
                                project.dependencies.append(
                                    DependencyEdge(
                                        source=file_obj.module,
                                        target=f"npm:{pkg}",
                                        weight=1,
                                        type="import",
                                    )
                                )
                except Exception:
                    pass

        # README/License/CI
        readme = repo_path / "README.md"
        if readme.exists() and (project.description is None or not project.description):
            try:
                with open(readme, "r", encoding="utf-8", errors="ignore") as fh:
                    project.description = fh.readline().strip() or project.description
            except Exception:
                pass

        project.license = project.license or _detect_spdx_license(repo_path)

        ci = []
        if (repo_path / ".github" / "workflows").exists():
            ci.append("GitHub Actions")
        if (repo_path / ".gitlab-ci.yml").exists():
            ci.append("GitLab CI")
        if (repo_path / ".travis.yml").exists():
            ci.append("Travis CI")
        if (repo_path / "Jenkinsfile").exists():
            ci.append("Jenkins")
        project.ci_configured = ci

        project.programming_languages = dict(
            sorted(language_loc.items(), key=lambda kv: kv[1], reverse=True)
        )
