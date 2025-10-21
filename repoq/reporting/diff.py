"""Diff utility for comparing two JSON-LD analysis results.

This module provides functions to:
- Compare two analysis snapshots (baseline vs current)
- Detect new/removed issues
- Track hotspot score regressions
- Support CI/CD quality gates

Used by the 'repoq diff' command for trend analysis.
"""
from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


def load_json(path: str):
    """Load JSON-LD file.

    Args:
        path: Path to JSON-LD file

    Returns:
        Parsed JSON dictionary

    Raises:
        OSError: If file cannot be read
        json.JSONDecodeError: If file is not valid JSON
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        logger.error(f"Failed to read file {path}: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from {path}: {e}")
        raise


def diff_jsonld(old_path: str, new_path: str) -> dict:
    """Compare two JSON-LD analysis files and detect regressions.

    Compares baseline (old) and current (new) analysis results to identify:
    - Issues added (new quality problems)
    - Issues removed (fixed problems)
    - Hotspot score increases (files becoming riskier)

    Args:
        old_path: Path to baseline JSON-LD file
        new_path: Path to current JSON-LD file

    Returns:
        Dictionary with keys:
        - 'issues_added': List of new issue IDs
        - 'issues_removed': List of resolved issue IDs
        - 'hotspots_growth': List of (file_id, old_score, new_score) tuples

    Raises:
        OSError: If files cannot be read
        json.JSONDecodeError: If files are not valid JSON

    Example:
        >>> result = diff_jsonld("baseline.jsonld", "current.jsonld")
        >>> if result['issues_added']:
        ...     print(f"New issues: {len(result['issues_added'])}")
    """
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
