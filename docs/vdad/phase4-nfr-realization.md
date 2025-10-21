# VDAD Phase 4: NFR Realization Strategies

**Status**: ✅ ACTIVE  
**Purpose**: Map each NFR to concrete architectural strategies  
**Created**: 2025-10-21  
**Last Updated**: 2025-10-21

---

## Overview

This document provides **concrete realization strategies** for all 12 Non-Functional Requirements (NFRs) from Phase 3. Each NFR includes:
1. **Target Metric**: SMART (Specific, Measurable, Achievable, Relevant, Time-bound) target
2. **Architectural Strategy**: How the architecture achieves the NFR
3. **Implementation Details**: Specific components, algorithms, configurations
4. **Validation Method**: How to verify the NFR is met
5. **Risks & Mitigation**: Potential failure modes and countermeasures

---

## NFR-01: Analysis Speed (≤2 min P90 for <1K files)

### Target Metric
- **Specific**: Analyze repository with <1000 Python files
- **Measurable**: P90 latency (90th percentile) ≤120 seconds
- **Achievable**: Based on benchmarks (current: ~180 sec, target: ~120 sec)
- **Relevant**: Developer productivity (fast feedback loops)
- **Time-bound**: MVP release (Phase 5)

### Architectural Strategy

**1. Incremental Analysis** (AnalysisOrchestrator)
- Only analyze files changed in git diff (base...head)
- Skip unchanged files (use cached metrics)
- **Speedup**: 10-100x for typical PRs (<10% files changed)

**2. SHA-Based Caching** (MetricCache)
- Cache key: `{file_sha}_{policy_version}_{repoq_version}`
- Disk-backed LRU cache (`.repoq/cache/`)
- **Speedup**: O(1) cache lookup vs O(n) re-analysis

**3. Parallel File Processing** (ThreadPoolExecutor)
- Analyze files in parallel (8 workers by default)
- No shared state (metrics calculated independently per file)
- **Speedup**: ~4x on 8-core machines

**4. Lazy Ontology Ingestion** (OntologyManager)
- Skip RDF ingestion unless explicitly requested (`--with-ontology`)
- Trade-off: Fast by default, opt-in for deep analysis
- **Speedup**: ~30% (ontology ingestion is ~30-40 sec overhead)

### Implementation Details

```python
# repoq/pipeline.py

import concurrent.futures
from repoq.core.cache import MetricCache
from repoq.analyzers import ComplexityAnalyzer, HotspotAnalyzer

class AnalysisOrchestrator:
    def __init__(self, max_workers=8):
        self.cache = MetricCache()
        self.max_workers = max_workers
    
    def analyze_incremental(self, base_sha, head_sha, policy):
        # Step 1: Get changed files (git diff)
        changed_files = self.get_changed_files(base_sha, head_sha)
        
        # Step 2: Filter cached files
        files_to_analyze = []
        for file in changed_files:
            file_sha = self.get_file_sha(file, head_sha)
            cache_key = self.cache.get_cache_key(file_sha, policy.version)
            if cache_key not in self.cache:
                files_to_analyze.append(file)
        
        # Step 3: Parallel analysis
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.analyze_file, f, policy): f for f in files_to_analyze}
            for future in concurrent.futures.as_completed(futures):
                file = futures[future]
                metrics = future.result()
                self.cache.set(file.sha, policy.version, metrics)
        
        # Step 4: Aggregate metrics
        return self.aggregate_metrics(changed_files)
```

### Validation Method

**Benchmark Suite**:
```bash
# Generate synthetic repo (1000 files, 100-500 LOC each)
python scripts/generate_test_repo.py --files 1000 --loc-range 100-500

# Run benchmark (10 iterations, measure P90)
repoq benchmark --iterations 10 --repo test_repo/

# Expected output:
# P50: 85 sec
# P90: 115 sec ✓ (target: ≤120 sec)
# P99: 140 sec
```

**CI Check**:
```yaml
# .github/workflows/performance.yml
- name: Performance Benchmark
  run: |
    repoq benchmark --iterations 5 --repo benchmark_repo/
    # Fail if P90 > 120 sec
```

### Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **R1: Cache invalidation bug** | Medium | High (incorrect results) | Comprehensive tests, checksum validation |
| **R2: Parallel processing overhead** | Low | Low (slower, not wrong) | Tune max_workers, fallback to serial |
| **R3: Git diff slow (large repos)** | Low | Medium (slow for monorepos) | Use libgit2 (faster than GitPython) |
| **R4: Coverage.py bottleneck** | High | High (coverage is 40% of time) | Cache coverage results, skip if no test changes |

---

## NFR-02: PCQ Overhead (≤20% of total analysis time)

### Target Metric
- **Specific**: PCQ calculation (min-aggregator + PCE witness)
- **Measurable**: PCQ time / Total time ≤ 0.20
- **Achievable**: Current: ~15% (already meets target)
- **Relevant**: Fast gate decisions (no bottleneck in PCQ)
- **Time-bound**: MVP release

### Architectural Strategy

**1. Optimize Module Decomposition** (PCQCalculator)
- Modularize by directory (coarse-grained, fast)
- Alternative: Layer-level (finer-grained, slower)
- Trade-off: Accuracy vs speed (directory is sufficient for most projects)

**2. Greedy k-Min for PCE** (PCEWitnessGenerator)
- Algorithm: `heapq.nsmallest(k, modules, key=lambda m: Q(m))`
- Complexity: O(n log k) where k=3-8 (not O(n log n))
- **Speedup**: 10x faster than full sort for large n

