# User Guide

!!! tip "Getting Started"
    This guide will help you master RepoQ's revolutionary semantic analysis capabilities. Start with basic usage and progress to advanced ontological intelligence features.

## 🚀 Quick Start

### Basic Repository Analysis

The simplest way to analyze a repository:

```bash
repoq structure /path/to/your/repo
```

This performs comprehensive structural analysis including:
- File organization and module dependencies  
- Code complexity metrics (cyclomatic, cognitive)
- Architecture pattern detection
- **Ontological intelligence** with semantic understanding

### Understanding the Output

RepoQ generates rich semantic output in multiple formats:

#### **Terminal Output**
```
📊 RepoQ Analysis Results
========================================

🏗️  Architecture Overview
   System: MyProject Analysis Platform
   Containers: 3 (Core Engine, CLI, Tests)
   Components: 12 (Primary: DataProcessor, ValidationEngine, ReportGenerator)

🧠 Ontological Intelligence
   Detected Patterns:
   ✓ Strategy Pattern in src/processors/
   ✓ Repository Pattern in src/data/
   ✓ Plugin Architecture in src/extensions/

🎯 Domain-Driven Design
   Bounded Contexts: 2
   ├─ Data Processing Domain (src/processors/, src/validators/)
   └─ Reporting Domain (src/reports/, src/formatters/)
   
   Entities: User, Project, AnalysisResult
   Value Objects: Metrics, Configuration, ReportData

📈 Quality Metrics
   Overall Score: 8.2/10
   ├─ Code Quality: 8.5/10 (complexity: good, maintainability: excellent)
   ├─ Architecture: 7.8/10 (modularity: good, some coupling issues)
   └─ Domain Modeling: 8.3/10 (clear boundaries, appropriate patterns)
```

#### **JSON Output for Tools**
```bash
repoq structure /path/to/repo --format json > analysis.json
```

```json
{
  "@context": "https://field33.com/ontologies/analysis/",
  "@type": "AnalysisResult",
  "project": {
    "@type": "Project",
    "path": "/path/to/repo",
    "language": "python",
    "lines_of_code": 15420
  },
  "architecture": {
    "@type": "c4:System", 
    "name": "MyProject",
    "containers": [
      {
        "@type": "c4:Container",
        "name": "Core Engine",
        "technology": "Python",
        "components": ["DataProcessor", "ValidationEngine"]
      }
    ]
  },
  "ontological_analysis": {
    "detected_patterns": [
      {
        "@type": "ArchitecturalPattern",
        "pattern": "Strategy",
        "location": "src/processors/",
        "confidence": 0.95,
        "benefits": ["extensibility", "testability"]
      }
    ],
    "domain_model": {
      "bounded_contexts": [
        {
          "@type": "ddd:BoundedContext",
          "name": "Data Processing",
          "modules": ["src/processors/", "src/validators/"]
        }
      ]
    }
  }
}
```

## 📖 Core Commands

### `repoq structure`

Comprehensive structural analysis with ontological intelligence.

```bash
# Basic analysis
repoq structure /path/to/repo

# With specific output format
repoq structure /path/to/repo --format json
repoq structure /path/to/repo --format rdf
repoq structure /path/to/repo --format markdown

# Focus on specific aspects
repoq structure /path/to/repo --ontology code     # Focus on code structure
repoq structure /path/to/repo --ontology c4       # Focus on architecture  
repoq structure /path/to/repo --ontology ddd      # Focus on domain design

# Include detailed metrics
repoq structure /path/to/repo --detailed --include-metrics
```

**Key Features:**
- **Automatic pattern detection** (Strategy, Repository, Factory, Observer, etc.)
- **Domain-driven design analysis** (entities, value objects, bounded contexts)
- **Architecture visualization** (C4 model mapping)
- **Cross-ontology inference** (connecting code → architecture → domain)

### `repoq complexity`

Deep complexity analysis with semantic understanding.

```bash
# File-level complexity
repoq complexity /path/to/repo

# Function-level detail
repoq complexity /path/to/repo --detailed

# Cognitive complexity focus
repoq complexity /path/to/repo --cognitive

# Export for analysis tools
repoq complexity /path/to/repo --format json > complexity.json
```

