# Changelog

> **Generated from RDF**: This document is auto-generated from `.repoq/changelog/releases.ttl`.
> Single Source of Truth: Edit RDF, regenerate CHANGELOG.

All notable changes to RepoQ will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v2.0.0-beta.1] - 2025-10-22

**Phase 2: SHACL Validation Infrastructure**

### Added

- SHACL shapes for story, ADR, changelog ontologies (720 lines) (`0e65280`)
- Validation module: repoq/core/validation.py (380 lines) with pyshacl integration (`0e65280`)
- Validation tests: 13/13 passing (tests/core/test_validation.py) (`0e65280`)
- CLI integration: 'repoq validate' command with Rich formatting (`0e65280`)
- Validation certificates: auto-generated in .repoq/certificates/ (`0e65280`)
- ADR-015: Digital Twin Architecture (hybrid approach) (`2313ed0`)

### Fixed

- ADR-014: Fixed to conform to SHACL shapes (proper Consequence/Alternative structure) (`2313ed0`)

## [v2.0.0-alpha.6] - 2025-10-22

**Extended SSoT: ADR and CHANGELOG as RDF**

### Added

- ADR ontology: .repoq/ontologies/adr.ttl (200+ lines) (`627bed8`)
- Changelog ontology: .repoq/ontologies/changelog.ttl (150+ lines) (`627bed8`)
- ADR generator: scripts/generate_adr_markdown.py (150+ lines) (`627bed8`)
- CHANGELOG generator: scripts/generate_changelog_markdown.py (130+ lines) (`627bed8`)
- Example RDF artifacts: ADR-014, releases (alpha.3/4/5) (`627bed8`)

## [v2.0.0-alpha.5] - 2025-01-15

**SSoT Enforcement: RDF-only workflow**

### Added

- Added tests/vdad/test_vdad_generation.py (RDF → Markdown tests) (`a011822`)

### Removed

- **BREAKING**: Removed scripts/extract_vdad_rdf.py (violates SSoT principle) (`a011822`)
- Removed tests/vdad/test_vdad_extraction.py (obsolete) (`a011822`)

## [v2.0.0-alpha.4] - 2025-01-15

**ADR-014: Single Source of Truth Principle**

### Added

- ADR-014: .repoq/ as SSoT for all RDF artifacts (`b9c1e14`)
- Generator: RDF → Markdown (scripts/generate_vdad_markdown.py, 180+ lines) (`b9c1e14`)

## [v2.0.0-alpha.3] - 2025-01-15

**Phase 5.6: VDAD as RDF (POC)**

### Added

- VDAD meta-ontology (.repoq/ontologies/vdad.ttl, 400+ lines) (`49d6909`)
- Extractor: Markdown → RDF (scripts/extract_vdad_rdf.py, 250+ lines) (`49d6909`)

