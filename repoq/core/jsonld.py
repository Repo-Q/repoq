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
    ctx_base = _load_context(DEFAULT_CONTEXT_PATH) or {"@context": {}}
    if context_file:
        ctx_user = _load_context(context_file)
        if isinstance(ctx_user, dict) and "@context" in ctx_user:
            # shallow merge
            ctx_base["@context"].update(ctx_user["@context"])
    if field33_context:
        ctx_f33 = _load_context(field33_context)
        if isinstance(ctx_f33, dict) and "@context" in ctx_f33:
            ctx_base["@context"].update(ctx_f33["@context"])

    data = {
        "@context": ctx_base["@context"],
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

    for m in project.modules.values():
        data["modules"].append(
            {
                "@id": m.id,
                "@type": "repo:Module",
                "name": m.name,
                "path": m.path,
                "containsFile": m.contains_files,
                "containsModule": m.contains_modules,
                "totalLinesOfCode": m.total_loc,
                "totalCommits": m.total_commits,
                "numAuthors": m.num_authors,
                "owner": m.owner,
                "hotspotScore": m.hotspot_score,
                "mainLanguage": m.main_language,
            }
        )

    for f in project.files.values():
        file_node = {
            "@id": f.id,
            "@type": ["repo:File", "schema:SoftwareSourceCode", "spdx:File", "prov:Entity"],
            "path": f.path,
            "fileName": f.path,
            "language": f.language,
            "linesOfCode": f.lines_of_code,
            "complexity": f.complexity,
            "maintainability": f.maintainability,
            "commitsCount": f.commits_count,
            "codeChurn": f.code_churn,
            "contributors": [{"@id": pid, **metrics} for pid, metrics in f.contributors.items()],
            "issues": f.issues,
            "lastModified": f.last_modified,
            "deprecated": f.deprecated,
            "testFile": f.test_file,
            "module": f.module,
            "hotness": f.hotness,
        }
        if f.checksum_algo and f.checksum_value:
            file_node["checksum"] = {
                "@type": "spdx:Checksum",
                "algorithm": f"spdx:checksumAlgorithm_{f.checksum_algo}",
                "checksumValue": f.checksum_value,
            }
        data["files"].append(file_node)

    for p in project.contributors.values():
        data["contributors"].append(
            {
                "@id": p.id,
                "@type": ["schema:Person", "foaf:Person", "prov:Agent", "prov:Person"],
                "name": p.name,
                "email": p.email or None,
                "emailHash": p.email_hash or None,
                "mbox_sha1sum": p.foaf_mbox_sha1sum or None,
                "commits": p.commits,
                "linesAdded": p.lines_added,
                "linesDeleted": p.lines_deleted,
                "owns": p.owns,
                "modulesContributed": p.modules_contributed,
            }
        )

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
            return "http://open-services.net/ns/cm#High"
        if p == "medium":
            return "http://open-services.net/ns/cm#Normal"
        return "http://open-services.net/ns/cm#Low"

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