**Complexity Metrics:**
- **Cyclomatic Complexity**: Control flow complexity
- **Cognitive Complexity**: Human comprehension difficulty  
- **Nested Complexity**: Depth of nesting structures
- **Maintainability Index**: Overall maintainability score

### `repoq history`

Git history analysis with pattern evolution tracking.

```bash
# Hotspot analysis
repoq history /path/to/repo

# Detailed change patterns
repoq history /path/to/repo --detailed

# Focus on specific time period
repoq history /path/to/repo --since "2024-01-01"
repoq history /path/to/repo --until "2024-12-31"

# Pattern evolution tracking
repoq history /path/to/repo --track-patterns
```

**History Insights:**
- **Code hotspots** (frequently changed files)
- **Architecture evolution** (pattern emergence/decay)
- **Domain model changes** (entity/boundary evolution)
- **Quality trends** (complexity over time)

### `repoq full`

Complete analysis combining all aspects.

```bash
# Full semantic analysis
repoq full /path/to/repo

# Export comprehensive report
repoq full /path/to/repo --format markdown > comprehensive-report.md

# Include all ontological layers
repoq full /path/to/repo --all-ontologies --detailed
```

**Full Analysis Includes:**
- Complete structural analysis
- Comprehensive complexity metrics
- Historical pattern evolution
- Cross-ontology semantic mappings
- Architecture quality assessment
- Domain model evaluation
- Improvement recommendations

## 🎯 Advanced Usage

### Ontological Intelligence Deep Dive

#### **Understanding Detected Patterns**

When RepoQ detects architectural patterns, it provides rich contextual information:

```bash
repoq structure /path/to/repo --detailed --explain-patterns
```

**Example Output:**
```yaml
detected_patterns:
  - pattern: "Strategy Pattern"
    location: "src/analyzers/"
    confidence: 0.95
    detection_evidence:
      - "Common interface: BaseAnalyzer"
      - "Multiple implementations: ComplexityAnalyzer, HistoryAnalyzer"
      - "Polymorphic usage in AnalysisEngine"
      - "Clear separation of algorithms"
    benefits:
      - "Easy to add new analysis types"
      - "Testable in isolation"
      - "Runtime algorithm selection"
    potential_improvements:
      - "Consider Abstract Factory for analyzer creation"
      - "Add configuration-based analyzer selection"
```

#### **Domain Model Analysis**

RepoQ automatically maps your code to domain-driven design concepts:

```bash
repoq structure /path/to/repo --ontology ddd --detailed
```

**Example Domain Analysis:**
```yaml
domain_model:
  bounded_contexts:
    - name: "User Management"
      modules: ["src/users/", "src/auth/"]
      entities: ["User", "Role", "Permission"]
      value_objects: ["Email", "Password", "UserPreferences"]
      services: ["AuthenticationService", "UserRegistrationService"]
      
    - name: "Project Analysis"  
      modules: ["src/analysis/", "src/metrics/"]
      entities: ["Project", "AnalysisSession"]
      value_objects: ["ComplexityScore", "QualityMetrics"]
      services: ["AnalysisOrchestrator", "ReportGenerator"]
      
  cross_context_relationships:
    - from: "User Management"
      to: "Project Analysis"
      relationship: "User owns Project"
      interface: "ProjectOwnershipService"
```

### Working with Different Languages

RepoQ provides language-specific analysis:

#### **Python Projects**
```bash
# Enhanced Python analysis
repoq structure /path/to/python-project --language python --detailed

# Focus on Python-specific patterns
repoq structure /path/to/python-project --patterns "decorator,context_manager,generator"

# Django/Flask project analysis
repoq structure /path/to/web-project --framework django
repoq structure /path/to/web-project --framework flask
```

#### **JavaScript/TypeScript Projects**
```bash
# Node.js project analysis
repoq structure /path/to/node-project --language javascript

# React application analysis
repoq structure /path/to/react-app --framework react

# TypeScript with enhanced type analysis
repoq structure /path/to/ts-project --language typescript --include-types
```

#### **Multi-Language Projects**
```bash
# Full-stack project analysis
repoq structure /path/to/fullstack-project --multi-language

# Microservices architecture
repoq structure /path/to/microservices --architecture microservices
```

### Integration with Development Workflow

#### **CI/CD Integration**

