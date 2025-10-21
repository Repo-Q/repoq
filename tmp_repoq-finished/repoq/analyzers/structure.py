from __future__ import annotations
import os, hashlib
from ..core.model import Project, File, Module

LANG_MAP = {
  ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".java":"Java",
  ".go":"Go", ".rs":"Rust", ".cpp":"C++", ".c":"C", ".hpp":"C++", ".h":"C/C++",
  ".cs":"C#", ".rb":"Ruby", ".php":"PHP"
}

def guess_lang(path: str) -> str | None:
    _, ext = os.path.splitext(path)
    return LANG_MAP.get(ext.lower())

def is_text(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            chunk = f.read(2048)
        chunk.decode("utf-8")
        return True
    except Exception:
        return False

def count_loc(path: str) -> int:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

def sha_sum(path: str, algo: str) -> str | None:
    if not algo: return None
    h = hashlib.sha256() if algo.lower()=="sha256" else hashlib.sha1()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

class StructureAnalyzer:
    def run(self, p: Project, repo_dir: str, cfg):
        # scan files
        for root,_,files in os.walk(repo_dir):
            if ".git" in root: continue
            for fn in files:
                rel = os.path.relpath(os.path.join(root, fn), repo_dir).replace("\\","/")
                # exclusions
                if any(gl in rel for gl in (".git/","node_modules/","dist/","build/","target/")):
                    continue
                if cfg.include_extensions:
                    if not any(rel.endswith(f".{ext}") for ext in cfg.include_extensions):
                        continue
                if any(rel.startswith(gl.strip("*")) for gl in cfg.exclude_globs):
                    continue
                # text source?
                full = os.path.join(repo_dir, rel)
                if not is_text(full): continue
                fid = f"repo:file:{rel}"
                fobj = File(id=fid, path=rel, language=guess_lang(rel), lines_of_code=count_loc(full))
                fobj.test_file = rel.lower().startswith("tests/") or rel.lower().endswith("_test.py") or rel.lower().endswith("test.py")
                if cfg.hash_algo:
                    fobj.checksum_algo = cfg.hash_algo
                    fobj.checksum_value = sha_sum(full, cfg.hash_algo)
                # module by top-level dir
                parts = rel.split("/")
                modname = parts[0] if len(parts)>1 else p.name
                mid = f"repo:module:{modname}"
                fobj.module = mid
                p.files[fid] = fobj
                m = p.modules.get(mid) or Module(id=mid, name=modname, path=modname)
                m.contains_files.append(fid); m.total_loc += fobj.lines_of_code
                p.modules[mid] = m
                # languages
                if fobj.language:
                    p.programming_languages[fobj.language] = p.programming_languages.get(fobj.language,0) + fobj.lines_of_code
        # main language per module
        for m in p.modules.values():
            lang_counter = {}
            for fid in m.contains_files:
                lang = p.files[fid].language
                if lang: lang_counter[lang] = lang_counter.get(lang,0) + p.files[fid].lines_of_code
            m.main_language = max(lang_counter, key=lang_counter.get) if lang_counter else None