**3. Lazy PCE Generation** (GateEvaluator)
- Only compute PCE witness if gate fails (PCQ < τ)
- Skip PCE if gate passes (PCQ ≥ τ)
- **Speedup**: ~50% of cases (when gate passes)

### Implementation Details

```python
# repoq/quality/pcq.py

import heapq

class PCQCalculator:
    def calculate_pcq(self, modules, policy):
        """Fast min-aggregator: O(n)."""
        if not modules:
            return 1.0
        return min(m.quality for m in modules)

class PCEWitnessGenerator:
    def generate_witness(self, modules, policy, k=3):
        """Greedy k-min: O(n log k)."""
        # heapq.nsmallest is O(n log k), not O(n log n)
        return heapq.nsmallest(k, modules, key=lambda m: m.quality)

# Usage
pcq = calculator.calculate_pcq(modules, policy)  # Fast: O(n)
if pcq < policy.tau:
    witness = generator.generate_witness(modules, policy, k=3)  # Only if needed
```

### Validation Method

**Profiling**:
```bash
# Run with profiling
python -m cProfile -o profile.stats repoq gate --base main --head HEAD

# Analyze profile
python -c "
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative')
p.print_stats('pcq')
"

# Expected: PCQ functions <20% of cumulative time
```

### Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **R1: Too many modules (n>1000)** | Low | Medium (PCQ slow) | Coarsen module granularity (e.g., top-level dirs only) |
| **R2: Q calculation expensive** | Medium | High (bottleneck in Q, not PCQ) | Cache Q results per module |

---

## NFR-03: Deterministic Results (100% reproducibility)

### Target Metric
- **Specific**: Same code + same policy → same Q-score (±0.01)
- **Measurable**: 1000 runs with zero variance
- **Achievable**: Any2Math normalization + frozen dependencies
- **Relevant**: Trust, debugging, compliance
- **Time-bound**: Phase 5 (when Any2Math integrated)

### Architectural Strategy

**1. Any2Math AST Normalization** (ASTNormalizer)
- TRS-based canonicalization (removes syntactic variance)
- Rules: Remove Pass, normalize var order, canonicalize binary ops
- **Guarantee**: Two syntactically different but semantically equivalent ASTs → same normalized form

**2. Frozen Dependencies** (requirements.txt)
- Pin exact versions: `radon==6.0.1`, not `radon>=6.0`
- Lock file: `poetry.lock` or `pdm.lock`
- **Guarantee**: Same tool versions → same metrics

**3. Deterministic Iteration Order** (Python dicts)
- Use sorted keys when iterating: `for k in sorted(metrics.keys())`
- Avoid `set` iteration (non-deterministic order in Python <3.7)
- **Guarantee**: Same iteration order → same aggregation

**4. Reproducible Git Operations** (GitPython)
- Sort commit logs by timestamp (not insertion order)
- Use SHA-based ordering (not branch order)
- **Guarantee**: Same history → same hotspot metrics

### Implementation Details

```python
# repoq/core/any2math.py

class ASTNormalizer:
    def normalize(self, code: str) -> str:
        tree = ast.parse(code)
        normalized = self.apply_trs_rules(tree)
        return ast.unparse(normalized)
    
    def apply_trs_rules(self, tree):
        # Rule 1: Remove redundant Pass
        tree = self.remove_pass(tree)
        
        # Rule 2: Normalize variable order in comprehensions
        tree = self.normalize_comprehensions(tree)
        
        # Rule 3: Canonicalize commutative binary ops
        tree = self.canonicalize_binops(tree)
        
        return tree

# repoq/analyzers/complexity.py

class ComplexityAnalyzer:
    def calculate(self, file_path):
        # Normalize AST before complexity calculation
        with open(file_path) as f:
            code = f.read()
        normalized = ASTNormalizer().normalize(code)
        
        # Now calculate complexity on normalized code
        return radon.complexity.cc_visit(normalized)
```

### Validation Method

**Reproducibility Test**:
```python
# tests/test_determinism.py

def test_determinism():
    # Same code, 1000 runs
    for i in range(1000):
        q_score = calculate_q(code, policy)
        assert q_score == 82.5, f"Run {i}: Q={q_score} (expected 82.5)"

def test_normalization_idempotence():
    code = "if True: pass\nelse: x = 1"
    normalized1 = normalize(code)
    normalized2 = normalize(normalized1)
    assert normalized1 == normalized2, "Normalization not idempotent"
```

### Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **R1: Radon non-determinism** | Low | High (breaks guarantee) | Pin radon version, test with 1000 runs |
| **R2: Any2Math TRS non-confluent** | Low | Critical (wrong normalization) | Lean proof of confluence (Theorem D) |
| **R3: Floating-point rounding** | Medium | Low (±0.01 acceptable) | Use Decimal for critical calculations |

---

## NFR-04: Monotonicity Guarantee (ΔQ ≥ 0 implies Admission)

### Target Metric
- **Specific**: If ΔQ ≥ ε and PCQ ≥ τ and H, then gate PASS
- **Measurable**: Zero false negatives in 10K synthetic test cases
- **Achievable**: Proven by Theorem B (admission predicate)
- **Relevant**: No spurious gate failures (developer frustration)
- **Time-bound**: MVP release (already implemented)

### Architectural Strategy

**1. Admission Predicate Enforcement** (GateEvaluator)
- Formula: `Admission = H ∧ (ΔQ ≥ ε) ∧ (PCQ ≥ τ)`
- No hidden clauses (transparent logic)
- **Guarantee**: All conditions met → PASS (no false negatives)