**GitHub Actions Example:**
```yaml
name: RepoQ Analysis
on: [push, pull_request]

jobs:
  quality-analysis:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install RepoQ
        run: pip install repoq
        
      - name: Run Analysis
        run: |
          repoq full . --format json > repoq-analysis.json
          repoq structure . --format markdown > ARCHITECTURE.md
          
      - name: Quality Gate
        run: |
          python -c "
          import json
          with open('repoq-analysis.json') as f:
              analysis = json.load(f)
          score = analysis['quality_metrics']['overall_score']
          if score < 7.0:
              print(f'Quality score {score} below threshold 7.0')
              exit(1)
          print(f'Quality score {score} - PASSED')
          "
          
      - name: Upload Analysis
        uses: actions/upload-artifact@v3
        with:
          name: repoq-analysis
          path: |
            repoq-analysis.json
            ARCHITECTURE.md
```

#### **Pre-commit Hook**
```bash
# Install pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Run RepoQ analysis before commit

echo "Running RepoQ quality analysis..."
repoq complexity . --threshold 15

if [ $? -ne 0 ]; then
    echo "❌ Quality gate failed - complexity too high"
    echo "Run 'repoq complexity . --detailed' for details"
    exit 1
fi

echo "✅ Quality gate passed"
EOF

chmod +x .git/hooks/pre-commit
```

#### **IDE Integration**

**VS Code Settings** (`.vscode/settings.json`):
```json
{
  "repoq.analysisOnSave": true,
  "repoq.complexityThreshold": 15,
  "repoq.showOntologicalInsights": true,
  "repoq.outputFormat": "json",
  "repoq.enablePatternDetection": true
}
```

## 📊 Understanding Output Formats

### JSON-LD Format (Semantic Web)

RepoQ's JSON-LD output is compatible with semantic web tools:

```bash
repoq structure /path/to/repo --format jsonld > analysis.jsonld
```

**Key Advantages:**
- **Semantic interoperability** with other tools
- **Rich metadata** with formal ontologies
- **Graph database compatibility** (Neo4j, Apache Jena)
- **SPARQL query support** for complex analysis

**Example Query (SPARQL):**
```sparql
PREFIX code: <https://field33.com/ontologies/code/>
PREFIX c4: <https://field33.com/ontologies/c4/>

SELECT ?component ?complexity WHERE {
  ?component a c4:Component ;
             code:hasComplexity ?complexity .
  FILTER (?complexity > 15)
}
```

### RDF/Turtle Format

For knowledge graph applications:

```bash
repoq structure /path/to/repo --format rdf > analysis.ttl
```

**Example RDF Output:**
```turtle
@prefix code: <https://field33.com/ontologies/code/> .
@prefix c4: <https://field33.com/ontologies/c4/> .
@prefix ddd: <https://field33.com/ontologies/ddd/> .

<project:MyProject> a c4:System ;
    c4:hasContainer <container:CoreEngine> ;
    code:hasLinesOfCode 15420 ;
    ddd:hasBoundedContext <context:DataProcessing> .

<container:CoreEngine> a c4:Container ;
    c4:hasComponent <component:DataProcessor> ;
    c4:technology "Python" .

<component:DataProcessor> a c4:Component ;
    code:hasComplexity 8 ;
    ddd:implementsPattern "Strategy" .
```

### Markdown Format (Documentation)

For human-readable documentation:

```bash
repoq structure /path/to/repo --format markdown > ARCHITECTURE.md
```

**Generated Documentation Includes:**
- Executive summary with key metrics
- Architecture diagrams (Mermaid format)
- Detailed component descriptions
- Quality assessment and recommendations
- Pattern explanation with examples

## 🔧 Configuration

### Configuration File

Create `.repoq.yaml` in your project root:

