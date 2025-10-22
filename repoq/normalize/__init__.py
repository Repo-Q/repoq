"""
Normalization subsystem for repoq.

This module implements Term Rewriting Systems (TRS) for various domain-specific
languages used in repoq: SPDX licenses, SemVer ranges, RDF graphs, filters, and metrics.

The normalization ensures:
- **Soundness**: transformations preserve semantics
- **Confluence**: order of rewrites doesn't matter (Church-Rosser)
- **Termination**: all rewrite sequences reach normal form
- **Idempotence**: NF(NF(x)) = NF(x)

This provides deterministic outputs for reports, diffs, and RDF exports.

Modules:
    base: Abstract TRS infrastructure (Term, Rule, RewriteSystem)
    spdx_trs: SPDX license expression normalization
    semver_trs: Semantic version range normalization
    rdf_trs: RDF/JSON-LD graph canonicalization
    filters_trs: History filter normalization (DNF/CNF)
    metrics_trs: Metric formula normalization
    shacl_trs: SHACL shape simplification

Example:
    >>> from repoq.normalize import normalize_spdx
    >>> normalize_spdx("(MIT AND Apache-2.0) OR MIT")
    'MIT'
    >>> normalize_spdx("MIT OR Apache-2.0")
    'Apache-2.0 OR MIT'  # Canonical order
"""

from .base import RewriteSystem, Rule, Term
from .filters_trs import (
    FileProperty,
    FilterExpression,
    GlobPattern,
    LogicalFilter,
    canonicalize_filter,
    canonicalize_filter_advanced,
    check_filter_equivalence,
    simplify_glob_patterns,
)
from .metrics_trs import (
    AggregationFunction,
    ArithmeticOperation,
    MetricConstant,
    MetricExpression,
    MetricVariable,
    canonicalize_metric,
    normalize_weights,
    optimize_metric_expression,
    parse_metric_expression,
)
from .rdf_trs import RDFTerm, canonicalize_rdf
from .semver_trs import SemVerTerm, normalize_semver
from .spdx_trs import SPDXTerm, normalize_spdx

__all__ = [
    # Base classes
    "Term",
    "Rule",
    "RewriteSystem",
    # SPDX
    "normalize_spdx",
    "SPDXTerm",
    # SemVer
    "normalize_semver",
    "SemVerTerm",
    # RDF
    "canonicalize_rdf",
    "RDFTerm",
    # Filters
    "normalize_filter",
    # Metrics
    "normalize_metric",
]
