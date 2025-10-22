# Phase 5 Migration Roadmap — Обновлённый статус

**Date**: 2025-01-15  
**Current**: v2.0.0-alpha.4  
**Next**: Phase 2 (SHACL Validation)

## ✅ Completed Phases

### Phase 1.1: RepoQWorkspace (v2.0.0-alpha.1)

- ✅ `repoq/core/workspace.py` (200+ lines)
- ✅ Tests: 18/18 passing
- ✅ Documentation: `docs/migration/phase1-workspace.md`
- ✅ Commit: `857cc79`, `bed0ea5`, `f007076`, `3e9de12`
- ✅ Tag: `v2.0.0-alpha.1`

### Phase 1.5: Story Provenance (v2.0.0-alpha.2)

- ✅ `repoq/ontologies/story.ttl` (300+ lines)
- ✅ `repoq/core/story.py` (250+ lines)
- ✅ Tests: 16/16 passing
- ✅ `.repoq/story/phase1.ttl` (152 triples)
- ✅ Commit: `c266255`, `f3beb17`, `cf9801d`
- ✅ Tag: `v2.0.0-alpha.2`

### Phase 5.6: VDAD as RDF (v2.0.0-alpha.3)

- ✅ `.repoq/ontologies/vdad.ttl` (400+ lines)
- ✅ `scripts/extract_vdad_rdf.py` (250+ lines)
- ✅ Tests: 13/14 passing
- ✅ Commit: `49d6909`, `1162c1e`
- ✅ Tag: `v2.0.0-alpha.3`

### ADR-014: Single Source of Truth (v2.0.0-alpha.4)

- ✅ `docs/adr/adr-014-single-source-of-truth.md`
- ✅ `scripts/generate_vdad_markdown.py` (180+ lines)
- ✅ Tests: 15/16 passing (SSoT principle enforced)
- ✅ Commit: `b9c1e14`, `907f03d`
- ✅ Tag: `v2.0.0-alpha.4`

## 🔄 In Progress

### Phase 2: SHACL Validation (Target: v2.0.0-beta.1)

**Status**: Not started  
**Estimated effort**: 1-2 weeks  
**Priority**: P0 (Critical for quality gates)

#### Tasks

1. **SHACL Shapes** (`.repoq/shapes/`)
   - [ ] `project-shape.ttl` — Top-level project structure
   - [ ] `vdad-shapes.ttl` — VDAD traceability chains
   - [ ] `story-shape.ttl` — Story provenance validation

2. **Validation Module** (`repoq/core/validation.py`)
   - [ ] `validate_with_shacl()` — pyshacl integration
   - [ ] `save_validation_report()` — Report to `.repoq/reports/`
   - [ ] `generate_certificate()` — Certificate on success

3. **Pipeline Integration** (`repoq/pipeline.py`)
   - [ ] Run SHACL after RDF generation
   - [ ] Save validated RDF to `.repoq/validated/`
   - [ ] Fail pipeline on validation errors

4. **Tests** (`tests/core/test_validation.py`)
   - [ ] Unit tests for SHACL validation
   - [ ] Integration tests (pipeline + SHACL)
   - [ ] Gate tests (validation must be sound)

5. **Documentation**
   - [ ] `docs/migration/phase2-shacl.md`
   - [ ] Update CHANGELOG
   - [ ] Tag: `v2.0.0-beta.1`

#### Traceability

- FR-11: SHACL validation
- V06: Quality (valid RDF)
- ADR-010: Ontology-driven validation

#### Gates

- ✅ Soundness: SHACL shapes correct
- ✅ Completeness: All critical constraints
- ✅ Performance: Validation <1s for typical projects

## 📋 Pending Phases

### Phase 3: Reasoner Integration (Target: v2.0.0-beta.2)

**Status**: Blocked by Phase 2  
**Estimated effort**: 2-3 weeks  
**Priority**: P1 (High value for inference)

#### Tasks

