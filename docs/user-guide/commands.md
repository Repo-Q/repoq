# CLI Commands

!!! info "Command Reference"
    Complete reference for all RepoQ CLI commands, options, and usage patterns.

## Command Overview

```
repoq [OPTIONS] COMMAND [ARGS]...
```

### Available Commands

| Command | Description |
|---------|-------------|
| `structure` | Analyze repository structure and dependencies |
| `complexity` | Analyze code complexity metrics |
| `history` | Analyze git commit history |
| `hotspots` | Detect code hotspots (complex + frequently changed) |
| `ci-qm` | Analyze CI/CD configuration and quality metrics |
| `weakness` | Detect code weaknesses and anti-patterns |
| `analyze` | Run all analyzers (comprehensive analysis) |
| `validate` | Validate RDF output against SHACL shapes |
| `config` | Manage configuration |
| `version` | Show version information |

---

## Global Options

Available for all commands:

```bash
Options:
  --config PATH          Path to configuration file [default: quality_policy.yaml]
  --output PATH          Output directory [default: output]
  --format FORMAT        Output format: markdown, json, jsonld, turtle [default: markdown]
  --verbose / --quiet    Verbose or quiet output
  --log-level LEVEL      Log level: DEBUG, INFO, WARNING, ERROR [default: INFO]
  --help                 Show help message and exit
```

**Examples:**

```bash
# Use custom config
repoq --config my-config.yaml structure /path/to/repo

# Change output directory
repoq --output /tmp/analysis structure /path/to/repo

# JSON output
repoq --format json structure /path/to/repo

# Verbose logging
repoq --verbose structure /path/to/repo
```

---

## `repoq structure`

Analyze repository structure, dependencies, and architecture.

### Usage

```bash
repoq structure [OPTIONS] REPO_PATH
```

### Options

```bash
Options:
  --include PATTERN      Include files matching pattern (glob)
  --exclude PATTERN      Exclude files matching pattern (glob)
  --max-depth N          Maximum directory depth [default: 10]
  --ontology / --no-ontology  Enable/disable ontological analysis [default: on]
  --patterns / --no-patterns  Enable/disable pattern detection [default: on]
```

### Examples

```bash
# Basic analysis
repoq structure /path/to/repo

# Include only Python files
repoq structure /path/to/repo --include "**/*.py"

# Exclude tests and build artifacts
repoq structure /path/to/repo --exclude "tests/**" --exclude "build/**"

# Limit depth
repoq structure /path/to/repo --max-depth 5

# Disable ontological analysis
repoq structure /path/to/repo --no-ontology

# JSON output
repoq structure /path/to/repo --format json > structure.json
```

### Output

- **Markdown report**: `output/structure_report.md`
- **JSON data**: `output/structure.json`
- **RDF/Turtle**: `output/structure.ttl`
- **Dependency graph**: `output/dependencies.dot` (if Graphviz installed)

---

## `repoq complexity`

Analyze code complexity using multiple metrics.

### Usage

```bash
repoq complexity [OPTIONS] REPO_PATH
```

### Options

```bash
Options:
  --metrics METRIC       Metrics to compute: cyclomatic, cognitive, maintainability, halstead
  --cyclomatic-max N     Maximum cyclomatic complexity [default: 15]
  --cognitive-max N      Maximum cognitive complexity [default: 20]
  --sort-by FIELD        Sort results by: complexity, file, line [default: complexity]
  --top N                Show only top N results [default: all]
```

### Examples

```bash
# All complexity metrics
repoq complexity /path/to/repo

# Specific metrics only
repoq complexity /path/to/repo --metrics cyclomatic,cognitive

# Custom thresholds
repoq complexity /path/to/repo --cyclomatic-max 10 --cognitive-max 15

# Top 10 most complex functions
repoq complexity /path/to/repo --top 10

# Sort by file
repoq complexity /path/to/repo --sort-by file
```

### Output

- **Markdown report**: `output/complexity_report.md`
- **CSV data**: `output/complexity.csv`
- **JSON data**: `output/complexity.json`

---

## `repoq history`

Analyze git commit history for churn, contributors, and trends.

### Usage

```bash
repoq history [OPTIONS] REPO_PATH
```

### Options

```bash
Options:
  --branch TEXT          Git branch to analyze [default: main]
  --since DATE           Start date (YYYY-MM-DD or relative: 1 week ago)
  --until DATE           End date (YYYY-MM-DD or relative: now)
  --authors TEXT         Comma-separated list of authors to include
  --max-commits N        Maximum number of commits to analyze [default: 1000]
  --files-only           Analyze file-level metrics only (faster)
```

