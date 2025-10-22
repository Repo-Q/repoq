# ADR-013: Incremental v2 Migration via Feature Flags

**Status**: ✅ Accepted  
**Date**: 2025-10-22  
**Stakeholders**: All (Developers, Team Leads, DevOps, Researchers, Maintainers)  
**Related ADRs**: ADR-002 (RDFLib), ADR-003 (Subprocess), ADR-006 (Stratification), ADR-007 (PCQ)  
**VDAD Phase**: Phase 5 (Migration Roadmap)

---

## Context

### Current State (v1.x)

RepoQ v1.x implements an **imperative-first pipeline**:

```
Analyzers (Python) → Python Model (dict/dataclass) → Quality Score (formula) → Gate Decision
```

**Gap Analysis Result**:

- **Alignment Score**: 48/100 ❌
- **Missing Components**:
  - No `.repoq/raw/` (ABox-raw не сохраняется)
  - No Reasoner (архитектурные invariants не проверяются)
  - SHACL не интегрирован (issues генерируются Python кодом)
  - No manifest.json (нет versioning/reproducibility)

### Target State (v2.0)

RepoQ v2.0 architecture (from `repoq-c4-v2.md`) specifies a **semantic-first pipeline**:

```
Extractors → ABox-raw (TTL) → Reasoner (OWL2-RL) → SHACL Validator → Quality (from RDF) → Certificate
```

**Value Proposition** (Phase 2 Value Register):

- **V01 (Transparency)**: SHACL violations with file-level traceability
- **V02 (Gaming Protection)**: PCQ min-aggregator (Theorem C)
- **V03 (Correctness)**: Formal proofs (14 theorems + Lean mechanization)
- **V04 (Monotonicity)**: Quality never regresses (Theorem B)
- **V05 (Speed)**: Incremental analysis (<2 min P90)
- **V06 (Fairness)**: Context-aware SHACL shapes (no false positives)
- **V07 (Reliability)**: Deterministic normalization (Any2Math)
- **V08 (Actionability)**: PCE k-repair witness (<30 sec to fix)

### Problem Statement

Need migration strategy that:

1. **Preserves all 6 formal theorems** (A-F from Phase 1 Domain Context)
2. **Maintains 100% backward compatibility** (NFR-12, Γ_back invariant)
3. **Allows gradual adoption** (developer choice, not forced)
4. **Delivers incremental value** (each phase usable independently)
5. **Minimizes risk** (easy rollback, continuous validation)
6. **Addresses all 8 Tier 1 values** (V01-V08 from Phase 2)

---

## Decision

**Adopt 4-Phase Incremental Migration with Feature Flags**:

### Phase 1: Foundation Layer (Weeks 1-2)

**Goal**: `.repoq/` workspace + manifest.json  
**Deliverables**:

- `RepoQWorkspace` class (manages directory structure)
- `manifest.json` with ontology checksums + TRS version
- Integration with existing gate (auto-creates manifest)

**Feature Flags**: None (always enabled, transparent to users)  
**Value Delivered**: **V07 (Reliability)** — reproducibility via checksums  
**Requirements**: FR-10 (Incremental Analysis), NFR-01 (Speed ≤2 min)

---

### Phase 2: SHACL Validation Layer (Weeks 3-5)

**Goal**: Declarative constraint validation  
**Deliverables**:

- 10+ SHACL shapes (complexity, hotspots, architecture, coverage)
- `SHACLValidator` component (pySHACL integration)
- `PCEWitnessGenerator` (k-repair witness from SHACL violations)
- `PCQGate` (ZAG min-aggregator integration)
- `issues.ttl` export (validated violations in RDF)

**Feature Flags**: `--shacl` (opt-in)  
**Value Delivered**: **V01 (Transparency)**, **V06 (Fairness)**, **V08 (Actionability)**  
**Requirements**: FR-01 (Detailed Output), FR-02 (Actionable Feedback), FR-04 (PCQ)

---

### Phase 3: Reasoner + Any2Math Layer (Weeks 6-7)

**Goal**: Formal correctness + architecture checks  
**Deliverables**:

