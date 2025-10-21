# TRS Formal Specifications

This directory contains formal specifications and verification rules for the RepoQ Term Rewriting Systems (TRS).

## Structure

- `trs_properties.py` - Core TRS property definitions and verification functions
- `confluence_rules.py` - Critical pair analysis and confluence verification  
- `termination_rules.py` - Termination measures and well-foundedness proofs
- `soundness_rules.py` - Mathematical soundness verification
- `self_application_rules.py` - Rules for safe self-application of RepoQ

## TRS Systems Covered

1. **SPDX TRS** - License identifier canonicalization
2. **SemVer TRS** - Semantic version normalization  
3. **RDF TRS** - RDF graph canonicalization
4. **Filters TRS** - Logical expression normalization (DNF/CNF)
5. **Metrics TRS** - Algebraic expression simplification

## Verification Levels

- **Basic**: Idempotence and determinism
- **Standard**: + Confluence via critical pair analysis
- **Advanced**: + Termination proofs + Soundness verification
- **Formal**: + Lean4 machine-checked proofs

## Usage

These rules are automatically executed by the CI pipeline in `.github/workflows/trs-verification.yml` to ensure:

1. All TRS maintain their formal properties
2. Self-application is safe and non-paradoxical
3. Performance remains within acceptable bounds
4. Backwards compatibility is preserved

## Property Guarantees

All TRS systems must satisfy:

- **Soundness**: Canonical forms preserve semantic equivalence
- **Confluence**: Different reduction orders lead to same normal form
- **Termination**: All rewriting sequences eventually terminate
- **Idempotence**: `canonicalize(canonicalize(x)) = canonicalize(x)`
- **Determinism**: Multiple runs produce identical results