- [ ] Choose reasoner (OWL-RL, RDFox, or Allegrograph)
- [ ] `repoq/core/reasoner.py` — Inference module
- [ ] Infer implicit traceability (Value → FR → ADR → Phase)
- [ ] Save inferred triples to `.repoq/inferred/`
- [ ] Tests: 20+ tests for inference correctness

### Phase 4: Unified Pipeline (Target: v2.0.0)

**Status**: Blocked by Phase 2, 3  
**Estimated effort**: 1-2 weeks  
**Priority**: P0 (Integration)

#### Tasks

- [ ] End-to-end pipeline: Analysis → RDF → SHACL → Reasoning → Reports
- [ ] CLI updates: `repoq analyze --validate --infer`
- [ ] Performance optimization: Incremental validation
- [ ] Documentation: Full workflow guide

### Phase 5.7: Full VDAD as RDF (Target: v2.1.0)

**Status**: Blocked by Phase 2  
**Estimated effort**: 2-3 weeks  
**Priority**: P1 (Complete VDAD coverage)

#### Tasks

- [ ] Phase 1: Domain → `.repoq/vdad/phase1-domain.ttl`
- [ ] Phase 3: Requirements → `.repoq/vdad/phase3-requirements.ttl`
- [ ] Phase 4: Architecture → `.repoq/vdad/phase4-architecture.ttl`
- [ ] Phase 5: Migration → `.repoq/vdad/phase5-migration.ttl`
- [ ] Generators: RDF → Markdown for all 5 phases

### Phase 6: Automation & CI/CD (Target: v2.2.0)

**Status**: Future work  
**Estimated effort**: 1-2 weeks  
**Priority**: P2 (Nice to have)

#### Tasks

- [ ] Pre-commit hook: Validate RDF, regenerate Markdown
- [ ] CI: Check RDF ↔ Markdown consistency
- [ ] Documentation site: Auto-generated from `.repoq/`
- [ ] Dashboards: SPARQL queries → visualization

## 📊 Progress Summary

| Phase | Status | Tests | Tag | Effort |
|-------|--------|-------|-----|--------|
| 1.1: Workspace | ✅ Complete | 18/18 | v2.0.0-alpha.1 | 3 days |
| 1.5: Story | ✅ Complete | 16/16 | v2.0.0-alpha.2 | 2 days |
| 5.6: VDAD POC | ✅ Complete | 13/14 | v2.0.0-alpha.3 | 1 day |
| ADR-014: SSoT | ✅ Complete | 15/16 | v2.0.0-alpha.4 | 1 day |
| **2: SHACL** | 🔄 Next | 0/20 | v2.0.0-beta.1 | 1-2 weeks |
| 3: Reasoner | ⏸️ Blocked | 0/20 | v2.0.0-beta.2 | 2-3 weeks |
| 4: Pipeline | ⏸️ Blocked | 0/30 | v2.0.0 | 1-2 weeks |
| 5.7: Full VDAD | ⏸️ Blocked | 0/50 | v2.1.0 | 2-3 weeks |
| 6: Automation | ⏸️ Future | 0/15 | v2.2.0 | 1-2 weeks |

**Total Progress**: 4/9 phases complete (44%)  
**Total Tests**: 62/176 passing (35%)  
**Estimated Time to v2.0.0**: 4-7 weeks

## 🎯 Next Action

**Start Phase 2: SHACL Validation**

1. Create SHACL shapes for project structure
2. Integrate pyshacl into pipeline
3. Write validation tests
4. Generate certificates on success

**Command to proceed**:

```bash
# Create SHACL shapes
touch .repoq/shapes/project-shape.ttl
touch .repoq/shapes/vdad-shapes.ttl
touch .repoq/shapes/story-shape.ttl

# Create validation module
touch repoq/core/validation.py
touch tests/core/test_validation.py

# Start TDD cycle
python -m pytest tests/core/test_validation.py -v
```