### Examples

```bash
# Entire history
repoq history /path/to/repo

# Last 30 days
repoq history /path/to/repo --since "30 days ago"

# Date range
repoq history /path/to/repo --since "2024-01-01" --until "2024-12-31"

# Specific branch
repoq history /path/to/repo --branch develop

# Specific authors
repoq history /path/to/repo --authors "alice@example.com,bob@example.com"

# Limit commits for performance
repoq history /path/to/repo --max-commits 100
```

### Output

- **Markdown report**: `output/history_report.md`
- **CSV data**: `output/commits.csv`, `output/file_churn.csv`
- **JSON data**: `output/history.json`

---

## `repoq hotspots`

Detect code hotspots: files that are both complex and frequently changed.

### Usage

```bash
repoq hotspots [OPTIONS] REPO_PATH
```

### Options

```bash
Options:
  --complexity-threshold N   Minimum complexity for hotspot [default: 10]
  --change-threshold N       Minimum change count for hotspot [default: 5]
  --coupling-threshold N     Minimum coupling for hotspot [default: 3]
  --min-score FLOAT          Minimum hotspot score (0-10) [default: 5.0]
  --top N                    Show only top N hotspots [default: 20]
```

### Examples

```bash
# Find hotspots
repoq hotspots /path/to/repo

# Stricter criteria
repoq hotspots /path/to/repo --complexity-threshold 15 --change-threshold 10

# Top 5 hotspots
repoq hotspots /path/to/repo --top 5

# Only high-score hotspots
repoq hotspots /path/to/repo --min-score 7.0
```

### Output

- **Markdown report**: `output/hotspots_report.md`
- **JSON data**: `output/hotspots.json`
- **Visualization**: Heatmap (if matplotlib available)

---

## `repoq ci-qm`

Analyze CI/CD configuration and quality metrics integration.

### Usage

```bash
repoq ci-qm [OPTIONS] REPO_PATH
```

### Options

```bash
Options:
  --ci-files PATTERN     Pattern for CI files [default: .github/workflows/**]
  --check-coverage       Check for test coverage reporting [default: true]
  --check-linting        Check for linting/formatting tools [default: true]
  --check-security       Check for security scanning [default: true]
```

### Examples

```bash
# Analyze CI/CD setup
repoq ci-qm /path/to/repo

# Custom CI file patterns
repoq ci-qm /path/to/repo --ci-files ".gitlab-ci.yml,Jenkinsfile"

# Check specific aspects only
repoq ci-qm /path/to/repo --check-coverage --no-check-linting
```

### Output

- **Markdown report**: `output/ci_qm_report.md`
- **JSON data**: `output/ci_qm.json`

---

## `repoq weakness`

Detect code weaknesses, anti-patterns, and technical debt markers.

### Usage

```bash
repoq weakness [OPTIONS] REPO_PATH
```

### Options

```bash
Options:
  --patterns TEXT        Patterns to search: TODO, FIXME, HACK, XXX
  --custom-pattern TEXT  Add custom pattern to search
  --severity LEVEL       Minimum severity: low, medium, high [default: low]
  --group-by FIELD       Group by: file, type, severity [default: type]
```

### Examples

```bash
# Find all weaknesses
repoq weakness /path/to/repo

# Specific patterns
repoq weakness /path/to/repo --patterns "TODO,FIXME"

# Custom patterns
repoq weakness /path/to/repo --custom-pattern "DEPRECATED" --custom-pattern "REMOVE"

# High severity only
repoq weakness /path/to/repo --severity high

# Group by file
repoq weakness /path/to/repo --group-by file
```

### Output

- **Markdown report**: `output/weakness_report.md`
- **JSON data**: `output/weaknesses.json`

---

## `repoq analyze`

Run all analyzers in a single comprehensive analysis.

### Usage

```bash
repoq analyze [OPTIONS] REPO_PATH
```

### Options

```bash
Options:
  --analyzers TEXT           Comma-separated list of analyzers to run
  --no-structure             Disable structure analyzer
  --no-complexity            Disable complexity analyzer
  --no-history               Disable history analyzer
  --no-hotspots              Disable hotspots detector
  --no-ci-qm                 Disable CI/QM analyzer
  --no-weakness              Disable weakness detector
  --parallel / --sequential  Run analyzers in parallel [default: parallel]
  --max-workers N            Maximum parallel workers [default: 4]
```

