"""Per-Component Quality (PCQ) with min-aggregation.

Phase 2.4: ZAG PCQ Anti-Gaming Aggregator
References: FR-04, ADR-007, V02 (Anti-gaming)

Implements gaming-resistant quality aggregation through minimum operator:
    PCQ(S) = min_{m∈modules} Q(m)

This prevents "compensation gaming" where developers hide low quality
in one module while improving others.

Theorem (Gaming Resistance):
    ∀ modules M, improving Q(m_i) for m_i ≠ min-module
    does NOT increase PCQ(M).

    Proof: PCQ = min_{m∈M} Q(m), so improving non-min modules
           leaves min unchanged, thus PCQ unchanged.

Example:
    >>> from repoq.core.model import Project, Module, File
    >>> from repoq.quality.pcq import calculate_pcq
    >>>
    >>> project = Project(id="test", name="Test")
    >>> # Add modules and files...
    >>> pcq = calculate_pcq(project)
    >>> assert 0 <= pcq <= 100
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from repoq.core.model import Project

# Import from sibling quality.py file (not quality/ directory)
# Use sys.modules trick to avoid circular import
_legacy_quality = None


def _get_legacy_quality():
    """Lazy import of legacy quality.py module."""
    global _legacy_quality
    if _legacy_quality is None:
        # Import the sibling quality.py file
        import importlib.util

        quality_py_path = Path(__file__).parent.parent / "quality.py"
        spec = importlib.util.spec_from_file_location("repoq._quality_legacy", quality_py_path)
        _legacy_quality = importlib.util.module_from_spec(spec)

        # Temporarily add repoq to sys.modules to handle relative imports in quality.py
        original_quality = sys.modules.get("repoq.quality")
        try:
            # Temporarily replace repoq.quality with the file version
            sys.modules["repoq._quality_legacy"] = _legacy_quality
            spec.loader.exec_module(_legacy_quality)
        finally:
            if original_quality:
                sys.modules["repoq.quality"] = original_quality

    return _legacy_quality


def calculate_pcq(project: "Project", module_type: str = "directory") -> float:
    """Calculate Per-Component Quality (PCQ) with min-aggregation.

    PCQ implements gaming resistance through minimum aggregation:
        PCQ(S) = min_{m∈modules} Q(m)

    This prevents "compensation gaming" where developers hide complexity
    in one module while improving others.

    Args:
        project: Project with modules/files
        module_type: "directory", "layer", or "bounded_context"

    Returns:
        PCQ score ∈ [0, 100], the minimum quality across all modules

    Example:
        >>> pcq = calculate_pcq(project, module_type="directory")
        >>> assert 0 <= pcq <= 100
        >>> # If any module has low quality, PCQ reflects that

    Note:
        Delegates to legacy implementation in repoq/quality.py (sibling file).
        Will be migrated to standalone implementation in future refactor.
    """
    legacy = _get_legacy_quality()
    return legacy.calculate_pcq(project, module_type)


def compute_quality_score(project: "Project", arch_model=None):
    """Wrapper for compute_quality_score from legacy quality.py."""
    legacy = _get_legacy_quality()
    return legacy.compute_quality_score(project, arch_model)


__all__ = ["calculate_pcq", "compute_quality_score"]