- `OWLReasoner` (OWL2-RL materialization, 77 ontologies)
- `Any2MathNormalizer` (TRS AST canonicalization + Lean proofs)
- Architecture SHACL shapes (C4 layers, DDD bounded contexts)
- Integration with gate (optional reasoning + normalization)

**Feature Flags**: `--reasoning`, `--normalize` (opt-in)  
**Value Delivered**: **V03 (Correctness)**, **V07 (Reliability)**, **V02 (Gaming Protection)**  
**Requirements**: FR-06 (Normalization), FR-07 (Confluence Proof), NFR-03 (Determinism)

---

### Phase 4: Unified Semantic Pipeline (Weeks 8-10)

**Goal**: Full Extract→Reason→SHACL→Quality pipeline  
**Deliverables**:

- `SemanticPipeline` with dual-mode (v1 legacy + v2 semantic)
- `compute_quality_from_rdf()` adapter (Python ≡ RDF equivalence)
- `SelfApplicationGuard` (stratified dogfooding, Theorem F)
- ADR-013 (this document)
- Migration guide + documentation

**Feature Flags**: `--semantic` (all features enabled)  
**Value Delivered**: All 8 Tier 1 values (V01-V08)  
**Requirements**: FR-17 (Self-Application), NFR-12 (Backward Compat), all 31 FR/NFR

---

### Feature Flag Strategy

```python
# repoq/cli.py
@click.option('--shacl', is_flag=True, help='Enable SHACL validation (Phase 2)')
@click.option('--reasoning', is_flag=True, help='Enable OWL2-RL reasoning (Phase 3)')
@click.option('--normalize', is_flag=True, help='Enable Any2Math normalization (Phase 3)')
@click.option('--semantic', is_flag=True, help='Enable full semantic pipeline (Phase 4, all flags)')
def gate(base, head, shacl, reasoning, normalize, semantic, ...):
    """Quality gate with optional v2 features."""
    
    if semantic:
        # Phase 4: Full semantic pipeline
        shacl = reasoning = normalize = True
    
    config = GateConfig(
        use_semantic=semantic,
        enable_shacl=shacl,
        enable_reasoning=reasoning,
        enable_normalization=normalize,
    )
    
    if config.use_semantic:
        pipeline = SemanticPipeline(config)
    else:
        # Legacy pipeline (v1, backward compatible)
        pipeline = LegacyPipeline(config)
    
    return pipeline.run(repo_path, config)
```

**Flag Defaults**: All `False` (opt-in only, backward compatible)

---

## Rationale

### Why Incremental Migration?

1. **Zero Breaking Changes** (NFR-12):
   - Legacy pipeline preserved as `_run_legacy_pipeline()`
   - Existing tests pass without modification
   - Users can keep using v1 behavior indefinitely

2. **Gradual Adoption** (Stakeholder: Alex, Jordan):
   - Developers can try one feature at a time (`--shacl`, then `--reasoning`)
   - Teams adopt at their own pace (no forced migration)
   - Early adopters provide feedback before full rollout

3. **Incremental Value** (Stakeholder: Morgan):
   - Phase 2: SHACL violations actionable immediately
   - Phase 3: Architecture checks catch violations
   - Phase 4: Full formal guarantees

4. **Risk Mitigation**:
   - Easy rollback: Disable flag if issues arise
   - Continuous validation: Tests at each phase (200+ total)
   - Performance benchmarks: <30% overhead requirement

5. **Formal Guarantees Preserved** (Stakeholder: Dr. Taylor):
   - Theorem A-F remain valid (quality formula unchanged)
   - Theorem 15.3 added (Lean proofs for Any2Math)
   - Γ_det invariant: Python ≡ RDF (same Q-score)

---

## Alternatives Considered

### Alternative 1: Big-Bang Rewrite

**Approach**: Rewrite entire pipeline in one PR, cutover at release

**Score**: 2/10 ❌

**Pros**:

- ✅ Clean architecture from day 1
- ✅ No technical debt (dual pipelines)

**Cons**:

- ❌ High risk (breaking changes likely)
- ❌ Long development cycle (3+ months)
- ❌ No incremental value (users wait until v2.0)
- ❌ Difficult rollback (must revert entire release)
- ❌ Testing burden (all features at once)

**Rejection Reason**: Unacceptable risk for production system with users

---

### Alternative 2: Parallel System

