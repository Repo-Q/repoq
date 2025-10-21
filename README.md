# RepoQ - Repository Quality Analysis

> ⚠️ **ACTIVE DEVELOPMENT**: This project is under active development and may contain breaking changes or unstable features. Use at your own risk in production environments.

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-57%20passing-orange)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-<10%25-red)](#roadmap)
[![Status](https://img.shields.io/badge/status-alpha-red)](https://github.com/kirill-0440/repoq)

Modern CLI tool for comprehensive Git repository quality analysis with semantic web export and CI/CD integration.

## Features

**Currently Available:**
- 📊 **Structure Analysis**: Files, modules, languages, LOC, dependencies  
- 📈 **Complexity Metrics**: Cyclomatic complexity, maintainability index
- 📚 **Git History**: Authorship, churn, temporal coupling
- 🔥 **Hotspots**: High-churn + high-complexity problem areas
- 🌐 **Semantic Export**: JSON-LD and RDF/Turtle with W3C ontologies
- 📊 **Graphs**: DOT/SVG dependency visualization

**In Development:**
- SHACL validation, Docker container, GitHub Actions
- Quality certificates, statistical coupling analysis

## Quick Start

```bash
# Install
pip install -e ".[full]"

# Analyze repository
repoq full ./my-project --format json

# Structure analysis
repoq structure ./my-project --md report.md

# Export for knowledge graphs  
repoq full ./my-project --format turtle > quality.ttl
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