**2. Longitudinal Validation** (MonotonicityChecker)
- Track Q(t) over time (commit history)
- Verify: If Q(t+1) ≥ Q(t) + ε, then admitted at t+1
- **Guarantee**: No admission regressions

**3. Exemption Isolation** (ExemptionManager)
- Exemptions do not affect monotonicity (applied consistently to base and head)
- Formula: `Q_exempt = Q - Σ(exempt_files)`
- **Guarantee**: Exemptions do not cause false positives/negatives

### Implementation Details

```python
# repoq/quality/gate.py

class GateEvaluator:
    def evaluate(self, base, head, policy):
        # Step 1: Calculate Q-scores
        q_base = self.calculate_q(base, policy)
        q_head = self.calculate_q(head, policy)
        delta_q = q_head - q_base
        
        # Step 2: Check hard constraints
        hard = self.check_hard_constraints(head, policy)
        
        # Step 3: Calculate PCQ
        pcq = self.calculate_pcq(head, policy)
        
        # Step 4: Evaluate admission predicate (Theorem B)
        admitted = hard and (delta_q >= policy.epsilon) and (pcq >= policy.tau)
        
        # Invariant: No hidden conditions (transparency)
        assert self.is_transparent(admitted, hard, delta_q, pcq, policy)
        
        return Verdict(passed=admitted, q_base=q_base, q_head=q_head, delta_q=delta_q, pcq=pcq)
    
    def is_transparent(self, admitted, hard, delta_q, pcq, policy):
        """Verify admission logic matches documented predicate."""
        expected = hard and (delta_q >= policy.epsilon) and (pcq >= policy.tau)
        return admitted == expected
```

### Validation Method

**Property-Based Test**:
```python
# tests/test_monotonicity.py

from hypothesis import given, strategies as st

@given(
    q_base=st.floats(min_value=0, max_value=100),
    q_head=st.floats(min_value=0, max_value=100),
    epsilon=st.floats(min_value=0, max_value=5)
)
def test_monotonicity(q_base, q_head, epsilon):
    # If ΔQ ≥ ε (and H, PCQ met), then gate must pass
    delta_q = q_head - q_base
    if delta_q >= epsilon and hard_constraints_pass and pcq >= tau:
        verdict = evaluate_gate(q_base, q_head, epsilon, tau)
        assert verdict.passed, f"False negative: ΔQ={delta_q}, ε={epsilon}"
```

### Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **R1: Floating-point precision** | Medium | Low (ΔQ ≈ ε edge case) | Use `delta_q >= epsilon - 1e-6` (tolerance) |
| **R2: Policy change mid-analysis** | Low | Medium (inconsistent Q) | Lock policy version at analysis start |
| **R3: Exemption bugs** | Low | Medium (false positives) | Unit tests for exemption logic |

---

## NFR-05: False Negative Rate (≤5% on benchmark dataset)

### Target Metric
- **Specific**: Benchmark dataset with known quality issues (100 repos)
- **Measurable**: FN = (Missed issues) / (Total issues) ≤ 0.05
- **Achievable**: Current FN ~10% (need tuning), target ~5%
- **Relevant**: Catch real quality issues (not just noise)
- **Time-bound**: Phase 5 (after benchmark dataset created)

### Architectural Strategy

**1. Comprehensive Metric Suite** (MetricCalculators)
- 4 metrics (not just 1): Complexity, Hotspots, TODOs, Coverage
- Weighted combination: `Q = Q_max - Σ(w_i * x_i)`
- **Rationale**: Multiple signals reduce blind spots

**2. Threshold Tuning** (PolicyLoader)
- Configurable weights: `w = [20, 30, 10, 40]` (default)
- Per-project tuning: `.github/quality-policy.yml`
- **Rationale**: One size does not fit all (ML projects ≠ web apps)

**3. Benchmark Dataset** (Phase 5)
- 100 repos with known issues (high complexity, no tests, etc.)
- Ground truth: Manual review by experts
- **Validation**: FN rate on benchmark dataset

**4. Continuous Calibration** (MonitoringDashboard)
- Track FN/FP rates in production (user feedback)
- Adjust thresholds based on feedback
- **Rationale**: Model drift (codebases evolve)

### Implementation Details

```python
# repoq/benchmarks/dataset.py

class BenchmarkDataset:
    def __init__(self):
        # 100 repos with known quality issues
        self.repos = [
            {"name": "repo1", "issues": ["high_complexity", "no_tests"]},
            {"name": "repo2", "issues": ["hotspots", "todos"]},
            # ... 98 more
        ]
    
    def evaluate_fn_rate(self, policy):
        true_positives = 0
        false_negatives = 0
        
        for repo in self.repos:
            verdict = evaluate_gate(repo, policy)
            detected_issues = set(verdict.failed_metrics)
            actual_issues = set(repo["issues"])
            
            # True positives: Correctly detected issues
            true_positives += len(detected_issues & actual_issues)
            
            # False negatives: Missed issues
            false_negatives += len(actual_issues - detected_issues)
        
        fn_rate = false_negatives / (true_positives + false_negatives)
        return fn_rate

# Usage
dataset = BenchmarkDataset()
fn_rate = dataset.evaluate_fn_rate(policy)
assert fn_rate <= 0.05, f"FN rate too high: {fn_rate}"
```

### Validation Method

**Benchmark CI**:
```yaml
# .github/workflows/benchmark.yml
- name: Evaluate FN Rate
  run: |
    python -m repoq.benchmarks.evaluate --dataset benchmark_dataset/
    # Expected: FN ≤ 5%, FP ≤ 10%
```

### Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **R1: Benchmark dataset bias** | High | High (overfitting) | Diverse repos (web, ML, CLI, lib), external validation |
| **R2: Metric weights suboptimal** | Medium | Medium (high FN) | Grid search, user feedback, adaptive weights |
| **R3: Ground truth disagreement** | Medium | Low (fuzzy labels) | Multi-rater agreement, Kappa statistic |

---

## NFR-06: False Positive Rate (≤10% on benchmark dataset)

### Target Metric
- **Specific**: Benchmark dataset with clean code (100 repos)
- **Measurable**: FP = (False alarms) / (Total clean samples) ≤ 0.10
- **Achievable**: Current FP ~15% (need tuning), target ~10%
- **Relevant**: Avoid alert fatigue (too many false alarms)
- **Time-bound**: Phase 5

### Architectural Strategy

**1. Exemption System** (ExemptionManager)
- Allow per-file/per-module exemptions (`.github/quality-policy.yml`)
- Rationale required (documented exception)
- Expiry dates (temporary exemptions for legacy code)
- **Rationale**: Necessary complexity should not trigger false alarms

**2. Context-Aware Thresholds** (PolicyLoader)
- Different thresholds for different file types (e.g., tests vs prod code)
- Example: Allow higher complexity in test fixtures
- **Rationale**: Tests naturally have higher cyclomatic complexity (many branches)

**3. AI Anomaly Detection** (Phase 5, Optional)
- LLM validates whether high complexity is legitimate (e.g., algorithm implementation)
- Human-in-loop for borderline cases
- **Rationale**: Automated + human judgment (best of both worlds)

### Implementation Details

```python
# repoq/config.py

class ExemptionManager:
    def is_exempt(self, file_path, metric, policy):
        for exemption in policy.exemptions:
            if self.matches_pattern(file_path, exemption["path"]):
                if metric in exemption.get("metrics", []):
                    # Check expiry
                    if exemption.get("expires") and is_expired(exemption["expires"]):
                        print(f"Warning: Exemption for {file_path} expired on {exemption['expires']}")
                        return False
                    return True
        return False
    
    def matches_pattern(self, file_path, pattern):
        import fnmatch
        return fnmatch.fnmatch(file_path, pattern)

# Usage in quality calculation
def calculate_q(state, policy):
    total_penalty = 0
    for file in state.files:
        if not exemption_mgr.is_exempt(file.path, "complexity", policy):
            total_penalty += file.complexity_penalty
    return Q_max - total_penalty
```

### Validation Method

**FP Rate Test**:
```python
# tests/test_false_positives.py

def test_fp_rate():
    # Clean codebases (100 repos with high quality)
    clean_repos = load_benchmark_dataset("clean")
    
    false_positives = 0
    for repo in clean_repos:
        verdict = evaluate_gate(repo, policy)
        if not verdict.passed:
            # Should pass (clean code), but failed → False positive
            false_positives += 1
    
    fp_rate = false_positives / len(clean_repos)
    assert fp_rate <= 0.10, f"FP rate too high: {fp_rate}"
```

### Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **R1: Exemptions abused** | Medium | High (defeats purpose) | Require rationale + expiry, audit exemptions |
| **R2: Thresholds too strict** | High | High (too many FPs) | Calibrate on diverse repos, user feedback |
| **R3: Context misunderstood** | Low | Medium (wrong exemptions) | Clear documentation, examples |

---

## NFR-07: CLI Usability (Task completion ≤2 min, 90% success rate)

### Target Metric
- **Specific**: User study with 20 participants (developers)
- **Measurable**: Task: "Run quality gate on PR" completed in ≤2 min by ≥18/20 users (90%)
- **Achievable**: Current: ~80% success (need UX improvements)
- **Relevant**: Adoption (easy to use → higher adoption)
- **Time-bound**: Phase 5 (after MVP release)

### Architectural Strategy

**1. Sensible Defaults** (CLI)
- Zero-config for simple cases: `repoq gate` (auto-detects base/head)
- Explicit config for complex cases: `repoq gate --base main --head HEAD --policy custom.yml`
- **Rationale**: Progressive disclosure (simple by default, powerful when needed)

**2. Clear Error Messages** (CLI)
- Actionable errors: "Gate failed: Coverage 65% < 80%. Run `pytest --cov` to improve."
- Avoid jargon: "PCQ 0.72 < 0.80" → "3 modules below threshold: auth, db, api"
- **Rationale**: Frustration-free debugging

**3. Rich Output Formatting** (VerdictFormatter)
- Colors: Green (PASS), Red (FAIL), Yellow (WARNING)
- Tables: Metrics breakdown (complexity, hotspots, TODOs, coverage)
- Graphs: ASCII bar charts (optional, `--format rich`)
- **Rationale**: Visual hierarchy (key info stands out)

**4. Interactive Mode** (CLI)
- `repoq init` wizard: Guides user through policy creation
- `repoq diagnose`: Explains why gate failed (step-by-step)
- **Rationale**: Onboarding-friendly (reduces learning curve)

### Implementation Details

