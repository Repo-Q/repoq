"""Configuration package for RepoQ.

Modules:
- settings: General application settings (legacy config.py)
- quality_policy: Quality policy YAML parser and validation
"""

from repoq.config.settings import *  # noqa: F401, F403

__all__ = ["settings", "quality_policy"]
