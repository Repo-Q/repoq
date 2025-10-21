# RepoQ - Practical Repository Quality Analysis

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-57%20passing-orange)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-<10%25-red)](#roadmap)
[![Docs](https://img.shields.io/badge/docs-mkdocs-blue)](https://kirill-0440.github.io/repoq/)

> **Modern CLI tool for comprehensive Git repository quality analysis** with semantic web export (JSON-LD, RDF/Turtle) and CI/CD integration.

RepoQ provides **practical code quality insights** through structural analysis, complexity metrics, Git history patterns, and semantic web-compatible exports for enterprise integration.

## 🎯 Core Features

### ✅ **Currently Available**
- **📊 Structure Analysis**: Files, modules, languages, LOC, dependencies
- **📈 Complexity Metrics**: Cyclomatic complexity (Lizard), maintainability index (Radon)  
- **📚 Git History**: Authorship, code churn, temporal coupling between files
- **🔥 Hotspots**: Automatic identification of problem areas (churn × complexity)
- **🐛 Quality Markers**: Detection of TODO/FIXME/HACK/Deprecated comments
- **✅ Test Integration**: JUnit XML parsing with OSLC QM mapping
- **🌐 Semantic Export**: JSON-LD and RDF/Turtle with W3C ontologies
- **📊 Dependency Graphs**: DOT/SVG visualization of coupling and dependencies
- **🔄 Quality Diff**: Compare analysis results for regression tracking

### 🚧 **In Development** (See [Roadmap](#roadmap))
- SHACL validation and quality certificates
- Docker container and GitHub Actions
- Incremental analysis and caching
- Statistical coupling significance testing
- SBOM/SPDX vulnerability integration

## 🚀 Quick Start

### Installation

```bash
# Basic installation
pip install -e .

# Full installation with all analyzers
pip install -e ".[full]"

# Development setup
pip install -e ".[full,dev]"
```

**Optional Dependencies:**
- `pydriller` — Detailed Git history analysis
- `lizard` — Multi-language cyclomatic complexity
- `radon` — Python maintainability metrics  
- `graphviz` — SVG graph generation
- `rdflib` — RDF/Turtle export
- `pyshacl` — SHACL validation (planned)

### Basic Usage

```bash
# Full analysis of local repository
repoq full ./my-project --format json

# Structure analysis only
repoq structure ./my-project --md report.md

# History and hotspots analysis
repoq history ./my-project --since "2024-01-01"

# Complexity analysis with thresholds
repoq complexity ./my-project --threshold 15

# Export as RDF/Turtle for semantic integration
repoq full ./my-project --format turtle > quality.ttl
```

### CI/CD Integration

```yaml
# .github/workflows/quality.yml
name: Code Quality Analysis
on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Full history for temporal analysis
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install RepoQ
        run: pip install repoq[full]
        
      - name: Run Quality Analysis
        run: |
          repoq full . --format json > quality.json
          repoq structure . --format markdown > QUALITY_REPORT.md
          
      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: quality-analysis
          path: |
            quality.json
            QUALITY_REPORT.md
```

## 📊 Output Formats

### JSON-LD (Semantic Web Compatible)

```json
{
  "@context": "https://field33.com/ontologies/repoq/",
  "@type": "QualityAnalysis",
  "project": {
    "@type": "Project",
    "name": "my-project",
    "languages": ["python", "javascript"],
    "linesOfCode": 15420,
    "files": 127
  },
  "metrics": {
    "@type": "QualityMetrics", 
    "overallScore": 7.8,
    "complexityScore": 8.2,
    "maintainabilityScore": 7.5,
    "testCoverage": 0.65
  },
  "hotspots": [
    {
      "@type": "Hotspot",
      "file": "src/core/processor.py",
      "churnScore": 0.89,
      "complexityScore": 23,
      "riskLevel": "high"
    }
  ]
}
```

### RDF/Turtle (Knowledge Graph)

```turtle
@prefix repoq: <https://field33.com/ontologies/repoq/> .
@prefix prov: <http://www.w3.org/ns/prov#> .

<project:my-project> a repoq:Project ;
    repoq:hasLanguage "python", "javascript" ;
    repoq:linesOfCode 15420 ;
    repoq:fileCount 127 ;
    repoq:overallQuality 7.8 .

<hotspot:processor.py> a repoq:Hotspot ;
    repoq:inFile "src/core/processor.py" ;
    repoq:churnScore 0.89 ;
    repoq:complexityScore 23 ;
    repoq:riskLevel "high" .
```

## 🔧 Configuration

Create `.repoq.yaml` in your project root:

```yaml
# RepoQ Configuration
analysis:
  include_patterns: ["**/*.py", "**/*.js", "**/*.ts"]
  exclude_patterns: ["**/test_*", "**/node_modules/**", "**/__pycache__/**"]
  max_file_size_mb: 10

complexity:
  cyclomatic_threshold: 15
  cognitive_threshold: 25
  
history:
  max_commits: 1000
  since_days: 365
  
export:
  default_format: "json"
  include_graphs: true
  semantic_annotations: true

cache:
  enabled: true
  directory: ".repoq_cache"
  ttl_hours: 24
```

## � Use Cases

### For Development Teams
- **Code Review Assistance**: Identify complexity hotspots and quality trends
- **Technical Debt Tracking**: Monitor quality metrics over time
- **Refactoring Prioritization**: Focus on high-churn, high-complexity areas
- **Architecture Analysis**: Understand coupling patterns and dependencies

### For CI/CD Pipelines  
- **Quality Gates**: Automated quality thresholds in PR workflows
- **Regression Detection**: Compare quality metrics between commits
- **Report Generation**: Automated quality reports for stakeholders
- **Semantic Integration**: Export to enterprise knowledge graphs

### For Engineering Organizations
- **Portfolio Analysis**: Cross-project quality insights and benchmarking
- **Standards Compliance**: Ensure coding standards across teams
- **Risk Assessment**: Identify maintenance risks and bus factor issues
- **Data-Driven Decisions**: Quality metrics for architecture and resource planning

## 🛠️ Supported Analyzers

| Analyzer | Languages | Metrics | Status |
|----------|-----------|---------|---------|
| **Built-in** | All | Files, LOC, dependencies | ✅ Stable |
| **Lizard** | 30+ (C/C++/Java/Python/JS/etc.) | Cyclomatic complexity | ✅ Stable |
| **Radon** | Python | Maintainability index, Halstead | ✅ Stable |
| **PyDriller** | Git repos | History, churn, coupling | ✅ Stable |
| **Graphviz** | All | Dependency visualization | ✅ Stable |
| **Tree-sitter** | 40+ | AST-based analysis | 🚧 Planned |

### Graceful Degradation
If optional analyzers are not installed, RepoQ continues with available features:
- Missing `lizard`: Skips complexity analysis, reports basic metrics only
- Missing `radon`: No maintainability index for Python files  
- Missing `pydriller`: Limited to current state analysis (no history)
- Missing `graphviz`: No graph generation, data still available in JSON

## 🗺️ Roadmap {#roadmap}

### 🎯 **Phase 1: Production Ready** (T+30 days)
**Goal**: Stable, tested, containerized tool ready for daily use

- [ ] **Test Coverage**: 80%+ coverage with golden snapshots and property-based tests
- [ ] **SHACL Validation**: Core shapes for Project/Module/File/Contributor validation
- [ ] **Container & CI**: Dockerfile + GitHub Action for consistent deployment
- [ ] **Reference Examples**: 2-3 OSS repository analyses as golden standards
- [ ] **Performance**: Caching, incremental analysis, `--since` filters
- [ ] **Documentation**: API reference, troubleshooting, configuration guide

**Acceptance Criteria**: Green CI, valid JSON-LD/RDF exports, containerized deployment

### 🔬 **Phase 2: Semantic Certification** (T+60 days)  
**Goal**: Verifiable quality certificates and enterprise integration

- [ ] **Canonical Context**: Stable JSON-LD `@context` with versioned ontologies
- [ ] **SHACL Rules**: Derived properties and quality inferences  
- [ ] **Quality Certificates**: W3C Verifiable Credentials for projects/modules/files
- [ ] **PR Integration**: Bot comments with quality insights and certificates
- [ ] **SPARQL Queries**: Standard queries for common quality questions
- [ ] **Enterprise Export**: OSLC QM/CM compatibility testing

**Acceptance Criteria**: Certificates in artifacts, PR bot works, SPARQL endpoints functional

### 🚀 **Phase 3: Advanced Analytics** (T+90 days)
**Goal**: Statistical rigor and optimization guidance

- [ ] **ZAG Integration**: PCQ/PCE/Manifest with fairness curves and AHR metrics
- [ ] **Statistical Coupling**: PMI, φ-coefficient, χ²-p-value for significant relationships
- [ ] **SBOM Security**: SPDX SBOM generation with CVE/OSV vulnerability mapping
- [ ] **Optimization Engine**: k-repair suggestions for measurable quality improvements
- [ ] **Advanced Visualization**: Interactive dashboards and temporal trend analysis
- [ ] **ML Pattern Recognition**: Automated architectural pattern detection

**Acceptance Criteria**: ZAG manifests validate, k-repair suggestions proven effective

### 🔮 **Future Vision** (T+180+ days)
- **Self-Improving Analysis**: Feedback loops for accuracy improvement
- **Cross-Language Intelligence**: Universal architectural concepts
- **Predictive Analytics**: Quality trend forecasting and early warning systems
- **Developer Experience**: IDE integrations and real-time quality feedback

## 🤝 Contributing

RepoQ welcomes contributions! Current priority areas:

### **High Priority** (Phase 1)
- **Test Coverage**: Unit tests for parsers, golden snapshots for exports
- **Performance**: Caching mechanisms and incremental analysis
- **Documentation**: Examples, tutorials, API documentation
- **SHACL Shapes**: Validation schemas for core quality concepts

### **Medium Priority** (Phase 2-3)
- **Language Support**: Additional complexity analyzers and AST parsers
- **Integrations**: IDE plugins, dashboard connectors, CI/CD templates
- **Visualization**: Enhanced graphs and interactive quality dashboards
- **Security Analysis**: SAST integration and vulnerability correlation

### Development Setup

```bash
# Clone and setup development environment
git clone https://github.com/kirill-0440/repoq.git
cd repoq
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[full,dev]"

# Run tests and quality checks
python -m pytest tests/ -v
ruff check repoq/
ruff format repoq/

# Generate test coverage report
python -m pytest --cov=repoq --cov-report=html tests/
```

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

RepoQ builds upon excellent open source tools:
- **[Lizard](https://github.com/terryyin/lizard)** for multi-language complexity analysis
- **[Radon](https://github.com/rubik/radon)** for Python maintainability metrics
- **[PyDriller](https://github.com/ishepard/pydriller)** for Git history analysis
- **[rdflib](https://github.com/RDFLib/rdflib)** for semantic web capabilities
- **[NetworkX](https://github.com/networkx/networkx)** for graph analysis

Special thanks to the semantic web and software engineering research communities for foundational concepts and standards.

---

**Ready to improve your code quality?** 🚀

[⭐ Star us on GitHub](https://github.com/kirill-0440/repoq) | [📖 Documentation](https://kirill-0440.github.io/repoq/) | [🐛 Report Issues](https://github.com/kirill-0440/repoq/issues) | [💬 Discussions](https://github.com/kirill-0440/repoq/discussions)

## 🎯 Use Cases

### For Developers
- **Architecture Validation**: Ensure design principles are followed
- **Pattern Discovery**: Identify beneficial architectural patterns automatically
- **Quality Assessment**: Multi-dimensional quality scoring with semantic context
- **Refactoring Guidance**: Ontology-driven improvement suggestions

### For Teams  
- **Code Reviews**: Semantic analysis for architectural consistency
- **Documentation**: Auto-generated architecture diagrams and domain models
- **Technical Debt**: Identify and prioritize quality issues with domain context
- **Knowledge Transfer**: Formal capture of architectural intent and patterns

### For Organizations
- **Portfolio Analysis**: Cross-project architectural insights and patterns
- **Standards Compliance**: Automated verification of architectural principles
- **Quality Metrics**: Comprehensive quality dashboards with semantic understanding
- **Risk Assessment**: Identify architectural anti-patterns and technical debt

## 📊 Example Output

When RepoQ analyzes a project, it provides rich semantic insights:

```json
{
  "@context": "https://field33.com/ontologies/analysis/",
  "@type": "AnalysisResult", 
  "ontological_analysis": {
    "detected_patterns": [
      {
        "pattern": "Strategy Pattern",
        "location": "src/analyzers/",
        "confidence": 0.95,
        "benefits": ["extensibility", "testability"]
      }
    ],
    "domain_model": {
      "bounded_contexts": [
        {
          "name": "Analysis Domain",
          "entities": ["Project", "AnalysisResult"],
          "value_objects": ["ComplexityScore", "QualityMetrics"]
        }
      ]
    }
  },
  "quality_metrics": {
    "overall_score": 8.7,
    "architecture_score": 9.2,
    "domain_modeling_score": 8.3
  }
}
```

## � Documentation

Comprehensive documentation available at: **[docs.repoq.dev](https://kirill-0440.github.io/repoq/)**

- **[Installation Guide](https://kirill-0440.github.io/repoq/getting-started/installation/)** - Complete setup instructions
- **[User Guide](https://kirill-0440.github.io/repoq/user-guide/usage/)** - Comprehensive usage examples  
- **[Ontological Intelligence](https://kirill-0440.github.io/repoq/ontology/intelligence/)** - Deep dive into semantic analysis
- **[Meta-Quality Loop](https://kirill-0440.github.io/repoq/ontology/meta-loop/)** - Self-understanding system
- **[API Reference](https://kirill-0440.github.io/repoq/api/reference/)** - Complete Python and REST API docs

## 🏗️ Architecture

RepoQ's revolutionary architecture combines multiple advanced technologies:

```mermaid
graph TB
    A[Code Analysis] --> B[Structural Analysis]
    B --> C[Ontological Intelligence]
    C --> D[Pattern Recognition] 
    D --> E[Domain Modeling]
    E --> F[Quality Synthesis]
    F --> G[Semantic Export]
    
    H[TRS Framework] --> I[Normalization]
    I --> J[Confluence Proofs]
    J --> K[Safe Transformations]
    
    L[Meta-Quality Loop] --> M[Self-Analysis]
    M --> N[Stratified Application]
    N --> O[Continuous Improvement]
```

### Core Components

- **🔍 Analyzers**: Multi-language structure, complexity, and history analysis
- **🧠 Ontology Engine**: Triple ontology system with cross-domain inference
- **⚡ TRS Framework**: Mathematical foundations for safe transformations
- **🎯 Pattern Detector**: AI-powered architectural pattern recognition
- **📊 Quality Synthesizer**: Multi-dimensional quality assessment with context
- **🌐 Semantic Exporter**: Knowledge graph generation and semantic web integration

## 🤝 Contributing

RepoQ is an open source project welcoming contributions from the community!

### Development Setup

```bash
# Clone the repository
git clone https://github.com/kirill-0440/repoq.git
cd repoq

# Set up development environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[full,dev]"

# Run tests
python -m pytest tests/

# Run quality checks
ruff check repoq/
ruff format repoq/
```

### Contributing Guidelines

1. **Fork** the repository and create a feature branch
2. **Write tests** for new functionality  
3. **Follow code style** using ruff formatting
4. **Update documentation** for new features
5. **Submit pull request** with clear description

### Areas for Contribution

- **🧠 Ontology Extensions**: New domain ontologies (security, performance, etc.)
- **🔍 Pattern Detection**: Additional architectural pattern recognition
- **📊 Metrics**: New quality metrics and assessment algorithms  
- **🌐 Integrations**: IDE plugins, CI/CD workflows, and tool integrations
- **📚 Documentation**: Examples, tutorials, and use case studies

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🌟 Acknowledgments

RepoQ builds upon decades of research in:

- **Formal Methods**: Term Rewriting Systems and confluence theory
- **Semantic Web**: W3C standards and ontological reasoning
- **Software Engineering**: Domain-driven design and architectural patterns
- **AI/ML**: Pattern recognition and semantic understanding

Special thanks to the open source community for foundational libraries:
- **rdflib** for semantic web capabilities
- **tree-sitter** for language parsing
- **NetworkX** for graph analysis
- **FastAPI** for API framework

---

**Join the revolution in software understanding!** 🚀

[⭐ Star us on GitHub](https://github.com/kirill-0440/repoq) | [📖 Read the Docs](https://kirill-0440.github.io/repoq/) | [🐛 Report Issues](https://github.com/kirill-0440/repoq/issues) | [💬 Discussions](https://github.com/kirill-0440/repoq/discussions)
repoq full https://github.com/user/repo.git \
  --graphs ./graphs \
  --ttl analysis.ttl \
  --validate-shapes

# Структурный анализ с фильтрацией
repoq structure ./project \
  --extensions py,js,java \
  --exclude "test_*,*.min.js" \
  --hash sha256

# Анализ истории за период
repoq history ./repo \
  --since "6 months ago" \
  --md history.md

# Сравнение результатов (CI/CD интеграция)
repoq diff baseline.jsonld current.jsonld \
  --report changes.json \
  --fail-on-regress medium
```

## 📖 Команды

### `repoq structure`
Анализ структуры репозитория:
- Файлы и модули
- Языки программирования и LOC
- Зависимости (Python, JavaScript/TypeScript)
- Лицензия и CI/CD конфигурация
- Контрольные суммы файлов

### `repoq history`
Анализ истории Git:
- Коммиты и авторство
- Статистика участников
- Code churn по файлам
- Temporal coupling (файлы, изменяемые вместе)

### `repoq full`
Комплексный анализ (structure + history):
- Все метрики структуры и истории
- Цикломатическая сложность
- Индекс сопровождаемости
- Hotspot анализ
- Детекция качества кода (TODO/FIXME/Deprecated)
- Парсинг результатов тестов (JUnit XML)

### `repoq diff`
Сравнение двух результатов анализа:
- Новые/исправленные проблемы
- Изменения hotspot scores
- Детекция регрессий качества

## ⚙️ Основные опции

| Опция | Описание |
|-------|----------|
| `-o, --output` | Путь к JSON-LD файлу (default: quality.jsonld) |
| `--md` | Генерация Markdown отчёта |
| `--since` | Временной диапазон для истории (e.g., "1 year ago") |
| `--extensions` | Фильтр расширений файлов (e.g., "py,js,java") |
| `--exclude` | Glob паттерны исключения (e.g., "test_*,*.min.js") |
| `--max-files` | Лимит количества файлов |
| `--graphs` | Директория для dependency/coupling графов |
| `--ttl` | Экспорт в RDF Turtle формат |
| `--validate-shapes` | SHACL валидация результатов |
| `--hash` | Алгоритм контрольных сумм: sha1 или sha256 |
| `--fail-on-issues` | Выход с ошибкой при проблемах (low/medium/high) |
| `-v, -vv` | Уровень детализации логов (INFO/DEBUG) |

## 📄 Форматы экспорта

### JSON-LD
Структурированные данные с семантическими аннотациями:
- **Проект**: `repo:Project`, `schema:SoftwareSourceCode`, `prov:Entity`
- **Файлы**: `repo:File`, `spdx:File` с метриками LOC/сложность/hotness
- **Модули**: `repo:Module` с агрегированной статистикой
- **Участники**: `foaf:Person`, `prov:Agent` с вкладом
- **Коммиты**: `prov:Activity` с авторством и временем
- **Проблемы**: `oslc_cm:ChangeRequest` для hotspots и TODO/FIXME
- **Тесты**: `oslc_qm:TestCase` и `oslc_qm:TestResult`
- **Зависимости**: `repo:DependencyEdge` между модулями/пакетами
- **Coupling**: `repo:CouplingEdge` для temporal coupling

### Markdown
Человекочитаемый отчёт с:
- Метаданные репозитория (URL, лицензия, CI)
- Распределение языков по LOC
- Топ-10 участников по коммитам
- Топ-15 hotspot файлов с метриками
- Список TODO/FIXME/Deprecated маркеров
- Результаты тестов (до 20 последних)

### Graphviz (DOT/SVG)
Визуализация:
- **dependencies.dot/svg**: граф зависимостей модулей и внешних пакетов
- **coupling.dot/svg**: граф temporal coupling между файлами

### RDF Turtle
Экспорт для triple-store и SPARQL запросов с полной поддержкой W3C онтологий.

## 📋 Documentation & Roadmap

### For Decision Makers
- **[� Executive Summary](EXECUTIVE_SUMMARY.md)** — production readiness assessment, ROI, approval request

### For Engineers
- **[🚀 Full Roadmap](ROADMAP.md)** — 4 phases, 7 months to v3.0 GA (with formal verification)
- **[✅ Phase 1 Checklist](PHASE1_CHECKLIST.md)** — actionable sprint plan (weeks 1-4)
- **[🧬 Ontology Formalization](ontologies/FORMALIZATION.md)** — OML/Lean4 specification

### Quick Start (Phase 1)
```bash
# Week 1: Setup testing infrastructure
pip install -e ".[full,dev]"
pytest --cov=repoq --cov-report=html
ruff check . --fix
mypy repoq/

# Self-hosting check
repoq full . -o artifacts/self.jsonld --validate-shapes
```

**Critical gaps** (blocking production):
1. 🔴 Test coverage <10% → need 80% (4 weeks)
2. 🔴 No formal ontology spec → need OML+Lean4 (6 weeks)
3. 🔴 No self-hosting CI → need GitHub Action (1 week)

**Timeline**: 7 months to production v3.0 | **Investment**: ~$150K | **ROI**: break-even in 3 years (SaaS)

**Contribute**: Pick a task from [PHASE1_CHECKLIST.md](PHASE1_CHECKLIST.md) and open a PR!

## 🔬 Normalization & Determinism

repoq включает подсистему **Term Rewriting Systems (TRS)** для обеспечения детерминированных и воспроизводимых результатов.

### SPDX License Normalization

Канонизация лицензионных выражений к нормальной форме:

```python
from repoq.normalize import normalize_spdx

# Идемпотентность: A OR A → A
normalize_spdx("MIT OR MIT")  # → "MIT"

# Коммутативность: лексикографическая сортировка
normalize_spdx("GPL-2.0 OR MIT OR Apache-2.0")  
# → "Apache-2.0 OR GPL-2.0 OR MIT"

# Абсорбция: A OR (A AND B) → A
normalize_spdx("(MIT AND Apache-2.0) OR MIT")  # → "MIT"
```

**Преимущества:**
- ✅ Детерминированные отчёты (нет "флапающих" diff'ов)
- ✅ Content-addressable кэширование по `hash(NF(license))`
- ✅ Формальные гарантии: confluence, termination, idempotence

См. `repoq/normalize/` для деталей.

## Лицензия

MIT
