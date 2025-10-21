# Configuration

!!! info "Customization"
    RepoQ can be customized through configuration files, CLI flags, and environment variables. This guide covers all configuration options.

## Configuration File

### quality_policy.yaml

The main configuration file for RepoQ. Place it in your project root or specify with `--config`.

**Default location:** `.repoq/quality_policy.yaml` or `quality_policy.yaml`

```yaml
# quality_policy.yaml - RepoQ Configuration

# Project metadata
project:
  name: "MyProject"
  version: "1.0.0"
  description: "My awesome project"

# Quality thresholds
quality:
  # Complexity limits
  complexity:
    cyclomatic_max: 15
    cognitive_max: 20
    function_length_max: 50
    class_length_max: 300
  
  # Maintainability thresholds
  maintainability:
    index_min: 65.0  # 0-100 scale
    comment_ratio_min: 0.1  # 10% minimum
  
  # Test coverage requirements
  testing:
    coverage_min: 0.8  # 80% minimum
    test_ratio_min: 1.0  # 1:1 test to source ratio
  
  # Overall quality score
  score:
    target: 8.0  # Target score (0-10)
    fail_below: 6.0  # Fail if below this

# Analyzers configuration
analyzers:
  # Structure analyzer
  structure:
    enabled: true
    include_patterns:
      - "**/*.py"
      - "**/*.js"
      - "**/*.ts"
    exclude_patterns:
      - "**/node_modules/**"
      - "**/__pycache__/**"
      - "**/venv/**"
      - "**/.venv/**"
      - "**/build/**"
      - "**/dist/**"
    max_depth: 10
  
  # Complexity analyzer
  complexity:
    enabled: true
    metrics:
      - cyclomatic
      - cognitive
      - maintainability
      - halstead
  
  # History analyzer
  history:
    enabled: true
    branch: "main"
    since: null  # null = entire history
    until: null  # null = HEAD
    max_commits: 1000
  
  # Hotspots detector
  hotspots:
    enabled: true
    complexity_threshold: 10
    change_threshold: 5
    coupling_threshold: 3
  
  # CI/QM analyzer
  ci_qm:
    enabled: true
    ci_files:
      - ".github/workflows/**"
      - ".gitlab-ci.yml"
      - "Jenkinsfile"
      - "azure-pipelines.yml"
  
  # Weakness detector
  weakness:
    enabled: true
    patterns:
      - "TODO"
      - "FIXME"
      - "HACK"
      - "XXX"

# Output configuration
output:
  # Output directory
  directory: "output"
  
  # Output formats
  formats:
    - markdown
    - json
    - jsonld
    - turtle
  
  # Report options
  report:
    include_recommendations: true
    include_examples: true
    include_metrics_table: true
    include_graphs: true
  
  # RDF/Semantic Web options
  rdf:
    base_uri: "http://example.org/analysis/"
    namespaces:
      repoq: "http://repoq.dev/ontology#"
      prov: "http://www.w3.org/ns/prov#"
      oslc: "http://open-services.net/ns/cm#"
      spdx: "http://spdx.org/rdf/terms#"

# Ontology configuration
ontology:
  # Enable ontological analysis
  enabled: true
  
  # Pattern detection
  patterns:
    enabled: true
    confidence_threshold: 0.7
    detect:
      - creational
      - structural
      - behavioral
      - architectural
  
  # Domain modeling
  domain:
    detect_bounded_contexts: true
    detect_entities: true
    detect_value_objects: true
    detect_services: true

# BAML AI Agent configuration (Phase 5.8)
ai_agent:
  # Agent phase: disabled, experimental, advisory, active, default_on
  phase: "disabled"
  
  # Confidence threshold for blocking
  confidence_threshold: 0.8
  
  # Require human review for critical issues
  require_human_review: true
  
  # Enable fallback chain (GPT-4 -> Claude -> GPT-4-mini)
  enable_fallback: true
  
  # Timeout for AI requests (seconds)
  timeout_seconds: 30

# Logging configuration
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  format: "%(levelname)s: %(message)s"
  file: null  # null = stdout only, or specify path

# Performance tuning
performance:
  # Parallel processing
  max_workers: 4
  
  # Memory limits
  max_memory_mb: 2048
  
  # Cache configuration
  cache:
    enabled: true
    ttl_seconds: 3600
    directory: ".repoq/cache"
```

## CLI Flags

### Global Flags

Available for all commands:

```bash
# Configuration file
repoq --config path/to/config.yaml <command>

# Output directory
repoq --output output/ <command>

# Verbosity
repoq --verbose <command>
repoq --quiet <command>

# Log level
repoq --log-level DEBUG <command>

# Version
repoq --version
```

### Command-Specific Flags

#### `repoq structure`

```bash
# Include/exclude patterns
repoq structure /path/to/repo --include "src/**" --exclude "tests/**"

# Maximum depth
repoq structure /path/to/repo --max-depth 5

# Output format
repoq structure /path/to/repo --format json
repoq structure /path/to/repo --format jsonld
repoq structure /path/to/repo --format turtle

# Enable/disable ontology
repoq structure /path/to/repo --ontology / --no-ontology
```

#### `repoq complexity`