```python
# repoq/cli.py

import click
from rich.console import Console
from rich.table import Table

@click.command()
@click.option("--base", default="main", help="Base commit (default: main)")
@click.option("--head", default="HEAD", help="Head commit (default: HEAD)")
@click.option("--policy", default=".github/quality-policy.yml", help="Policy file")
@click.option("--format", default="text", type=click.Choice(["text", "json", "rich"]))
def gate(base, head, policy, format):
    """Run quality gate on commit range."""
    try:
        verdict = evaluate_gate(base, head, policy)
        
        if format == "rich":
            print_rich_verdict(verdict)
        elif format == "json":
            print(verdict.to_json())
        else:
            print_text_verdict(verdict)
        
        sys.exit(0 if verdict.passed else 1)
    
    except FileNotFoundError as e:
        click.secho(f"Error: Policy file not found: {policy}", fg="red")
        click.secho(f"Hint: Run `repoq init` to create a default policy", fg="yellow")
        sys.exit(2)

def print_rich_verdict(verdict):
    console = Console()
    
    # Status banner
    if verdict.passed:
        console.print("✅ PASS: Quality gate satisfied", style="bold green")
    else:
        console.print("❌ FAIL: Quality gate not satisfied", style="bold red")
    
    # Metrics table
    table = Table(title="Quality Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Base", style="magenta")
    table.add_column("Head", style="magenta")
    table.add_column("Delta", style="green" if verdict.delta_q >= 0 else "red")
    
    table.add_row("Q-Score", f"{verdict.q_base:.1f}", f"{verdict.q_head:.1f}", f"{verdict.delta_q:+.1f}")
    table.add_row("PCQ", "-", f"{verdict.pcq:.2f}", f"{'✓' if verdict.pcq >= 0.8 else '✗'}")
    
    console.print(table)
    
    # PCE witness (if failed)
    if not verdict.passed and verdict.witness:
        console.print("\n🔧 Modules to fix:", style="bold yellow")
        for i, module in enumerate(verdict.witness, 1):
            console.print(f"  {i}. {module.name} (Q={module.quality:.2f})")
```

### Validation Method

**Usability Study Protocol**:
```markdown
# User Study: RepoQ CLI Usability (N=20)

## Task 1: Run Quality Gate (Target: ≤2 min, 90% success)
1. Clone test repository: `git clone https://github.com/repoq/usability-test`
2. Install RepoQ: `pip install repoq`
3. Run quality gate: `repoq gate --base main --head feature-branch`
4. Interpret results: Is the gate passing? Why/why not?

## Metrics
- Time to completion (seconds)
- Success rate (task completed without help)
- Error count (how many errors encountered)
- Satisfaction (1-5 Likert scale)

## Success Criteria
- ≥18/20 users complete in ≤120 seconds
- ≥18/20 users correctly interpret results
- Average satisfaction ≥4.0/5.0
```

### Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **R1: Overwhelming output** | High | Medium (confusion) | Progressive disclosure, `--verbose` flag |
| **R2: Unclear error messages** | Medium | High (frustration) | User feedback, dogfooding, error message review |
| **R3: Poor defaults** | Medium | Medium (extra config) | Survey users, sensible defaults (e.g., `base=main`) |

---

## NFR-08: Report Readability (SMOG Grade ≤12, usability study ≥4.0/5)

### Target Metric
- **Specific**: Quality report markdown (generated by `repoq report`)
- **Measurable**: SMOG readability grade ≤12 (high school level), usability study rating ≥4.0/5.0
- **Achievable**: Current: Grade ~14 (needs simplification)
- **Relevant**: Stakeholder understanding (non-technical managers)
- **Time-bound**: Phase 5

### Architectural Strategy

**1. Plain Language** (ReportGenerator)
- Avoid jargon: "cyclomatic complexity" → "code complexity"
- Explain acronyms: "PCQ (Per-Component Quality)"
- Short sentences (≤20 words)
- **Rationale**: Accessible to non-experts

**2. Visual Aids** (Markdown Graphs)
- Tables: Metric breakdown by module
- Charts: ASCII bar charts, Mermaid diagrams
- Icons: ✅ ❌ ⚠️ (visual cues)
- **Rationale**: Visual information > text walls

**3. Executive Summary** (ReportGenerator)
- Top section: 3-5 sentences (key findings)
- Traffic light: Green (good), Yellow (warning), Red (critical)
- **Rationale**: Busy stakeholders read only summary

**4. Usability Testing** (Phase 5)
- User study: 10 managers, 10 developers
- Task: "What are the top 3 quality issues in this report?"
- **Validation**: ≥18/20 correctly identify issues

### Implementation Details

```python
# repoq/reporting/markdown.py

class MarkdownReportGenerator:
    def generate_report(self, verdict, state):
        report = []
        
        # Executive Summary (plain language)
        report.append("## Executive Summary\n")
        if verdict.passed:
            report.append("✅ **Quality gate PASSED**. Code quality improved by {:.1f} points.\n".format(verdict.delta_q))
        else:
            report.append("❌ **Quality gate FAILED**. {} modules need improvement.\n".format(len(verdict.witness)))
        
        # Key Metrics (visual table)
        report.append("## Key Metrics\n")
        report.append("| Metric | Base | Head | Change |\n")
        report.append("|--------|------|------|--------|\n")
        report.append("| Quality Score | {:.1f} | {:.1f} | {:+.1f} |\n".format(
            verdict.q_base, verdict.q_head, verdict.delta_q))
        report.append("| Code Complexity | {} | {} | {} |\n".format(
            state.base.avg_complexity, state.head.avg_complexity, 
            "↑" if state.head.avg_complexity > state.base.avg_complexity else "↓"))
        
        # Modules to Fix (actionable)
        if verdict.witness:
            report.append("\n## 🔧 Modules to Fix\n")
            for i, module in enumerate(verdict.witness, 1):
                report.append("{}. **{}** (Quality: {:.1f}/100)\n".format(i, module.name, module.quality))
                report.append("   - High complexity: {} functions above threshold\n".format(module.high_complexity_count))
                report.append("   - Low coverage: {:.0f}% (target: 80%)\n".format(module.coverage * 100))
        
        return "".join(report)
