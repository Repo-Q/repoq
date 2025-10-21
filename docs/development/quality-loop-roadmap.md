# Meta-Optimizing Quality Loop: Implementation Roadmap

## Executive Summary

This document outlines the implementation strategy for a **monotonic quality guarantee system** - a self-reinforcing quality loop where every commit either improves code quality or is blocked by CI gates.

**Current Status**: Technical foundation ready (64% test coverage, TRS systems validated, VC certificates implemented, 77 artifacts in tmp/ ready for integration)  
**Methodology**: Value-Driven Analysis and Design (VDAD) integrated with agile architectural practices  
**Recommended Approach**: MVP-first for rapid validation, then iterative expansion following VDAD 7-step process  
**Timeline**: Structured as iterative phases without fixed dates (see VDAD Integration section)

> 📋 **New**: This roadmap now integrates the VDAD (Value-Driven Analysis and Design) methodology for systematic stakeholder-centric development. See [VDAD Integration](#vdad-integration-roadmap) section below for the comprehensive 6-month strategic plan.

---

## Core Concept: Guaranteed Quality Monotonicity

### Mathematical Foundation

The system enforces strict monotonicity through:

1. **Hard Constraints** (blocking): Critical metrics must not degrade
   - `tests_ok`: All unit/integration tests must pass
   - `hotspots_ratio`: High-complexity/high-churn files ≤ baseline
   - `todo_count`: New TODO/FIXME/BUG comments forbidden
   - `security_alerts`: No new critical vulnerabilities (SAST/OSV)

2. **Soft Goal** (quality improvement): Integral quality score Q must increase
   ```
   Q = 100 - 20·avg(complexity) - 20·avg(churn) - 30·hotspots_ratio 
       - 7·[¬CI] - 8·[¬ownership_ok] - φ(tests)
   ```

3. **Monotonic Rule**: PR accepted only if:
   - All hard constraints satisfied
   - Q_after ≥ Q_before + ε (ε = 0.1-0.5 noise guard-band)

### Quality Formula Integration

The Q score maps directly to existing RepoQ VC certificates:
```json
{
  "@type": "VerifiableCredential",
  "credentialSubject": {
    "@type": "repo:Project",
    "score": Q,  // ← Integral quality metric
    "complexity": avg_complexity,
    "churn": avg_churn,
    "hotspots": hotspots_ratio
  }
}
```

---

## Implementation Variants

### 🎯 **Variant 1: Full Implementation** (8-12 weeks)

**Scope**: Complete production system with all advanced features

#### Components
```
Full Implementation Pipeline
├── Incremental Analysis Engine
│   ├── Git diff-based change detection
│   ├── Selective re-analysis of affected files
│   └── Cached baseline storage
├── Policy Configuration System
│   ├── .github/quality-policy.yml parser
│   ├── Dynamic weight adjustment
│   └── Waiver token management
├── Hard Constraints Validators
│   ├── pytest integration (tests_must_pass)
│   ├── TODO/FIXME detector (AST-based)
│   ├── SAST/OSV security scanning
│   └── CI presence verification
├── Delta Measurement Framework
│   ├── HEAD vs BASE comparison
│   ├── Statistical noise filtering
│   └── Confidence intervals for metrics
├── GitHub Actions Integration
│   ├── quality-gate.yml workflow
│   ├── Automatic baseline updates
│   └── Artifact publishing
├── Comment Bot & Baseline Updater
│   ├── PR comment with ΔQ breakdown
│   ├── PCE k-repair witnesses
│   └── Baseline commit automation
└── Organizational Dashboard
    ├── Multi-repo Q trajectory tracking
    ├── Waiver token usage monitoring
    └── SPARQL knowledge graph queries
```

#### Timeline & Resources
- **Duration**: 8-12 weeks
- **Team**: 2-3 engineers
- **Risk**: High complexity, potential scope creep

#### Benefits
- ✅ Complete feature set
- ✅ Production-grade gaming protection
- ✅ Advanced analytics and insights

#### Risks
- ❌ Long time to market
- ❌ May destabilize current codebase
- ❌ High maintenance burden

---

### ⭐ **Variant 2: MVP with Basic Monotonicity** (2-3 weeks) - RECOMMENDED

**Scope**: Minimum viable product for concept validation

#### Phase 1: Core Gate Implementation (Week 1)

##### 1.1 Basic Gate Command
```python
# New CLI command: repoq gate
@app.command()
def gate(
    base: str = typer.Option(..., help="Base commit SHA or path"),
    head: str = typer.Option(".", help="HEAD path to compare"),
    policy: str = typer.Option(
        ".github/quality-policy.yml", 
        help="Quality policy configuration"
    ),
    output: str = typer.Option(None, help="JSON output for CI")
):
    """
    Compare quality metrics between BASE and HEAD.
    Exit code 0 if quality improved, 2 if degraded.
    """
    base_metrics = analyze_repository(base)
    head_metrics = analyze_repository(head)
    
    result = validate_monotonicity(base_metrics, head_metrics, policy)
    
    if output:
        save_gate_result(result, output)
    
    print_gate_report(result)
    raise typer.Exit(0 if result.passed else 2)
```

##### 1.2 Simple Q Aggregator
```python
def calculate_quality_score(metrics: ProjectMetrics) -> float:
    """Basic Q formula for MVP."""
    avg_complexity = metrics.structure.avg_complexity or 0
    hotspots_ratio = len(metrics.hotspots) / max(len(metrics.files), 1)
    todo_count = len([i for i in metrics.issues if i.type == "TodoComment"])
    
    Q = 100 - 20 * min(avg_complexity / 10, 1.0) \
            - 30 * hotspots_ratio \
            - 10 * min(todo_count / 100, 1.0)
    
    return max(0, min(100, Q))
```

##### 1.3 Basic Hard Constraints
```python
def validate_hard_constraints(base, head, policy) -> List[Violation]:
    violations = []
    
    # Test pass requirement (via pytest exit code)
    if policy.tests_must_pass:
        result = subprocess.run(["pytest"], capture_output=True)
        if result.returncode != 0:
            violations.append(Violation("tests_failed", ...))
    
    # TODO count non-increasing
    if policy.no_new_todos:
        base_todos = count_todos(base)
        head_todos = count_todos(head)
        if head_todos > base_todos:
            violations.append(Violation("new_todos", 
                count=head_todos - base_todos))
    
    # Hotspots ratio non-increasing
    if policy.hotspots_non_increasing:
        if head.hotspots_ratio > base.hotspots_ratio + 0.01:
            violations.append(Violation("hotspots_increased", ...))
    
    return violations
```

#### Phase 2: CI Integration (Week 2)

##### 2.1 Quality Policy Configuration
```yaml
# .github/quality-policy.yml
version: "1.0"

hard_constraints:
  tests_must_pass: true
  no_new_todos: true
  hotspots_non_increasing: true
  max_complexity_increase: 5  # points

soft_goal:
  epsilon: 0.2  # Minimum Q improvement
  aggregator: "basic"  # basic|advanced|zag

budgets:
  waiver_tokens_per_sprint: 1
  waiver_requires_approval: true

reporting:
  comment_on_pr: true
  upload_artifacts: true
```

##### 2.2 GitHub Actions Workflow
```yaml
# .github/workflows/quality-gate.yml
name: Quality Gate
on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  quality-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Need history for base comparison
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      
      - name: Install RepoQ
        run: pip install -e ".[full]"
      
      - name: Checkout BASE
        run: |
          git checkout ${{ github.event.pull_request.base.sha }}
          mkdir -p /tmp/base
          repoq full . -o /tmp/base/quality.jsonld
      
      - name: Checkout HEAD
        run: |
          git checkout ${{ github.sha }}
          repoq full . -o /tmp/head/quality.jsonld
      
      - name: Run Quality Gate
        run: |
          repoq gate \
            --base /tmp/base/quality.jsonld \
            --head /tmp/head/quality.jsonld \
            --policy .github/quality-policy.yml \
            --output gate-result.json
      
      - name: Upload Results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: quality-gate-results
          path: gate-result.json
```

#### Phase 3: Local Developer Experience (Week 3)

##### 3.1 Pre-push Hook
```bash
#!/bin/bash
# .git/hooks/pre-push
echo "🔍 Running quick quality check..."

repoq structure . -o /tmp/quick-check.jsonld --quiet

if [ $? -ne 0 ]; then
    echo "❌ Quality check failed. Push blocked."
    exit 1
fi

echo "✅ Local quality check passed"
```

##### 3.2 Developer Documentation
```markdown
# docs/development/quality-gate-guide.md
- How to interpret gate failures
- Using --policy-dry-run for local testing
- Requesting waiver tokens
- Understanding Q score breakdown
```

#### MVP Success Criteria

- ✅ Working `repoq gate` command with exit codes
- ✅ Basic Q formula in VC certificates
- ✅ Simple hard constraints (tests, TODO, hotspots)
- ✅ GitHub Actions integration
- ✅ Developer can test locally before push

#### MVP Timeline
| Week | Deliverable |
|------|-------------|
| Week 1 | Core gate command + Q aggregator |
| Week 2 | CI integration + policy config |
| Week 3 | Local hooks + documentation |

#### Benefits
- ✅ Fast time to market (2-3 weeks)
- ✅ Validates concept with real usage
- ✅ Low risk, evolutionary approach
- ✅ Immediate value for developers

#### Risks
- ⚠️ Limited gaming protection (no ZAG PCQ yet)
- ⚠️ Basic noise handling (fixed ε)
- ⚠️ No organizational dashboard

---

### 🔬 **Variant 3: Research Prototype** (1 week)

**Scope**: Mathematical validation only, no production integration

#### Purpose
- Validate Q formula calibration
- Test noise tolerance (ε tuning)
- Experiment with weight optimization

#### Not Included
- CI integration
- Policy system
- Hard constraints

#### Use Case
Academic validation before committing to implementation

---

## Risk Analysis

### Technical Risks

#### 1. Performance Impact
**Risk**: Double analysis (BASE + HEAD) = 2x CI time

**Impact**: High for large repositories (>10k files)

**Mitigation**:
- Implement incremental analysis (Phase 2+)
- Cache baseline analysis results
- Parallelize analyzer execution
- Use `structure` mode for fast pre-push checks

#### 2. Metric Noise
**Risk**: Small code changes cause Q fluctuations larger than ε

**Impact**: False negatives block legitimate PRs

**Mitigation**:
- Adaptive ε based on change size
- Statistical smoothing (rolling average)
- Whitelist for known-noisy files (tests, generated code)

#### 3. Gaming Susceptibility
**Risk**: Developers optimize Q without real quality improvement

**Impact**: Q increases but actual quality degrades

**Mitigation** (Post-MVP):
- ZAG PCQ min-aggregator (forces worst module improvement)
- Manual audit samples (10% of PRs)
- Correlation analysis Q vs bugs/incidents

### Process Risks

#### 1. Developer Friction
**Risk**: Quality gate blocks urgent hotfixes

**Impact**: Reduced development velocity, workarounds

**Mitigation**:
- Clear waiver process (1-2 tokens/sprint)
- Fast local feedback (<30s)
- Educational documentation

#### 2. False Positives
**Risk**: Legitimate code changes fail gate incorrectly

**Impact**: Developer frustration, loss of trust

**Mitigation**:
- Comprehensive test suite for gate logic
- Dry-run mode for testing policies
- Quick appeal process

---

## Current State Assessment

### ✅ Ready Components (from existing codebase)

```python
# Already implemented:
✓ VC certificates generation (certs/generator.py, quality.py)
✓ JSON-LD/RDF export infrastructure
✓ SHACL validation shapes
✓ Basic GitHub Actions workflow
✓ ZAG integration scaffolding (integrations/zag.py)
✓ TRS mathematical soundness (5/7 violations fixed)
```

### ⚠️ Missing for MVP

```python
# Need to implement:
☐ Incremental analysis (BASE vs HEAD comparison)
☐ repoq gate CLI command
☐ Quality policy YAML parser
☐ Hard constraint validators
☐ TODO/FIXME detector
☐ Gate result reporting
```

### 🔴 Blockers for Production

```python
# Critical gaps:
✗ Test coverage 64% (need 80%+)
✗ No pytest integration
✗ No security scanning (SAST/OSV)
✗ Performance not optimized for CI
✗ No waiver token system
```

---

## Decision: MVP Prioritization

### Why Variant 2 (MVP) is Recommended

1. **Rapid Validation**: 2-3 weeks to working system vs 8-12 weeks for full implementation
2. **Low Risk**: Evolutionary approach, doesn't destabilize current codebase
3. **Immediate Value**: Developers get quality feedback in CI immediately
4. **Proof of Concept**: Validates monotonicity concept with real usage data
5. **Foundation for Growth**: Clean architecture allows Phase 2/3 additions

### Implementation Order

**Priority P0** (MVP - Week 1-3):
- [x] TRS mathematical soundness
- [ ] `repoq gate` command implementation
- [ ] Basic Q aggregator in VC certificates
- [ ] Simple hard constraints (tests, TODO, hotspots)
- [ ] GitHub Actions quality-gate.yml
- [ ] Quality policy YAML support

**Priority P1** (Production Hardening - Week 4-8):
- [ ] ZAG PCQ integration for gaming protection
- [ ] Statistical noise filtering (adaptive ε)
- [ ] Waiver token system
- [ ] Performance optimization (caching, incremental analysis)
- [ ] Comment bot with ΔQ breakdown

**Priority P2** (Advanced Features - Week 8-12):
- [ ] PCE k-repair witnesses in PR comments
- [ ] Organizational dashboard (multi-repo tracking)
- [ ] Weight adaptation via contextual bandits
- [ ] Security integration (OSV, SAST)
- [ ] SPARQL knowledge graph queries

---

## Next Steps

### Immediate Actions (This Sprint)

1. **Commit to MVP approach**: Finalize decision with stakeholders
2. **Create feature branch**: `feature/quality-gate-mvp`
3. **Implement core gate logic**: Start with `repoq gate` command
4. **Write comprehensive tests**: Gate logic must have 95%+ coverage
5. **Document policy format**: Specify `.github/quality-policy.yml` schema

### Week 1 Deliverables

- [ ] `repoq gate` command functional with exit codes
- [ ] Basic Q formula calculating correctly
- [ ] Unit tests for gate validation logic
- [ ] Policy YAML parser with validation

### Week 2 Deliverables

- [ ] GitHub Actions workflow tested on real PRs
- [ ] Hard constraints implemented and tested
- [ ] Gate failure reporting (terminal + JSON)
- [ ] Developer documentation draft

### Week 3 Deliverables

- [ ] Pre-push hook template
- [ ] Complete developer guide
- [ ] Performance benchmarks (analysis time)
- [ ] MVP release and announcement

---

## Success Metrics

### MVP Phase (T+3 weeks)
- ✅ Quality gate blocks ≥80% of quality-degrading PRs
- ✅ False positive rate <5%
- ✅ CI overhead <2 minutes per PR
- ✅ Developer satisfaction score ≥4/5

### Production Phase (T+12 weeks)
- ✅ Zero quality regressions merged to main
- ✅ Average Q score improves 10+ points over 3 months
- ✅ Gaming attempts detected and prevented (via ZAG PCQ)
- ✅ 90% of waivers are legitimate emergency cases

---

## Conclusion

The meta-optimizing quality loop is **architecturally sound** and **technically feasible** with RepoQ's existing infrastructure. The **MVP approach (Variant 2)** provides the fastest path to validation while minimizing risk.

**Recommendation**: Begin implementation following the integrated VDAD roadmap (see next section). Start with Phase 1 (Domain Immersion) while executing MVP deliverables, ensuring value-driven decisions at every step.

**Key Success Factor**: Maintain focus on core monotonicity guarantee in MVP, while systematically building stakeholder value alignment through VDAD process. Advanced features (ZAG gaming protection, weight adaptation, AI agents) emerge naturally from stakeholder value prioritization in Phases 2-3.

---

## VDAD Integration Roadmap

**Methodology**: Value-Driven Analysis and Design (VDAD) — a 7-step process for integrating human/ethical values into the development lifecycle ([ethical-se.github.io](https://ethical-se.github.io)).

**Key Principles**:
- **Stakeholder-centric**: All decisions traced back to stakeholder values
- **Iterative**: Each 6-month cycle refines domain understanding
- **AI-assisted**: LLM copilot supports analysis, design, and documentation
- **Formal foundations**: VDAD complements (not replaces) mathematical rigor from `formal-foundations-complete.md`

**Integration with RepoQ**: This VDAD roadmap runs in parallel with the tactical MVP/Production phases above, providing strategic direction and value validation.

---

### Phase 1: Domain Immersion & Stakeholder Mapping

**VDAD Steps**: Step 1 (Domain Analysis), Step 2 (Stakeholder Identification)

**Objective**: Gain deep understanding of RepoQ's domain and identify all stakeholders.

#### Tasks

**1.1 Domain Analysis**
- [ ] Study formal documentation (`formal-foundations-complete.md`, 14 theorems, 6 guarantees)
- [ ] Review tmp/ artifacts (77 files: meta-loop, ZAG, Any2Math integrations)
- [ ] Analyze existing codebase (64% coverage, TRS systems, VC certificates)
- [ ] Map domain concepts using Domain-Driven Design:
  - Core domain: Quality metrics (Q, PCQ, complexity, hotspots)
  - Supporting domains: TRS normalization, ontologies, VC certificates
  - Generic domains: Git integration, CLI, reporting
- **AI Copilot Role**: Summarize large documents, generate domain glossary, propose initial bounded contexts

**1.2 Context Modeling**
- [ ] Build Context Map showing system boundaries and relationships
- [ ] Create domain entity diagram (Project, File, Metric, Certificate, etc.)
- [ ] Define ubiquitous language for RepoQ (terms like "admission policy", "PCQ", "stratification")
- [ ] Document bounded contexts:
  - Analysis Context: Code parsing, metric calculation
  - Quality Context: Q scoring, gate decisions, PCQ/PCE
  - Ontology Context: Code/C4/DDD ontologies, semantic inference
  - Integration Context: CI/CD, GitHub Actions, CLI
- **AI Copilot Role**: Generate draft Context Map, suggest entity relationships, validate terminology consistency

**1.3 Stakeholder Mapping**
- [ ] Identify stakeholder groups:
  - **Developers**: Primary users of quality gates
  - **Team Leads/Managers**: Track quality trends, allocate improvement effort
  - **DevOps Engineers**: Integrate into CI/CD pipelines
  - **Open Source Community**: Contributors, adopters
  - **Researchers**: Formal methods, software engineering academics
  - **Ourselves**: Project maintainers
- [ ] Create stakeholder map with roles, responsibilities, and touchpoints
- [ ] For each group, document:
  - Goals (e.g., developers: fast feedback, managers: quality visibility)
  - Pain points (e.g., developers: cryptic error messages, managers: gaming metrics)
  - Expectations (e.g., DevOps: <2min CI overhead)
- **AI Copilot Role**: Generate stakeholder personas, cross-check stakeholder list with similar projects, suggest missing groups

**Deliverables**:
- Domain model document (bounded contexts, entities, ubiquitous language)
- Context Map diagram (Mermaid or C4 model)
- Stakeholder map with personas/roles (table or visual map)

---

### Phase 2: Value Elicitation & Prioritization

**VDAD Steps**: Step 3 (Value Identification), Step 4 (Value Prioritization)

**Objective**: Identify what each stakeholder group values and prioritize these values.

#### Tasks

**2.1 Value Identification**
- [ ] For each stakeholder group, elicit core values:
  - **Developers**: Fast feedback, actionable insights, transparency, fairness (no arbitrary blocks)
  - **Managers**: Quality visibility, gaming protection, team accountability
  - **DevOps**: Reliability, low maintenance, integration simplicity
  - **Community**: Openness, reproducibility, scientific rigor
  - **Researchers**: Formal correctness, innovation (proof-carrying certificates, TRS)
- [ ] Conduct value mapping workshop (with AI copilot as facilitator):
  - Use Stakeholder Value Map template ([ethical-se.github.io](https://ethical-se.github.io))
  - For each value, document:
    - **Value name**: e.g., "Transparency"
    - **Description**: "System explains why PR was blocked"
    - **Stakeholders**: Developers (high), Managers (medium)
    - **Examples**: Gate output shows ΔQ breakdown, PCE witness for improvement
- [ ] Create Value Register (spreadsheet or database) tracking all values
- **AI Copilot Role**: Extract values from existing documentation/issues, propose typical values for QA tools, structure Value Register

**2.2 Value Impact Mapping**
- [ ] Map each system feature/function to values it supports:
  - `repoq gate` → Values: Monotonicity, Transparency, Fast feedback
  - PCQ/PCE (ZAG) → Values: Gaming protection, Fairness, Accountability
  - Any2Math normalization → Values: Reproducibility, Correctness, Scientific rigor
  - Ontological intelligence → Values: Actionability, Insight depth
  - VC certificates → Values: Auditability, Trust, Traceability
- [ ] Identify value gaps: areas where stakeholder values are not addressed
- [ ] Create Value Impact Map diagram showing feature↔value connections
- **AI Copilot Role**: Auto-generate impact map from Value Register + feature list, highlight gaps, suggest new features for unmet values

**2.3 Value Prioritization**
- [ ] Define prioritization criteria:
  - **Stakeholder count**: How many groups care?
  - **Strategic alignment**: Does it support RepoQ's mission (formal quality assurance)?
  - **Impact**: High/medium/low effect on project success?
  - **Risk**: Does neglecting this value create ethical/legal issues?
- [ ] Score each value on criteria (e.g., 1-5 scale)
- [ ] Produce prioritized value list (Tier 1: critical, Tier 2: important, Tier 3: nice-to-have)
- [ ] Document rationale for each priority decision
- **AI Copilot Role**: Apply scoring rubric automatically, generate priority matrix, validate consistency of rankings

**Deliverables**:
- Value Register (comprehensive list with descriptions, stakeholders, priority)
- Value Impact Map (feature ↔ value connections)
- Prioritized value list with justifications

---

### Phase 3: Strategic Decisions & Requirements

**VDAD Steps**: Step 5 (Digitalization Decision), Step 6 (Requirements Elaboration)

**Objective**: Translate prioritized values into strategic decisions and concrete requirements.

#### Tasks

**3.1 Strategic Decisions (Digitalization Decision)**
- [ ] For each Tier 1 value, decide how to address it:
  - **Transparency** → Add detailed gate output with ΔQ breakdown, PCE witness
  - **Gaming protection** → Integrate ZAG PCQ (already in tmp/zag_repoq-finished/)
  - **Correctness** → Use Any2Math for deterministic normalization (tmp/repoq-any2math-integration/)
  - **Scientific rigor** → Publish formal proofs (formal-foundations-complete.md)
  - **Fast feedback** → Optimize analysis time, incremental processing
- [ ] Document strategic rationale for each decision:
  - **Context**: Why is this value important now?
  - **Decision**: What specific action/feature addresses it?
  - **Alternatives considered**: What other options were rejected and why?
- [ ] Record decisions in Strategic Decision Log (similar to ADR format)
- **AI Copilot Role**: Propose decision options, analyze trade-offs, draft decision records

**3.2 Ethical Requirements (IEEE 7000 EVR)**
- [ ] Formulate Ethical Value Requirements (EVR) for key values:
  - **Transparency EVR**: "System SHALL provide human-readable explanation for every gate rejection, including specific metrics that failed and recommended fixes"
  - **Fairness EVR**: "System SHALL NOT penalize developers for legitimate code complexity (e.g., implementing algorithms); complex code allowed if justified and well-tested"
  - **Gaming protection EVR**: "System SHALL detect and block attempts to artificially inflate Q score (e.g., via PCQ min-aggregator: all modules must meet threshold, not just average)"
  - **Privacy EVR**: "System SHALL NOT transmit repository contents to external services without explicit consent (all analysis local or self-hosted)"
- [ ] Link each EVR to one or more values in Value Register
- [ ] Ensure EVRs are verifiable (with acceptance criteria)
- **AI Copilot Role**: Generate EVR templates, check IEEE 7000 compliance, suggest verification methods

**3.3 Functional & Non-Functional Requirements**
- [ ] Update functional requirements based on strategic decisions:
  - FR1: `repoq gate` command with exit codes (0=pass, 1=fail)
  - FR2: Q metric calculation with configurable weights (.github/quality-policy.yml)
  - FR3: Hard constraints validation (tests, TODO, hotspots)
  - FR4: PCQ min-aggregator integration (ZAG)
  - FR5: PCE k-repair witness generation
  - FR6: Ontological intelligence (Code/C4/DDD pattern detection)
  - FR7: Self-application safety (stratification levels 0-2)
  - FR8: Any2Math normalization for deterministic metrics
  - ...
- [ ] Define NFRs (SMART criteria):
  - **Performance**: Analysis time ≤2 minutes for repos <1000 files, ≤5 minutes for <10000 files
  - **Reliability**: Gate false positive rate <5%, false negative rate <1%
  - **Usability**: Developer can understand gate failure in <30 seconds
  - **Security**: No credentials leaked in logs, no external data transmission
  - **Maintainability**: Code coverage ≥80%, documentation coverage 100%
  - **Compatibility**: Works with GitHub Actions, GitLab CI, local git hooks
- [ ] Validate requirements against Value Register (each requirement supports ≥1 value)
- **AI Copilot Role**: Generate SMART-formatted NFRs, cross-check requirements vs values, identify missing requirements

**Deliverables**:
- Strategic Decision Log (why we're building what)
- Ethical Value Requirements (EVR) document
- Updated Requirements Specification (FR + NFR)

---

### Phase 4: Architecture Design & Decision Recording

**VDAD Steps**: Step 7 (Architecture Design)

**Objective**: Design system architecture satisfying all requirements, with full traceability to values.

#### Tasks

**4.1 High-Level Architecture Design**
- [ ] Design component architecture using existing formal foundations:
  - **Core Engine**: Metric calculation, TRS normalization, Q scoring
  - **Gate Logic**: Admission policy evaluation, hard constraints
  - **Ontology Intelligence**: Code/C4/DDD analyzers, semantic inference (tmp/repoq-meta-loop-addons/)
  - **ZAG Integration**: PCQ/PCE module (tmp/zag_repoq-finished/)
  - **Any2Math Bridge**: Lean normalization adapter (tmp/repoq-any2math-integration/)
  - **Certificate Generator**: VC credential creation with proof-carrying evidence
  - **CLI**: Command-line interface (`gate`, `meta-self`, `any2math-normalize`)
  - **CI Integration**: GitHub Actions, GitLab CI runners
  - **Knowledge Base**: RDF store for ontologies, SPARQL endpoint
- [ ] Apply DDD tactical patterns:
  - Bounded contexts: Analysis, Quality, Ontology, Integration
  - Aggregates: Project (root), File, Metric, Certificate
  - Services: AnalysisService, GateService, OntologyService
  - Repositories: ProjectRepository (git abstraction)
- [ ] Create architecture diagram (C4 model recommended):
  - Context diagram: RepoQ system + external systems (Git, CI, LLM)
  - Container diagram: Major components and data flows
  - Component diagram (for complex containers): Internal modules
- **AI Copilot Role**: Generate draft C4 diagrams from component list, suggest DDD patterns, validate architectural consistency

**4.2 NFR Realization**
- [ ] For each NFR, design architectural mechanism:
  - **Performance NFR** → Caching layer (metrics, normalized artifacts), incremental analysis
  - **Reliability NFR** → Statistical noise filtering (ε-guard), test suite (80%+ coverage)
  - **Usability NFR** → Structured error messages, PCE witness in output
  - **Security NFR** → Read-only file access, no network calls (except opt-in LLM)
  - **Maintainability NFR** → Modular architecture, ADR log, comprehensive docs
- [ ] Document architectural tactics in architecture document (arc42 template)
- **AI Copilot Role**: Propose architectural tactics from patterns catalog, validate NFR coverage

**4.3 Architecture Decision Records (ADR)**
- [ ] Establish ADR log in `docs/architecture/decisions/`
- [ ] Create ADR for every significant decision:
  - **ADR-001**: Use BAML for AI agent (type-safe LLM outputs)
  - **ADR-002**: Choose RDFLib + Oxigraph for RDF storage (Python-native, standards-compliant)
  - **ADR-003**: Integrate Any2Math via subprocess (isolate Lean runtime)
  - **ADR-004**: Adopt arc42 for architecture documentation (comprehensive, proven)
  - **ADR-005**: Use Mermaid for diagrams (text-based, git-friendly, MkDocs-compatible)
  - **ADR-006**: Stratification levels 0-2 for self-analysis (prevents paradoxes per Theorem F)
  - **ADR-007**: PCQ min-aggregator for gaming protection (ZAG framework, Theorem C)
  - ...
- [ ] Use lightweight ADR format (MADR or Y-statements):
  ```markdown
  # ADR-001: Use BAML for AI Agent
  
  **Context**: Need type-safe, reliable AI agent for semantic analysis.
  
  **Decision**: Adopt BoundaryML BAML framework.
  
  **Rationale**: BAML provides DSL for LLM functions with compile-time type checking,
  reducing hallucination risk and improving testability.
  
  **Consequences**: +Type safety, +Testability, -Learning curve, -Vendor lock-in (mitigated by open-source)
  ```
- **AI Copilot Role**: Generate ADR drafts from verbal explanations, auto-fill ADR template, maintain ADR index

**4.4 AI Agent Design (BAML Integration)**
- [ ] Define AI agent responsibilities:
  - **Semantic Code Analysis**: Understand PR context beyond syntax (intent, patterns)
  - **Explanation Generation**: Translate gate failures into human-readable advice
  - **Improvement Suggestions**: Propose specific code changes (PCE witness augmentation)
  - **Anomaly Detection**: Flag unusual patterns (potential gaming, security issues)
- [ ] Design BAML functions for each responsibility:
  ```baml
  function AnalyzePRContext(diff: string, metrics: Metrics) -> PRContext {
    client GPT4
    prompt #"
      Analyze this git diff and metrics:
      
      Diff: {{ diff }}
      Metrics: {{ metrics }}
      
      Extract:
      - Intent: What is the developer trying to accomplish?
      - Patterns: What design patterns are used?
      - Risks: What could go wrong?
    "#
  }
  ```
- [ ] Specify agent boundaries (security, resource limits):
  - Read-only access to repository
  - Max 10 LLM calls per analysis (cost control)
  - Timeout: 30 seconds per function
  - No external network except LLM API
- [ ] Plan phased rollout:
  - **Phase 1**: Experimental mode (agent provides suggestions, no gate impact)
  - **Phase 2**: Advisory mode (agent suggestions shown in PR comments)
  - **Phase 3**: Active mode (agent detects gaming, can influence gate decision)
- **AI Copilot Role**: Generate BAML function stubs, validate function signatures, suggest safety constraints

**Deliverables**:
- Architecture document (arc42 format recommended)
- C4 diagrams (context, container, component)
- ADR log (comprehensive decision record)
- BAML agent specification (functions, boundaries, rollout plan)

---

### Phase 5: Implementation, Integration & Validation

**VDAD Step**: Implementation + Continuous Value Validation

**Objective**: Build system, integrate AI agent (when ready), validate against values.

#### Tasks

**5.1 Core Implementation**
- [ ] Implement priority 0 components (from tmp-artifacts-inventory.md):
  - Safety Guards: SelfApplicationGuard, ResourceLimiter (tmp/repoq-meta-loop-addons/trs/engine.py)
  - SHACL shapes: meta_loop.ttl → repoq/shapes/
  - Basic gate logic: repoq/gate.py (already exists, enhance with tmp/ components)
- [ ] Integrate ZAG PCQ/PCE (Priority 1):
  - Copy tmp/zag_repoq-finished/integrations/zag.py → repoq/integrations/
  - Add PCQ min-aggregator to repoq/quality.py
  - Implement witness generation in gate output
- [ ] Integrate Any2Math normalization (Priority 1):
  - Copy tmp/repoq-any2math-integration/ → repoq/integrations/any2math/
  - Add `--normalize any2math` flag to `repoq gate`
  - Enrich VC certificates with NormalizationEvidence
- [ ] Implement ontological intelligence (Priority 2):
  - Copy tmp/repoq-meta-loop-addons/ontologies/ → repoq/ontologies/
  - Implement SemanticInferenceEngine with SPARQL
  - Add pattern detection (5-7 patterns: MVC, Layered, Plugin, etc.)
- **AI Copilot Role**: Review PRs for adherence to architecture, suggest refactorings, generate unit test stubs

**5.2 AI Agent Deployment**
- [ ] Implement BAML functions from Phase 4 design
- [ ] Create agent wrapper service (HTTP API or CLI command)
- [ ] Test agent on historical PRs:
  - Verify semantic accuracy (manual review of 20+ PR analyses)
  - Measure false positive rate for gaming detection
  - Validate explanation quality (developer survey)
- [ ] Deploy in experimental mode:
  - Agent runs on all PRs but outputs to separate log
  - No impact on gate decisions
  - Collect feedback from developers
- [ ] Gradual rollout to advisory/active modes (if experimental succeeds)
- **AI Copilot Role**: Generate BAML test cases, validate LLM outputs, monitor agent performance metrics

**5.3 Comprehensive Testing**
- [ ] Unit tests (target: 80%+ coverage):
  - TRS engine: Termination, confluence, idempotence
  - Q metric: Correctness of formula, edge cases (empty repo, single file)
  - Gate logic: All combinations of hard constraints + Q threshold
  - PCQ/PCE: Min-aggregator, witness generation
  - Any2Math bridge: Normalization correctness, fallback mode
- [ ] Integration tests:
  - End-to-end PR simulation: git diff → analysis → gate decision → VC certificate
  - CI workflows: GitHub Actions, GitLab CI
  - Multi-repository scenarios
- [ ] NFR validation:
  - Performance benchmarks (measure analysis time on repos of varying sizes)
  - Stress tests (1000-file repo, 100-file PR diff)
  - Usability tests (developer survey on error message clarity)
- [ ] Value validation:
  - For each Tier 1 value, verify ≥1 test validates it:
    - Transparency: Test that gate output includes ΔQ breakdown
    - Gaming protection: Test that PCQ detects metric compensation
    - Correctness: Test that Any2Math produces deterministic results
- **AI Copilot Role**: Generate test cases from requirements, perform mutation testing, analyze coverage gaps

**5.4 Documentation & Review**
- [ ] Update all documentation:
  - Architecture document (reflect as-built architecture)
  - User guide (how to install, configure, use `repoq gate`)
  - Developer guide (how to extend analyzers, add patterns)
  - ADR log (record any implementation decisions)
- [ ] Conduct architecture review:
  - Check alignment with requirements (traceability matrix)
  - Validate NFR achievement (review test results)
  - Verify value satisfaction (for each value, show evidence it's addressed)
- [ ] AI self-audit:
  - Run `repoq meta-self` (stratified self-analysis, level 2)
  - Review findings: architectural patterns detected, quality score, improvement recommendations
  - Address any critical issues before release
- **AI Copilot Role**: Review documentation for completeness, generate traceability matrix, summarize audit findings

**5.5 Iteration Planning**
- [ ] Retrospective: What worked, what didn't?
  - Review against initial stakeholder values
  - Collect feedback from early adopters (if any)
  - Identify new values/requirements that emerged
- [ ] Plan next iteration (6-month cycle):
  - Re-run VDAD Step 1: Has domain understanding changed?
  - Update stakeholder map: New groups? Changed priorities?
  - Refresh Value Register: New values? Deprecated values?
  - Adjust architecture for new requirements
- [ ] Archive iteration artifacts:
  - Save Value Register, ADR log, architecture docs to version-tagged folder
  - Maintain historical record for future reference
- **AI Copilot Role**: Analyze usage metrics, survey feedback, propose next iteration themes

**Deliverables**:
- Working RepoQ system (MVP or production-ready depending on scope)
- Comprehensive test suite (80%+ coverage)
- Complete documentation (architecture, user guide, developer guide)
- Iteration retrospective report
- Next iteration plan

---

## VDAD-Aligned Success Metrics

### Phase 1 (Domain Immersion)
- ✅ Domain model document complete (bounded contexts, entities)
- ✅ Stakeholder map identifies ≥5 groups
- ✅ Context Map approved by all team members

### Phase 2 (Value Elicitation)
- ✅ Value Register contains ≥20 distinct values
- ✅ Each stakeholder group has ≥3 values identified
- ✅ Value Impact Map covers ≥80% of planned features

### Phase 3 (Requirements)
- ✅ All Tier 1 values translated into ≥1 requirement
- ✅ All EVRs have verifiable acceptance criteria
- ✅ NFRs meet SMART criteria (Specific, Measurable, Agreed, Realistic, Time-bound)

### Phase 4 (Architecture)
- ✅ Architecture satisfies all NFRs (validation documented)
- ✅ ADR log records ≥10 significant decisions
- ✅ C4 diagrams pass peer review

### Phase 5 (Implementation)
- ✅ Test coverage ≥80%
- ✅ All Tier 1 values validated by tests
- ✅ Self-audit (repoq meta-self) shows no critical issues
- ✅ Developer satisfaction ≥4/5 (if external users exist)

---

## Integration of VDAD with Existing Roadmap

**How VDAD phases align with MVP/Production timeline**:

| MVP/Production Phase | VDAD Phases | Key Integration Points |
|---------------------|-------------|------------------------|
| **Pre-MVP: Planning** | Phase 1-2 | Domain analysis informs feature prioritization; stakeholder values drive MVP scope |
| **MVP: Week 1-3** | Phase 3 | Requirements from Value Register → gate logic implementation |
| **Production: Week 4-8** | Phase 4 | Architecture design → ZAG/Any2Math integration decisions recorded in ADR |
| **Advanced: Week 8-12** | Phase 5 | AI agent deployment, ontological intelligence, comprehensive testing against values |
| **Post-Launch** | Iteration Planning | Retrospective feeds into next VDAD cycle (re-run Steps 1-7 with updated context) |

**Key Principle**: VDAD provides **strategic direction** (what to build and why), while MVP/Production phases provide **tactical execution** (how to build and when). Both run in parallel, informing each other.

---

## References & Methodology Sources

1. **Stefan Kapferer et al.** (2024). *Value-Driven Analysis and Design (VDAD) Process*. [ethical-se.github.io](https://ethical-se.github.io) — 7-step process for integrating human/ethical values into software development
2. **Olaf Zimmermann, Mirko Stocker** (2021-2024). *Design Practice Repository (DPR)*. [GitHub](https://github.com/socadk/design-practice-repository) — Agile architectural practices, ADR templates, SMART requirements
3. **RepoQ Project** (2025). *Formal Foundations Complete*. [GitHub](https://github.com/kirill-0440/repoq) — 14 theorems, 6 formal guarantees, 77 tmp/ artifacts
4. **BoundaryML** (2023). *BAML Framework*. [GitHub](https://github.com/BoundaryML/baml) — Type-safe AI agent DSL for reliable LLM workflows
5. **IEEE 7000-2021**. *Standard for Addressing Ethical Concerns during System Design*. — Framework for Ethical Value Requirements (EVR)

---