**Approach**: Build v2 alongside v1, maintain both, cutover at deprecation deadline

**Score**: 4/10 ❌

**Pros**:

- ✅ Safety (v1 remains untouched)
- ✅ Time to validate v2 thoroughly

**Cons**:

- ❌ Code duplication (2x maintenance burden)
- ❌ Bug fixes must be applied to both systems
- ❌ No gradual adoption (forced migration at cutover)
- ❌ Eventual forced migration (user frustration)

**Rejection Reason**: Maintenance burden too high for small team

---

### Alternative 3: Feature-Flag Incremental (SELECTED)

**Approach**: Add v2 features behind flags, deprecate v1 eventually (v3.0)

**Score**: 9/10 ✅

**Pros**:

- ✅ Zero breaking changes (Γ_back invariant)
- ✅ Gradual adoption (user choice)
- ✅ Early value delivery (each phase)
- ✅ Easy rollback (disable flag)
- ✅ Continuous validation (tests each phase)
- ✅ Low risk (incremental changes)

**Cons**:

- ⚠️ Temporary code complexity (dual paths until v3.0)
- ⚠️ Requires discipline (feature flag hygiene)

**Mitigation**:

- Clean abstraction (`SemanticPipeline` vs `LegacyPipeline`)
- Code review for flag usage
- Remove legacy pipeline in v3.0 (6 months grace period)

---

## Consequences

### Positive

✅ **Zero Breaking Changes** (NFR-12):

- All v1.x tests pass without modification
- Existing users' workflows unchanged
- No forced migration

✅ **Gradual Adoption**:

- Developers try features incrementally (`--shacl`, `--reasoning`)
- Teams adopt at their own pace
- Early adopters provide feedback

✅ **Incremental Value Delivery**:

- Phase 2 (Week 3): SHACL violations actionable
- Phase 3 (Week 6): Architecture checks working
- Phase 4 (Week 8): Full semantic pipeline

✅ **Easy Rollback**:

- Disable flag if performance/correctness issues
- No risky database migrations or schema changes
- Continuous deployment safe

✅ **All 8 Tier 1 Values Addressed**:

- V01 (Transparency): SHACL violations with file paths
- V02 (Gaming Protection): PCQ min-aggregator
- V03 (Correctness): Lean mechanized proofs
- V04 (Monotonicity): Quality formula unchanged
- V05 (Speed): Incremental workspace
- V06 (Fairness): Context-aware SHACL
- V07 (Reliability): Any2Math normalization
- V08 (Actionability): PCE k-repair witness

✅ **Formal Guarantees Preserved**:

- All 6 theorems (A-F) remain valid
- Theorem 15.3 added (Any2Math confluence)
- Γ_det invariant: Python ≡ RDF quality

---

### Negative

⚠️ **Temporary Code Complexity**:

- Dual pipeline paths (`_run_semantic_pipeline()` vs `_run_legacy_pipeline()`)
- Feature flag conditionals in gate logic
- Increased test matrix (v1 + v2 variants)

**Mitigation**:

- Clean abstraction: `SemanticPipeline` and `LegacyPipeline` as separate classes
- Strategy pattern for pipeline selection
- Remove legacy pipeline in v3.0 (after 6 months grace period)

⚠️ **Feature Flag Hygiene Required**:

- Risk of "flag sprawl" (too many flags)
- Flag dependencies (e.g., `--semantic` implies `--shacl`)
- Forgotten flags (technical debt)

**Mitigation**:

- Limit to 4 flags (`--shacl`, `--reasoning`, `--normalize`, `--semantic`)
- Document flag relationships clearly
- Deprecation plan: Remove flags in v3.0

---

## Risks & Mitigation

### Risk 1: Adoption Resistance (<30% teams using v2 features)

**Probability**: Medium  
**Impact**: Medium (business value not realized)

**Mitigation**:

- ROI demos: Show architecture violations caught by `--reasoning`
- Training webinars for Team Leads (Morgan persona)
- Documentation: Clear migration guide + examples
- Incentives: Highlight teams using v2 in dashboards

**Decision Point**: Week 5 (Post-Phase 2)

- If adoption ≥30%: ✅ Continue to Phase 3/4
- If adoption 10-30%: ⚠️ Enhanced marketing/training
- If adoption <10%: ❌ PAUSE, investigate barriers

