# Changelog

> **Generated from RDF**: This document is auto-generated from `.repoq/changelog/releases.ttl`.
> Single Source of Truth: Edit RDF, regenerate CHANGELOG.

All notable changes to RepoQ will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0-alpha.5] - 2025-01-15

**SSoT Enforcement: RDF-only workflow**

### Added

- Added tests/vdad/test_vdad_generation.py (RDF → Markdown tests) (`a011822`)

### Removed

- **BREAKING**: Removed scripts/extract_vdad_rdf.py (violates SSoT principle) (`a011822`)
- Removed tests/vdad/test_vdad_extraction.py (obsolete) (`a011822`)

## [2.0.0-alpha.4] - 2025-01-15

**ADR-014: Single Source of Truth Principle**

### Added

- ADR-014: .repoq/ as SSoT for all RDF artifacts (`b9c1e14`)
- Generator: RDF → Markdown (scripts/generate_vdad_markdown.py, 180+ lines) (`b9c1e14`)

## [2.0.0-alpha.3] - 2025-01-15

**Phase 5.6: VDAD as RDF (POC)**

### Added

- VDAD meta-ontology (.repoq/ontologies/vdad.ttl, 400+ lines) (`49d6909`)
- Extractor: Markdown → RDF (scripts/extract_vdad_rdf.py, 250+ lines) (`49d6909`)
