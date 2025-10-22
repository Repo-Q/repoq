# Tutorial 4: Advanced Filtering

!!! tip "Learning Objectives"
    - Master file filtering patterns
    - Use tree-sitter for AST-based filtering
    - Create complex filter expressions
    - Optimize analysis performance

## Prerequisites

- Basic glob pattern knowledge
- Understanding of Abstract Syntax Trees (optional)
- Completed [Tutorial 1: First Analysis](01-first-analysis.md)

## Why Filtering Matters

Filtering helps you:
- **Focus analysis**: Target specific code areas
- **Improve performance**: Skip irrelevant files
- **Reduce noise**: Exclude generated/vendor code
- **Custom workflows**: Different filters for different purposes

## Basic Glob Patterns

### Include Patterns

```bash
# Python files only
repoq analyze . --filter "**/*.py"

# JavaScript and TypeScript
repoq analyze . --filter "**/*.{js,ts,jsx,tsx}"

# Specific directory
repoq analyze . --filter "src/**/*"

# Multiple patterns
repoq analyze . \
  --filter "src/**/*.py" \
  --filter "lib/**/*.py"
```

### Exclude Patterns

```bash
# Exclude tests
repoq analyze . --exclude "tests/**"

# Exclude multiple
repoq analyze . \
  --exclude "tests/**" \
  --exclude "**/__pycache__/**" \
  --exclude "*.pyc"

# Exclude generated code
repoq analyze . \
  --exclude "**/migrations/**" \
  --exclude "**/*_pb2.py" \
  --exclude "**/node_modules/**"
```

### Combined Filters

```bash
# Include Python in src/, exclude tests
repoq analyze . \
  --filter "src/**/*.py" \
  --exclude "src/tests/**"

# Complex pattern
repoq analyze . \
  --filter "**/*.{py,js}" \
  --exclude "tests/**" \
  --exclude "build/**" \
  --exclude "dist/**" \
  --exclude "**/vendor/**"
```

## Glob Pattern Reference

### Wildcards

| Pattern | Matches | Example |
|---------|---------|---------|
| `*` | Any characters (not `/`) | `*.py` matches `foo.py` |
| `**` | Any directories | `src/**/*.py` matches `src/a/b/c.py` |
| `?` | Single character | `file?.py` matches `file1.py` |
| `[abc]` | Character set | `file[123].py` matches `file2.py` |
| `{a,b}` | Alternatives | `*.{py,js}` matches both |

### Examples

```bash
# All Python files in any subdirectory
**/*.py

# Python files in src/ at any depth
src/**/*.py

# Test files (multiple patterns)
**/test_*.py
**/*_test.py

# Exclude patterns
!tests/**           # NOT in tests/
!**/migrations/**   # NOT migrations anywhere
```

## Configuration File Filters

### quality_policy.yaml

```yaml
# Global filters
filters:
  include:
    - "src/**/*.py"
    - "lib/**/*.py"
  
  exclude:
    - "tests/**"
    - "**/__pycache__/**"
    - "**/migrations/**"
    - "**/*_pb2.py"  # Protocol buffers
    - "**/node_modules/**"

# Analyzer-specific filters
analyzers:
  complexity:
    enabled: true
    filters:
      include:
        - "src/**/*.py"
      exclude:
        - "src/generated/**"
  
  security:
    enabled: true
    filters:
      include:
        - "**/*.py"
        - "**/*.js"
      exclude:
        - "tests/**"  # Don't check test fixtures
```

**Use with CLI:**
```bash
repoq analyze . --config quality_policy.yaml
```

## Tree-sitter AST Filtering

For advanced filtering based on code structure:

### Filter by Complexity

```bash
# Only analyze complex functions (cyclomatic > 10)
repoq analyze . --ast-filter "complexity > 10"

# High cognitive complexity
repoq analyze . --ast-filter "cognitive_complexity > 15"
```

### Filter by Function Characteristics

```python
# filter_expr.py - Custom AST filter

from tree_sitter import Language, Parser
import tree_sitter_python as tspython

def filter_functions(code):
    """Return functions matching criteria."""
    
    parser = Parser()
    parser.set_language(Language(tspython.language()))
    
    tree = parser.parse(bytes(code, "utf8"))
    
    functions = []
    
    def visit(node):
        if node.type == 'function_definition':
            # Get function name
            name_node = node.child_by_field_name('name')
            name = code[name_node.start_byte:name_node.end_byte]
            
            # Get parameters
            params = node.child_by_field_name('parameters')
            param_count = len([c for c in params.children if c.type == 'identifier'])
            
            # Filter criteria
            if param_count > 3:  # Functions with > 3 parameters
                functions.append({
                    'name': name,
                    'line': node.start_point[0] + 1,
                    'params': param_count,
                })
        
        for child in node.children:
            visit(child)
    
    visit(tree.root_node)
    return functions
```

