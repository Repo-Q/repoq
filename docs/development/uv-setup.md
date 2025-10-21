# uv Setup Guide

This project uses [uv](https://github.com/astral-sh/uv) for fast, reliable Python package management.

## Installation

### Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip
pip install uv
```

### Install Project Dependencies

```bash
# Install all dependencies (including dev and docs)
uv sync --all-groups --all-extras

# Install only production dependencies
uv sync --extra full

# Install dev dependencies only
uv sync --group dev
```

## Usage

### Run Commands

```bash
# Run pytest
uv run pytest tests/

# Run mkdocs server
uv run mkdocs serve

# Run repoq CLI
uv run repoq --help

# Run any Python script
uv run python script.py
```

### Add Dependencies

```bash
# Add production dependency
uv add package-name

# Add dev dependency
uv add --group dev package-name

# Add optional dependency
uv add --optional full package-name
```

### Update Dependencies

```bash
# Update all dependencies
uv sync --upgrade

# Update specific package
uv add --upgrade package-name
```

## Lock File

`uv.lock` contains pinned versions of all dependencies. This ensures reproducible builds across environments.

- **Commit `uv.lock`** to version control
- **Update lock file**: `uv lock --upgrade`
- **Verify lock file**: `uv lock --check`

## Benefits of uv

1. **Speed**: 10-100x faster than pip
2. **Reliability**: Deterministic resolution with lock file
3. **Simplicity**: Single tool for package management
4. **Compatibility**: Works with existing `pyproject.toml`

## Migration from pip/venv

If you have an existing `requirements.txt`:

```bash
# Convert to pyproject.toml
uv init

# Install from requirements.txt
uv pip install -r requirements.txt

# Generate lock file
uv lock
```

## Troubleshooting

### ModuleNotFoundError

```bash
# Reinstall dependencies
uv sync --all-groups --all-extras --reinstall
```

### Lock file out of sync

```bash
# Regenerate lock file
uv lock --upgrade
```

### Python version issues

```bash
# Specify Python version
uv venv --python 3.11
uv sync --python 3.11
```

## Resources

- [uv Documentation](https://docs.astral.sh/uv/)
- [uv GitHub](https://github.com/astral-sh/uv)
- [pyproject.toml Spec](https://peps.python.org/pep-0621/)
