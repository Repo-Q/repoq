"""JSON-LD export module for converting Project models to linked data format.

This module provides functionality to serialize repository analysis results
into JSON-LD format, following W3C standards and supporting multiple ontologies
including PROV-O, OSLC, SPDX, FOAF, and Schema.org.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from .model import Project

logger = logging.getLogger(__name__)


def _load_context(path: Optional[str]) -> Optional[Dict[str, Any]]:
    """Load JSON-LD context from a file.

    Args:
        path: Path to the JSON-LD context file. If None, returns None.

    Returns:
        Parsed JSON-LD context dictionary, or None if file cannot be loaded.

    Note:
        Errors during loading are logged but not raised, allowing graceful
        degradation to default context.
    """
    if not path:
        return None

    try:
        context_path = Path(path)
        if not context_path.exists():
            logger.warning(f"Context file not found: {path}")
            return None

        with context_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            logger.warning(f"Invalid context file format (not a dict): {path}")
            return None

        return data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON context file {path}: {e}")
        return None
    except OSError as e:
        logger.error(f"Failed to read context file {path}: {e}")
        return None
    except Exception as e:
        logger.exception(f"Unexpected error loading context from {path}: {e}")
        return None


DEFAULT_CONTEXT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "ontologies", "context_ext.jsonld"
)


def _merge_contexts(
    base_context: Dict[str, Any],
    context_file: Optional[str],
    field33_context: Optional[str],
) -> Dict[str, Any]:
    """Merge base JSON-LD context with optional custom contexts.

    Args:
        base_context: Base context dictionary with @context key
        context_file: Optional path to custom context file
        field33_context: Optional path to Field33-specific context

    Returns:
        Merged context dictionary
    """
    if context_file:
        ctx_user = _load_context(context_file)
        if isinstance(ctx_user, dict) and "@context" in ctx_user:
            base_context["@context"].update(ctx_user["@context"])
    
    if field33_context:
        ctx_f33 = _load_context(field33_context)
        if isinstance(ctx_f33, dict) and "@context" in ctx_f33:
            base_context["@context"].update(ctx_f33["@context"])
    
    return base_context


def _build_project_metadata(project: Project, context: Dict[str, Any]) -> Dict[str, Any]:
    """Build base JSON-LD metadata for project.

    Args:
        project: Project model
        context: Merged JSON-LD context

    Returns:
        Dict with @context, @id, @type, and project metadata
    """
    return {
        "@context": context["@context"],
        "@id": project.id,
        "@type": [
            "repo:Project",
            "schema:SoftwareSourceCode",
            "codemeta:SoftwareSourceCode",
            "prov:Entity",
            "okn_sd:Software",
        ],
        "name": project.name,
        "description": project.description,
        "programmingLanguages": list(project.programming_languages.keys()),
        "license": project.license,
        "repositoryURL": project.repository_url,
        "lastCommitDate": project.last_commit_date,
        "analyzedAt": project.analyzed_at,
        "repoqVersion": project.repoq_version,
        "ciConfigured": project.ci_configured,
        "modules": [],
        "files": [],
        "contributors": [],
        "issues": [],
        "dependencies": [],
        "coupling": [],
        "commits": [],
        "config": [],
        "tests": [],
    }


def _serialize_module(module) -> Dict[str, Any]:
    """Serialize Module entity to JSON-LD.

    Args:
        module: Module model object

    Returns:
        Dict with module properties
    """
    return {
        "@id": module.id,
        "@type": "repo:Module",
        "name": module.name,
        "path": module.path,
        "containsFile": module.contains_files,
        "containsModule": module.contains_modules,
        "totalLinesOfCode": module.total_loc,
        "totalCommits": module.total_commits,
        "numAuthors": module.num_authors,
        "owner": module.owner,
        "hotspotScore": module.hotspot_score,
        "mainLanguage": module.main_language,
    }


def _serialize_file(file) -> Dict[str, Any]:
    """Serialize File entity to JSON-LD.

    Args:
        file: File model object

    Returns:
        Dict with file properties
    """
    file_node = {
        "@id": file.id,
        "@type": ["repo:File", "schema:SoftwareSourceCode", "spdx:File", "prov:Entity"],
        "path": file.path,
        "fileName": file.path,
        "language": file.language,
        "linesOfCode": file.lines_of_code,
        "complexity": file.complexity,
        "maintainability": file.maintainability,
        "commitsCount": file.commits_count,
        "codeChurn": file.code_churn,
        "contributors": [{"@id": pid, **metrics} for pid, metrics in file.contributors.items()],
        "issues": file.issues,
        "lastModified": file.last_modified,
        "deprecated": file.deprecated,
        "testFile": file.test_file,
        "module": file.module,
        "hotness": file.hotness,
    }
    
    # Include per-function metrics if available
    if file.functions:
        file_node["functions"] = [
            {
                "name": func.name,
                "cyclomaticComplexity": func.cyclomatic_complexity,
                "linesOfCode": func.lines_of_code,
                "parameters": func.parameters,
                "startLine": func.start_line,
                "endLine": func.end_line,
                "tokenCount": func.token_count,
                "maxNestingDepth": func.max_nesting_depth,
            }
            for func in file.functions
        ]
    
    if file.checksum_algo and file.checksum_value:
        file_node["checksum"] = {
            "@type": "spdx:Checksum",
            "algorithm": f"spdx:checksumAlgorithm_{file.checksum_algo}",
            "checksumValue": file.checksum_value,
        }
    
    return file_node


def _serialize_contributor(contributor) -> Dict[str, Any]:
    """Serialize Person/Contributor entity to JSON-LD.

    Args:
        contributor: Person model object

    Returns:
        Dict with contributor properties
    """
    return {
        "@id": contributor.id,
        "@type": ["schema:Person", "foaf:Person", "prov:Agent", "prov:Person"],
        "name": contributor.name,
        "email": contributor.email or None,
        "emailHash": contributor.email_hash or None,
        "mbox_sha1sum": contributor.foaf_mbox_sha1sum or None,
        "commits": contributor.commits,
        "linesAdded": contributor.lines_added,
        "linesDeleted": contributor.lines_deleted,
        "owns": contributor.owns,
        "modulesContributed": contributor.modules_contributed,
    }


def _oslc_sev(sev: str) -> str:
    """Map severity level to OSLC CM severity URI.

    Args:
        sev: Severity level string (case-insensitive): 'high', 'medium', or 'low'.

    Returns:
        OSLC CM severity URI. Defaults to Minor for unrecognized values.
    """
    s = (sev or "").lower()
    if s == "high":
        return "http://open-services.net/ns/cm#Critical"
    if s == "medium":
        return "http://open-services.net/ns/cm#Major"
    return "http://open-services.net/ns/cm#Minor"


def _oslc_pri(pri: Optional[str]) -> Optional[str]:
    """Map priority level to OSLC CM priority URI.

    Args:
        pri: Priority level string (case-insensitive): 'high', 'medium', or 'low'.
            Returns None if pri is None or empty.

    Returns:
        OSLC CM priority URI, or None if input is None/empty.
        Defaults to Low for unrecognized values.
    """
    if not pri:
        return None
    p = pri.lower()
    if p == "high":
        return "http://open-services.net/ns/cm#PriorityHigh"
    if p == "medium":
        return "http://open-services.net/ns/cm#PriorityMedium"
    return "http://open-services.net/ns/cm#PriorityLow"


def to_jsonld(
    project: Project,
    context_file: Optional[str] = None,
    field33_context: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert a Project model to JSON-LD format.

    Serializes repository analysis results into W3C JSON-LD format with support
    for multiple ontologies and custom context extensions.

    Args:
        project: The Project model containing analysis results to export.
        context_file: Optional path to custom JSON-LD context file for extending
            the default ontology mappings.
        field33_context: Optional path to Field33-specific context file for
            domain-specific extensions.

    Returns:
        A dictionary representing the project in JSON-LD format, including:
        - @context: Combined ontology context (PROV-O, OSLC, SPDX, etc.)
        - Project metadata (name, description, repository URL, etc.)
        - Files with metrics (LOC, complexity, maintainability, hotness)
        - Contributors with statistics (commits, lines added/deleted)
        - Issues mapped to OSLC Change Requests
        - Dependencies and coupling relationships
        - Commits as PROV-O Activities
        - Test results mapped to OSLC QM

    Raises:
        ValueError: If project.id is empty or None.

    Example:
        >>> project = Project(id="repo:myproject", name="MyProject")
        >>> jsonld_data = to_jsonld(project)
        >>> print(jsonld_data["@type"])
        ['repo:Project', 'schema:SoftwareSourceCode', ...]
    """
    if not project.id:
        raise ValueError("Project ID cannot be empty")

    if not project.name:
        logger.warning(f"Project {project.id} has no name set")
    
    # Merge contexts
    ctx_base = _load_context(DEFAULT_CONTEXT_PATH) or {"@context": {}}
    context = _merge_contexts(ctx_base, context_file, field33_context)
    
    # Build base metadata
    data = _build_project_metadata(project, context)

    
    # Serialize modules
    for m in project.modules.values():
        data["modules"].append(_serialize_module(m))

    # Serialize files
    for f in project.files.values():
        data["files"].append(_serialize_file(f))

    # Serialize contributors
    for p in project.contributors.values():
        data["contributors"].append(_serialize_contributor(p))

    # Serialize issues
    for i in project.issues.values():
        node = {
            "@id": i.id,
            "@type": (
                ["oslc_cm:ChangeRequest", i.type, "repo:Issue"]
                if i.type != "oslc_cm:ChangeRequest"
                else ["oslc_cm:ChangeRequest", "repo:Issue"]
            ),
            "file": i.file_id,
            "dcterms:title": i.title or i.description,
            "description": i.description,
            "severity": {"@id": _oslc_sev(i.severity)},
        }
        pri = _oslc_pri(i.priority)
        if pri:
            node["priority"] = {"@id": pri}
        if i.status:
            node["status"] = i.status
        data["issues"].append(node)

    for e in project.dependencies:
        data["dependencies"].append(
            {"source": e.source, "target": e.target, "weight": e.weight, "type": e.type}
        )

    for c in project.coupling:
        data["coupling"].append(
            {
                "a": c.a,
                "b": c.b,
                "weight": c.weight,
            }
        )

    for c in project.commits:
        data["commits"].append(
            {
                "@id": c.id,
                "@type": ["prov:Activity", "repo:Commit"],
                "dcterms:description": c.message,
                "endedAtTime": c.ended_at,
                "wasAssociatedWith": {"@id": c.author_id} if c.author_id else None,
            }
        )

    for v in project.versions:
        data["config"].append(
            {
                "@id": v.id,
                "@type": ["oslc_config:VersionResource"],
                "versionId": v.version_id,
                "branch": v.branch,
                "committer": {"@id": v.committer} if v.committer else None,
                "committed": v.committed,
            }
        )

    for tr in project.tests_results:
        data["tests"].append(
            {
                "@id": tr.id,
                "@type": ["oslc_qm:TestResult"],
                "reportsOnTestCase": {"@id": tr.testcase},
                "status": tr.status,
                "time": tr.time,
                "description": tr.message,
            }
        )

    return data


