from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import yaml, os

@dataclass
class Thresholds:
    complexity_high: int = 15
    hotspot_top_n: int = 50
    ownership_owner_threshold: float = 0.8
    fail_on_issues: str | None = None

@dataclass
class AnalyzeConfig:
    mode: str = "full"
    since: str | None = None
    include_extensions: List[str] | None = None
    exclude_globs: List[str] = field(default_factory=lambda: ["**/.git/**","**/node_modules/**"])
    max_files: int | None = None
    graphs_dir: str | None = None
    jsonld_path: str = "quality.jsonld"
    md_path: str | None = None
    ttl_path: str | None = None
    validate_shapes: bool = False
    shapes_dir: str | None = None
    context_file: str | None = None
    field33_context: str | None = None
    fail_on_issues: str | None = None
    branch: str | None = None
    depth: int | None = None
    hash_algo: str | None = None

    thresholds: Thresholds = field(default_factory=Thresholds)

def load_config(path: str | None) -> dict:
    if not path or not os.path.exists(path): return {}
    return yaml.safe_load(open(path,"r",encoding="utf-8")) or {}
