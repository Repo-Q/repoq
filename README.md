# RepoQ - Repository Quality Analysis

> **ontoMBVE**: Ontology-based Model-Based Validation Engineering  
> First system combining formal ontologies, SHACL validation, and proof-carrying evidence for software quality.

> ⚠️ **ACTIVE DEVELOPMENT**: This project is under active development and may contain breaking changes or unstable features. Use at your own risk in production environments.

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![CI](https://github.com/kirill-0440/repoq/workflows/CI/badge.svg)](https://github.com/kirill-0440/repoq/actions/workflows/ci.yml)
[![SHACL](https://github.com/kirill-0440/repoq/workflows/SHACL%20Semantic%20Validation/badge.svg)](https://github.com/kirill-0440/repoq/actions/workflows/shacl-validation.yml)
[![Tests](https://img.shields.io/badge/tests-408%20passing-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-62%25-yellowgreen)](tests/)
[![Docker](https://img.shields.io/badge/docker-161MB-blue)](https://hub.docker.com/r/kirill0440/repoq)
[![Status](https://img.shields.io/badge/status-beta-orange)](https://github.com/kirill-0440/repoq)
[![Methodology](https://img.shields.io/badge/methodology-ontoMBVE-purple)](docs/methodology/ontoMBVE.md)

**RepoQ** implements **ontoMBVE** (Ontology-based Model-Based Validation Engineering) — a novel methodology for software quality assurance combining:

- 🧬 **Formal Ontologies** (RDF/OWL: CODE, DDD, SPDX)
- 🔍 **SHACL Validation** (declarative quality constraints)
- 📜 **Proof-Carrying Evidence** (PCE witnesses + anti-gaming PCQ)
- 🔬 **Formal Verification** (Lean4 proofs, planned)

See [Methodology Documentation](docs/methodology/ontoMBVE.md) for details.

## Features

**Currently Available:**

- 🆕 **Workspace Management (Phase 1)**: `.repoq/` directory for reproducible analysis
  - Automatic workspace initialization on every run
  - `manifest.json` with commit SHA + ontology checksums
  - Traceability for audits and debugging (FR-10, Theorem A)
  - See [Phase 1 docs](docs/migration/phase1-workspace.md)
- 📊 **Structure Analysis**: Files, modules, languages, LOC, dependencies  
- 📈 **Complexity Metrics**: Cyclomatic complexity, maintainability index
- 📚 **Git History**: Authorship, churn, temporal coupling
- 🔥 **Hotspots**: High-churn + high-complexity problem areas
- 🌐 **Semantic Export**: JSON-LD and RDF/Turtle with W3C ontologies
- 📊 **Graphs**: DOT/SVG dependency visualization
- 🔧 **Refactoring Plan**: Automated actionable tasks based on PCE algorithm
- ⚙️ **Quality Gates**: CI/CD-ready quality comparison and admission predicates
- ✅ **SHACL Validation**: Semantic constraint checking with CI/CD integration
- 🔄 **Meta-Loop Ontologies**: Self-analysis with stratified reflection (meta, test, trs, quality, docs)
- 🧪 **Test Coverage Export**: pytest coverage → RDF/Turtle (test:TestCase, test:Coverage)
- 🔀 **TRS Rules Extraction**: Normalization rules → RDF/Turtle (trs:Rule, trs:RewriteSystem)
- 📈 **Quality Recommendations**: ΔQ-based prioritization → RDF/Turtle (quality:Recommendation)
- 🔁 **Self-Validation**: Meta-loop closure with circular dependency detection (meta:SelfAnalysis)
- 🆕 **Extended Ontologies (Phase 0.5)**: 5 new domain-specific ontologies with OWL2/SHACL validation:
  - 🧪 **test.ttl**: Testing & coverage (PropertyTest, ContractTest, ConceptCoverage) - 5 issue types
  - 🔒 **security.ttl**: Vulnerabilities & secrets (CVE, SecretLeak, CVSS scoring) - 7 issue types
  - 🏛️ **arch.ttl**: Architecture layers (Hexagonal/Clean/Layered patterns, DAG enforcement) - 6 issue types
  - 📜 **license.ttl**: License compliance (SPDX integration, directional compatibility rules) - 6 issue types
  - 🔌 **api.ttl**: API contracts (semver enforcement, breaking change detection) - 5 issue types

**In Development:**

- Quality certificates, statistical coupling analysis
- SPARQL query endpoint, GraphViz RDF visualization

## Quick Start

```bash
# Install
pip install -e ".[full]"

# Analyze repository
repoq analyze ./my-project -o quality.jsonld --md report.md

# Generate refactoring plan
repoq refactor-plan quality.jsonld --top-k 10 -o refactoring-plan.md

# Quality gate for CI/CD
repoq gate --base main --head HEAD --strict

# Self-analysis (dogfooding)
repoq meta-self --level 1 -o meta-analysis.jsonld
```

## Refactoring Plan Generation

RepoQ can automatically generate **actionable refactoring tasks** using the PCE (Proof of Correct Execution) algorithm:

```bash
# Analyze project first
repoq analyze . -o baseline.jsonld

# Generate top-5 refactoring tasks
repoq refactor-plan baseline.jsonld --top-k 5

# Export as Markdown
repoq refactor-plan baseline.jsonld -o plan.md

# Export as JSON for CI/CD
repoq refactor-plan baseline.jsonld --format json -o tasks.json

# Generate GitHub Issues format
repoq refactor-plan baseline.jsonld --format github -o issues.json
```

**Output includes:**

- 🎯 **Priority-ranked tasks** (critical/high/medium/low)
- 📈 **Expected ΔQ improvement** per task
- ⏱️ **Effort estimates** (15 min to 8 hours)
- 📋 **Specific recommendations** (e.g., "split into smaller functions")
- 📊 **Current metrics** (complexity, LOC, TODOs, issues)
- 🆕 **Per-Function Recommendations** (NEW!): Identifies exact functions to refactor with line numbers

### Per-Function Metrics (NEW in v0.4.0)

RepoQ now captures **detailed per-function complexity metrics**, enabling targeted refactoring:

**What's captured:**

- Function name and cyclomatic complexity (CCN)
- Lines of code (LOC), parameter count
- Line range (start/end) for quick navigation
- Token count and max nesting depth

**Example output:**

```markdown
### Task #3: repoq/cli.py
**Priority**: 🔴 CRITICAL
**Expected ΔQ**: +108.0 points
**Estimated effort**: 4-8 hours

**Issues**:
- High cyclomatic complexity (26.0)
- Large file (1535 LOC)

**Recommendations**:
1. 🎯 Refactor function `_run_command` (CCN=26, lines 593-772) → split complex logic
2. 🎯 Refactor function `_run_trs_verification` (CCN=16, lines 775-843) → split complex logic
3. 🎯 Refactor function `_handle_refactor_plan_output` (CCN=13, lines 1446-1530) → split complex logic
4. 📏 Consider splitting file (1535 LOC) into smaller modules (<300 LOC)
```

**Benefits:**

- ✅ Know **exactly which function** to refactor (no manual analysis needed!)
- ✅ Jump directly to problematic code (line numbers provided)
- ✅ Prioritized by complexity (top-3 most complex functions first)
- ✅ Better ΔQ estimates (function-level granularity)

**Old approach** (file-level only):

```text
❌ "Reduce complexity from 26.0 to <10"  
   (Which function? Where? Need to run lizard manually...)
```

**New approach** (per-function):

```text
✅ "Refactor function `_run_command` (CCN=26, lines 593-772)"  
   (Exact target, no guesswork!)
```

## Semantic Web Export (Phase 2)

RepoQ generates **rich RDF/Turtle data** with 6 semantic enrichment layers:

```bash
# Export with all enrichment layers
repoq analyze . --ttl-output analysis.ttl \
  --enrich-meta \
  --enrich-test-coverage \
  --enrich-trs-rules \
  --enrich-quality-recommendations \
  --enrich-self-analysis

# SHACL validation against ontologies
python -c "
from repoq.core.rdf_export import validate_shapes
result = validate_shapes(project, 'repoq/shapes/')
print(f'Conforms: {result[\"conforms\"]}')
"
```

**Enrichment Layers:**

1. **Meta-Ontology** (`meta:SelfAnalysis`): Stratified self-analysis with Russell's paradox guards
2. **Test Coverage** (`test:TestCase`, `test:Coverage`): pytest coverage → RDF triples
3. **TRS Rules** (`trs:Rule`, `trs:RewriteSystem`): Normalization rules with confluence tracking
4. **Quality Recommendations** (`quality:Recommendation`): ΔQ-based refactoring priorities
5. **Self-Validation** (`meta:SelfAnalysis`): Circular dependency detection, universe violations
6. **Base Analysis** (`repo:Project`, `repo:File`): Structure, complexity, dependencies

**SPARQL Query Example:**

```sparql
# Find top-5 recommendations by ΔQ
SELECT ?rec ?file ?deltaQ ?priority
WHERE {
  ?rec a quality:Recommendation ;
       quality:deltaQ ?deltaQ ;
       quality:priority ?priority ;
       quality:targetsFile ?file .
}
ORDER BY DESC(?deltaQ)
LIMIT 5
```

## Ontology Validation (Phase 0.5)

RepoQ uses **OntologistAgent** for automated ontology validation with 5-gate quality checks:

```bash
# Validate ontology for analyzer
python -c "
from repoq.ontologies.ontologist_agent import OntologistAgent, AnalyzerMetadata

metadata = AnalyzerMetadata(
    name='SecurityAnalyzer',
    ontology='security.ttl',
    rdf_namespace='http://example.org/vocab/security#',
    issue_types=['ExposedAPIKey', 'VulnerableDependency', ...]
)

agent = OntologistAgent()
report = agent.validate_for_analyzer(metadata)
print(report.summary())  # ✅ Passed (5 gates checked)
"
```

**5 Validation Gates:**

1. **Ontology Exists**: File parseable as Turtle/RDF
2. **Issue Types Defined**: All analyzer issue types have OWL classes
3. **No Cycles**: Class hierarchy is acyclic (DAG enforcement)
4. **Namespace Isolation**: No collisions with other ontologies
5. **Property Consistency**: Domains/ranges defined and valid

**Integration with AnalyzerRegistry** (coming in Phase 1):

```python
from repoq.core.registry import AnalyzerRegistry

# Registration automatically validates ontology
@AnalyzerRegistry.register(
    ontology="security.ttl",
    issue_types=["ExposedAPIKey", "VulnerableDependency"]
)
class SecurityAnalyzer(BaseAnalyzer):
    pass  # If ontology invalid, registration fails (fail-fast)
```

**OML Formalization** (see `repoq/ontologies/FORMALIZATION.md`):

All 5 ontologies have formal OML specifications with Lean4 invariants:

- **arch.ttl**: `layer_hierarchy_acyclic` theorem (well-founded recursion)
- **license.ttl**: `compatibility_not_symmetric` proof (MIT→GPL ≠ GPL→MIT)
- **security.ttl**: `cvss_valid` constraint (CVSS ∈ [0,10])
- **api.ttl**: `breaking_change_requires_major_bump` (semver enforcement)

## CI/CD Integration

```yaml
# .github/workflows/quality.yml
- name: Quality Analysis
  run: |
    pip install repoq[full]
    repoq full . --format json > quality.json
    repoq structure . --format markdown > QUALITY_REPORT.md

# .github/workflows/shacl-validation.yml (automatic)
- name: SHACL Semantic Validation
  run: |
    repoq analyze . --ttl-output analysis.ttl --enrich-meta
    python -c "from repoq.core.rdf_export import validate_shapes; ..."
```

## Output Example

```json
{
  "@context": "https://field33.com/ontologies/repoq/",
  "@type": "QualityAnalysis",
  "project": {
    "name": "my-project",
    "linesOfCode": 15420,
    "overallScore": 7.8
  },
  "hotspots": [
    {
      "file": "src/core/processor.py",
      "churnScore": 0.89,
      "complexityScore": 23,
      "riskLevel": "high"
    }
  ]
}
```

## Roadmap

**✅ Phase 1 (COMPLETE)**: Core analysis, refactoring plans, quality gates, CI/CD integration  
**✅ Phase 2 (COMPLETE)**: Meta-loop ontologies, RDF export, SHACL validation, self-analysis  
**🚧 Phase 3 (In Progress)**: SPARQL endpoint, GraphViz RDF visualization, quality certificates  
**📅 Phase 4 (Planned)**: Statistical coupling, SBOM security, ML-based recommendations

## Configuration

Create `.repoq.yaml`:

```yaml
analysis:
  include_patterns: ["**/*.py", "**/*.js"]
  exclude_patterns: ["**/test_*", "**/node_modules/**"]
complexity:
  cyclomatic_threshold: 15
export:
  default_format: "json"
  semantic_annotations: true
```

## Contributing

Priority areas: test coverage, Docker container, performance optimization.

```bash
git clone https://github.com/kirill-0440/repoq.git
cd repoq
pip install -e ".[full,dev]"
python -m pytest --cov=repoq tests/
```

## Documentation

Complete docs: **https://kirill-0440.github.io/repoq/**

## License

MIT License - see [LICENSE](LICENSE) file.
