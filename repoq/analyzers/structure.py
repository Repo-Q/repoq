"""Structure analyzer for repository organization and static metrics.

This module analyzes the static structure of a repository including:
- File and module organization
- Programming language detection and LOC counting
- Dependency extraction (Python, JavaScript/TypeScript)
- License and README detection
- CI/CD system detection
- File checksums for integrity verification
- Ontological concept extraction and validation
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..core.deps import js_imports, python_imports
from ..core.model import DependencyEdge, File, Module, Project
from ..normalize.spdx_trs import normalize_spdx
from ..normalize.semver_trs import normalize_semver
from ..core.utils import checksum_file, guess_language, is_excluded
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


def _detect_spdx_license(repo_path: Path) -> Optional[str]:
    """
    Auto-detect SPDX license identifier from common files with normalization.

    Returns normalized SPDX license expression or None if undetected.
    """
    license_files = ["LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING", "COPYING.md"]

    for fname in license_files:
        license_file = repo_path / fname
        if license_file.exists():
            try:
                with open(license_file, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()

                # Basic SPDX detection patterns
                if "MIT License" in content or "MIT license" in content:
                    return normalize_spdx("MIT")
                elif "Apache License" in content and "Version 2.0" in content:
                    return normalize_spdx("Apache-2.0")
                elif "GNU GENERAL PUBLIC LICENSE" in content and "Version 2" in content:
                    return normalize_spdx("GPL-2.0")
                elif "GNU GENERAL PUBLIC LICENSE" in content and "Version 3" in content:
                    return normalize_spdx("GPL-3.0")
                elif "BSD" in content:
                    if "3-Clause" in content:
                        return normalize_spdx("BSD-3-Clause")
                    elif "2-Clause" in content:
                        return normalize_spdx("BSD-2-Clause")
                    else:
                        return normalize_spdx("BSD-3-Clause")  # Default

            except Exception:
                pass

    return None


def _parse_dependency_manifests(repo_path: Path) -> List[DependencyEdge]:
    """
    Parse dependency manifests (package.json, pyproject.toml, etc.) and extract
    normalized version constraints.

    Returns list of DependencyEdge objects with version constraints.
    """
    dependencies = []

    # Python: pyproject.toml
    pyproject_file = repo_path / "pyproject.toml"
    if pyproject_file.exists():
        try:
            import tomllib

            with open(pyproject_file, "rb") as fh:
                data = tomllib.load(fh)

            # Main dependencies
            for dep in data.get("project", {}).get("dependencies", []):
                dep_name, version_constraint = _parse_python_dep(dep)
                if dep_name:
                    dependencies.append(
                        DependencyEdge(
                            source="project",
                            target=f"pypi:{dep_name}",
                            weight=1,
                            type="runtime",
                            version_constraint=normalize_semver(version_constraint)
                            if version_constraint
                            else None,
                            original_constraint=version_constraint,
                        )
                    )

            # Optional dependencies
            for group_deps in data.get("project", {}).get("optional-dependencies", {}).values():
                for dep in group_deps:
                    dep_name, version_constraint = _parse_python_dep(dep)
                    if dep_name:
                        dependencies.append(
                            DependencyEdge(
                                source="project",
                                target=f"pypi:{dep_name}",
                                weight=1,
                                type="build",
                                version_constraint=normalize_semver(version_constraint)
                                if version_constraint
                                else None,
                                original_constraint=version_constraint,
                            )
                        )

        except Exception as e:
            logger.debug(f"Failed to parse pyproject.toml: {e}")

    # Python: requirements.txt
    requirements_file = repo_path / "requirements.txt"
    if requirements_file.exists():
        try:
            with open(requirements_file, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        dep_name, version_constraint = _parse_python_dep(line)
                        if dep_name:
                            dependencies.append(
                                DependencyEdge(
                                    source="project",
                                    target=f"pypi:{dep_name}",
                                    weight=1,
                                    type="runtime",
                                    version_constraint=normalize_semver(version_constraint)
                                    if version_constraint
                                    else None,
                                    original_constraint=version_constraint,
                                )
                            )
        except Exception as e:
            logger.debug(f"Failed to parse requirements.txt: {e}")

    # JavaScript/TypeScript: package.json
    package_json = repo_path / "package.json"
    if package_json.exists():
        try:
            import json

            with open(package_json, "r", encoding="utf-8") as fh:
                data = json.load(fh)

            # Dependencies
            for dep_name, version_constraint in data.get("dependencies", {}).items():
                dependencies.append(
                    DependencyEdge(
                        source="project",
                        target=f"npm:{dep_name}",
                        weight=1,
                        type="runtime",
                        version_constraint=normalize_semver(version_constraint),
                        original_constraint=version_constraint,
                    )
                )

            # Dev dependencies
            for dep_name, version_constraint in data.get("devDependencies", {}).items():
                dependencies.append(
                    DependencyEdge(
                        source="project",
                        target=f"npm:{dep_name}",
                        weight=1,
                        type="build",
                        version_constraint=normalize_semver(version_constraint),
                        original_constraint=version_constraint,
                    )
                )

        except Exception as e:
            logger.debug(f"Failed to parse package.json: {e}")

    return dependencies


def _parse_python_dep(dep_spec: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parse Python dependency specification into name and version constraint.

    Examples:
        "requests>=2.25.0" -> ("requests", ">=2.25.0")
        "django~=4.2.0" -> ("django", "~=4.2.0")
        "numpy" -> ("numpy", None)

    Returns:
        Tuple of (package_name, version_constraint)
    """
    import re

    # Pattern for Python dependency specs
    pattern = r"^([a-zA-Z0-9_\-\.]+)(?:\s*([><=~!]+\s*[0-9]+(?:\.[0-9]+)*(?:\.[0-9]+)*(?:[a-zA-Z0-9\-]*)?(?:,\s*[><=~!]+\s*[0-9]+(?:\.[0-9]+)*(?:\.[0-9]+)*(?:[a-zA-Z0-9\-]*)?)*))?\s*(?:;.*)?$"

    match = re.match(pattern, dep_spec.strip())
    if match:
        name = match.group(1)
        constraint = match.group(2)
        # Convert Python ~= to SemVer ~
        if constraint and "~=" in constraint:
            constraint = constraint.replace("~=", "~")
        return name, constraint

    return None, None


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
                                        target=f"pypi:{mod}",
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

        # Extract dependencies from manifest files (with normalized version constraints)
        try:
            manifest_deps = _parse_dependency_manifests(repo_path)
            project.dependencies.extend(manifest_deps)
        except Exception as e:
            logger.debug(f"Failed to parse dependency manifests: {e}")

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

        # ONTOLOGICAL INTEGRATION: Extract domain concepts
        project = self._enrich_with_ontological_analysis(project, repo_path)

        return project

    def _enrich_with_ontological_analysis(self, project: Project, repo_path: Path) -> Project:
        """Enrich project with ontological concept extraction."""
        try:
            # Import ontology manager (optional dependency)
            from ..ontologies.ontology_manager import OntologyManager

            manager = OntologyManager()

            # Perform ontological analysis on project structure
            analysis_result = manager.analyze_project_structure(project)

            # Add ontological insights to project metadata
            if not hasattr(project, "ontological_analysis"):
                project.ontological_analysis = {}

            project.ontological_analysis.update(analysis_result)

            logger.info(
                f"Ontological analysis completed: {len(analysis_result.get('concepts', []))} concepts extracted"
            )

        except ImportError:
            logger.debug("Ontology manager not available - skipping ontological analysis")
        except Exception as e:
            logger.warning(f"Ontological analysis failed: {e}")

        return project