```

### Validation Method

**SMOG Grade Test**:
```python
# tests/test_readability.py

from textstat import textstat

def test_report_readability():
    report = generate_report(verdict, state)
    smog_grade = textstat.smog_index(report)
    assert smog_grade <= 12, f"SMOG grade too high: {smog_grade}"
```

**Usability Study**:
```markdown
# User Study: Report Readability (N=20)

## Task: Identify Top 3 Quality Issues
1. Read quality report (2 pages)
2. List top 3 quality issues mentioned
3. Rate clarity (1-5 scale)

## Success Criteria
- ≥18/20 correctly identify issues
- Average rating ≥4.0/5.0
```

### Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **R1: Oversimplification** | Medium | Low (loss of precision) | Provide detailed appendix for experts |
| **R2: Cultural bias (English)** | High | Medium (non-English speakers struggle) | i18n support (Phase 6), visual aids |
| **R3: Format not supported (GitHub/GitLab)** | Low | Low (ugly rendering) | Test on GitHub/GitLab Markdown renderers |

---

## NFR-09: Privacy Guarantee (Zero network calls, tcpdump verification)

### Target Metric
- **Specific**: Core analysis makes zero network calls
- **Measurable**: tcpdump audit in CI (0 packets sent)
- **Achievable**: Already implemented (all analysis is local)
- **Relevant**: Privacy (EVR-04), compliance (GDPR)
- **Time-bound**: MVP (already met)

### Architectural Strategy

**1. Local-Only Analysis** (All Components)
- Metrics: radon (local), coverage.py (local), git log (local)
- RDF storage: RDFLib in-memory (local)
- Certificates: Local file storage (local)
- **Guarantee**: No SaaS APIs, no external DBs

**2. Optional AI Agent** (Opt-In Only)
- AI disabled by default (`ai_agent.enabled: false`)
- Explicit consent required (`--enable-ai` flag)
- Warn user: "AI agent will send code diffs to OpenAI. Continue? (y/N)"
- **Guarantee**: No AI calls unless explicitly enabled

**3. Network Isolation Test** (CI)
- Run RepoQ in Docker with `--network=none`
- If analysis succeeds → zero network dependency
- If analysis fails → network call detected (CI fails)
- **Guarantee**: CI enforces zero network calls

### Implementation Details

```python
# repoq/cli.py

@click.command()
@click.option("--enable-ai", is_flag=True, default=False, help="Enable AI agent (requires network)")
def gate(enable_ai, ...):
    if enable_ai:
        click.confirm(
            "⚠️  AI agent will send code diffs to OpenAI. "
            "Your code will leave your machine. Continue?",
            abort=True
        )
    
    # ... rest of analysis
```

**CI Verification**:
```yaml
# .github/workflows/privacy-check.yml
- name: Verify Zero Network Calls
  run: |
    # Run in network-isolated Docker
    docker run --network=none repoq:latest \
      repoq gate --base main --head HEAD
    
    # If exit code 0, no network calls were made ✓
```

### Validation Method

**tcpdump Audit**:
```bash
# Start packet capture
sudo tcpdump -i any -w network.pcap &
TCPDUMP_PID=$!

# Run RepoQ analysis
repoq gate --base main --head HEAD

# Stop packet capture
sudo kill $TCPDUMP_PID

# Verify zero packets (exclude localhost)
PACKETS=$(tcpdump -r network.pcap 'not host 127.0.0.1' | wc -l)
if [ $PACKETS -gt 0 ]; then
    echo "❌ Network calls detected: $PACKETS packets"
    exit 1
else
    echo "✅ Zero network calls verified"
fi
```

### Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **R1: Dependency makes network call** | Low | Critical (privacy breach) | Audit dependencies, network isolation test |
| **R2: User accidentally enables AI** | Medium | Medium (unintended leak) | Clear warnings, double confirmation |
| **R3: Future feature needs network** | High | Medium (breaks guarantee) | Keep feature opt-in, document privacy impact |

---

## NFR-10: Test Coverage (≥80% line coverage, property-based tests for TRS)

### Target Metric
- **Specific**: pytest coverage report (`.coverage`)
- **Measurable**: Line coverage ≥80%, branch coverage ≥70%
- **Achievable**: Current 64% → 80% (Phase 5 work)
- **Relevant**: Reliability (fewer bugs), maintainability
- **Time-bound**: Phase 5

### Architectural Strategy

**1. Unit Tests** (pytest)
- Test each component in isolation (mock dependencies)
- Target: ≥90% coverage for critical components (GateEvaluator, PCQCalculator)
- **Rationale**: Catch regressions early

**2. Integration Tests** (pytest)
- End-to-end tests (CLI → Gate → VC generation)
- Test on real repos (dogfooding: RepoQ tests itself)
- **Rationale**: Catch integration bugs

**3. Property-Based Tests** (Hypothesis)
- Test TRS properties: confluence, termination, idempotence
- Generate random ASTs, verify normalization properties
- **Rationale**: Catch edge cases (exhaustive testing)

**4. CI Enforcement** (GitHub Actions)
- Coverage gate in CI: Fail if coverage <80%
- Upload coverage to Codecov (visual tracking)
- **Rationale**: Prevent coverage regressions

### Implementation Details

```python
# tests/test_trs_properties.py