### Filter by Patterns

```bash
# Functions with specific decorators
repoq analyze . --ast-filter "has_decorator('@api_endpoint')"

# Classes inheriting from BaseModel
repoq analyze . --ast-filter "inherits_from('BaseModel')"

# Functions with many branches
repoq analyze . --ast-filter "branch_count > 5"
```

## Performance Optimization

### Depth Limiting

```bash
# Analyze only 2 levels deep
repoq analyze . --max-depth 2

# Example directory structure:
# ./                    depth=0
# ./src/                depth=1
# ./src/core/           depth=2
# ./src/core/utils/     depth=3 (skipped)
```

### File Size Limits

```bash
# Skip files > 100KB
repoq analyze . --max-file-size 102400

# Skip large and binary files
repoq analyze . \
  --max-file-size 1048576 \
  --exclude "*.png" \
  --exclude "*.jpg" \
  --exclude "*.pdf"
```

### Parallel Processing

```bash
# Use 8 parallel workers
repoq analyze . --max-workers 8

# Auto-detect CPU cores
repoq analyze . --max-workers auto
```

## Context-Aware Filtering

### Git-Based Filtering

```bash
# Only analyze changed files since last commit
git diff --name-only HEAD~1 | repoq analyze --files -

# Files changed in PR
git diff --name-only origin/main...HEAD \
  | grep "\.py$" \
  | repoq analyze --files -

# Recently modified (last 7 days)
find . -name "*.py" -mtime -7 \
  | repoq analyze --files -
```

### Hotspot-Driven Filtering

```bash
# 1. Find hotspots
repoq analyze . --output initial/

# 2. Extract hotspot files
jq -r '.hotspots[].file' initial/analysis.json > hotspot_files.txt

# 3. Analyze only hotspots
repoq analyze . --files-from hotspot_files.txt
```

## Custom Filter Functions

### Python Filter Script

```python
# custom_filter.py

import os
from pathlib import Path
from typing import List

def should_analyze(file_path: Path) -> bool:
    """Custom filter logic."""
    
    # Skip if not Python
    if file_path.suffix != '.py':
        return False
    
    # Skip test files
    if 'test' in file_path.stem.lower():
        return False
    
    # Skip if no docstring (quick check)
    try:
        with file_path.open() as f:
            first_line = f.readline().strip()
            if not first_line.startswith('"""'):
                return False  # No module docstring
    except Exception:
        return False
    
    # Skip small files (< 10 lines)
    try:
        line_count = sum(1 for _ in file_path.open())
        if line_count < 10:
            return False
    except Exception:
        return False
    
    return True

def get_files_to_analyze(root: Path) -> List[Path]:
    """Get filtered file list."""
    files = []
    
    for path in root.rglob('*.py'):
        if should_analyze(path):
            files.append(path)
    
    return files

if __name__ == '__main__':
    root = Path('.')
    files = get_files_to_analyze(root)
    
    # Write to file
    with open('filtered_files.txt', 'w') as f:
        for file_path in files:
            f.write(f"{file_path}\n")
    
    print(f"Found {len(files)} files to analyze")
```

**Use with RepoQ:**
```bash
python custom_filter.py
repoq analyze . --files-from filtered_files.txt
```

## Conditional Analysis

### Environment-Based

```bash
# Different filters for CI vs local
if [ "$CI" = "true" ]; then
  # CI: Analyze everything
  repoq analyze .
else
  # Local: Quick analysis
  repoq analyze . \
    --filter "src/**/*.py" \
    --exclude "tests/**" \
    --max-depth 3
fi
```

### Branch-Based

```bash
# Main branch: Full analysis
if [ "$(git branch --show-current)" = "main" ]; then
  repoq analyze . --all-analyzers --verbose

# Feature branches: Quick check
else
  git diff --name-only origin/main...HEAD \
    | grep "\.py$" \
    | repoq analyze --files - --quick
fi
```

## Filter Profiles

### .repoqrc

Create reusable filter profiles:

