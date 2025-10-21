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

from .base import Term, Rule, RewriteSystem
from .spdx_trs import normalize_spdx, SPDXTerm
from .semver_trs import normalize_semver, SemVerTerm
from .rdf_trs import canonicalize_rdf, RDFTerm
from .filters_trs import (
    canonicalize_filter,
    canonicalize_filter_advanced,
    check_filter_equivalence,
    simplify_glob_patterns,
    FilterExpression,
    GlobPattern,
    FileProperty,
    LogicalFilter,
)
from .metrics_trs import (
    canonicalize_metric,
    optimize_metric_expression,
    normalize_weights,
    MetricExpression,
    MetricConstant,
    MetricVariable,
    ArithmeticOperation,
    AggregationFunction,
    parse_metric_expression,
)

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
