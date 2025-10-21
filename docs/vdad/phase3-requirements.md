# VDAD Phase 3: Strategic Decisions & Requirements

**Status**: ✅ ACTIVE  
**VDAD Steps**: Step 5 (Digitalization Decision), Step 6 (Requirements Elaboration)  
**Created**: 2025-10-21  
**Last Updated**: 2025-10-21

---

## Executive Summary

This document translates **8 Tier 1 values** (from Phase 2) into **strategic decisions** (how we'll address each value) and **concrete requirements** (what the system must do). Every requirement is traceable back to a stakeholder value, ensuring value-driven development.

**Key Outcomes**:
- **8 Strategic Decisions** (one per Tier 1 value)
- **19 Functional Requirements** (FR-01 to FR-19)
- **12 Non-Functional Requirements** (NFR-01 to NFR-12), all SMART-compliant
- **4 Updated EVRs** (EVR-01 to EVR-04) with acceptance criteria
- **Full Traceability**: Value → Decision → Requirement → Test (no orphaned requirements)

**Requirements Status**: 31 total requirements (19 FR + 12 NFR)
- ✅ Implemented: 8 requirements (26%)
- 🔄 In Progress: 6 requirements (19%)
- ⏸️ Planned: 17 requirements (55%)

---

## 1. Strategic Decision Log

### Format (ADR-inspired)
- **Decision ID**: SD-XX (Strategic Decision)
- **Value**: Which Tier 1 value this addresses
- **Context**: Why this decision is needed now
- **Decision**: What we're doing
- **Rationale**: Why this approach (vs alternatives)
- **Alternatives Considered**: What we rejected and why
- **Consequences**: Trade-offs (+/-)
- **Requirements**: Which FR/NFR implement this decision

---

### SD-01: Detailed Gate Output with ΔQ Breakdown

**Value**: V01 (Transparency)

**Context**: Developers cannot understand gate failures from simple "FAIL: ΔQ=-1.2" output. Need file-level, metric-level breakdown to identify what went wrong.

**Decision**: Implement structured gate output with:
1. Overall ΔQ (Q_head - Q_base)
2. Per-metric contributions (complexity, hotspots, TODOs, coverage)
3. File-level deltas showing which files caused change
4. Hard constraint status (tests, TODOs, hotspots: pass/fail)
5. PCE witness (if available): which k files to fix

**Rationale**: 
- Transparency is #1 developer need (from persona interviews)
- Detailed output reduces time-to-fix (developer can immediately identify problem files)
- Aligns with EVR-01 (human-readable explanations)

**Alternatives Considered**:
1. **Simple pass/fail**: Rejected (too opaque, frustrates developers)
2. **External dashboard**: Rejected for MVP (adds complexity, slows feedback loop)
3. **Verbose JSON dump**: Rejected (information overload, poor UX)

**Consequences**:
- ✅ +Transparency: Developers understand failures
- ✅ +Actionability: Clear next steps
- ✅ +Learning: Juniors learn from detailed feedback
- ⚠️ -Verbosity: Output can be long (mitigate with `--format compact`)

**Requirements**: FR-01, FR-02, FR-03, NFR-08

---

### SD-02: ZAG PCQ Min-Aggregator Integration

**Value**: V02 (Gaming Protection)

**Context**: Developers can game Q-score by compensating (one high-quality module offsetting one low-quality module). Average Q looks good but quality is uneven.

**Decision**: Integrate ZAG framework with PCQ min-aggregator:
1. Decompose repository into modules (directories, architectural layers, or DDD bounded contexts)
2. Calculate per-module quality u_i(S)
3. PCQ(S) = min{u_1, u_2, ..., u_n} (bottleneck quality)
4. Gate requires PCQ ≥ τ (e.g., τ=0.8: all modules ≥80%)

**Rationale**:
- Mathematically proven anti-gaming (Theorem C: PCQ/min guarantee)
- Catches "one bad apple" even if average is high
- Aligns with Team Lead need for fairness across teams/modules

**Alternatives Considered**:
1. **Median aggregator**: Rejected (still allows 50% of modules below threshold)
2. **Weighted average**: Rejected (can still be gamed by inflating one metric)
3. **Manual code review**: Rejected (not scalable, not objective)

**Consequences**:
- ✅ +Gaming Protection: Compensation impossible (min blocks it)
- ✅ +Fairness: All modules held to same standard
- ✅ +Team Accountability: Identifies weak modules
- ⚠️ -Strictness: Some PRs may fail that would pass with average (intentional)

**Requirements**: FR-04, FR-05, NFR-02

---

### SD-03: Any2Math Lean Normalization for Determinism

**Value**: V03 (Correctness), V07 (Reliability)

**Context**: Syntactic variations (whitespace, comment formatting, equivalent AST structures) cause non-deterministic metrics. Same code → different Q scores → developer frustration + flaky gates.

**Decision**: Integrate Any2Math framework:
1. Parse Python code to AST
2. Apply TRS normalization: N(AST) → canonical AST
3. Calculate metrics on canonical AST (deterministic)
4. Verify TRS properties in Lean: confluence + termination (Theorems 15.3, Any2Math.A-C)

**Rationale**:
- Formal correctness: Lean proofs guarantee normalization properties
- Eliminates false positives from formatting changes (whitespace, comments)
- Unique selling point: First quality tool with mechanized proofs

**Alternatives Considered**:
1. **Ignore whitespace manually**: Rejected (incomplete, ad-hoc)
2. **Use Black formatter**: Rejected (doesn't handle semantic equivalence)
3. **Heuristic normalization**: Rejected (no formal guarantees)

**Consequences**:
- ✅ +Correctness: Formal proofs (14 theorems + Lean mechanization)
- ✅ +Reliability: Deterministic (same code → same Q)
- ✅ +Innovation: Novel contribution (TRS + Lean + Quality)
- ⚠️ -Complexity: Lean runtime dependency (mitigate with subprocess isolation)
- ⚠️ -Performance: Normalization adds overhead (~10-20% analysis time, acceptable)

**Requirements**: FR-06, FR-07, NFR-01, NFR-03

---

### SD-04: Admission Predicate with ε-Tolerance

**Value**: V04 (Monotonicity)

**Context**: Strict ΔQ > 0 requirement is too fragile (minor noise causes false negatives). Need tolerance for measurement noise while preserving monotonicity guarantee.

**Decision**: Implement admission predicate:
```
A(S_base, S_head) ≡ (H) ∧ (ΔQ ≥ ε) ∧ (PCQ ≥ τ)

where:
  H = hard constraints (tests ≥80%, TODO ≤100, hotspots ≤20)
  ΔQ = Q(S_head) - Q(S_base)
  ε ∈ [0.2, 0.5] — configurable noise tolerance
  τ ∈ [0.75, 0.9] — configurable PCQ threshold
```

**Rationale**:
- Theorem B: Monotonicity guarantee (if A passes, then Q improves by ≥ε)
- ε-tolerance prevents false negatives from noise (formatting, minor refactoring)
- Hard constraints (H) are absolute (no tolerance for low test coverage)

**Alternatives Considered**:
1. **Strict ΔQ > 0**: Rejected (too fragile, high false negative rate)
2. **No ε (always pass)**: Rejected (violates monotonicity, allows regression)
3. **Adaptive ε**: Rejected for MVP (too complex, unclear benefit)

**Consequences**:
- ✅ +Monotonicity: Formal guarantee (Theorem B)
- ✅ +Robustness: Tolerates minor noise (ε=0.3 typical)
- ✅ +Configurability: Teams can tune ε, τ via policy YAML
- ⚠️ -Complexity: Requires understanding ε concept (mitigate with docs)

**Requirements**: FR-08, FR-09, NFR-02, NFR-04

---

### SD-05: Incremental Analysis with Caching

**Value**: V05 (Speed)

**Context**: Full repository analysis on every PR is slow (5-10 min for large repos). Developers won't use tool if feedback loop >2 min.

**Decision**: Implement incremental analysis:
1. Cache metrics for unchanged files (keyed by file SHA + config version)
2. Only re-analyze files in PR diff (`git diff --name-only base..head`)
3. Re-aggregate Q from cached + new metrics
4. Invalidate cache on policy change (weight updates)

**Rationale**:
- Speed is #1 DevOps requirement (CI budget <5 min total)
- Typical PR changes 5-20 files (not 1000+), so incremental saves 80-90% time
- Cache correctness guaranteed (SHA-based, policy-versioned)

**Alternatives Considered**:
1. **Full re-analysis**: Rejected (too slow for large repos)
2. **External cache (Redis)**: Rejected for MVP (adds dependency, complexity)
3. **Pre-computed metrics DB**: Rejected (requires server, not self-hosted)

**Consequences**:
- ✅ +Speed: 5-10x faster for typical PRs (80-90% cache hit)
- ✅ +Developer Satisfaction: Fast feedback loop (<2 min)
- ⚠️ -Storage: Cache grows over time (mitigate with LRU eviction)
- ⚠️ -Cache Invalidation: Policy changes require full re-analysis (acceptable for rare event)

**Requirements**: FR-10, NFR-05, NFR-06

---

### SD-06: PCE k-Repair Witness with Exemptions

**Value**: V06 (Fairness), V08 (Actionability)

**Context**: Gate blocks PRs with "fix quality" message, but doesn't say *how*. Developers frustrated by vague feedback. Also, some complexity is necessary (algorithms, state machines) and shouldn't be penalized.

**Decision**: Implement PCE k-repair witness + exemption system:
1. **PCE Witness**: When gate fails, compute minimal k-file subset that, if improved, would pass gate
   - Algorithm: Greedy search for k files with highest ΔQ potential
   - Output: "Fix these k={3,5,8} files: auth.py, login.py, session.py"
2. **Exemptions**: Allow context-aware exceptions
   - Inline: `# repoq: ignore-complexity algorithm` (suppresses complexity warning for function)
   - Config: `.github/quality-policy.yml` exemptions section (e.g., `tests/` has lower complexity threshold)
   - Ontology-based: MVC controllers can have higher complexity than models (pattern-aware)

**Rationale**:
- PCE is constructive (Theorem E: k-repair witness exists)
- Exemptions address fairness (don't penalize necessary complexity)
- Actionability: Developers know *exactly* what to fix

**Alternatives Considered**:
1. **No exemptions**: Rejected (unfair to algorithm-heavy code)
2. **Manual waiver system**: Rejected (not scalable, requires approval process)
3. **AI-generated suggestions only**: Rejected (not deterministic, Phase 5 feature)

**Consequences**:
- ✅ +Actionability: Clear fix path (k files identified)
- ✅ +Fairness: Necessary complexity not penalized
- ✅ +Constructiveness: Help improve, not just block
- ⚠️ -Complexity: Exemption rules need careful design (can be abused)
- ⚠️ -Computation: PCE witness adds ~5-10% overhead (acceptable)

**Requirements**: FR-11, FR-12, FR-13, NFR-07

---

### SD-07: Local Analysis with Optional LLM

**Value**: V07 (Reliability), V16 (Privacy, Tier 2 but critical for enterprises)

**Context**: Sending code to external services (SonarCloud, CodeClimate) violates enterprise security policies. Also introduces network dependency (flaky gates).

**Decision**: All analysis local by default, LLM opt-in:
1. **Core Analysis**: Python-native (AST parsing, radon, git log) — no network calls
2. **RDF Storage**: Embedded (RDFLib in-memory or Oxigraph local file)
3. **Any2Math**: Subprocess (Lean runtime local)
4. **BAML AI Agent** (Phase 5): Opt-in only
   - Requires `--enable-ai` flag + API key in env var
   - Explicit consent in `.github/quality-policy.yml`
   - Clear warning: "AI agent will send code snippets to OpenAI API"

**Rationale**:
- Privacy is hard requirement for 30% of enterprises (from survey)
- Reliability: No network → no flaky failures
- Aligns with EVR-04 (Privacy)

**Alternatives Considered**:
1. **SaaS-only**: Rejected (violates enterprise policies)
2. **Self-hosted LLM required**: Rejected (too complex for MVP)
3. **No AI at all**: Rejected (Phase 5 innovation goal)

**Consequences**:
- ✅ +Privacy: No data leakage (compliant with GDPR, SOC 2)
- ✅ +Reliability: No network dependencies
- ✅ +Enterprise Adoption: Meets security requirements
- ⚠️ -AI Limited: Optional AI reduces differentiation (mitigate with clear value prop)

**Requirements**: FR-14, FR-15, NFR-09

---

### SD-08: Stratified Self-Application

**Value**: V11 (Safety, Tier 2 but architecturally critical)

**Context**: RepoQ should dogfood (analyze itself), but naive self-analysis risks paradoxes (Russell's paradox, Gödel incompleteness analogs). Need formal safety guarantee.

**Decision**: Implement stratified self-application:
1. **Level 0**: External code (user repositories)
2. **Level 1**: RepoQ codebase (dogfooding: RepoQ analyzes its own code)
3. **Level 2**: Meta-analysis (RepoQ checks if its own Q metric is well-formed)
4. **Guard**: `SelfApplicationGuard` enforces L_i can only analyze L_j if i > j (strict ordering)
5. **CLI**: `repoq meta-self --level 2` runs stratified self-analysis

**Rationale**:
- Theorem F: Self-application safety proof (stratification prevents paradoxes)
- Unique innovation: First quality tool with proven safe self-analysis
- Dogfooding builds confidence (if RepoQ passes its own gate, it's credible)

**Alternatives Considered**:
1. **No self-analysis**: Rejected (misses dogfooding benefit)
2. **Naive self-analysis**: Rejected (risk of paradoxes, no formal guarantee)
3. **External meta-checker**: Rejected (defeats purpose of self-analysis)

**Consequences**:
- ✅ +Safety: Formal proof (Theorem F)
- ✅ +Innovation: Novel contribution (safe self-understanding)
- ✅ +Credibility: Dogfooding proves tool works
- ⚠️ -Complexity: Stratification concept requires explanation (mitigate with docs, diagrams)

**Requirements**: FR-16, FR-17, NFR-10

---

## 2. Functional Requirements

### 2.1 Transparency & Output (SD-01)

#### FR-01: Detailed Gate Output
**Description**: `repoq gate` SHALL output structured report including:
- Overall verdict (PASS/FAIL)
- ΔQ = Q(HEAD) - Q(BASE)
- Per-metric breakdown: complexity, hotspots, TODOs, coverage (individual contributions)
- Hard constraint status (tests ≥80%, TODO ≤100, hotspots ≤20): ✓/✗ for each
- File-level deltas (top 10 files by |ΔQ_file|)

**Value**: V01 (Transparency), V08 (Actionability)  
**Priority**: P0 (MVP)  
**Status**: ✅ Implemented (repoq/gate.py)  
**Test**: `tests/test_gate.py::test_detailed_output`

---

#### FR-02: PCE Witness in Output
**Description**: When gate FAILs, output SHALL include PCE k-repair witness:
- "To pass gate, improve these k files: [file1, file2, ..., file_k]"
- Estimated ΔQ if witness fixed: "Expected Q improvement: +2.3"
- k configurable (default: k=3, max: k=8)

**Value**: V08 (Actionability), V10 (Constructiveness)  
**Priority**: P1 (Production)  
**Status**: 🔄 In Progress (tmp/zag_repoq-finished/integrations/zag.py)  
**Test**: `tests/test_gate.py::test_pce_witness`

---

#### FR-03: PR Comment Bot
**Description**: When running in GitHub Actions, RepoQ SHALL post formatted PR comment with:
- Gate verdict (✅ PASS / ❌ FAIL)
- ΔQ summary (colored: green if +, red if -)
- Breakdown table (metric | base | head | delta)
- PCE witness (if FAIL)
- Link to VC certificate (if PASS)

**Value**: V01 (Transparency), V05 (Speed)  
**Priority**: P1 (Production)  
**Status**: ⏸️ Planned  
**Test**: `tests/test_ci_integration.py::test_pr_comment`

---

### 2.2 Gaming Protection (SD-02)

#### FR-04: PCQ Min-Aggregator
**Description**: System SHALL calculate piecewise collective quality:
```python
def calculate_pcq(modules: List[Module], policy: Policy) -> float:
    """
    PCQ(S) = min_{i ∈ modules} u_i(S)
    where u_i = per-module Q score
    """
    module_qualities = [calculate_module_q(m, policy) for m in modules]
    return min(module_qualities)
```
Modules defined by:
- Directory structure (default: top-level dirs)
- Architectural layers (if ontology available: presentation, business, data)
- DDD bounded contexts (if annotated in config)

**Value**: V02 (Gaming Protection), V04 (Monotonicity), V06 (Fairness)  
**Priority**: P1 (Production)  
**Status**: 🔄 In Progress (tmp/zag_repoq-finished/integrations/zag.py)  
**Test**: `tests/test_pcq.py::test_min_aggregator`

---

#### FR-05: PCQ Threshold in Admission
**Description**: Admission predicate SHALL include PCQ check:
```
A(S_base, S_head) ≡ (H) ∧ (ΔQ ≥ ε) ∧ (PCQ(S_head) ≥ τ)
```
where τ ∈ [0.75, 0.9] configurable in `.github/quality-policy.yml`.

If PCQ < τ, gate FAILs with message:
"PCQ bottleneck: Module 'auth' has quality {pcq_value:.2f} < threshold {tau:.2f}"

**Value**: V02 (Gaming Protection), V06 (Fairness)  
**Priority**: P1 (Production)  
**Status**: ⏸️ Planned  
**Test**: `tests/test_gate.py::test_pcq_admission`

---

### 2.3 Correctness & Determinism (SD-03)

#### FR-06: Any2Math Normalization
**Description**: System SHALL normalize Python AST before metric calculation:
1. Parse code to AST (`ast.parse(code)`)
2. Apply TRS rewrite rules: N(AST) → canonical AST
   - Remove redundant nodes (Pass statements, unnecessary parens)
   - Normalize names (consistent variable ordering in comprehensions)
   - Canonicalize expressions (a+b == b+a → sorted order)
3. Calculate metrics on canonical AST
4. Cache normalized AST (keyed by file SHA + normalization version)

**Value**: V03 (Correctness), V07 (Reliability), V14 (Reproducibility)  
**Priority**: P1 (Production)  
**Status**: ⏸️ Planned (tmp/repoq-any2math-integration/)  
**Test**: `tests/test_any2math.py::test_normalization_deterministic`

---

#### FR-07: Lean Proof Verification (Optional)
**Description**: System MAY verify TRS properties in Lean:
- Confluence: ∀ t1, t2: N(t1) = N(t2) if t1 ≡ t2 (syntactic equivalence)
- Termination: ∀ t: N(t) terminates in finite steps
- Idempotence: N(N(t)) = N(t)

If Lean runtime available (`lean --version` succeeds):
- Verify proofs on startup (or via `repoq verify-proofs`)
- Log verification result (PASS/FAIL/SKIP)

**Value**: V03 (Correctness), V18 (Innovation)  
**Priority**: P2 (Advanced)  
**Status**: ⏸️ Planned  
**Test**: `tests/test_lean_proofs.py::test_confluence_proof`

---

### 2.4 Monotonicity & Admission (SD-04)

#### FR-08: Admission Predicate
**Description**: Gate SHALL evaluate admission predicate:
```python
def admission_predicate(base: QualityState, head: QualityState, policy: Policy) -> bool:
    H = hard_constraints_pass(head, policy)  # tests≥80%, TODO≤100, hotspots≤20
    delta_q = head.q_score - base.q_score
    pcq = calculate_pcq(head.modules, policy)
    
    return H and (delta_q >= policy.epsilon) and (pcq >= policy.tau)
```

**Value**: V04 (Monotonicity), V02 (Gaming Protection)  
**Priority**: P0 (MVP)  
**Status**: ✅ Implemented (repoq/gate.py, simplified version without PCQ)  
**Test**: `tests/test_gate.py::test_admission_predicate`

---

#### FR-09: Configurable ε and τ
**Description**: `.github/quality-policy.yml` SHALL define:
```yaml
thresholds:
  epsilon: 0.3        # Noise tolerance (ΔQ ≥ ε)
  tau: 0.8            # PCQ threshold (all modules ≥ τ)
  
hard_constraints:
  test_coverage_min: 0.80
  todo_count_max: 100
  hotspot_threshold: 20
```

Validation:
- ε ∈ [0.0, 1.0], recommended [0.2, 0.5]
- τ ∈ [0.0, 1.0], recommended [0.75, 0.9]
- If invalid, warn and use defaults

**Value**: V04 (Monotonicity), V06 (Fairness)  
**Priority**: P0 (MVP)  
**Status**: ⏸️ Planned  
**Test**: `tests/test_config.py::test_policy_validation`

---

### 2.5 Speed & Performance (SD-05)

#### FR-10: Incremental Analysis
**Description**: System SHALL only re-analyze changed files:
1. Compute file set: `changed_files = git diff --name-only base..head`
2. Load cached metrics for unchanged files (cache keyed by `{file_sha}_{policy_version}`)
3. Re-analyze changed files only
4. Aggregate Q from cached + new metrics

Cache invalidation:
- Policy change (weights, thresholds) → invalidate all
- File change (SHA differs) → invalidate file
- RepoQ version change → invalidate all (safety)

**Value**: V05 (Speed), V07 (Reliability)  
**Priority**: P1 (Production)  
**Status**: ⏸️ Planned  
**Test**: `tests/test_incremental.py::test_cache_hit_rate`

---

### 2.6 Fairness & Actionability (SD-06)

#### FR-11: PCE k-Repair Witness
**Description**: When gate FAILs, compute PCE witness:
```python
def compute_pce_witness(state: QualityState, policy: Policy, k: int) -> List[str]:
    """
    Find k files that, if improved, would pass gate.
    Algorithm: Greedy selection by ΔQ potential.
    """
    files_by_potential = sorted(state.files, key=lambda f: f.delta_q_potential, reverse=True)
    witness = files_by_potential[:k]
    return [f.path for f in witness]
```

**Value**: V08 (Actionability), V10 (Constructiveness), V17 (Incrementality)  
**Priority**: P1 (Production)  
**Status**: 🔄 In Progress (tmp/zag_repoq-finished/integrations/zag.py)  
**Test**: `tests/test_pce.py::test_witness_generation`

---

#### FR-12: Inline Exemptions
**Description**: System SHALL recognize inline exemptions:
```python
# repoq: ignore-complexity algorithm
def dijkstra_shortest_path(graph, start, end):
    # Complexity naturally high (graph algorithm)
    # ... implementation ...
```

Exemption types:
- `ignore-complexity`: Suppress complexity warnings for function/class
- `ignore-hotspots`: Allow high churn (e.g., config files)
- `legacy-module`: Temporary lower standards (with expiry date)

**Value**: V06 (Fairness), V17 (Incrementality)  
**Priority**: P1 (Production)  
**Status**: ⏸️ Planned  
**Test**: `tests/test_exemptions.py::test_inline_ignore`

---

#### FR-13: Config-Based Exemptions
**Description**: `.github/quality-policy.yml` SHALL support exemptions:
```yaml
exemptions:
  complexity:
    - path: "algorithms/*.py"
      max_complexity: 20  # Higher threshold for algorithms
    - path: "tests/"
      max_complexity: 15  # Lower threshold for tests (simpler)
  
  legacy:
    - path: "legacy_module/"
      expires: "2026-06-01"  # Temporary exemption
      reason: "Gradual refactoring plan"
```

**Value**: V06 (Fairness), V17 (Incrementality)  
**Priority**: P2 (Advanced)  
**Status**: ⏸️ Planned  
**Test**: `tests/test_exemptions.py::test_config_exemptions`

---

### 2.7 Privacy & Local Analysis (SD-07)

#### FR-14: Local-Only Core Analysis
**Description**: Core analysis SHALL NOT make network calls:
- AST parsing: Python built-in `ast` module (local)
- Complexity: `radon` library (local)
- Hotspots: `git log` parsing (local)
- TODOs: Regex scanning (local)
- Coverage: `coverage.py` (local)
- RDF: RDFLib in-memory or Oxigraph local file (local)

Network audit test: Assert zero outbound connections during analysis.

**Value**: V16 (Privacy), V07 (Reliability)  
**Priority**: P0 (MVP)  
**Status**: ✅ Implemented (all analyzers local)  
**Test**: `tests/test_privacy.py::test_no_network_calls`

---

#### FR-15: Opt-In AI Agent
**Description**: BAML AI agent (Phase 5) SHALL be opt-in only:
1. Disabled by default (no AI without consent)
2. Enable via CLI flag: `repoq gate --enable-ai`
3. Enable via config:
```yaml
ai_agent:
  enabled: true
  provider: "openai"  # or "anthropic", "self-hosted"
  api_key_env: "REPOQ_AI_API_KEY"
  consent: "I understand code snippets will be sent to external LLM API"
```
4. Warning on first run: "AI agent will send code snippets to {provider}. Continue? (y/n)"

**Value**: V16 (Privacy), V12 (Learning)  
**Priority**: P2 (Advanced)  
**Status**: ⏸️ Planned (Phase 5: BAML integration)  
**Test**: `tests/test_ai_agent.py::test_opt_in_required`

---

### 2.8 Safety & Self-Application (SD-08)

#### FR-16: Stratified Self-Analysis
**Description**: System SHALL enforce stratification for self-analysis:
```python
class SelfApplicationGuard:
    def check_stratification(self, current_level: int, target_level: int):
        if target_level <= current_level:
            raise StratificationViolation(
                f"Cannot analyze level {target_level} from level {current_level}. "
                f"Stratification requires target > current."
            )
        
        if target_level - current_level > 1:
            raise StratificationViolation(
                f"Cannot skip levels. Analyze level {current_level + 1} first."
            )
```

Levels:
- L_0: External code (default)
- L_1: RepoQ codebase (dogfooding)
- L_2: Meta-analysis (RepoQ's Q metric self-check)

**Value**: V11 (Safety), V18 (Innovation)  
**Priority**: P2 (Advanced)  
**Status**: 🔄 In Progress (tmp/repoq-meta-loop-addons/trs/engine.py)  
**Test**: `tests/test_stratification.py::test_guard_violation`

---

#### FR-17: meta-self CLI Command
**Description**: Implement `repoq meta-self --level N`:
```bash
# Level 1: Analyze RepoQ's own code
repoq meta-self --level 1
# Output: Q(RepoQ) = 82.5, patterns=[Layered, Plugin], violations=[]

# Level 2: Meta-analysis (check if RepoQ's Q metric is self-consistent)
repoq meta-self --level 2
# Output: Meta-check PASS: RepoQ's ontology satisfies its own SHACL shapes
```

**Value**: V11 (Safety), V18 (Innovation)  
**Priority**: P2 (Advanced)  
**Status**: ⏸️ Planned  
**Test**: `tests/test_meta_self.py::test_level1_dogfooding`

---

### 2.9 Integration & CI/CD

#### FR-18: GitHub Actions Integration
**Description**: Provide `.github/workflows/quality-gate.yml` template:
```yaml
name: Quality Gate
on: [pull_request]

jobs:
  quality-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Full history for hotspot analysis
      
      - name: Install RepoQ
        run: pip install repoq
      
      - name: Run Quality Gate
        run: |
          repoq gate \
            --base ${{ github.event.pull_request.base.sha }} \
            --head ${{ github.sha }} \
            --format pr-comment > gate_output.txt
      
      - name: Post PR Comment
        if: always()
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const output = fs.readFileSync('gate_output.txt', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: output
            });
      
      - name: Fail if Gate Blocked
        run: exit $(cat gate_exit_code.txt)
```

**Value**: V05 (Speed), V13 (Simplicity)  
**Priority**: P1 (Production)  
**Status**: ⏸️ Planned  
**Test**: `tests/test_ci_integration.py::test_github_actions_workflow`

---

#### FR-19: VC Certificate Export
**Description**: System SHALL export W3C Verifiable Credentials:
```python
def generate_certificate(decision: GateDecision, key: PrivateKey) -> VC:
    vc = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", "QualityAssessmentCredential"],
        "issuer": "did:repoq:v1",
        "issuanceDate": datetime.utcnow().isoformat(),
        "credentialSubject": {
            "repository": decision.repo_url,
            "commit": decision.commit_sha,
            "q_score": decision.q_head,
            "delta_q": decision.delta_q,
            "verdict": decision.verdict,
            "policy_version": decision.policy_version
        },
        "proof": {
            "type": "EcdsaSecp256k1Signature2019",
            "created": datetime.utcnow().isoformat(),
            "proofPurpose": "assertionMethod",
            "verificationMethod": "did:repoq:v1#key-1",
            "jws": sign_ecdsa(key, vc_payload)
        }
    }
    return vc
```

**Value**: V09 (Auditability), V03 (Correctness)  
**Priority**: P0 (MVP)  
**Status**: ✅ Implemented (repoq/core/model.py)  
**Test**: `tests/test_vc.py::test_certificate_signature`

---

## 3. Non-Functional Requirements (SMART Format)

### 3.1 Performance

#### NFR-01: Analysis Time (Speed)
**Requirement**: Analysis time SHALL be ≤2 minutes (90th percentile) for repositories with <1000 files, and ≤5 minutes for <10,000 files, measured on standard hardware (4-core CPU, 8GB RAM).

**Specific**: Analysis time for repos of varying sizes  
**Measurable**: P90 latency in minutes  
**Agreed**: Validated with DevOps stakeholders  
**Realistic**: Achievable with incremental analysis + caching  
**Time-bound**: Enforced in every release  

**Value**: V05 (Speed)  
**Priority**: P0 (MVP)  
**Status**: 🔄 In Progress (current: ~3 min for 1K files, needs optimization)  
**Test**: `tests/performance/test_analysis_time.py::test_p90_latency`

---

#### NFR-02: PCQ Computation Overhead
**Requirement**: PCQ min-aggregator SHALL add ≤20% overhead to Q calculation time (measured as: time_with_pcq / time_without_pcq ≤ 1.2).

**Value**: V02 (Gaming Protection), V05 (Speed)  
**Priority**: P1 (Production)  
**Status**: ⏸️ Planned  
**Test**: `tests/performance/test_pcq_overhead.py::test_20_percent_overhead`

---

### 3.2 Correctness & Determinism

#### NFR-03: Deterministic Analysis
**Requirement**: System SHALL produce identical Q scores for identical inputs (same code + policy + RepoQ version) across 100 consecutive runs, with zero variance.

**Value**: V07 (Reliability), V14 (Reproducibility)  
**Priority**: P0 (MVP)  
**Status**: ✅ Implemented (validated via property-based tests)  
**Test**: `tests/test_determinism.py::test_100_runs_identical`

---

#### NFR-04: Monotonicity Guarantee
**Requirement**: For any commit sequence S_1 → S_2 → ... → S_n where each transition passes admission predicate, Q(S_i+1) - Q(S_i) ≥ ε SHALL hold for all i ∈ [1, n-1]. Verified via longitudinal study (≥100 commits).

**Value**: V04 (Monotonicity), V03 (Correctness)  
**Priority**: P0 (MVP)  
**Status**: ✅ Implemented (Theorem B proven, validated empirically)  
**Test**: `tests/test_monotonicity.py::test_longitudinal_100_commits`

---

### 3.3 Reliability

#### NFR-05: False Negative Rate
**Requirement**: Gate false negative rate (failing to block quality regression) SHALL be <1%, measured on benchmark dataset of 1000 known-bad commits.

**Value**: V07 (Reliability), V04 (Monotonicity)  
**Priority**: P1 (Production)  
**Status**: ⏸️ Planned (need benchmark dataset)  
**Test**: `tests/test_reliability.py::test_false_negative_rate`

---

#### NFR-06: False Positive Rate
**Requirement**: Gate false positive rate (blocking legitimate improvement) SHALL be <5%, measured on benchmark dataset of 1000 known-good commits.

**Value**: V07 (Reliability), V06 (Fairness)  
**Priority**: P1 (Production)  
**Status**: ⏸️ Planned (need benchmark dataset)  
**Test**: `tests/test_reliability.py::test_false_positive_rate`

---

### 3.4 Usability

#### NFR-07: Time to Comprehension
**Requirement**: Developers SHALL be able to identify root cause of gate failure in <30 seconds (median), measured via usability study with ≥20 participants (eye-tracking or self-reported).

**Value**: V01 (Transparency), V08 (Actionability)  
**Priority**: P1 (Production)  
**Status**: ⏸️ Planned (need user study)  
**Test**: User study protocol in `docs/vdad/user-study-protocol.md`

---

#### NFR-08: Developer Satisfaction
**Requirement**: Developer satisfaction survey SHALL achieve ≥80% agreement on statement: "RepoQ gate output is clear and actionable" (5-point Likert scale, 4-5 = agree).

**Value**: V01 (Transparency), V08 (Actionability), V12 (Learning)  
**Priority**: P1 (Production)  
**Status**: ⏸️ Planned (survey after 6-month deployment)  
**Test**: Survey results in `docs/vdad/satisfaction-survey-results.md`

---

### 3.5 Security & Privacy

#### NFR-09: Zero Network Calls
**Requirement**: Core analysis (levels 0-1) SHALL make zero outbound network connections, verified via network traffic monitoring during analysis (tcpdump or Wireshark).

**Value**: V16 (Privacy), V07 (Reliability)  
**Priority**: P0 (MVP)  
**Status**: ✅ Implemented  
**Test**: `tests/test_privacy.py::test_network_audit`

---

### 3.6 Maintainability

#### NFR-10: Test Coverage
**Requirement**: Code coverage SHALL be ≥80% line coverage and ≥70% branch coverage, measured via `coverage.py`, enforced in CI.

**Value**: V03 (Correctness), V07 (Reliability)  
**Priority**: P0 (MVP)  
**Status**: 🔄 In Progress (current: 64%, target: 80%)  
**Test**: CI checks in `.github/workflows/ci.yml`

---

### 3.7 Scalability

#### NFR-11: Large Repository Support
**Requirement**: System SHALL successfully analyze repositories up to 100,000 files within 30 minutes (without incremental analysis), and within 5 minutes (with incremental, assuming 1% churn).

**Value**: V05 (Speed), V23 (Flexibility, Tier 3)  
**Priority**: P2 (Advanced)  
**Status**: ⏸️ Planned  
**Test**: `tests/performance/test_large_repo.py::test_100k_files`

---

### 3.8 Compatibility

#### NFR-12: Python Version Support
**Requirement**: RepoQ SHALL support Python 3.9+ (3.9, 3.10, 3.11, 3.12), verified via CI matrix testing on all versions.

**Value**: V13 (Simplicity), V19 (Openness)  
**Priority**: P0 (MVP)  
**Status**: ✅ Implemented (CI matrix covers 3.9-3.12)  
**Test**: `.github/workflows/ci.yml` (matrix: [3.9, 3.10, 3.11, 3.12])

---

## 4. Ethical Value Requirements (EVR) — Updated

### EVR-01: Transparency (Updated)

**IEEE 7000 Mapping**: Transparency, Explainability

**Requirement**: System SHALL provide human-readable explanation for every gate rejection, including:
1. Overall verdict: PASS/FAIL with clear reason
2. ΔQ breakdown: Per-metric contributions (complexity, hotspots, TODOs, coverage)
3. File-level analysis: Top 10 files by |ΔQ_file| with individual metrics
4. Hard constraint status: Tests, TODOs, hotspots (✓/✗ for each)
5. PCE witness (if FAIL): "Fix these k files: [...]" with estimated ΔQ improvement
6. Certificate link (if PASS): URL or ID of VC certificate

**Acceptance Criteria**:
- **AC-01.1**: Developer comprehension survey: ≥90% can identify root cause from output
- **AC-01.2**: Time to comprehension: Median <30 seconds (eye-tracking or self-report)
- **AC-01.3**: All gate failures include PCE witness (100% coverage)
- **AC-01.4**: PR comment format validation: Markdown table with ≥5 columns (metric, base, head, delta, status)

**Supporting Requirements**: FR-01, FR-02, FR-03, NFR-07, NFR-08

**Verification Method**: Usability study (n≥20), Survey, Automated formatting checks

---

### EVR-02: Gaming Protection (Updated)

**IEEE 7000 Mapping**: Accountability, Fairness

**Requirement**: System SHALL detect and block attempts to artificially inflate Q score through:
1. **Metric compensation**: One high score masking another low score → PCQ min-aggregator prevents (all modules ≥τ)
2. **Trivial tests**: `assert True` inflating coverage without real validation → AI agent flags anomalous patterns (Phase 5)
3. **Syntactic manipulation**: Whitespace, comments, formatting changes → Any2Math normalization eliminates

**Acceptance Criteria**:
- **AC-02.1**: PCQ prevents compensation: In test cases with one bad module (u_i < τ) and high average Q, gate SHALL FAIL
- **AC-02.2**: False positive rate for gaming detection: <10% (don't block legitimate code)
- **AC-02.3**: True positive rate for gaming detection: ≥80% (catch most gaming attempts in controlled experiments)
- **AC-02.4**: Any2Math normalization: Identical Q for semantically equivalent code (100 test pairs)

**Supporting Requirements**: FR-04, FR-05, FR-06, NFR-02

**Verification Method**: Unit tests (compensation scenarios), Controlled gaming experiments, Normalization test suite

---

### EVR-03: Fairness (Updated)

**IEEE 7000 Mapping**: Fairness, Non-discrimination

**Requirement**: System SHALL NOT penalize developers for:
1. **Necessary complexity**: Algorithms, state machines, complex business logic → Inline exemptions allowed (`# repoq: ignore-complexity algorithm`)
2. **Legitimate refactoring**: Temporary churn increase during refactoring → PCE allows multi-step improvement path
3. **Domain-specific patterns**: Frontend complexity differs from backend → Configurable weights per module/layer
4. **Legacy code improvement**: Can't fix all debt in one PR → Exemptions with expiry dates, incremental standards

**Acceptance Criteria**:
- **AC-03.1**: Exemption coverage: ≥90% of algorithm-heavy functions can use inline exemptions without abuse
- **AC-03.2**: PCE multi-step: For legacy modules with Q < τ, PCE SHALL identify k-file subset for incremental improvement
- **AC-03.3**: Fairness survey: ≥80% developers agree "Gate is fair" (5-point Likert, 4-5 = agree)
- **AC-03.4**: No false positives on well-tested complex code: Test suite with 50+ algorithm implementations, zero gate blocks

**Supporting Requirements**: FR-11, FR-12, FR-13, NFR-06

**Verification Method**: Exemption abuse analysis, Developer survey, Algorithm test suite, Case studies

---

### EVR-04: Privacy (Updated)

**IEEE 7000 Mapping**: Privacy, Data Protection

**Requirement**: System SHALL NOT transmit repository contents to external services without explicit user consent:
1. **Core analysis local**: All AST parsing, metric calculation, git log analysis local (zero network calls)
2. **RDF storage local**: RDFLib in-memory or Oxigraph embedded (no external DB)
3. **Optional AI agent**: BAML AI agent (Phase 5) requires:
   - Explicit opt-in: `--enable-ai` flag OR config `ai_agent.enabled: true`
   - Consent acknowledgment: "I understand code snippets will be sent to {provider}"
   - API key in env var (not committed to repo): `REPOQ_AI_API_KEY`
4. **No telemetry**: No usage data sent to maintainers without opt-in

**Acceptance Criteria**:
- **AC-04.1**: Network audit: Zero outbound connections during core analysis (tcpdump monitoring)
- **AC-04.2**: AI opt-in enforcement: Attempting `--enable-ai` without API key SHALL fail with clear error
- **AC-04.3**: Compliance validation: GDPR, SOC 2, ISO 27001 compatible (legal review)
- **AC-04.4**: Data retention: No persistent storage of code beyond local cache (auto-expired after 30 days)

**Supporting Requirements**: FR-14, FR-15, NFR-09

**Verification Method**: Network traffic analysis, Legal compliance audit, Opt-in validation tests

---

## 5. Requirements Traceability Matrix

| Value | Decision | Functional Req | NFR | EVR | Test | Status |
|-------|----------|----------------|-----|-----|------|--------|
| **V01 Transparency** | SD-01 | FR-01, FR-02, FR-03 | NFR-07, NFR-08 | EVR-01 | test_detailed_output, test_pce_witness, test_pr_comment, user_study | ✅ FR-01 Done<br>🔄 FR-02/03 In Progress |
| **V02 Gaming Protection** | SD-02 | FR-04, FR-05 | NFR-02 | EVR-02 | test_min_aggregator, test_pcq_admission, test_gaming_scenarios | 🔄 In Progress |
| **V03 Correctness** | SD-03 | FR-06, FR-07 | NFR-03, NFR-04 | EVR-02 (partial) | test_normalization_deterministic, test_confluence_proof, test_monotonicity | ⏸️ Planned (Any2Math) |
| **V04 Monotonicity** | SD-04 | FR-08, FR-09 | NFR-04 | - | test_admission_predicate, test_longitudinal_100_commits | ✅ FR-08 Done<br>⏸️ FR-09 Planned |
| **V05 Speed** | SD-05 | FR-10 | NFR-01, NFR-11 | - | test_cache_hit_rate, test_p90_latency, test_large_repo | ⏸️ Planned |
| **V06 Fairness** | SD-06 | FR-11, FR-12, FR-13 | NFR-06 | EVR-03 | test_witness_generation, test_inline_ignore, test_config_exemptions, fairness_survey | 🔄 FR-11 In Progress<br>⏸️ FR-12/13 Planned |
| **V07 Reliability** | SD-03, SD-07 | FR-06, FR-14 | NFR-03, NFR-05, NFR-06, NFR-09 | - | test_determinism, test_false_negative_rate, test_network_audit | ✅ FR-14, NFR-03, NFR-09 Done<br>⏸️ Others Planned |
| **V08 Actionability** | SD-01, SD-06 | FR-01, FR-02, FR-11 | NFR-07 | EVR-01 | test_pce_witness, test_detailed_output, user_study | ✅ FR-01 Done<br>🔄 FR-02/11 In Progress |
| **V09 Auditability** | - | FR-19 | - | - | test_certificate_signature | ✅ Done |
| **V11 Safety** | SD-08 | FR-16, FR-17 | NFR-10 | - | test_guard_violation, test_level1_dogfooding | 🔄 FR-16 In Progress<br>⏸️ FR-17 Planned |
| **V16 Privacy** | SD-07 | FR-14, FR-15 | NFR-09 | EVR-04 | test_no_network_calls, test_opt_in_required | ✅ FR-14, NFR-09 Done<br>⏸️ FR-15 Planned |

**Coverage Summary**:
- **Values**: 11/27 explicitly traced (all Tier 1 + 3 Tier 2)
- **Requirements**: 31 total (19 FR + 12 NFR)
  - ✅ Implemented: 8 (26%)
  - 🔄 In Progress: 6 (19%)
  - ⏸️ Planned: 17 (55%)
- **EVRs**: 4/4 fully detailed with acceptance criteria
- **Tests**: 25+ test cases identified

---

## 6. Requirements Validation Checklist

### 6.1 Completeness
- ✅ All 8 Tier 1 values have ≥1 strategic decision
- ✅ All strategic decisions have ≥1 FR or NFR
- ✅ All EVRs have ≥2 acceptance criteria
- ✅ All requirements traceable to value

### 6.2 SMART Criteria (NFRs)
- ✅ **Specific**: All NFRs define exact metrics (e.g., ≤2 min, ≥80% coverage)
- ✅ **Measurable**: All NFRs have quantitative acceptance criteria
- ✅ **Agreed**: Validated against stakeholder needs (Phase 1-2)
- ✅ **Realistic**: Achievable with planned architecture (Phase 4)
- ✅ **Time-bound**: Enforced in CI or release milestones

### 6.3 Consistency
- ✅ No conflicting requirements (e.g., speed vs correctness balanced via tiers)
- ✅ EVRs align with IEEE 7000 (transparency, fairness, privacy, accountability)
- ✅ Requirements align with formal guarantees (14 theorems)

### 6.4 Testability
- ✅ All requirements have identified test cases
- 🔄 Benchmark datasets needed (NFR-05, NFR-06) — In Progress
- 🔄 User studies needed (NFR-07, NFR-08) — Planned for post-MVP

---

## 7. Success Criteria (VDAD Phase 3)

- ✅ **Strategic Decisions**: 8 decisions (one per Tier 1 value)
- ✅ **Functional Requirements**: 19 FR (covering all Tier 1 values)
- ✅ **Non-Functional Requirements**: 12 NFR (all SMART-compliant)
- ✅ **EVRs**: 4 EVRs updated with ≥2 acceptance criteria each
- ✅ **Traceability Matrix**: Full chain (Value → Decision → Requirement → Test)
- ✅ **Requirements Coverage**: 100% Tier 1 values → ≥1 requirement
- ⏭️ **Next**: Phase 4 (Architecture Design) — Design system satisfying all 31 requirements

---

## 8. AI Copilot Role (Phase 3 Retrospective)

**What AI Did**:
1. Extracted 8 Strategic Decisions from Tier 1 values
2. Designed ADR-style decision records (Context, Decision, Rationale, Alternatives, Consequences)
3. Generated 19 FR and 12 NFR from decisions
4. Formulated SMART NFRs (Specific, Measurable, Agreed, Realistic, Time-bound)
5. Updated 4 EVRs with detailed acceptance criteria (2-4 criteria each)
6. Created Requirements Traceability Matrix (Value → Decision → Requirement → Test)
7. Validated requirements against Phase 2 Value Register (100% Tier 1 coverage)

**What AI Should Do Next (Phase 4)**:
1. Design high-level architecture satisfying all 31 requirements
2. Create C4 diagrams (Context, Container, Component) showing how components fulfill requirements
3. Document NFR realization strategies (e.g., caching for NFR-01 Speed)
4. Generate ADRs for architectural decisions (BAML vs custom AI, RDFLib vs Oxigraph, etc.)
5. Design BAML AI agent spec (functions, boundaries, rollout plan)

---

## 9. References

1. Stefan Kapferer et al. (2024). *Value-Driven Analysis and Design (VDAD)*. [ethical-se.github.io](https://ethical-se.github.io) — Steps 5-6: Strategic Decisions & Requirements
2. IEEE 7000-2021. *Standard for Addressing Ethical Concerns during System Design*. — EVR framework
3. Karl Wiegers & Joy Beatty (2013). *Software Requirements (3rd ed.)*. Microsoft Press — SMART requirements, traceability
4. Alistair Cockburn (2001). *Writing Effective Use Cases*. Addison-Wesley — Acceptance criteria
5. Michael Keeling (2017). *Design It!*. Pragmatic Bookshelf — ADR format, decision rationale
6. RepoQ Project (2025). *Phase 2: Value Register*. `docs/vdad/phase2-value-register.md` — 27 values, prioritization
7. RepoQ Project (2025). *Formal Foundations*. `docs/development/formal-foundations-complete.md` — 14 theorems grounding requirements

---

**Document Status**: ✅ COMPLETE  
**Review**: Pending (validate requirements with stakeholders via workshops)  
**Next Steps**: Create `phase4-architecture.md` with component design, C4 diagrams, ADRs, NFR realization.
