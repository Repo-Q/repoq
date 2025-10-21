from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from .model import Project


def _load_context(path: Optional[str]) -> Any:
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


DEFAULT_CONTEXT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "ontologies", "context_ext.jsonld"
)


def to_jsonld(
    project: Project, context_file: Optional[str] = None, field33_context: Optional[str] = None
) -> Dict[str, Any]:
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
        s = (sev or "").lower()
        if s == "high":
            return "http://open-services.net/ns/cm#Critical"
        if s == "medium":
            return "http://open-services.net/ns/cm#Major"
        return "http://open-services.net/ns/cm#Minor"

    def _oslc_pri(pri: Optional[str]) -> Optional[str]:
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
    data = to_jsonld(project, context_file=context_file, field33_context=field33_context)
    try:
        import orjson

        with open(path, "wb") as f:
            f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))
    except Exception:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
