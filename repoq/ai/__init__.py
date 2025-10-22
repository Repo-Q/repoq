"""
AI-Assisted Analysis Module for RepoQ
Phase 5.8: BAML AI Agent Integration

This module provides AI-powered validation and analysis capabilities:
- TRS rule validation (confluence, termination)
- Ontology consistency checking
- Stratification safety analysis
- Code review assistance

4-Phase Rollout:
1. EXPERIMENTAL: Internal testing only
2. ADVISORY: Suggestions, no blocking
3. ACTIVE: Can block with human review
4. DEFAULT_ON: Default behavior with opt-out
"""

from repoq.ai.baml_agent import (
    AgentConfig,
    AgentPhase,
    BAMLAgent,
    configure_agent,
    get_agent,
)

__all__ = [
    "BAMLAgent",
    "AgentConfig",
    "AgentPhase",
    "get_agent",
    "configure_agent",
]