---

### Risk 2: Performance Degradation (>30% overhead)

**Probability**: Medium  
**Impact**: High (users won't adopt slow tool)

**Mitigation**:

- Benchmark suite at each phase
- Cache materialized facts (reasoner output)
- Incremental reasoning (only re-infer changed triples)
- Oxigraph for large repos (>10K files)

**Decision Point**: Week 8 (Post-Phase 3)

- If overhead <30%: ✅ Continue to Phase 4
- If overhead 30-50%: ⚠️ Optimize reasoner before Phase 4
- If overhead >50%: ❌ PAUSE, investigate bottlenecks

---

### Risk 3: Complexity Increase (code harder to maintain)

**Probability**: Low  
**Impact**: Medium (technical debt)

**Mitigation**:

- Strict modularity: Bounded contexts enforced
- Integration tests: 200+ tests across 4 phases
- ADRs for major decisions (this document)
- Code review: Architecture Board approval required

---

## Implementation

### Timeline

**Total Duration**: 10 weeks (50 business days)  
**Total Effort**: 240 hours (200 eng + 40 QA)  
**Target Release**: v2.0.0 on 2025-12-31

| Phase | Duration | Deliverables | Tests |
|-------|----------|--------------|-------|
| Phase 1 | 2 weeks | Workspace + manifest | 20 tests |
| Phase 2 | 3 weeks | SHACL + PCQ/PCE | 80 tests |
| Phase 3 | 2 weeks | Reasoner + Any2Math | 70 tests |
| Phase 4 | 3 weeks | Semantic pipeline + ADR | 90 tests |

### Success Criteria

**Phase-Level Metrics**:

- Phase 1: ✅ `.repoq/manifest.json` in 100% of gate runs
- Phase 2: ✅ `--shacl` finds ≥5 violations (real projects)
- Phase 3: ✅ `--reasoning` finds ≥2 architecture violations
- Phase 4: ✅ `--semantic` passes 20/20 integration tests

**Release-Level Metrics** (v2.0.0):

- ✅ Alignment Score ≥90/100 (vs 48/100 current)
- ✅ Performance overhead <30% (benchmark suite)
- ✅ Adoption ≥30% (teams using ≥1 v2 feature)
- ✅ Zero breaking changes (all v1.x tests passing)
- ✅ Documentation complete (ADRs, migration guide, examples)

---

## Approval & Sign-Off

**Prepared by**: AI Engineering Team  
**Date**: 2025-10-22  
**Status**: 🚧 PENDING APPROVAL

**Approvals Required**:

- [ ] Engineering Lead (technical feasibility)
- [ ] Product Manager (business value, stakeholder alignment)
- [ ] QA Lead (testing strategy, 200+ tests)
- [ ] DevRel Lead (migration guide, training materials)
- [ ] Security Lead (SHACL shapes, attack surface)

**Stakeholder Review**:

- [ ] Developers (Alex, Jordan) — Early access to `--shacl` flag
- [ ] Team Leads (Morgan) — Architecture violation reports
- [ ] DevOps (Casey) — CI/CD integration, performance benchmarks
- [ ] Researchers (Dr. Taylor) — Formal proofs, Lean mechanization

---

## Related Documents

- **Phase 5 Migration Roadmap**: `docs/vdad/phase5-migration-roadmap.md` (detailed 4-phase plan)
- **Phase 1 Domain Context**: `docs/vdad/phase1-domain-context.md` (6 formal theorems, 4 bounded contexts)
- **Phase 2 Value Register**: `docs/vdad/phase2-value-register.md` (8 Tier 1 values)
- **Phase 3 Requirements**: `docs/vdad/phase3-requirements.md` (19 FR + 12 NFR)
- **Phase 4 Architecture**: `docs/vdad/phase4-architecture-overview.md` (C4 diagrams, bounded contexts)
- **C4 v2 Diagrams**: `docs/architecture/repoq-c4-v2.md` (target semantic-first pipeline)
- **Related ADRs**: ADR-002 (RDFLib), ADR-003 (Subprocess), ADR-006 (Stratification), ADR-007 (PCQ)

---

**END OF ADR-013**
