# RepoQ - Repository Quality Analysis

> ⚠️ **ACTIVE DEVELOPMENT**: This project is under active development and may contain breaking changes or unstable features. Use at your own risk in production environments.

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![CI](https://github.com/kirill-0440/repoq/workflows/CI/badge.svg)](https://github.com/kirill-0440/repoq/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-229%20passing-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-63%25-yellow)](#phase-55-coverage)
[![Docker](https://img.shields.io/badge/docker-161MB-blue)](https://hub.docker.com/r/kirill0440/repoq)
[![Status](https://img.shields.io/badge/status-beta-orange)](https://github.com/kirill-0440/repoq)

Modern CLI tool for comprehensive Git repository quality analysis with semantic web export and CI/CD integration.

## Features

**Currently Available:**
- 📊 **Structure Analysis**: Files, modules, languages, LOC, dependencies  
- 📈 **Complexity Metrics**: Cyclomatic complexity, maintainability index
- 📚 **Git History**: Authorship, churn, temporal coupling
- 🔥 **Hotspots**: High-churn + high-complexity problem areas
- 🌐 **Semantic Export**: JSON-LD and RDF/Turtle with W3C ontologies
- 📊 **Graphs**: DOT/SVG dependency visualization
- 🔧 **Refactoring Plan**: Automated actionable tasks based on PCE algorithm
- ⚙️ **Quality Gates**: CI/CD-ready quality comparison and admission predicates

**In Development:**
- SHACL validation, Docker container, GitHub Actions
- Quality certificates, statistical coupling analysis

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

Example task:
```markdown
### Task #1: repoq/analyzers/structure.py
**Priority**: 🔴 CRITICAL
**Expected ΔQ**: +218.0 points
**Estimated effort**: 4-8 hours

**Issues**:
- High cyclomatic complexity (48.0)

**Recommendations**:
1. Reduce complexity from 48.0 to <10 (split into smaller functions)
```

## CI/CD Integration

```yaml
# .github/workflows/quality.yml
- name: Quality Analysis
  run: |
    pip install repoq[full]
    repoq full . --format json > quality.json
    repoq structure . --format markdown > QUALITY_REPORT.md
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

**T+30 (Production Ready)**: 80% test coverage, Docker, GitHub Actions, SHACL validation  
**T+60 (Semantic Certs)**: Quality certificates, PR bot, SPARQL queries  
**T+90 (Advanced Analytics)**: Statistical coupling, SBOM security, ML patterns

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