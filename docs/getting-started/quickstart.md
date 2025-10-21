# Getting Started

!!! success "Quick Start"
    Get RepoQ running in under 5 minutes. This guide covers installation and your first repository analysis.

## Prerequisites

- **Python**: 3.9 or higher (3.11+ recommended)
- **Operating System**: Linux, macOS, or Windows
- **Memory**: 512MB+ available RAM
- **Optional**: Graphviz for dependency diagrams

## Installation

### Option 1: Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is the fastest Python package installer:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install RepoQ with all features
uv pip install repoq[full]

# Verify installation
uv run repoq --version
```

### Option 2: Using pip

```bash
# Install with all features
pip install repoq[full]

# Or minimal installation
pip install repoq

# Verify installation
repoq --version
```

### Option 3: From Source (Development)

```bash
# Clone repository
git clone https://github.com/kirill-0440/repoq.git
cd repoq

# Install with uv
uv sync --all-groups --all-extras

# Or with pip
pip install -e ".[full,dev,docs]"

# Verify installation
uv run repoq --version
```

## Your First Analysis

### 1. Analyze a Local Repository

```bash
# Basic structural analysis
repoq structure /path/to/your/repo

# Full analysis with all analyzers
repoq analyze /path/to/your/repo
```

**Expected output:**
```
📊 RepoQ Analysis Starting...
✓ Loading repository: /path/to/your/repo
✓ Running structure analyzer...
✓ Running complexity analyzer...
✓ Running history analyzer...
✓ Running hotspots detector...
✓ Generating report...

📈 Analysis Complete!
   Files analyzed: 142
   Total lines: 8,543
   Quality score: 8.2/10
   
   Report: output/analysis_report.md
   RDF data: output/analysis.ttl
```

### 2. View the Report

```bash
# Open Markdown report
cat output/analysis_report.md

# Or view in browser (if you have a Markdown viewer)
open output/analysis_report.md
```

### 3. Explore RDF/Semantic Data

```bash
# View RDF/Turtle output
cat output/analysis.ttl

# Validate with SHACL shapes
repoq validate output/analysis.ttl --shapes shapes/shacl_project.ttl
```

## Understanding the Output

### Terminal Output

RepoQ provides real-time feedback during analysis:

```
📊 RepoQ Analysis Results
========================================

🏗️  Structure Analysis
   Total files: 142
   Python files: 98
   Test files: 44
   Modules: 12
   Average file size: 85 lines

🧮 Complexity Metrics
   Cyclomatic complexity: 6.2 (good)
   Cognitive complexity: 8.1 (moderate)
   Maintainability index: 72.3 (maintainable)

🔥 Hotspots
   Top 3 files requiring attention:
   1. src/core/processor.py (complexity: 18, changes: 45)
   2. src/api/routes.py (complexity: 15, changes: 32)
   3. src/utils/helpers.py (complexity: 12, changes: 28)

📈 Overall Quality Score: 8.2/10
```

### File Outputs

RepoQ generates multiple output files:

```
output/
├── analysis_report.md     # Human-readable Markdown report
├── analysis.json          # Machine-readable JSON
├── analysis.jsonld        # JSON-LD with semantic annotations
├── analysis.ttl           # RDF/Turtle for semantic web
├── dependency_graph.dot   # Graphviz dependency graph
└── metrics.csv            # Metrics data for spreadsheets
```

## Common Use Cases

### Analyze Specific Directories

```bash
# Analyze only src/ directory
repoq structure /path/to/repo --include "src/**"

# Exclude tests
repoq structure /path/to/repo --exclude "tests/**"
```

### Generate Specific Output Formats

```bash
# JSON output
repoq structure /path/to/repo --format json > analysis.json

# JSON-LD with semantic annotations
repoq structure /path/to/repo --format jsonld > analysis.jsonld

# RDF/Turtle
repoq structure /path/to/repo --format turtle > analysis.ttl
```

### Analyze Git History

```bash
# Include commit history analysis
repoq history /path/to/repo

# Analyze specific time range
repoq history /path/to/repo --since "2024-01-01" --until "2024-12-31"

# Focus on specific authors
repoq history /path/to/repo --authors "alice,bob"
```

### Detect Code Hotspots

```bash
# Find frequently changed + complex files
repoq hotspots /path/to/repo

# Customize thresholds
repoq hotspots /path/to/repo --complexity-threshold 15 --change-threshold 10
```

## Next Steps

- **[Configuration](configuration.md)**: Customize RepoQ behavior with `quality_policy.yaml`
- **[CLI Reference](commands.md)**: Complete list of commands and options
- **[Workflows](workflows.md)**: Common analysis workflows and best practices
- **[Tutorials](../tutorials/)**: Step-by-step guides for specific tasks
- **[API Reference](../api/reference.md)**: Use RepoQ programmatically in Python

## Troubleshooting

### Command Not Found

```bash
# If 'repoq' command is not found, try:
python -m repoq --help

# Or with uv:
uv run repoq --help
```

### Import Errors

```bash
# Install full dependencies
pip install repoq[full]

# Or with uv
uv sync --all-extras
```

### Permission Errors

```bash
# Ensure you have read access to the repository
ls -la /path/to/repo

# Run with verbose logging for details
repoq structure /path/to/repo --verbose
```

### Large Repository Performance

```bash
# Limit analysis depth
repoq structure /path/to/repo --max-depth 3

# Analyze incrementally
repoq structure /path/to/repo/src
repoq structure /path/to/repo/tests
```

## Getting Help

- **Documentation**: [https://kirill-0440.github.io/repoq/](https://kirill-0440.github.io/repoq/)
- **GitHub Issues**: [https://github.com/kirill-0440/repoq/issues](https://github.com/kirill-0440/repoq/issues)
- **CLI Help**: `repoq --help` or `repoq <command> --help`
- **Examples**: See [Tutorials](../tutorials/) section

!!! tip "Pro Tip"
    Use `repoq --help` to discover all available commands and options. Each command has its own `--help` flag for detailed usage.
