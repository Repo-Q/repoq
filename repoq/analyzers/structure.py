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
from typing import Dict, List, Optional

from ..core.deps import js_imports, python_imports
from ..core.model import DependencyEdge, File, Module, Project
from ..core.utils import checksum_file, guess_language, is_excluded
from ..normalize.semver_trs import normalize_semver
from ..normalize.spdx_trs import normalize_spdx
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


def _process_file(
    fpath: Path,
    repo_path: Path,
    cfg,
    project: Project,
) -> Optional[File]:
    """Process a single file: count LOC, detect language, compute checksum.

    Args:
        fpath: Absolute path to file
        repo_path: Repository root path
        cfg: Configuration with hash_algo
        project: Project model for module lookup

    Returns:
        File object or None if file should be skipped
    """
    rel = fpath.relative_to(repo_path).as_posix()

    # Detect language and count LOC
    language = guess_language(rel)
    loc = 0
    if _is_textlike(fpath):
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                loc = sum(1 for _ in fh)
        except Exception:
            loc = 0

    # Create File object
    fid = f"repo:file:{rel}"
    file_obj = File(id=fid, path=rel, language=language, lines_of_code=loc)

    # Detect test files
    if "/tests/" in f"/{rel}/" or rel.endswith("_test.py") or rel.endswith("Test.java"):
        file_obj.test_file = True

    # Compute checksum
    if cfg.hash_algo:
        try:
            file_obj.checksum_algo = cfg.hash_algo.lower()
            file_obj.checksum_value = checksum_file(str(fpath), cfg.hash_algo)
        except Exception:
            file_obj.checksum_algo = None
            file_obj.checksum_value = None

    # Attach to module (top-level directory)
    parts = rel.split("/")
    if len(parts) > 1:
        top = parts[0]
        mid = f"repo:module:{top}"
        if mid in project.modules:
            file_obj.module = mid
            m = project.modules[mid]
            m.contains_files.append(fid)
            m.total_loc += loc

    return file_obj


def _extract_file_dependencies(
    file_obj: File,
    fpath: Path,
    project: Project,
) -> None:
    """Extract dependencies (imports) from a single file.

    Args:
        file_obj: File object to extract dependencies from
        fpath: Absolute path to file
        project: Project model to add dependencies to

    Note:
        Mutates project.dependencies in-place
    """
    if not file_obj.module or not _is_textlike(fpath):
        return

    try:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read()

        # Python imports
        if file_obj.language == "Python":
            imps = python_imports(content)
            for mod in imps:
                project.dependencies.append(
                    DependencyEdge(
                        source=file_obj.module,
                        target=f"pypi:{mod}",
                        weight=1,
                        type="import",
                    )
                )

        # JavaScript/TypeScript imports
        elif file_obj.language in ("JavaScript", "TypeScript"):
            imps = js_imports(content)
            for pkg in imps:
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


def _process_repository_metadata(
    project: Project,
    repo_path: Path,
) -> None:
    """Process repository metadata: README, license, CI configuration.

    Args:
        project: Project model to populate
        repo_path: Repository root path

    Note:
        Mutates project.description, project.license, project.ci_configured
    """
    # README description
    readme = repo_path / "README.md"
    if readme.exists() and (project.description is None or not project.description):
        try:
            with open(readme, "r", encoding="utf-8", errors="ignore") as fh:
                project.description = fh.readline().strip() or project.description
        except Exception:
            pass

    # SPDX license detection
    project.license = project.license or _detect_spdx_license(repo_path)

    # CI/CD system detection
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

        # Initialize top-level modules
        self._init_modules(project, repo_path, cfg)

        # Scan directory tree and process files
        count = self._scan_and_process_files(project, repo_path, cfg, language_loc)

        logger.info(f"Processed {count} files")

        # Extract dependencies from manifest files
        self._extract_manifest_dependencies(project, repo_path)

        # Process repository metadata (README, license, CI)
        _process_repository_metadata(project, repo_path)

        # Set programming languages distribution
        project.programming_languages = dict(
            sorted(language_loc.items(), key=lambda kv: kv[1], reverse=True)
        )

        # Enrich with ontological analysis
        self._enrich_with_ontological_analysis(project, repo_path)

    def _init_modules(self, project: Project, repo_path: Path, cfg) -> None:
        """Initialize top-level modules from directory structure.

        Args:
            project: Project model to populate
            repo_path: Repository root path
            cfg: Configuration with exclude_globs
        """
        for entry in sorted(repo_path.iterdir()):
            if (
                entry.is_dir()
                and not entry.name.startswith(".")
                and not is_excluded(entry.name, cfg.exclude_globs)
            ):
                mid = f"repo:module:{entry.name}"
                project.modules[mid] = Module(id=mid, name=entry.name, path=entry.as_posix())

    def _scan_and_process_files(
        self,
        project: Project,
        repo_path: Path,
        cfg,
        language_loc: Dict[str, int],
    ) -> int:
        """Scan directory tree and process all files.

        Args:
            project: Project model to populate
            repo_path: Repository root path
            cfg: Configuration with filters
            language_loc: Dictionary to accumulate LOC by language

        Returns:
            Number of files processed
        """
        count = 0

        for root, dirs, files in os.walk(repo_path.as_posix()):
            # Filter directories
            relroot = Path(root).relative_to(repo_path).as_posix()
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and not is_excluded(f"{relroot}/{d}" if relroot != "." else d, cfg.exclude_globs)
            ]

            # Process files
            for fname in files:
                fpath = Path(root) / fname
                rel = fpath.relative_to(repo_path).as_posix()

                # Apply filters
                if is_excluded(rel, cfg.exclude_globs):
                    continue
                if rel.startswith(".git/"):
                    continue
                if cfg.max_files and count >= cfg.max_files:
                    break

                ext = fpath.suffix[1:].lower()
                if cfg.include_extensions and ext not in cfg.include_extensions:
                    continue

                # Process file
                file_obj = _process_file(fpath, repo_path, cfg, project)
                if file_obj:
                    project.files[file_obj.id] = file_obj

                    # Update language LOC
                    if file_obj.language:
                        language_loc[file_obj.language] += file_obj.lines_of_code

                    # Extract dependencies
                    _extract_file_dependencies(file_obj, fpath, project)

                    count += 1

        return count

    def _extract_manifest_dependencies(self, project: Project, repo_path: Path) -> None:
        """Extract dependencies from manifest files (package.json, pyproject.toml, etc.).

        Args:
            project: Project model to add dependencies to
            repo_path: Repository root path
        """
        try:
            manifest_deps = _parse_dependency_manifests(repo_path)
            project.dependencies.extend(manifest_deps)
        except Exception as e:
            logger.debug(f"Failed to parse dependency manifests: {e}")

    def _enrich_with_ontological_analysis(self, project: Project, repo_path: Path) -> None:
        """Enrich project with ontological concept extraction.
        
        Args:
            project: Project model to enrich with ontological insights
            repo_path: Repository root path
            
        Note:
            Mutates project.ontological_analysis in-place
        """
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
