"""Repository loader utilities for Git operations.

This module provides functions to:
- Detect and clone Git repositories from URLs
- Validate local Git repositories
- Retrieve HEAD commit hash

Supports both local paths and remote URLs (HTTP/HTTPS/SSH).
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def is_url(s: str) -> bool:
    """Check if string is a Git repository URL.

    Args:
        s: String to check

    Returns:
        True if string starts with http://, https://, or git@

    Example:
        >>> is_url("https://github.com/user/repo.git")
        True
        >>> is_url("/local/path")
        False
    """
    return s.startswith("http://") or s.startswith("https://") or s.startswith("git@")


def prepare_repo(
    path_or_url: str, depth: Optional[int] = None, branch: Optional[str] = None
) -> Tuple[str, Optional[str]]:
    """Prepare repository for analysis by cloning or validating local path.

    For URLs: Clones repository to temporary directory with optional depth/branch.
    For local paths: Validates .git directory exists and returns absolute path.

    Args:
        path_or_url: Git URL or local repository path
        depth: Optional clone depth for shallow clones (e.g., 1 for single commit)
        branch: Optional branch name to clone

    Returns:
        Tuple of (repo_directory, cleanup_path):
        - repo_directory: Absolute path to repository root
        - cleanup_path: Path to delete after analysis (tmpdir) or None for local repos

    Raises:
        RuntimeError: If path is not a valid Git repository
        subprocess.CalledProcessError: If git clone fails

    Example:
        >>> repo_dir, cleanup = prepare_repo("https://github.com/user/repo.git")
        >>> # ... analyze repo_dir ...
        >>> if cleanup:
        ...     shutil.rmtree(cleanup)
    """
    # Check if URL first (URLs don't need path resolution)
    if is_url(path_or_url):
        tmpdir = tempfile.mkdtemp(prefix="repoq_")
        cmd = ["git", "clone"]
        if depth:
            cmd += ["--depth", str(depth)]
        if branch:
            cmd += ["--branch", branch]
        cmd += [path_or_url, tmpdir]

        logger.info(f"Cloning repository {path_or_url} to {tmpdir}")
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return tmpdir, tmpdir
        except subprocess.CalledProcessError as e:
            logger.error(f"Git clone failed: {e.stderr}")
            raise

    # For local paths, resolve to absolute path
    abs_path = os.path.abspath(path_or_url)

    if os.path.isdir(abs_path) and os.path.isdir(os.path.join(abs_path, ".git")):
        logger.debug(f"Using local repository at {abs_path}")
        return abs_path, None

    raise RuntimeError(f"Not a git repo path or URL: {path_or_url}")


def get_head(path: str) -> str:
    """Get HEAD commit hash for a Git repository.

    Args:
        path: Absolute path to Git repository

    Returns:
        HEAD commit SHA as hex string, or empty string if command fails

    Example:
        >>> get_head("/path/to/repo")
        'a1b2c3d4e5f6...'
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.warning(f"Failed to get HEAD commit for {path}: {e.stderr}")
        return ""
    except Exception as e:
        logger.warning(f"Unexpected error getting HEAD for {path}: {e}")
        return ""
