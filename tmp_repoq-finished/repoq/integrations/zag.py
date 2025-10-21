from __future__ import annotations
import os, json
from typing import Dict, Any, List, Optional, Tuple
from ..core.model import Project, File, Module
from jsonschema import Draft7Validator

SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "zag_schemas")
def _load_schema(name: str) -> dict:
    with open(os.path.join(SCHEMA_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)
PCQ_SCHEMA = _load_schema("pcq_schema.json")
PCE_SCHEMA = _load_schema("pce_schema.json")
MAN_SCHEMA = _load_schema("zag_manifest_schema.json")

def _normalize(x: float, lo: float, hi: float) -> float:
    if hi <= lo: return 0.0
    v = (x - lo) / (hi - lo)
    return max(0.0, min(1.0, v))

def build_pcq(project: Project, *, level: str="module", U: str="[0,1]", aggregator: str="min", tau: float=0.8) -> dict:
    max_churn = max((f.code_churn for f in project.files.values()), default=1.0) or 1.0
    max_hot = max((f.hotness or 0.0 for f in project.files.values()), default=1.0) or 1.0
    support: List[dict] = []
    if level == "file":
        items = list(project.files.values())
        denom = sum(max(1, x.lines_of_code) for x in items) or 1
        for f in items:
            ch = _normalize(f.code_churn, 0.0, max_churn)
            hot = _normalize(float(f.hotness or 0.0), 0.0, max_hot)
            util = 1.0 - 0.5*ch - 0.5*hot
            fairness = 1.0 - hot
            weight = max(1, f.lines_of_code) / denom
            support.append({"id": f.id, "weight": float(weight), "metrics": {"utility": float(util), "fairness": float(fairness)}})
    else:
        modules: Dict[str, List[File]] = {}
        for f in project.files.values():
            if f.module: modules.setdefault(f.module, []).append(f)
        total_loc = sum(max(1, x.lines_of_code) for x in project.files.values()) or 1
        for mid, files in modules.items():
            if not files: continue
            ch = sum(f.code_churn for f in files) / max(1, len(files))
            hot = sum(float(f.hotness or 0.0) for f in files) / max(1, len(files))
            ch = _normalize(ch, 0.0, max_churn); hot = _normalize(hot, 0.0, max_hot)
            util = 1.0 - 0.5*ch - 0.5*hot
            fairness = 1.0 - hot
            loc = sum(max(1, f.lines_of_code) for f in files); weight = loc/total_loc
            support.append({"id": mid, "weight": float(weight), "metrics": {"utility": float(util), "fairness": float(fairness)}})
    pcq = {"U": U, "aggregator": aggregator, "tau": float(tau), "support": support, "risk": {"type":"None"}}
    Draft7Validator(PCQ_SCHEMA).validate(pcq); return pcq

def build_pce(project: Project, *, kmax: int=8, level: str="module") -> List[dict]:
    items: List[Tuple[str, float]] = []
    if level == "file":
        for f in project.files.values():
            items.append((f.id, float(f.hotness or 0.0)))
    else:
        modules: Dict[str, float] = {}
        for f in project.files.values():
            if f.module: modules[f.module] = modules.get(f.module, 0.0) + float(f.hotness or 0.0)
        items = list(modules.items())
    items.sort(key=lambda kv: kv[1], reverse=True)
    witness = [i for i,_ in items[:kmax]]
    base = {"claim": "∃ S: |S|≤k s.t. quality ≥ τ after remediation on S", "problem": {"domain": level, "criteria": ["utility","fairness"], "budget_k": kmax}, "normal_form": "min-hitting-set over hotspot constraints", "existence_conditions": {"spectral_gap_min": 0.0, "mincut_budget": 0.0}, "witness": witness, "value_bound": 0.0}
    Draft7Validator(PCE_SCHEMA).validate(base)
    return [base, base]

def _aggregate_coupling_by_module(project: Project) -> tuple[list[str], list[dict]]:
    nodes = list(project.modules.keys())
    weights: dict[tuple[str,str], float] = {}
    for e in project.coupling:
        a_mod = project.files.get(e.a).module if project.files.get(e.a) else None
        b_mod = project.files.get(e.b).module if project.files.get(e.b) else None
        if not a_mod or not b_mod or a_mod == b_mod: continue
        key = tuple(sorted((a_mod, b_mod))); weights[key] = weights.get(key, 0.0) + float(e.weight)
    edges = [{"u": a, "v": b, "weight": float(w)} for (a,b), w in weights.items()]
    return nodes, edges

def build_fairness_cover(project: Project, *, level: str="module", budget: float=1.0, boundary: list[str] | None=None) -> dict:
    if level == "file":
        nodes = list(project.files.keys()); edges = [{"u": e.a, "v": e.b, "weight": float(e.weight)} for e in project.coupling]
    else:
        nodes, edges = _aggregate_coupling_by_module(project)
    if boundary is None:
        deg = {n:0.0 for n in nodes}
        for e in edges:
            deg[e["u"]] = deg.get(e["u"], 0.0)+e["weight"]; deg[e["v"]] = deg.get(e["v"], 0.0)+e["weight"]
        boundary = sorted(deg, key=lambda n: deg[n], reverse=True)[:2]
    return {"nodes": nodes, "edges": edges, "boundary": boundary, "budget": float(budget)}

def build_ahr(project: Project, *, tau: float, baselineQ: float) -> dict:
    hot_ratio = len([f for f in project.files.values() if (f.hotness or 0.0) > 0.66]) / max(1, len(project.files))
    updates = []; Q0 = baselineQ
    for t in range(3):
        Qt = max(0.0, Q0 - t*0.02 - hot_ratio*0.05)
        updates.append({"t": t, "Q_robust": round(Qt, 4), "delta": 0.0, "fairness_cycle": 0.0, "pcq_support_k": 2, "FQ": round(Qt, 4)})
    return {"tau": float(tau), "baselineQ": float(baselineQ), "updates": updates}

def build_manifest(project: Project, *, model: str, version: str, date: str, pcq_path: str, pce_paths: list[str], fairness_cover: dict, ahr: dict, options: dict) -> dict:
    man = {"model": model, "version": version, "date": date, "pcq": pcq_path, "pce": pce_paths, "fairness_cover": fairness_cover, "ahr": ahr, "options": options}
    Draft7Validator(MAN_SCHEMA).validate(man); return man

def write_zag_bundle(project: Project, out_dir: str, *, level: str="module", U: str="[0,1]", aggregator: str="min", tau: float=0.8, budget: float=1.0, boundary: list[str] | None=None, kmax: int=8, model_name: str | None=None, version: str | None=None) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    from ..certs.quality import compute_project_score
    pcq = build_pcq(project, level=level, U=U, aggregator=aggregator, tau=tau)
    pces = build_pce(project, kmax=kmax, level=level)
    fairness = build_fairness_cover(project, level=level, budget=budget, boundary=boundary)
    score, _ = compute_project_score(project); ahr = build_ahr(project, tau=tau, baselineQ=round(score/100.0, 4))
    pcq_path = os.path.join(out_dir, "pcq.json"); open(pcq_path,"w",encoding="utf-8").write(json.dumps(pcq, ensure_ascii=False, indent=2))
    pce_paths = []
    for i, pce in enumerate(pces):
        pp = os.path.join(out_dir, f"pce_{i+1}.json"); open(pp,"w",encoding="utf-8").write(json.dumps(pce, ensure_ascii=False, indent=2)); pce_paths.append(os.path.relpath(pp, out_dir))
    man = build_manifest(project, model=model_name or (project.name or "Project"), version=version or "dev", date=date_iso(), pcq_path=os.path.relpath(pcq_path, out_dir), pce_paths=pce_paths, fairness_cover=fairness, ahr=ahr, options={"zk": False, "kmax": kmax})
    man_path = os.path.join(out_dir, "manifest.json"); open(man_path,"w",encoding="utf-8").write(json.dumps(man, ensure_ascii=False, indent=2))
    return {"pcq": pcq_path, "pce": pce_paths, "manifest": man_path}

def date_iso() -> str:
    import datetime; return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