```yaml
# RepoQ Configuration
analysis:
  # Language-specific settings
  language: "python"
  include_tests: true
  exclude_patterns:
    - "**/__pycache__/**"
    - "**/node_modules/**"
    - "**/venv/**"
    - "**/.*"

# Ontological analysis settings
ontology:
  enabled_ontologies: ["code", "c4", "ddd"]
  pattern_detection: true
  cross_inference: true
  confidence_threshold: 0.8

# Quality thresholds
quality:
  complexity:
    cyclomatic_max: 15
    cognitive_max: 25
    nesting_max: 4
  architecture:
    coupling_max: 7
    cohesion_min: 0.7
  domain:
    context_separation_min: 0.8

# Output preferences  
output:
  default_format: "json"
  include_metrics: true
  detailed_patterns: true
  show_recommendations: true

# Performance settings
performance:
  max_file_size_mb: 10
  analysis_timeout_sec: 300
  parallel_analysis: true
  cache_results: true
```

### Environment Variables

```bash
# Set default configuration
export REPOQ_CONFIG="/path/to/.repoq.yaml"
export REPOQ_OUTPUT_FORMAT="json"
export REPOQ_COMPLEXITY_THRESHOLD="15"

# Performance tuning
export REPOQ_MAX_WORKERS="4"
export REPOQ_CACHE_DIR="/tmp/repoq-cache"

# Debugging
export REPOQ_DEBUG="true"
export REPOQ_LOG_LEVEL="INFO"
```

## 🎓 Best Practices

### Effective Analysis Workflow

1. **Start with Basic Structure Analysis**
   ```bash
   repoq structure /path/to/repo
   ```

2. **Identify Quality Issues**
   ```bash
   repoq complexity /path/to/repo --detailed
   ```

3. **Understand Historical Context**
   ```bash
   repoq history /path/to/repo --track-patterns
   ```

4. **Comprehensive Assessment**
   ```bash
   repoq full /path/to/repo --all-ontologies
   ```

### Interpreting Results

#### **Quality Scores**
- **9.0-10.0**: Exceptional quality, minimal improvements needed
- **8.0-8.9**: High quality, minor optimizations possible
- **7.0-7.9**: Good quality, some improvements recommended
- **6.0-6.9**: Moderate quality, significant improvements needed
- **<6.0**: Poor quality, major refactoring required

#### **Complexity Thresholds**
- **Cyclomatic Complexity**: >15 requires attention, >25 critical
- **Cognitive Complexity**: >25 difficult to understand, >50 critical
- **Nesting Depth**: >4 levels considered excessive

#### **Architecture Patterns**
- **Strategy Pattern**: Indicates good algorithm separation
- **Repository Pattern**: Good data access abstraction
- **Factory Pattern**: Proper object creation encapsulation
- **Observer Pattern**: Loose coupling for event handling

### Performance Optimization

#### **Large Repositories**
```bash
# Use parallel analysis
repoq structure /path/to/large-repo --parallel --workers 8

# Focus analysis  
repoq structure /path/to/large-repo --include "src/**" --exclude "tests/**"

# Cache results
export REPOQ_CACHE_DIR="/tmp/repoq-cache"
repoq structure /path/to/large-repo --use-cache
```

#### **Memory Management**
```bash
# Limit memory usage
repoq structure /path/to/repo --max-memory 2048  # MB

# Process files in batches
repoq structure /path/to/repo --batch-size 100
```

## 🔍 Troubleshooting

### Common Issues

#### **"No files found to analyze"**
```bash
# Check file patterns
repoq structure /path/to/repo --verbose

# Adjust include/exclude patterns
repoq structure /path/to/repo --include "**/*.py" --include "**/*.js"
```

#### **High memory usage**
```bash
# Reduce analysis scope
repoq structure /path/to/repo --exclude "**/*test*" --exclude "**/vendor/**"

# Use streaming analysis
repoq structure /path/to/repo --stream --batch-size 50
```

#### **Slow analysis**
```bash
# Enable parallel processing
repoq structure /path/to/repo --parallel

# Skip expensive analysis
repoq structure /path/to/repo --skip-history --skip-complexity
```

### Debug Mode

```bash
# Enable detailed logging
export REPOQ_DEBUG=true
export REPOQ_LOG_LEVEL=DEBUG

repoq structure /path/to/repo --verbose
```

### Getting Help

```bash
# Command help
repoq --help
repoq structure --help

# Version information
repoq --version

# Configuration validation
repoq config --validate
repoq config --show
```

---

This user guide covers the full spectrum of RepoQ's capabilities, from basic usage to advanced ontological intelligence. Start with simple commands and gradually explore the powerful semantic analysis features that make RepoQ unique! 🚀