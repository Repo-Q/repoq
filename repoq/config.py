"""Configuration management for repoq analysis.

This module defines configuration dataclasses and loading functions for:
- Analysis thresholds (complexity, hotspots, ownership)
- File filtering (extensions, globs, max files)
- Export options (JSON-LD, RDF, Markdown, graphs)
- Git options (branch, depth, since)
- Validation options (SHACL shapes)

Configuration can be loaded from YAML files or CLI arguments.
"""
from __future__ import annotations

import logging
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class Thresholds:
    """Quality thresholds for analysis and reporting.

    Attributes:
        complexity_high: Cyclomatic complexity threshold for high severity (default: 15)
        hotspot_top_n: Number of top hotspots to report (default: 50)
        ownership_owner_threshold: Ownership percentage to be considered owner (default: 0.5)
        fail_on_issues: Exit with error on issues at severity level (default: None)
    """
    complexity_high: int = 15
    hotspot_top_n: int = 50
    ownership_owner_threshold: float = 0.5  # >50% — владелец
    fail_on_issues: Optional[str] = None  # low|medium|high


@dataclass
class AnalyzeConfig:
    """Main configuration for repository analysis.

    Aggregates all analysis parameters including thresholds, filters, export
    options, and Git settings. Can be constructed from CLI args, YAML config,
    or programmatically.

    Attributes:
        mode: Analysis mode: "structure", "history", or "full" (default: "full")
        since: Time range for history (e.g., "1 year ago") (default: None)
        include_extensions: Whitelist of file extensions to analyze (default: None)
        exclude_globs: Glob patterns to exclude from analysis (default: common build dirs)
        max_files: Limit maximum files to analyze (default: None)
        md_path: Markdown report output path (default: None)
        jsonld_path: JSON-LD output path (default: "quality.jsonld")
        graphs_dir: Directory for dependency/coupling graphs (default: None)
        branch: Git branch to analyze (default: None)
        depth: Git clone depth for shallow clones (default: None)
        thresholds: Quality thresholds configuration (default: Thresholds())
        cache_dir: Directory for caching (default: ".repoq")
        fail_on_issues: Exit with error on issues at severity level (default: None)
        ttl_path: RDF Turtle export path (default: None)
        validate_shapes: Enable SHACL validation (default: False)
        shapes_dir: Directory with SHACL shape files (default: None)
        context_file: Custom JSON-LD context file (default: None)
        field33_context: Field33 context extension (default: None)
        hash_algo: File checksum algorithm: "sha1" or "sha256" (default: None)
    """

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
    """Load configuration from YAML file.

    Args:
        path: Path to YAML configuration file, or None

    Returns:
        Dictionary with configuration values, or empty dict if path is None

    Raises:
        FileNotFoundError: If path is provided but file does not exist
        yaml.YAMLError: If file is not valid YAML

    Example:
        >>> config = load_config("repoq.yaml")
        >>> print(config.get("mode"))
        'full'
    """
    if not path:
        return {}
    
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    
    try:
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        logger.debug(f"Loaded configuration from {path}")
        return data
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse YAML config {path}: {e}")
        raise
    except OSError as e:
        logger.error(f"Failed to read config file {path}: {e}")
        raise
