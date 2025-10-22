# Changelog

All notable changes to RepoQ will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0-alpha.5] - 2025-01-15

### Changed - SSoT Enforcement: RDF-only workflow ✅

**Removed Extraction** (Markdown → RDF):
- ❌ Removed `scripts/extract_vdad_rdf.py` (violates SSoT principle)
- ❌ Removed `tests/vdad/test_vdad_extraction.py` (obsolete)
- Rationale: Extraction creates dual source of truth (Markdown ↔ RDF drift)

**Enforced Generation** (RDF → Markdown):
- ✅ `scripts/generate_vdad_markdown.py` — ONLY workflow
- ✅ New tests: `tests/vdad/test_vdad_generation.py` (7/7 passing)
- Workflow: Edit `.repoq/vdad/*.ttl` → Generate `docs/vdad/*.md`

**Updated ADR-014**:
- Workflow diagram: RDF (edit) → Markdown (generate)
- Rules: No Markdown → RDF extraction (one-way transformation)
- Migration: Manual RDF editing or Protégé/VS Code extensions

**Traceability:**
- ADR-014: Single Source of Truth (.repoq/ for RDF)
- FR-10: Reproducibility (RDF checksums)
- Theorem A: Reproducibility (no drift)

**Gates:**
- ✅ Soundness: RDF → Markdown deterministic
- ✅ SSoT enforced: No bidirectional sync
- ✅ No drift: Markdown always generated from RDF

**Statistics:**
- Removed: 250+ lines (extractor)
- Removed: 300+ lines (extraction tests)
- Added: 200+ lines (generation tests)
- Tests: 7/7 passing (100%)
- Commit: TBD

## [2.0.0-alpha.4] - 2025-01-15

### Added - ADR-014: Single Source of Truth Principle ✅

**Architecture Decision: `.repoq/` as SSoT**
- All RDF artifacts stored in `.repoq/` (single source of truth)
- `docs/` contains only generated Markdown (human-readable)
- Edit RDF → regenerate Markdown (not vice versa)
- No sidecar TTL files in `docs/` (eliminated duplication)

**New Module: `scripts/generate_vdad_markdown.py`**
- `generate_phase2_markdown()`: RDF → Markdown generator (180+ lines)
- Extracts values, stakeholders from `.repoq/vdad/*.ttl`
- Generates formatted Markdown with "Generated from RDF" marker
- Output: `docs/vdad/phase2-values-generated.md`

**ADR-014 Document**: `docs/adr/adr-014-single-source-of-truth.md`
- Rationale: Eliminate RDF ↔ Markdown duplication
- Structure: `.repoq/` (RDF SSoT) + `docs/` (generated Markdown)
- Workflow: Edit RDF → regenerate docs → commit both
- Alternatives considered: Markdown SSoT (rejected), Dual SSoT (rejected)

**Updated Tests**: `tests/vdad/test_vdad_extraction.py` (15/16 passing)
- `TestMarkdownGeneration`: New test class for RDF → Markdown
  - `test_generate_markdown_from_rdf()`: Verify generation works
  - `test_ssot_principle_enforced()`: Verify paths (RDF in .repoq/, MD in docs/)
- `TestEndToEnd`: Updated to verify SSoT paths

**Traceability:**
- FR-10: Reproducibility (RDF checksums in manifest)
- V07: Observability (RDF as queryable database)
- Theorem A: Reproducibility (SSoT eliminates drift)

**Gates:**
- ✅ Soundness: Generated Markdown matches RDF content
- ✅ Deterministic: Same RDF → same Markdown
- ✅ SSoT enforced: RDF in `.repoq/`, Markdown in `docs/`

**Statistics:**
- Generator: 180+ lines Python
- Tests: 16 tests (15 passed, 1 skipped)
- Commit: `b9c1e14`

## [2.0.0-alpha.3] - 2025-01-15

### Added - Phase 5.6: VDAD as RDF (POC) ✅

