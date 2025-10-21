from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class Thresholds:
    complexity_high: int = 15
    hotspot_top_n: int = 50
    ownership_owner_threshold: float = 0.5  # >50% — владелец
    fail_on_issues: Optional[str] = None  # low|medium|high


@dataclass
class AnalyzeConfig:
    mode: str = "full"  # structure|history|full
    since: Optional[str] = None  # e.g., "1 year ago"
    include_extensions: Optional[List[str]] = None  # ["py","js","java"]
    exclude_globs: List[str] = field(
        default_factory=lambda: [
            "**/.git/**",
            "**/node_modules/**",
            "**/.venv/**",
            "**/venv/**",
            "**/dist/**",
            "**/build/**",
            "**/target/**",
        ]
    )
    max_files: Optional[int] = None
    md_path: Optional[str] = None
    jsonld_path: str = "quality.jsonld"
    graphs_dir: Optional[str] = None
    branch: Optional[str] = None
    depth: Optional[int] = None
    thresholds: Thresholds = field(default_factory=Thresholds)
    cache_dir: str = ".repoq"
    fail_on_issues: Optional[str] = None
    ttl_path: Optional[str] = None
    validate_shapes: bool = False
    shapes_dir: Optional[str] = None
    context_file: Optional[str] = None
    field33_context: Optional[str] = None
    hash_algo: Optional[str] = None  # "sha1"|"sha256"


def load_config(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {}
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data
