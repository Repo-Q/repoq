from __future__ import annotations
import json, os

def _read(path: str):
    with open(path, "r", encoding="utf-8") as f: return json.load(f)
def _write(path: str, data: dict):
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

def _id_to_file(fid: str) -> str:
    core = fid.split(":",2)[-1].replace("/", "_"); return os.path.join("files", f"{core}.jsonld")
def _mod_to_file(mid: str) -> str:
    name = mid.split(":")[-1]; return os.path.join("modules", f"{name}.jsonld")

def link_certs_into_jsonld(jsonld_path: str, certs_dir: str) -> None:
    if not (os.path.exists(jsonld_path) and os.path.isdir(certs_dir)): return
    data = _read(jsonld_path)
    ctx = data.get("@context")
    if isinstance(ctx, dict):
        ctx.setdefault("hasCertificate", "cert:hasCertificate")
        data["@context"] = ctx
    data.setdefault("hasCertificate", [])
    top_link = os.path.join(os.path.basename(certs_dir), "project.jsonld")
    if top_link not in data["hasCertificate"]:
        data["hasCertificate"].append(top_link)
    for m in data.get("modules", []):
        link = os.path.join(os.path.basename(certs_dir), _mod_to_file(m.get("@id")))
        m.setdefault("hasCertificate", [])
        if link not in m["hasCertificate"]:
            m["hasCertificate"].append(link)
    for f in data.get("files", []):
        link = os.path.join(os.path.basename(certs_dir), _id_to_file(f.get("@id")))
        f.setdefault("hasCertificate", [])
        if link not in f["hasCertificate"]:
            f["hasCertificate"].append(link)
    _write(jsonld_path, data)

def annotate_certs_assurance(certs_dir: str, level: str) -> None:
    idx_path = os.path.join(certs_dir, "index.jsonld")
    if not os.path.exists(idx_path): return
    idx = _read(idx_path)
    def _ann(p):
        if os.path.exists(p):
            cert = _read(p)
            cert.setdefault("credentialSubject", {})["assuranceLevel"] = level
            _write(p, cert)
    _ann(os.path.join(certs_dir, "project.jsonld"))
    for rel in idx.get("modules", []):
        _ann(os.path.join(certs_dir, rel.replace("/", os.sep)))
    for rel in idx.get("files", []):
        _ann(os.path.join(certs_dir, rel.replace("/", os.sep)))
