from __future__ import annotations
import json

def diff_jsonld(old: str, new: str) -> dict:
    a = json.load(open(old,"r",encoding="utf-8"))
    b = json.load(open(new,"r",encoding="utf-8"))
    return {"files_old": len(a.get("files",[])), "files_new": len(b.get("files",[]))}