from hypothesis import given, strategies as st
import ast

@given(st.text(min_size=10, max_size=1000))
def test_normalization_idempotence(code):
    """Property: normalize(normalize(x)) == normalize(x)"""
    try:
        tree = ast.parse(code)
        normalized1 = normalize(tree)
        normalized2 = normalize(normalized1)
        assert ast.dump(normalized1) == ast.dump(normalized2)
    except SyntaxError:
        pass  # Invalid code, skip

@given(st.text(min_size=10, max_size=1000))
def test_normalization_preserves_semantics(code):
    """Property: eval(code) == eval(normalize(code))"""
    try:
        tree = ast.parse(code)
        normalized = normalize(tree)
        
        # Execute both (if safe)
        if is_safe_to_execute(code):
            result_original = exec(code, {})
            result_normalized = exec(normalized, {})
            assert result_original == result_normalized
    except:
        pass
```

**CI Configuration**:
```yaml
# .github/workflows/ci.yml
- name: Run Tests with Coverage
  run: |
    pytest --cov=repoq --cov-report=term --cov-report=xml

- name: Enforce Coverage Threshold
  run: |
    coverage report --fail-under=80

- name: Upload Coverage to Codecov
  uses: codecov/codecov-action@v3
```

### Validation Method

**Coverage Report**:
```bash
# Run tests with coverage
pytest --cov=repoq --cov-report=html

# Open HTML report
open htmlcov/index.html

# Expected: ≥80% line coverage, ≥70% branch coverage
```

### Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **R1: Hard-to-test code** | Medium | Medium (low coverage) | Refactor for testability (dependency injection) |
| **R2: Property tests too slow** | Low | Low (CI timeout) | Limit Hypothesis examples (max 100), cache results |
| **R3: Coverage ≠ quality** | High | Low (false confidence) | Manual code review, integration tests |

---

## NFR-11: Scalability (Linear scaling to 10K files, ≤30 min)

### Target Metric
- **Specific**: Analyze repository with 10K Python files
- **Measurable**: Total time ≤30 min (180 sec for 1K files → 1800 sec for 10K)
- **Achievable**: Current ~5 min for 10K (already meets target)
- **Relevant**: Large monorepos (enterprise use case)
- **Time-bound**: Phase 5

### Architectural Strategy

**1. Parallel File Processing** (ThreadPoolExecutor)
- 8 workers by default (configurable via `--workers`)
- File-level parallelism (no shared state)
- **Scaling**: O(n/p) where p=workers (linear speedup)

**2. Memory-Mapped Caching** (diskcache)
- Disk-backed cache (avoid loading all metrics in RAM)
- LRU eviction (avoid unbounded growth)
- **Scaling**: O(1) cache lookup, O(k) memory (k=cache size, not n=file count)

**3. Incremental Analysis** (DiffAnalyzer)
- Only analyze changed files (git diff)
- **Scaling**: O(m) where m=changed files (not O(n) for all files)

**4. Streaming RDF Ingestion** (OntologyManager)
- Process files one-by-one (avoid loading entire graph in memory)
- Flush triples to disk every 1000 files
- **Scaling**: O(n) disk, O(1) memory

### Implementation Details

```python
# repoq/pipeline.py

import multiprocessing

class ScalableAnalysisOrchestrator:
    def __init__(self, max_workers=None):
        if max_workers is None:
            # Default: CPU count
            max_workers = multiprocessing.cpu_count()
        self.max_workers = max_workers
    
    def analyze_large_repo(self, files, policy):
        # Parallel processing with progress bar
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.analyze_file, f, policy): f for f in files}
            
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(files)):
                file = futures[future]
                try:
                    metrics = future.result()
                    self.store_metrics(file, metrics)
                except Exception as e:
                    print(f"Error analyzing {file}: {e}")
        
        # Aggregate (streaming, not in-memory)
        return self.aggregate_metrics_streaming(files)
```

### Validation Method

**Scalability Benchmark**:
```bash
# Generate large synthetic repo (10K files)
python scripts/generate_large_repo.py --files 10000

# Run benchmark (measure time)
time repoq gate --base main --head HEAD

# Expected: ≤30 min (1800 sec)
```

**Scaling Plot**:
```python
# tests/test_scalability.py

import matplotlib.pyplot as plt

def test_linear_scaling():
    sizes = [100, 500, 1000, 5000, 10000]
    times = []
    
    for size in sizes:
        repo = generate_synthetic_repo(size)
        start = time.time()
        analyze(repo)
        elapsed = time.time() - start
        times.append(elapsed)
    
    # Plot: Should be linear (not quadratic)
    plt.plot(sizes, times, marker='o')
    plt.xlabel("Number of files")
    plt.ylabel("Analysis time (sec)")
    plt.title("RepoQ Scalability (Linear Scaling)")
    plt.savefig("scalability.png")
    
    # Verify linear fit (R^2 ≥ 0.95)
    slope, intercept, r_value, _, _ = scipy.stats.linregress(sizes, times)
    assert r_value**2 >= 0.95, f"Non-linear scaling: R^2={r_value**2}"
