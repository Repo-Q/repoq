"""Quality assurance module.

Implements PCE (Proof-Carrying Evidence) and PCQ (Proof-Carrying Quality)
for anti-gaming and actionable feedback.

Modules:
    - pce_generator: k-repair witness generation
    - pcq: ZAG min-aggregator (Phase 2.4)

Legacy compatibility:
    Re-exports functions from sibling quality.py file for backward compatibility.
"""

# NEW: PCE/PCQ modules
from repoq.quality.pce_generator import FileRepair, PCEGenerator, WitnessK
from repoq.quality.pcq import calculate_pcq, compute_quality_score

# Legacy re-exports from quality.py (sibling file)
# Import with importlib to avoid circular dependency
import sys
from pathlib import Path

# Lazy load legacy quality.py
_legacy_quality = None


def _get_legacy_quality():
    """Lazy import of legacy quality.py module."""
    global _legacy_quality
    if _legacy_quality is None:
        import importlib.util

        quality_py_path = Path(__file__).parent.parent / "quality.py"
        spec = importlib.util.spec_from_file_location(
            "repoq._quality_legacy", quality_py_path
        )
        _legacy_quality = importlib.util.module_from_spec(spec)
        sys.modules["repoq._quality_legacy"] = _legacy_quality
        spec.loader.exec_module(_legacy_quality)

    return _legacy_quality


# Re-export legacy classes/functions for backward compatibility
def __getattr__(name):
    """Dynamic attribute access for legacy quality.py exports."""
    legacy = _get_legacy_quality()
    if hasattr(legacy, name):
        return getattr(legacy, name)
    raise AttributeError(f"module 'repoq.quality' has no attribute '{name}'")


__all__ = [
    # NEW modules (Phase 2)
    "PCEGenerator",
    "WitnessK",
    "FileRepair",
    "calculate_pcq",
    "compute_quality_score",
    # Legacy re-exports (from quality.py)
    "QualityMetrics",
    "calculate_delta",
    "generate_pce_witness",
]