### Examples

```bash
# Full analysis (all analyzers)
repoq analyze /path/to/repo

# Specific analyzers only
repoq analyze /path/to/repo --analyzers "structure,complexity,hotspots"

# Exclude history (for CI/CD speed)
repoq analyze /path/to/repo --no-history

# Sequential execution (for debugging)
repoq analyze /path/to/repo --sequential

# Limit parallelism
repoq analyze /path/to/repo --max-workers 2
```

### Output

- **Markdown report**: `output/full_report.md`
- **JSON data**: `output/analysis.json`
- **JSON-LD**: `output/analysis.jsonld`
- **RDF/Turtle**: `output/analysis.ttl`
- **Individual analyzer outputs** in `output/` directory

---

## `repoq validate`

Validate RDF output against SHACL shapes.

### Usage

```bash
repoq validate [OPTIONS] RDF_FILE
```

### Options

```bash
Options:
  --shapes PATH          Path to SHACL shapes file [default: shapes/shacl_project.ttl]
  --format FORMAT        RDF format: turtle, xml, n3 [default: turtle]
  --inference / --no-inference  Enable RDFS/OWL inference [default: on]
  --abort-on-error       Abort on first validation error [default: false]
```

### Examples

```bash
# Validate with default shapes
repoq validate output/analysis.ttl

# Custom SHACL shapes
repoq validate output/analysis.ttl --shapes custom_shapes.ttl

# Disable inference
repoq validate output/analysis.ttl --no-inference

# Abort on first error
repoq validate output/analysis.ttl --abort-on-error
```

### Output

- **Console**: Validation results with violations
- **JSON report**: `output/validation_report.json` (if violations found)

---

## `repoq config`

Manage RepoQ configuration.

### Usage

```bash
repoq config [OPTIONS] COMMAND
```

### Subcommands

```bash
Commands:
  show       Show effective configuration
  validate   Validate configuration file
  init       Create default configuration file
```

### Examples

```bash
# Show effective configuration
repoq config show

# Show configuration for specific command
repoq config show structure

# Validate configuration file
repoq config validate quality_policy.yaml

# Create default configuration
repoq config init
repoq config init --output my-config.yaml
```

---

## `repoq version`

Show version information.

### Usage

```bash
repoq version [OPTIONS]
```

### Options

```bash
Options:
  --short    Show version number only
```

### Examples

```bash
# Full version info
repoq version

# Version number only
repoq version --short
```

---

## Exit Codes

RepoQ uses standard exit codes:

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (invalid arguments, file not found) |
| 2 | Quality threshold not met (--fail-on-quality) |
| 3 | Validation failed (SHACL validation errors) |
| 4 | Configuration error |

**Example:**

```bash
# Exit with error if quality score < 7.0
repoq analyze /path/to/repo --fail-below 7.0

# Check exit code
echo $?  # 0 = success, 2 = quality threshold not met
```

---

## Scripting and Automation

### Bash Script Example

```bash
#!/bin/bash
set -e

REPO_PATH="/path/to/repo"
OUTPUT_DIR="/tmp/repoq-output"

# Run analysis
repoq analyze "$REPO_PATH" \
  --output "$OUTPUT_DIR" \
  --format json \
  --no-history \
  --fail-below 7.0

# Extract quality score
SCORE=$(jq -r '.quality_score' "$OUTPUT_DIR/analysis.json")
echo "Quality score: $SCORE"

# Send to monitoring system
curl -X POST https://monitoring.example.com/metrics \
  -H "Content-Type: application/json" \
  -d "{\"project\": \"myproject\", \"score\": $SCORE}"
```

### CI/CD Integration (GitHub Actions)

```yaml
# .github/workflows/quality.yml
name: Code Quality

on: [push, pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for repoq history
      
      - name: Install RepoQ
        run: pip install repoq[full]
      
      - name: Run Analysis
        run: repoq analyze . --no-history --fail-below 7.0
      
      - name: Upload Reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: repoq-reports
          path: output/
```

---

## Next Steps

- **[Configuration](configuration.md)**: Customize RepoQ behavior
- **[Workflows](workflows.md)**: Common usage patterns
- **[Tutorials](../tutorials/)**: Step-by-step guides
- **[API Reference](../api/reference.md)**: Use RepoQ in Python scripts

!!! tip "Cheat Sheet"
    Download the [CLI cheat sheet](../assets/repoq-cheatsheet.pdf) for quick reference of common commands.