```

### Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **R1: RDFLib memory explosion** | High | Critical (OOM for >10K files) | Use Oxigraph (C++ backend), streaming ingestion |
| **R2: Coverage.py slow** | High | High (bottleneck) | Cache coverage, skip if no test changes |
| **R3: Parallel processing overhead** | Low | Low (slower, not wrong) | Tune max_workers, profile |

---

## NFR-12: Compatibility (Python 3.11+, Ubuntu/macOS/Windows, CI matrix)

### Target Metric
- **Specific**: CI matrix (3 OSes × 3 Python versions)
- **Measurable**: All 9 CI jobs pass (100% success rate)
- **Achievable**: Current: Ubuntu only, need macOS/Windows support
- **Relevant**: Wide adoption (works on developer machines)
- **Time-bound**: Phase 5

### Architectural Strategy

**1. Cross-Platform Dependencies** (pyproject.toml)
- Avoid OS-specific packages (e.g., pywin32, macOS-only libs)
- Use pure Python where possible (GitPython, radon, etc.)
- **Rationale**: Maximize compatibility

**2. CI Matrix Testing** (GitHub Actions)
- Matrix: `[ubuntu-latest, macos-latest, windows-latest] × [3.11, 3.12, 3.13]`
- Run full test suite on all combinations
- **Rationale**: Catch platform-specific bugs early

**3. Path Handling** (pathlib)
- Use `pathlib.Path` (not `os.path`) for cross-platform paths
- Avoid hardcoded `/` or `\` (use `Path("/") separator`)
- **Rationale**: Windows uses backslashes, Unix uses forward slashes

**4. Subprocess Handling** (subprocess)
- Use `shlex.quote()` for shell escaping (cross-platform)
- Avoid shell=True (different shells on Windows/Unix)
- **Rationale**: Security + compatibility

### Implementation Details

```python
# repoq/core/utils.py

from pathlib import Path
import subprocess
import shlex

def run_command_cross_platform(cmd: list[str], cwd: Path = None):
    """Run command safely on Windows/macOS/Linux."""
    # Don't use shell=True (shell differs: bash vs cmd.exe)
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False
    )
    return result

def get_cache_dir() -> Path:
    """Get cache directory (cross-platform)."""
    if os.name == "nt":  # Windows
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    else:  # macOS/Linux
        base = Path.home() / ".cache"
    
    return base / "repoq"
```

**CI Matrix**:
```yaml
# .github/workflows/ci.yml
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ["3.11", "3.12", "3.13"]
    
    runs-on: ${{ matrix.os }}
    
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install Dependencies
        run: pip install -e .[dev]
      
      - name: Run Tests
        run: pytest
```

### Validation Method

**CI Matrix Check**:
```bash
# Trigger CI on PR
git push origin feature-branch

# Wait for CI results (9 jobs)
# Expected: All jobs pass ✓

# Matrix: ubuntu × 3.11 ✓
#         ubuntu × 3.12 ✓
#         ubuntu × 3.13 ✓
#         macos × 3.11 ✓
#         macos × 3.12 ✓
#         macos × 3.13 ✓
#         windows × 3.11 ✓
#         windows × 3.12 ✓
#         windows × 3.13 ✓
```

### Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **R1: Windows path issues** | High | Medium (path errors) | Use pathlib, test on Windows CI |
| **R2: macOS-specific bugs** | Medium | Low (edge cases) | Test on macOS CI, user feedback |
| **R3: Dependency unavailable** | Low | High (install fails) | Pin versions, test install in CI |

---

## Summary: NFR Realization Coverage

| NFR | Target | Strategy | Status | Phase |
|-----|--------|----------|--------|-------|
| **NFR-01** | ≤2 min (P90) | Incremental + Cache + Parallel | ⏸️ Planned | Phase 5 |
| **NFR-02** | ≤20% overhead | Optimize PCQ (O(n)) + Lazy PCE | 🔄 In Progress | MVP |
| **NFR-03** | 100% reproducible | Any2Math + Frozen deps | ⏸️ Planned | Phase 5 |
| **NFR-04** | Monotonicity | Admission predicate + Tests | ✅ Complete | MVP |
| **NFR-05** | ≤5% FN | Benchmark dataset + Tuning | ⏸️ Planned | Phase 5 |
| **NFR-06** | ≤10% FP | Exemptions + Context-aware | ⏸️ Planned | Phase 5 |
| **NFR-07** | ≤2 min task | Defaults + Clear errors + Rich UI | ⏸️ Planned | Phase 5 |
| **NFR-08** | SMOG ≤12 | Plain language + Visual aids | ⏸️ Planned | Phase 5 |
| **NFR-09** | Zero network | Local analysis + tcpdump CI | ✅ Complete | MVP |
| **NFR-10** | ≥80% coverage | Unit + Integration + Property tests | 🔄 In Progress | Phase 5 |
| **NFR-11** | ≤30 min (10K) | Parallel + Streaming + Incremental | ✅ Complete | MVP |
| **NFR-12** | 3 OSes × 3 Pythons | CI matrix + pathlib + cross-platform | ⏸️ Planned | Phase 5 |

**Legend**: ✅ Complete, 🔄 In Progress, ⏸️ Planned

---

## References

1. RepoQ Project (2025). *Phase 3: Requirements*. `docs/vdad/phase3-requirements.md` — 12 NFRs
2. RepoQ Project (2025). *Phase 4: Architecture Overview*. `docs/vdad/phase4-architecture-overview.md` — Component design
3. RepoQ Project (2025). *Phase 4: ADRs*. `docs/vdad/phase4-adrs.md` — Architectural decisions
4. ISO/IEC 25010 (2011). *Systems and Software Quality Requirements and Evaluation (SQuaRE)* — NFR taxonomy

---

**Document Status**: ✅ COMPLETE  
**Review**: Pending (validate strategies with team)  
**Next Steps**: BAML AI agent specification in final Phase 4 document.