**New Ontology: `.repoq/ontologies/vdad.ttl`**
- VDAD meta-ontology (400+ lines) for 5 VDAD phases
- Phase 1: `Stakeholder` (Developer, TeamLead, DevOps, Researcher), `BoundedContext`
- Phase 2: `Value` (Tier1Value, Tier2Value)
- Phase 3: `Requirement` (FunctionalRequirement, NonFunctionalRequirement)
- Phase 4: `ArchitectureDecisionRecord`, `Theorem`
- Phase 5: `MigrationPhase`, `Deliverable`
- Properties: `satisfiedBy`, `implementedBy`, `stakeholder`, `priority` (P0/P1/P2)
- Traceability chains: Value → Requirement → ADR → MigrationPhase

**New Module: `scripts/extract_vdad_rdf.py`**
- `parse_phase2_values_markdown()`: Extract values and stakeholders from Markdown
- `generate_phase2_rdf()`: Generate RDF graph from structured data
- `extract_phase2_values()`: Full extraction pipeline (Markdown → TTL)
- Regex-based parsing for values (##V\d+), stakeholders (### Name (Role))
- Output: `.repoq/vdad/phase2-values.ttl`

**Tests: `tests/vdad/test_vdad_extraction.py`** (13/14 passing)
- `TestMarkdownParsing`: Parse values, stakeholders, metadata
- `TestRDFGeneration`: Generate correct RDF structure
- `TestEndToEnd`: Full extraction pipeline
- `TestGateVDADExtraction`: Deterministic output, no data loss, valid references

**Architecture Decision: `.repoq/` Unification**
- All RDF artifacts in `.repoq/` (ontologies, shapes, vdad, story)
- Replaced `.vdad/` with `.repoq/ontologies/vdad.ttl` + `.repoq/vdad/` for data
- Updated `.gitignore`: Include `.repoq/ontologies/*.ttl`, `.repoq/shapes/*.ttl`

**Traceability:**
- V07: Observability (VDAD structure as queryable RDF)
- FR-10: Reproducible analysis (VDAD versioning + checksums)
- ADR-013: Incremental migration (Phase 2 POC first)

**Gates:**
- ✅ Soundness: Valid RDF output (rdflib parsing)
- ✅ Deterministic: Same Markdown → same TTL (tested)
- ✅ No data loss: All values/stakeholders preserved
- ✅ Valid references: Value→stakeholder links verified

**Statistics:**
- VDAD ontology: 400+ lines TTL
- Extractor: 250+ lines Python
- Tests: 14 tests (13 passed, 1 skipped)
- Commit: `49d6909`

## [2.0.0-alpha.2] - 2025-01-15

### Added - Phase 1.5: Story Provenance (POC) ✅

**New Ontology: `repoq/ontologies/story.ttl`**
- Story ontology (300+ lines) with PROV-O-inspired semantics
- Classes: `Phase`, `Artifact`, `Commit`, `Gate`
- Properties: `satisfies`, `implements`, `verifies` (VDAD traceability)
- Enumerations: `StatusValue`, `GateStatusValue`

**New Module: `repoq/core/story.py`**
- `generate_phase_story()`: Generate RDF graph from PhaseInfo
- `extract_requirements()`: Parse FR-XX, V-XX, ADR-XXX from text (regex)
- `get_git_commit_info()`: Extract git metadata (SHA, author, date, files)
- `save_story()`: Serialize graph to Turtle (.ttl)

**Generated Artifact: `.repoq/story/phase1.ttl`**
- Phase 1 story with 152 triples
- 4 commits (857cc79, bed0ea5, f007076, 3e9de12)
- 5 artifacts (workspace.py, tests, docs)
- 7 gates (soundness, confluence, termination, etc.)
- Full traceability: FR-10, V07, Theorem A, NFR-01, ADR-008/010/013

**Tests**:
- 16 new tests for story generation (100% passing)
- Test classes:
  - `TestRequirementExtraction` (8 tests)
  - `TestGitCommitInfo` (2 tests)
  - `TestPhaseStoryGeneration` (4 tests)
  - `TestStorySaving` (2 tests)

**Scripts**:
- `scripts/generate_phase1_story.py`: Generate Phase 1 story from metadata

**Total Test Count**: 494 tests (476 existing + 18 workspace + 16 story - 16 overlaps)

### Changed

- `.gitignore`: Exclude `.repoq/*` but include `.repoq/story/*.ttl` (provenance tracking)

### Traceability

| Requirement | Implementation |
|-------------|----------------|
| FR-10 | Full provenance via story.ttl (commits + artifacts + requirements) |
| V07 | Transparent development history in RDF format |
| Theorem A | Story complements manifest.json for reproducibility |
| ADR-013 | Story tracks incremental migration phases |

### Use Cases

**1. Audit Trail**:
```sparql
# Query: Which commits satisfy FR-10?
SELECT ?commit ?message WHERE {
  ?commit story:satisfies vdad:fr-10 ;
          story:message ?message .
}
```

**2. Impact Analysis**:
```sparql
# Query: Which artifacts depend on workspace.py?
SELECT ?artifact WHERE {
  ?artifact vdad:verifies <artifacts/repoq-core-workspace.py> .
}
```

**3. Requirements Coverage**:
```sparql
# Query: Which requirements are satisfied in Phase 1?
SELECT ?req WHERE {
  <phases/phase1> vdad:satisfies ?req .
}
```

### Migration Notes

**POC Status**:
- ✅ Story generation works (16/16 tests passing)
- ✅ Phase 1 story artifact committed (152 triples)
- ⏸️ Pipeline integration deferred to Phase 2+ (manual generation for now)
- ⏸️ SPARQL endpoint deferred to Phase 5

**Known Limitations**:
- Manual story generation (run `python scripts/generate_phase1_story.py`)
- No automatic story updates on commit (git hooks deferred)
- No validation against story ontology (pyshacl integration in Phase 2)

---

## [2.0.0-alpha.1] - 2025-01-15

### Added - Phase 1: Workspace Foundation ✅

**New Module: `repoq/core/workspace.py`**
- `RepoQWorkspace` class for managing `.repoq/` directory structure
- `ManifestEntry` dataclass for reproducibility metadata
- `compute_ontology_checksums()` for SHA256 checksums of ontologies
- Automatic `.repoq/` initialization on every analysis run
- `manifest.json` generation with:
  - Commit SHA (from git)
  - Policy version (2.0.0-alpha)
  - Ontology checksums (SHA256)
  - Timestamp (ISO 8601)

**Directory Structure**:
```
.repoq/
├── raw/           # Raw analysis artifacts (JSON-LD, RDF/XML)
├── validated/     # SHACL-validated RDF (Phase 2)
├── reports/       # Human-readable reports (MD, HTML)
├── certificates/  # Quality gate certificates (signed)
├── cache/         # Incremental analysis cache
└── manifest.json  # Reproducibility metadata
```

**Pipeline Integration**:
- `run_pipeline()` now initializes workspace at start
- Manifest generated at end with checksums
- Traceability: FR-10, V07, Theorem A, NFR-01, ADR-008, ADR-013

**Tests**:
- 15 unit tests for `RepoQWorkspace` class
- 3 integration tests for pipeline integration
- **Total: 18/18 passing** (100% success rate)
- Performance: <50ms workspace overhead (NFR-01 satisfied)

**Documentation**:
- `docs/migration/phase1-workspace.md` (90 lines)
- README.md updated with workspace feature
- Migration notes and rollback plan included

**Commits**:
- 857cc79: feat(workspace): implement RepoQWorkspace (Phase 1.1)
- bed0ea5: feat(pipeline): integrate RepoQWorkspace with pipeline (Phase 1.2)
- f007076: docs(phase1): complete Phase 1 documentation (Phase 1.3)

### Changed

- `repoq/pipeline.py`: Added workspace initialization and manifest generation
- README.md: Added workspace feature at top of Features section

### Traceability

| Requirement | Implementation |
|-------------|----------------|
| FR-10 | Reproducible analysis via manifest.json |
| V07 | Observability via .repoq/ structure |
| Theorem A | Reproducibility via SHA256 checksums |
| NFR-01 | Performance <50ms overhead (measured) |
| ADR-008 | Git as source of truth (commit SHA in manifest) |
| ADR-010 | Incremental analysis (cache/ directory) |
| ADR-013 | Incremental migration (zero breaking changes) |

### Migration Notes

**Zero Breaking Changes ✅**
- No CLI changes
- No config changes
- No API changes
- Only addition: `.repoq/` directory created automatically

**Rollback Plan**:
1. Delete `.repoq/` directory (safe - all data in git)
2. Revert commits: `git revert f007076^..f007076`
3. Tests will still pass (workspace is optional in Phase 1)

**Known Limitations**:
- Manifest not validated yet (comes in Phase 2)
- Cache not populated yet (comes in Phase 2+)
- Certificates not generated yet (comes in Phase 2)

---

## [Unreleased]

### Planned - Phase 2: SHACL Validation (Weeks 2-3)

**Features**:
- SHACL validation in pipeline
- Save validated RDF to `.repoq/validated/`
- Certificate generation on validation success
- Validation cache in `.repoq/cache/`

**Tests**:
- 10+ tests for SHACL integration
- Validation roundtrip tests
- Certificate signature tests

**Commits** (planned):
- feat(shacl): add SHACL validation to pipeline
- feat(certs): generate certificates on validation success
- docs(phase2): complete Phase 2 documentation

### Planned - Phase 3: Reasoner Integration (Weeks 4-6)

**Features**:
- OWL reasoning in pipeline
- Infer implicit facts (hotspot propagation, etc.)
- Save inferred triples to `.repoq/validated/`
- Reasoning cache in `.repoq/cache/`

**Tests**:
- 15+ tests for reasoner integration
- Inference correctness tests
- Performance tests (reasoner overhead <10%)

**Commits** (planned):
- feat(reasoner): add OWL reasoning to pipeline
- feat(inference): infer implicit facts from ontologies
- docs(phase3): complete Phase 3 documentation

### Planned - Phase 4: Unified Pipeline (Weeks 7-10)

**Features**:
- Feature flag for v2 pipeline
- Parallel execution (v1 + v2)
- Metrics comparison (v1 vs v2)
- Gradual cutover based on success metrics

**Tests**:
- 20+ tests for v2 pipeline
- Feature flag tests
- Parallel execution tests
- Cutover tests

**Commits** (planned):
- feat(v2): implement v2 pipeline with feature flag
- feat(cutover): gradual cutover based on metrics
- docs(phase4): complete Phase 4 documentation

---

## [1.0.0] - 2024-12-01 (Previous Release)

### Added

- Initial release with structure, complexity, history, hotspots
- Semantic export (JSON-LD, RDF/Turtle)
- Quality gates for CI/CD
- SHACL validation
- Meta-loop ontologies (meta, test, trs, quality, docs)
- Extended ontologies (test, security, arch, license, api)
- Docker support

### Known Issues

- No workspace management (fixed in 2.0.0-alpha.1)
- No reproducibility guarantees (fixed in 2.0.0-alpha.1)
- No incremental analysis (planned for Phase 2+)

---

## Links

- **Phase 5 Roadmap**: `docs/vdad/phase5-migration-roadmap.md`
- **Quick Reference**: `docs/vdad/phase5-quick-reference.md`
- **ADR-013**: `docs/vdad/phase4-adr-013-incremental-migration.md`
- **Phase 1 Docs**: `docs/migration/phase1-workspace.md`