```bash
# Specific metrics
repoq complexity /path/to/repo --metrics cyclomatic,cognitive

# Thresholds
repoq complexity /path/to/repo --cyclomatic-max 15 --cognitive-max 20

# Sort results
repoq complexity /path/to/repo --sort-by complexity
```

#### `repoq history`

```bash
# Time range
repoq history /path/to/repo --since "2024-01-01" --until "2024-12-31"

# Specific branch
repoq history /path/to/repo --branch develop

# Author filter
repoq history /path/to/repo --authors "alice,bob"

# Limit commits
repoq history /path/to/repo --max-commits 100
```

#### `repoq hotspots`

```bash
# Thresholds
repoq hotspots /path/to/repo --complexity-threshold 15 --change-threshold 10

# Minimum hotspot score
repoq hotspots /path/to/repo --min-score 7.0

# Top N results
repoq hotspots /path/to/repo --top 10
```

#### `repoq analyze` (Full Analysis)

```bash
# Run all analyzers
repoq analyze /path/to/repo

# Select specific analyzers
repoq analyze /path/to/repo --analyzers structure,complexity,hotspots

# Disable specific analyzers
repoq analyze /path/to/repo --no-history --no-ci-qm
```

## Environment Variables

### API Keys (for BAML AI Agent)

```bash
# OpenAI API key
export OPENAI_API_KEY="sk-..."

# Anthropic (Claude) API key
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Configuration Overrides

```bash
# Override output directory
export REPOQ_OUTPUT_DIR="/tmp/repoq-output"

# Override log level
export REPOQ_LOG_LEVEL="DEBUG"

# Override cache directory
export REPOQ_CACHE_DIR="/tmp/repoq-cache"
```

### Example Usage

```bash
# Set API keys in .env file
echo "OPENAI_API_KEY=sk-..." >> .env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env

# Load environment variables
source .env

# Run analysis with AI agent
repoq analyze /path/to/repo --config quality_policy.yaml
```

## Configuration Precedence

RepoQ uses the following precedence (highest to lowest):

1. **CLI flags**: `--option value`
2. **Environment variables**: `REPOQ_OPTION=value`
3. **Config file**: `quality_policy.yaml`
4. **Defaults**: Built-in defaults

**Example:**

```bash
# Config file sets: cyclomatic_max = 15
# Environment sets: REPOQ_CYCLOMATIC_MAX = 20
# CLI flag sets: --cyclomatic-max 10

# Result: cyclomatic_max = 10 (CLI wins)
```

## Configuration Examples

### Minimal Configuration

```yaml
# Bare minimum configuration
project:
  name: "MyProject"

quality:
  complexity:
    cyclomatic_max: 15

output:
  directory: "output"
```

### CI/CD Configuration

```yaml
# Optimized for CI/CD pipelines
project:
  name: "MyProject"

quality:
  score:
    fail_below: 7.0

analyzers:
  structure:
    enabled: true
  complexity:
    enabled: true
  history:
    enabled: false  # Skip in CI for speed
  hotspots:
    enabled: false  # Skip in CI for speed

output:
  directory: "ci-reports"
  formats:
    - json  # Machine-readable for CI

logging:
  level: "WARNING"  # Reduce noise in CI logs

performance:
  max_workers: 2  # Limit CPU usage in CI
```

### Strict Quality Policy

```yaml
# Strict quality requirements
project:
  name: "HighQualityProject"

quality:
  complexity:
    cyclomatic_max: 10
    cognitive_max: 15
    function_length_max: 30
  
  maintainability:
    index_min: 75.0
    comment_ratio_min: 0.2
  
  testing:
    coverage_min: 0.9  # 90% coverage
  
  score:
    target: 9.0
    fail_below: 8.0

analyzers:
  weakness:
    enabled: true
    patterns:
      - "TODO"
      - "FIXME"
      - "HACK"
      - "XXX"
      - "print("  # No debug prints in production
```

### Research/Experimentation Configuration

```yaml
# For research and experimentation
project:
  name: "ResearchProject"

quality:
  score:
    fail_below: 0.0  # Never fail

analyzers:
  structure:
    enabled: true
    max_depth: 99  # Unlimited depth
  
  history:
    enabled: true
    max_commits: 10000  # Deep history

ontology:
  enabled: true
  patterns:
    confidence_threshold: 0.5  # Lower threshold

ai_agent:
  phase: "experimental"  # Enable AI agent for testing

output:
  formats:
    - markdown
    - json
    - jsonld
    - turtle
    - csv

logging:
  level: "DEBUG"
```

## Validating Configuration

```bash
# Check configuration syntax
repoq config validate quality_policy.yaml

# Show effective configuration (with all defaults)
repoq config show

# Show configuration for specific command
repoq config show structure
```

## Next Steps

- **[CLI Reference](commands.md)**: Complete list of commands
- **[Workflows](workflows.md)**: Common configuration patterns
- **[Tutorials](../tutorials/)**: Step-by-step guides
- **[API Reference](../api/reference.md)**: Programmatic configuration

!!! tip "Best Practice"
    Start with a minimal configuration and gradually add constraints as your project matures. Use CI/CD integration to enforce quality gates.
