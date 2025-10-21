from __future__ import annotations
import os, json

def _load(path: str):
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def write_markdown_pack(certs_dir: str, out_md: str = None) -> str:
    idx = _load(os.path.join(certs_dir, "index.jsonld"))
    lines = ["# Сертификаты качества", ""]
    pj = os.path.join(certs_dir, "project.jsonld")
    if os.path.exists(pj):
        c = _load(pj); cs = c.get("credentialSubject", {})
        lines += ["## Проект", f"- score: **{cs.get('score','-')}**  grade: **{cs.get('grade','-')}**  assurance: **{cs.get('assuranceLevel','-')}**"]
        gates = cs.get("qualityGates", {})
        if gates: lines.append("- Quality Gates: " + ", ".join(f"{k}={v}" for k,v in gates.items()))
    lines += ["", "## Модули"]
    for rel in idx.get("modules", []):
        p = os.path.join(certs_dir, rel.replace("/", os.sep))
        if os.path.exists(p):
            c = _load(p); cs = c.get("credentialSubject", {})
            lines.append(f"- {rel}: score={cs.get('score','-')} grade={cs.get('grade','-')} assurance={cs.get('assuranceLevel','-')}")
    lines += ["", "## Файлы (top-20 по убыванию риска)"]
    file_rows = []
    for rel in idx.get("files", []):
        p = os.path.join(certs_dir, rel.replace("/", os.sep))
        if os.path.exists(p):
            c = _load(p); cs = c.get("credentialSubject", {})
            score = float(cs.get("score", 0.0) or 0.0)
            hot = float(cs.get("metrics",{}).get("hotness", 0.0) or 0.0)
            file_rows.append((1.0-score/100.0 + hot, rel, cs))
    file_rows.sort(reverse=True)
    for _, rel, cs in file_rows[:20]:
        lines.append(f"- {rel}: score={cs.get('score','-')} grade={cs.get('grade','-')} hotness={cs.get('metrics',{}).get('hotness','-')}")
    out_md = out_md or os.path.join(certs_dir, "README.md")
    with open(out_md, "w", encoding="utf-8") as f: f.write("\n".join(lines) + "\n")
    return out_md
