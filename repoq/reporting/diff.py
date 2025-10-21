from __future__ import annotations

import json


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def diff_jsonld(old_path: str, new_path: str) -> dict:
    old = load_json(old_path)
    new = load_json(new_path)

    def idx_issues(d: dict) -> set:
        return set(i["@id"] for i in d.get("issues", []))

    def idx_files(d: dict) -> dict:
        return {f["@id"]: f for f in d.get("files", [])}

    issues_added = idx_issues(new) - idx_issues(old)
    issues_removed = idx_issues(old) - idx_issues(new)
    files_old = idx_files(old)
    files_new = idx_files(new)
    hotspots_growth = []
    for fid, fnew in files_new.items():
        fprev = files_old.get(fid)
        if not fprev:
            continue
        s_prev = float(fprev.get("hotness") or 0)
        s_new = float(fnew.get("hotness") or 0)
        if s_new > s_prev:
            hotspots_growth.append((fid, s_prev, s_new))
    return {
        "issues_added": sorted(list(issues_added)),
        "issues_removed": sorted(list(issues_removed)),
        "hotspots_growth": hotspots_growth,
    }