```yaml
# .repoqrc
profiles:
  full:
    filters:
      include: ["**/*"]
      exclude: ["tests/**", "**/node_modules/**"]
    analyzers: ["all"]
  
  quick:
    filters:
      include: ["src/**/*.py"]
      exclude: ["tests/**", "**/migrations/**"]
    analyzers: ["structure", "complexity"]
    max_depth: 3
  
  hotspots:
    filters:
      include: ["src/**/*.py"]
    analyzers: ["complexity", "history", "hotspots"]
  
  security:
    filters:
      include: ["**/*.{py,js}"]
      exclude: ["tests/**"]
    analyzers: ["security", "weakness"]
```

**Use profiles:**
```bash
# Full analysis
repoq analyze . --profile full

# Quick check
repoq analyze . --profile quick

# Security audit
repoq analyze . --profile security
```

## Real-World Examples

### Django Project

```bash
repoq analyze . \
  --filter "**/*.py" \
  --exclude "**/migrations/**" \
  --exclude "**/tests/**" \
  --exclude "manage.py" \
  --exclude "**/settings/*.py"
```

### React/TypeScript Project

```bash
repoq analyze . \
  --filter "src/**/*.{ts,tsx}" \
  --exclude "**/*.test.{ts,tsx}" \
  --exclude "**/*.spec.{ts,tsx}" \
  --exclude "**/node_modules/**" \
  --exclude "build/**"
```

### Monorepo

```bash
# Analyze specific service
repoq analyze . \
  --filter "services/api/**/*.py" \
  --exclude "services/api/tests/**"

# Analyze all services
for service in services/*/; do
  echo "Analyzing $service"
  repoq analyze "$service" \
    --filter "**/*.py" \
    --exclude "tests/**" \
    --output "reports/$(basename $service)"
done
```

## Debugging Filters

### Dry Run

```bash
# See which files would be analyzed
repoq analyze . \
  --filter "src/**/*.py" \
  --exclude "tests/**" \
  --dry-run

# Output:
# Would analyze 45 files:
#   src/core/main.py
#   src/core/utils.py
#   src/api/routes.py
#   ...
```

### Verbose Filtering

```bash
# Show filter decisions
repoq analyze . \
  --filter "**/*.py" \
  --exclude "tests/**" \
  --verbose-filter

# Output:
# ✓ src/main.py (matches filter)
# ✗ tests/test_main.py (excluded)
# ✓ src/utils.py (matches filter)
# ✗ build/lib.py (excluded)
```

## Best Practices

### 1. Start Broad, Then Narrow

```bash
# 1. Full analysis to understand codebase
repoq analyze .

# 2. Focus on problem areas
repoq analyze . --filter "src/problematic/**"

# 3. Target specific issues
repoq analyze . --filter "src/problematic/hotspot.py"
```

### 2. Use Configuration Files

**Bad** (command gets unwieldy):
```bash
repoq analyze . --filter "**/*.py" --exclude "tests/**" --exclude "**/migrations/**" --exclude "vendor/**" --max-depth 5 --max-workers 4
```

**Good** (use config):
```yaml
# quality_policy.yaml
filters:
  include: ["**/*.py"]
  exclude: ["tests/**", "**/migrations/**", "vendor/**"]

performance:
  max_depth: 5
  max_workers: 4
```

```bash
repoq analyze . --config quality_policy.yaml
```

### 3. Document Filter Rationale

```yaml
# quality_policy.yaml
filters:
  exclude:
    # Auto-generated by protobuf compiler
    - "**/*_pb2.py"
    
    # Django migrations (schema history)
    - "**/migrations/**"
    
    # Third-party code (vendor)
    - "vendor/**"
    
    # Test fixtures (not production code)
    - "tests/fixtures/**"
```

## Next Steps

- **[Tutorial 5: RDF Queries](05-rdf-queries.md)** - Query analysis results
- **[Architecture: Analyzer Pipeline](../architecture/analyzer-pipeline.md)** - How filtering works internally
- **[User Guide: Configuration](../user-guide/configuration.md)** - Full configuration reference

## Summary

You learned how to:

- ✅ Use glob patterns for include/exclude filtering
- ✅ Apply tree-sitter AST-based filtering
- ✅ Optimize performance with depth/size limits
- ✅ Create context-aware filters (Git, hotspots)
- ✅ Build custom filter functions
- ✅ Use filter profiles for reusability

**Key Takeaways:**

1. **Glob patterns**: Master `**/*.ext` and exclude patterns
2. **Configuration**: Use YAML for complex filters
3. **Performance**: Limit depth, file size, and use parallelism
4. **Context**: Filter based on Git changes or hotspots
5. **Profiles**: Create reusable filter configurations

---

!!! tip "Filter Efficiently"
    Good filtering makes analysis 10x faster and results more actionable. Start with excludes (tests, vendor) before adding complex includes.
