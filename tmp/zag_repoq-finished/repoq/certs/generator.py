from __future__ import annotations
import os, json, base64
from typing import Optional
from ..core.model import Project
from .quality import compute_project_score, compute_module_score, compute_file_score

def _b64url(b: bytes) -> str:
    import base64
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")

def _sign_hmac(payload: bytes, secret: str) -> str:
    import hmac, hashlib, json
    header = {"alg":"HS256","typ":"JWT"}
    h = _b64url(json.dumps(header, separators=(",",":")).encode())
    p = _b64url(payload)
    mac = hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    s = _b64url(mac)
    return f"{h}.{p}.{s}"

def _sign_ed25519(payload: bytes, pem_path: str) -> dict:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    with open(pem_path, "rb") as f:
        priv = serialization.load_pem_private_key(f.read(), password=None)
    sig = priv.sign(payload)
    return {"proofPurpose":"assertionMethod","verificationMethod":"did:repoq:ed25519#key-1","jws": _b64url(sig)}

def _now_iso() -> str:
    import datetime; return datetime.datetime.utcnow().replace(microsecond=0).isoformat()+"Z"

def _exp_iso(days: int) -> str:
    import datetime; return (datetime.datetime.utcnow().replace(microsecond=0) + datetime.timedelta(days=days)).isoformat()+"Z"

def _write(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

def _vc_base(issuer: str, subject_id: str, layer: str, profile: str, valid_days: int, analysis_run_id: str | None=None) -> dict:
    vc = {
        "@context": [
            {"@vocab":"http://example.org/vocab/repo#"},
            "https://www.w3.org/2018/credentials/v1",
            {"vc":"https://www.w3.org/2018/credentials#","sec":"https://w3id.org/security#","cert":"http://example.org/vocab/cert#","prov":"http://www.w3.org/ns/prov#"}
        ],
        "@type": ["vc:VerifiableCredential", "cert:QualityCertificate"],
        "issuer": issuer, "issuanceDate": _now_iso(), "expirationDate": _exp_iso(valid_days),
        "credentialSubject": {"id": subject_id, "layer": layer, "profile": profile}
    }
    if analysis_run_id:
        vc["prov:wasGeneratedBy"] = {"@id": analysis_run_id, "@type": ["prov:Activity","repo:CertificationRun"]}
    return vc

def generate_certificates(project: Project, out_dir: str, issuer: str = "did:repoq:tool", profile: str = "STANDARD", valid_days: int = 90, sign_secret: Optional[str] = None, sign_key: Optional[str] = None) -> dict:
    index = {"@context":"repoq/ontologies/context_ext.jsonld","project": None, "modules": [], "files": []}
    os.makedirs(out_dir, exist_ok=True)

    # project
    score, gates = compute_project_score(project)
    grade = "A" if score>=90 else "B" if score>=80 else "C" if score>=70 else "D" if score>=60 else "E" if score>=50 else "F"
    vc = _vc_base(issuer, project.id, "Project", profile, valid_days)
    vc["credentialSubject"].update({"score": round(score,2), "grade": grade, "qualityGates": gates})
    if sign_secret: vc["proof"] = {"type":"sec:DataIntegrityProof","proofPurpose":"assertionMethod","jws": _sign_hmac(json.dumps(vc, separators=(',',':')).encode(), sign_secret)}
    if sign_key: vc["proof"] = {"type":"sec:Ed25519Signature2020", **_sign_ed25519(json.dumps(vc, separators=(',',':')).encode(), sign_key)}
    _write(os.path.join(out_dir, "project.jsonld"), vc); index["project"] = "project.jsonld"

    # modules
    for mid, m in project.modules.items():
        score, gates = compute_module_score(project, m)
        grade = "A" if score>=90 else "B" if score>=80 else "C" if score>=70 else "D" if score>=60 else "E" if score>=50 else "F"
        vc = _vc_base(issuer, mid, "Module", profile, valid_days)
        vc["credentialSubject"].update({"score": round(score,2), "grade": grade, "qualityGates": gates, "metrics": {"files": len(m.contains_files), "loc": m.total_loc, "mainLanguage": m.main_language}})
        if sign_secret: vc["proof"] = {"type":"sec:DataIntegrityProof","proofPurpose":"assertionMethod","jws": _sign_hmac(json.dumps(vc, separators=(',',':')).encode(), sign_secret)}
        if sign_key: vc["proof"] = {"type":"sec:Ed25519Signature2020", **_sign_ed25519(json.dumps(vc, separators=(',',':')).encode(), sign_key)}
        fname = f"{m.name}.jsonld"; _write(os.path.join(out_dir, "modules", fname), vc); index["modules"].append(os.path.join("modules", fname))

    # files
    for fid, f in project.files.items():
        score, gates = compute_file_score(f)
        grade = "A" if score>=90 else "B" if score>=80 else "C" if score>=70 else "D" if score>=60 else "E" if score>=50 else "F"
        vc = _vc_base(issuer, fid, "File", profile, valid_days)
        vc["credentialSubject"].update({"score": round(score,2), "grade": grade, "qualityGates": gates, "metrics": {"loc": f.lines_of_code, "complexity": f.complexity, "churn": f.code_churn, "hotness": f.hotness, "testFile": f.test_file}})
        if f.checksum_value and f.checksum_algo:
            vc["credentialSubject"]["spdx:checksum"] = {"@type": "spdx:Checksum", "algorithm": f"spdx:checksumAlgorithm_{f.checksum_algo}", "checksumValue": f.checksum_value}
        if sign_secret: vc["proof"] = {"type":"sec:DataIntegrityProof","proofPurpose":"assertionMethod","jws": _sign_hmac(json.dumps(vc, separators=(',',':')).encode(), sign_secret)}
        if sign_key: vc["proof"] = {"type":"sec:Ed25519Signature2020", **_sign_ed25519(json.dumps(vc, separators=(',',':')).encode(), sign_key)}
        fname = f"{fid.split(':',2)[-1].replace('/','_')}.jsonld"
        _write(os.path.join(out_dir, "files", fname), vc); index["files"].append(os.path.join("files", fname))

    _write(os.path.join(out_dir, "index.jsonld"), index)
    return index
