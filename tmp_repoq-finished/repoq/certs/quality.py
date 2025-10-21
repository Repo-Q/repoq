from __future__ import annotations
from typing import Dict, Tuple, List
from ..core.model import Project, File, Module

def _grade(score: float) -> str:
    return "A" if score>=90 else "B" if score>=80 else "C" if score>=70 else "D" if score>=60 else "E" if score>=50 else "F"

def _gates(score: float, hotspot_ratio: float, ci: bool, doc_ok: bool, ownership_ok: bool, tests_ratio: float, profile: str="STANDARD") -> Dict[str, str]:
    p = profile.upper()
    if p == "STRICT": min_score,max_hot,min_tests = 85,0.05,0.4
    elif p == "RELAXED": min_score,max_hot,min_tests = 60,0.25,0.0
    else: min_score,max_hot,min_tests = 75,0.15,0.2
    return {
        "score": "pass" if score >= min_score else "fail",
        "hotspots": "pass" if hotspot_ratio <= max_hot else "fail",
        "ci": "pass" if ci else "fail",
        "docs": "pass" if doc_ok else "fail",
        "ownership": "pass" if ownership_ok else "fail",
        "tests": "pass" if tests_ratio >= min_tests else "fail",
    }

def compute_project_score(p: Project) -> Tuple[float, Dict[str,str]]:
    files = list(p.files.values())
    if not files:
        return 100.0, _gates(100.0, 0.0, bool(p.ci_configured), bool(p.description), True, 1.0)
    max_cplx = max((f.complexity or 0.0 for f in files), default=1.0) or 1.0
    avg_cplx = sum((f.complexity or 0.0) for f in files) / max(1,len(files))
    churn_total = sum(f.code_churn for f in files)
    max_churn = max((f.code_churn for f in files), default=1) or 1
    hotspot_ratio = len([f for f in files if (f.hotness or 0.0) > 0.66]) / max(1,len(files))
    doc_ok = True  # heuristic
    ci_ok = bool(p.ci_configured)
    # ownership heuristic
    owned_hard = 0
    for f in files:
        total_lines = sum(m.get("linesAdded",0) for m in f.contributors.values()) or 0
        if total_lines>0:
            max_lines = max(m.get("linesAdded",0) for m in f.contributors.values())
            if (max_lines/total_lines)>=0.8: owned_hard += 1
    ownership_ok = (owned_hard/ max(1,len(files))) <= 0.5
    tests_ratio = len(p.tests_results) / max(1,len(files))

    score = 100.0
    score -= (avg_cplx/(max_cplx or avg_cplx or 1.0)) * 20.0
    score -= (churn_total/((max_churn*len(files)) or churn_total or 1.0)) * 20.0
    score -= hotspot_ratio * 30.0
    if not ci_ok: score -= 7.0
    if not ownership_ok: score -= 8.0
    if tests_ratio < 0.2: score -= (0.2 - tests_ratio) * 30.0
    score = max(0.0, min(100.0, score))
    return score, _gates(score, hotspot_ratio, ci_ok, doc_ok, ownership_ok, tests_ratio)

def compute_module_score(p: Project, m: Module) -> Tuple[float, Dict[str,str]]:
    files = [p.files[fid] for fid in m.contains_files if fid in p.files]
    if not files:
        return 100.0, _gates(100.0, 0.0, bool(p.ci_configured), True, True, 1.0)
    max_cplx = max((f.complexity or 0.0 for f in files), default=1.0) or 1.0
    avg_cplx = sum((f.complexity or 0.0) for f in files)/max(1,len(files))
    churn_total = sum(f.code_churn for f in files)
    max_churn = max((f.code_churn for f in files), default=1) or 1
    hotspot_ratio = len([f for f in files if (f.hotness or 0.0) > 0.66]) / max(1,len(files))
    ownership_ok = True
    tests_ratio = 1.0 if any(f.test_file for f in files) else 0.0

    score = 100.0
    score -= (avg_cplx/(max_cplx or avg_cplx or 1.0)) * 20.0
    score -= (churn_total/((max_churn*len(files)) or churn_total or 1.0)) * 20.0
    score -= hotspot_ratio * 30.0
    if tests_ratio < 0.2: score -= (0.2 - tests_ratio) * 30.0
    score = max(0.0, min(100.0, score))
    return score, _gates(score, hotspot_ratio, bool(p.ci_configured), True, ownership_ok, tests_ratio)

def compute_file_score(f: File) -> Tuple[float, Dict[str,str]]:
    loc = max(1, f.lines_of_code or 1)
    cplx = float(f.complexity or 0.0)
    churn = float(f.code_churn or 0.0)
    hot = float(f.hotness or 0.0)
    score = 100.0
    score -= min(20.0, (cplx/20.0)*20.0)
    score -= min(20.0, (churn/(10*loc))*20.0)
    score -= hot * 40.0
    if f.test_file: score += 5.0
    score = max(0.0, min(100.0, score))
    gates = {"score": "pass" if score >= 75 else "fail", "hotspots": "pass" if hot <= 0.33 else "fail", "tests": "pass" if f.test_file else "fail"}
    return score, gates