def dump_jsonld(
    project: Project,
    path: str,
    context_file: Optional[str] = None,
    field33_context: Optional[str] = None,
) -> None:
    """Export a Project model to JSON-LD file.

    Converts the project to JSON-LD format and writes it to the specified file.
    Uses orjson for fast serialization if available, falls back to standard json.

    Args:
        project: The Project model to export.
        path: Output file path. Parent directories will be created if needed.
        context_file: Optional path to custom JSON-LD context file.
        field33_context: Optional path to Field33-specific context file.

    Raises:
        ValueError: If project.id is empty or path is invalid.
        OSError: If file cannot be written (permissions, disk space, etc.).

    Example:
        >>> project = Project(id="repo:myproject", name="MyProject")
        >>> dump_jsonld(project, "output/analysis.jsonld")
    """
    if not path:
        raise ValueError("Output path cannot be empty")

    # Ensure parent directory exists
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to JSON-LD
    data = to_jsonld(project, context_file=context_file, field33_context=field33_context)

    # Try fast serialization with orjson
    try:
        import orjson

        logger.debug(f"Writing JSON-LD to {path} using orjson")
        with output_path.open("wb") as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))

    except ImportError:
        # Fallback to standard json
        logger.debug(f"Writing JSON-LD to {path} using standard json (orjson not available)")
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    except (OSError, IOError) as e:
        logger.error(f"Failed to write JSON-LD file {path}: {e}")
        raise

    except Exception as e:
        logger.exception(f"Unexpected error writing JSON-LD to {path}: {e}")
        raise

    logger.info(f"Successfully exported JSON-LD to {path}")
