.PHONY: help install test lint format type-check security pre-commit clean

# Default target
help:
	@echo "RepoQ Development Tasks"
	@echo ""
	@echo "Setup:"
	@echo "  install         Install all dependencies with uv"
	@echo "  pre-commit      Install pre-commit hooks"
	@echo ""
	@echo "Testing:"
	@echo "  test            Run all tests"
	@echo "  test-unit       Run unit tests only (fast)"
	@echo "  test-smoke      Run smoke tests (critical)"
	@echo "  test-integration Run integration tests"
	@echo "  test-e2e        Run end-to-end tests"
	@echo "  test-cov        Run tests with coverage report"
	@echo ""
	@echo "Quality:"
	@echo "  lint            Run ruff linter"
	@echo "  format          Format code with ruff"
	@echo "  type-check      Run mypy type checker"
	@echo "  security        Run bandit security checks"
	@echo "  check-all       Run all quality checks"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean           Remove generated files"
	@echo "  docs            Build documentation"

# Setup
install:
	uv sync --all-extras

pre-commit:
	uv run pre-commit install
	@echo "✓ Pre-commit hooks installed"

# Testing
test:
	uv run pytest tests/ -v

test-unit:
	uv run pytest tests/unit/ -v -m "unit or smoke"

test-smoke:
	uv run pytest tests/unit/test_smoke.py -v -m smoke

test-integration:
	uv run pytest tests/integration/ -v -m integration

test-e2e:
	uv run pytest tests/e2e/ -v -m e2e

test-cov:
	uv run pytest tests/ --cov=repoq --cov-report=html --cov-report=term

test-parallel:
	uv run pytest tests/ -n auto -v

# Quality checks
lint:
	uv run ruff check repoq/ tests/

lint-fix:
	uv run ruff check --fix repoq/ tests/

format:
	uv run ruff format repoq/ tests/

format-check:
	uv run ruff format --check repoq/ tests/

type-check:
	uv run mypy repoq/ --config-file=pyproject.toml

security:
	uv run bandit -r repoq/ -c pyproject.toml

check-all: lint format-check type-check security test-smoke
	@echo "✓ All quality checks passed"

# Pre-commit
pre-commit-run:
	uv run pre-commit run --all-files

pre-commit-update:
	uv run pre-commit autoupdate

# Documentation
docs:
	uv run mkdocs build

docs-serve:
	uv run mkdocs serve

# Self-analysis
analyze-self:
	uv run repoq analyze . \
		--exclude "site/**,tmp/**,artifacts/**,.venv/**,*.jsonld,*.md" \
		--extensions py \
		--output repoq_analysis.jsonld \
		--md repoq_analysis.md

# Maintenance
clean:
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf site
	rm -rf dist
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete

clean-all: clean
	rm -rf .venv
	rm -rf uv.lock

# CI simulation
ci: check-all test-cov
	@echo "✓ CI checks passed"

# Development workflow
dev-check: format lint test-unit
	@echo "✓ Quick development checks passed"
