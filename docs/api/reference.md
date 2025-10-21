# API Reference

!!! info "Auto-generated API Documentation"
    This API reference is automatically generated from Python docstrings using mkdocstrings. All modules, classes, and functions are documented with type hints and examples.

## Overview

RepoQ provides a comprehensive Python API organized into functional modules:

- **Core** (`repoq.core`): Data models, RDF export, repository loading, utilities
- **Analyzers** (`repoq.analyzers`): Structure, complexity, history, hotspots, CI/QM, weakness detection
- **AI** (`repoq.ai`): BAML agent for TRS/ontology validation with 4-phase rollout
- **Reporting** (`repoq.reporting`): Markdown reports, Graphviz diagrams, diff analysis

---

## Core Modules

### Data Models

::: repoq.core.model
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### RDF Export

::: repoq.core.rdf_export
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### Repository Loader

::: repoq.core.repo_loader
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### Dependency Graph

::: repoq.core.deps
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### JSON-LD Utilities

::: repoq.core.jsonld
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### Stratification Guard

::: repoq.core.stratification_guard
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### Utilities

::: repoq.core.utils
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

---

## Ontologies

### Ontology Manager

::: repoq.ontologies.ontology_manager
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

---

## Analyzers

### Base Analyzer

::: repoq.analyzers.base
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### Structure Analyzer

::: repoq.analyzers.structure
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### Complexity Analyzer

::: repoq.analyzers.complexity
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### History Analyzer

::: repoq.analyzers.history
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### Hotspots Analyzer

::: repoq.analyzers.hotspots
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### CI/QM Analyzer

::: repoq.analyzers.ci_qm
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### Weakness Detector

::: repoq.analyzers.weakness
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

---

## AI Module

### BAML Agent

::: repoq.ai.baml_agent
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3
      members:
        - AgentPhase
        - AgentConfig
        - BAMLAgent
        - get_agent
        - configure_agent

---

## Reporting

### Markdown Reporter

::: repoq.reporting.markdown
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### Graphviz Diagrams

::: repoq.reporting.graphviz
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### Diff Reporter

::: repoq.reporting.diff
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

---

## CLI Interface

### Command-Line Interface

::: repoq.cli
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

### Configuration

::: repoq.config
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

---

## Usage Examples

### Basic Analysis

```python
from repoq.analyzers.structure import StructureAnalyzer
from repoq.reporting.markdown import MarkdownReporter

# Analyze repository
analyzer = StructureAnalyzer()
result = analyzer.analyze("/path/to/repo")

# Generate report
reporter = MarkdownReporter()
report = reporter.generate(result)
print(report)
```

### TRS Validation with BAML Agent

```python
import asyncio
from repoq.ai.baml_agent import BAMLAgent, AgentConfig, AgentPhase

async def validate_rule():
    # Configure agent for EXPERIMENTAL phase
    config = AgentConfig(
        phase=AgentPhase.EXPERIMENTAL,
        confidence_threshold=0.8
    )
    agent = BAMLAgent(config)
    
    # Validate TRS rule
    result = await agent.validate_trs_rule(
        rule_lhs="f(g(x))",
        rule_rhs="h(x)",
        existing_rules=["g(a) -> b", "h(b) -> c"],
        context="Confluence check for critical pair"
    )
    
    print(f"Confluence: {result['result'].confluence_status}")
    print(f"Should block: {result['should_block']}")

asyncio.run(validate_rule())
```

### RDF Export

```python
from repoq.core.rdf_export import RDFExporter
from repoq.analyzers.structure import StructureAnalyzer

# Analyze and export to RDF
analyzer = StructureAnalyzer()
result = analyzer.analyze("/path/to/repo")

exporter = RDFExporter()
turtle = exporter.export_to_turtle(result)

# Save to file
with open("analysis.ttl", "w") as f:
    f.write(turtle)
```

### Ontology Validation

```python
from repoq.core.ontology_manager import OntologyManager

manager = OntologyManager()

# Load custom ontology
custom_ontology = """
@prefix repoq: <http://repoq.dev/ontology#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

repoq:CustomAnalyzer a rdfs:Class ;
    rdfs:subClassOf repoq:Analyzer .
"""

# Validate against SHACL shapes
is_valid, violations = manager.validate_ontology(
    custom_ontology,
    shape_file="shapes/shacl_project.ttl"
)

if not is_valid:
    for violation in violations:
        print(f"Violation: {violation.message}")
```

---

## Type Reference

All classes use Python type hints for better IDE support and static analysis:

```python
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
from pathlib import Path

@dataclass
class AnalysisResult:
    """Result of repository analysis."""
    repo_path: Path
    files_analyzed: int
    total_lines: int
    complexity_metrics: Dict[str, float]
    detected_patterns: List[str]
    quality_score: float
    
@dataclass
class TRSValidationResult:
    """Result of TRS rule validation."""
    confluence_status: str  # "CONFLUENT", "NON_CONFLUENT", "UNKNOWN"
    termination_status: str  # "TERMINATES", "NON_TERMINATING", "UNKNOWN"
    critical_pairs: List[Dict[str, str]]
    confidence: float
    reasoning: str
```

For complete type definitions, see the [Core Models](#data-models) section.
