from __future__ import annotations
import json, os
from typing import Optional
from .model import Project

BASE_CONTEXT = {
  "@context": {
    "schema": "https://schema.org/",
    "codemeta": "https://w3id.org/codemeta#",
    "repo": "http://example.org/vocab/repo#",
    "dcterms": "http://purl.org/dc/terms/",
    "prov": "http://www.w3.org/ns/prov#",
    "oslc": "http://open-services.net/ns/core#",
    "oslc_cm": "http://open-services.net/ns/cm#",
    "oslc_qm": "http://open-services.net/ns/qm#",
    "oslc_config": "http://open-services.net/ns/config#",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "spdx": "http://spdx.org/rdf/terms#",
    "okn_sd": "https://w3id.org/okn/o/sd#",
    "vc": "https://www.w3.org/2018/credentials#",
    "sec": "https://w3id.org/security#",
    "cert": "http://example.org/vocab/cert#",
    "name": "schema:name",
    "description": "schema:description",
    "programmingLanguages": "schema:programmingLanguage",
    "repositoryURL": "schema:codeRepository",
    "lastCommitDate": "dcterms:modified",
    "hasCertificate": "cert:hasCertificate"
  }
}

def dump_jsonld(p: Project, path: str, *, context_file: Optional[str] = None, field33_context: Optional[str] = None) -> None:
    data = BASE_CONTEXT.copy()
    if context_file and os.path.exists(context_file):
        with open(context_file,"r",encoding="utf-8") as f:
            data = json.load(f)
    data.update({
        "@id": p.repository_url or p.id,
        "@type": ["repo:Project", "okn_sd:Software"],
        "name": p.name,
        "description": p.description or "",
        "programmingLanguages": list(p.programming_languages.keys()),
        "license": p.license or "",
        "modules": [],
        "files": [],
        "contributors": [],
        "issues": [],
    })
    for m in p.modules.values():
        data["modules"].append({
            "@id": m.id, "@type": "repo:Module", "name": m.name, "path": m.path,
            "containsFile": m.contains_files, "totalLinesOfCode": m.total_loc, "mainLanguage": m.main_language
        })
    for f in p.files.values():
        data["files"].append({
            "@id": f.id, "@type": ["repo:File","schema:SoftwareSourceCode"],
            "path": f.path, "language": f.language, "linesOfCode": f.lines_of_code,
            "complexity": f.complexity, "commitsCount": f.commits_count, "codeChurn": f.code_churn,
            "lastModified": f.last_modified, "testFile": f.test_file, "module": f.module
        })
    for aid, a in p.contributors.items():
        data["contributors"].append({"@id": aid, "@type": "foaf:Person", "name": aid, "commits": a.get("commits",0)})
    for iid, i in p.issues.items():
        data["issues"].append({"@id": i.id, "@type": f"repo:{i.type}", "file": i.file, "description": i.description, "severity": i.severity})
    with open(path,"w",encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
