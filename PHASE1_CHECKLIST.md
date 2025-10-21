"""
Phase 1 Sprint 1 Checklist

Duration: Week 1-2
Goal: Testing Infrastructure → Coverage 50%+
Status: 🔴 Not Started
"""

## Week 1: Foundation (Days 1-5)

### Day 1-2: Test Infrastructure Setup
- [ ] Create test directory structure
  - [ ] `tests/analyzers/` (unit tests)
  - [ ] `tests/core/` (unit tests)
  - [ ] `tests/properties/` (property-based)
  - [ ] `tests/integration/` (end-to-end)
  - [ ] `tests/fixtures/` (shared test data)

- [ ] Configure pytest
  - [ ] Add `pytest.ini` with coverage settings
  - [ ] Install `pytest-cov`, `hypothesis`, `pytest-mock`
  - [ ] Setup coverage reporting (HTML + XML)

- [ ] Create mock repositories
  - [ ] `tests/fixtures/mock_repo_simple/` (5 files)
  - [ ] `tests/fixtures/mock_repo_complex/` (50+ files, multiple languages)
  - [ ] `tests/fixtures/mock_repo_edge_cases/` (empty files, symlinks, etc.)

**Deliverable**: 
```bash
pytest --cov=repoq --cov-report=term-missing
# Target: 10% coverage (baseline)
```

### Day 3-4: StructureAnalyzer Tests
- [ ] Implement `test_structure.py` (15 tests)
  - [ ] `test_analyzer_initialization`
  - [ ] `test_run_on_empty_project`
  - [ ] `test_detects_python_files`
  - [ ] `test_detects_test_files`
  - [ ] `test_creates_modules`
  - [ ] `test_respects_max_files_limit`
  - [ ] `test_respects_extension_filter`
  - [ ] `test_respects_exclude_globs`
  - [ ] `test_computes_lines_of_code`
  - [ ] `test_detects_programming_languages`
  - [ ] `test_idempotent_execution`
  - [ ] `test_handles_empty_directory`
  - [ ] `test_file_id_uniqueness`
  - [ ] `test_module_id_uniqueness`
  - [ ] `test_module_hierarchy_valid`

**Deliverable**: 
```bash
pytest tests/analyzers/test_structure.py -v
# All tests pass, coverage 60%+ for structure.py
```

### Day 5: ComplexityAnalyzer Tests
- [ ] Implement `test_complexity.py` (10 tests)
  - [ ] `test_complexity_non_negative`
  - [ ] `test_maintainability_computed`
  - [ ] `test_handles_invalid_syntax`
  - [ ] `test_lizard_integration`
  - [ ] `test_radon_integration`
  - [ ] `test_complexity_threshold_detection`
  - [ ] `test_skips_non_code_files`
  - [ ] `test_idempotent_execution`
  - [ ] `test_updates_existing_files`
  - [ ] `test_handles_missing_lizard`

**Deliverable**: Coverage 30%+ for project

---

## Week 2: Core Analyzers (Days 6-10)

### Day 6: HistoryAnalyzer Tests
- [ ] Implement `test_history.py` (10 tests)
  - [ ] `test_detects_commits`
  - [ ] `test_respects_since_filter`
  - [ ] `test_computes_code_churn`
  - [ ] `test_identifies_contributors`
  - [ ] `test_computes_contributor_stats`
  - [ ] `test_handles_merge_commits`
  - [ ] `test_handles_empty_history`
  - [ ] `test_commit_chronology`
  - [ ] `test_author_email_hashing`
  - [ ] `test_pydriller_integration`

### Day 7: WeaknessAnalyzer & HotspotsAnalyzer Tests
- [ ] Implement `test_weakness.py` (8 tests)
  - [ ] `test_detects_todos`
  - [ ] `test_detects_fixmes`
  - [ ] `test_detects_deprecated`
  - [ ] `test_severity_mapping`
  - [ ] `test_creates_issues`
  - [ ] `test_links_issues_to_files`
  - [ ] `test_handles_binary_files`
  - [ ] `test_respects_exclude_patterns`

- [ ] Implement `test_hotspots.py` (6 tests)
  - [ ] `test_computes_hotness_score`
  - [ ] `test_normalizes_scores`
  - [ ] `test_requires_prior_analysis`
  - [ ] `test_top_n_hotspots`
  - [ ] `test_handles_missing_metrics`
  - [ ] `test_deterministic_ranking`

### Day 8: CI/QM Analyzer Tests
- [ ] Implement `test_ci_qm.py` (8 tests)
  - [ ] `test_detects_ci_configs`
  - [ ] `test_parses_junit_xml`
  - [ ] `test_creates_test_cases`
  - [ ] `test_creates_test_results`
  - [ ] `test_handles_invalid_junit`
  - [ ] `test_handles_missing_ci`
  - [ ] `test_status_mapping`
  - [ ] `test_links_tests_to_files`

### Day 9-10: Core & Integration Tests
- [ ] Implement `test_model.py` (10 tests)
  - [ ] `test_project_initialization`
  - [ ] `test_file_dataclass_invariants`
  - [ ] `test_person_email_hashing`
  - [ ] `test_foaf_sha1_computation`
  - [ ] `test_issue_severity_enum`
  - [ ] `test_to_dict_serialization`
  - [ ] `test_module_hierarchy`
  - [ ] `test_dependency_edge_creation`
  - [ ] `test_coupling_edge_creation`
  - [ ] `test_version_resource`

- [ ] Implement `test_jsonld.py` (8 tests)
  - [ ] `test_to_jsonld_basic`
  - [ ] `test_context_loading`
  - [ ] `test_context_merging`
  - [ ] `test_field33_context`
  - [ ] `test_oslc_severity_mapping`
  - [ ] `test_spdx_checksum_format`
  - [ ] `test_prov_commit_format`
  - [ ] `test_foaf_person_format`

- [ ] Implement `test_pipelines.py` (6 tests)
  - [ ] `test_structure_mode_pipeline`
  - [ ] `test_history_mode_pipeline`
  - [ ] `test_full_mode_pipeline`
  - [ ] `test_pipeline_order`
  - [ ] `test_pipeline_with_errors`
  - [ ] `test_pipeline_partial_completion`

**Deliverable**: 
```bash
pytest --cov=repoq --cov-report=html
# Target: 60%+ coverage
open htmlcov/index.html
```

---

## Week 3-4: Advanced Testing (Days 11-20)

### Property-Based Tests (Days 11-13)
- [ ] Setup Hypothesis
- [ ] Implement 10 property tests (see `test_analyzers_properties.py`)
- [ ] Add invariant checks:
  - [ ] All IDs are unique
  - [ ] All paths are relative
  - [ ] All metrics are non-negative
  - [ ] Module hierarchy is acyclic
  - [ ] Coupling is symmetric

### Integration Tests (Days 14-16)
- [ ] CLI tests (8 scenarios)
  - [ ] `test_cli_structure_command`
  - [ ] `test_cli_history_command`
  - [ ] `test_cli_full_command`
  - [ ] `test_cli_with_graphs`
  - [ ] `test_cli_with_ttl`
  - [ ] `test_cli_with_validation`
  - [ ] `test_cli_fail_on_issues`
  - [ ] `test_cli_invalid_args`

### Performance Tests (Days 17-18)
- [ ] Create `tests/benchmarks/`
- [ ] Benchmark each analyzer
- [ ] Set baseline performance targets
- [ ] Add regression tracking

### CI Setup (Days 19-20)
- [ ] Configure GitHub Actions (`.github/workflows/ci.yml`)
- [ ] Add multi-Python version matrix (3.9-3.12)
- [ ] Setup Codecov integration
- [ ] Add lint checks (ruff, black, mypy)
- [ ] Add security scans (bandit, safety)
- [ ] Configure self-hosting job

**Deliverable**: 
```bash
# Local CI simulation
act -j test  # if using act
# OR
git push  # triggers GitHub Actions
# Target: All checks green, coverage ≥70%
```

---

## Acceptance Criteria (Phase 1 Complete)

✅ **DONE when**:
- [ ] Coverage ≥ 70% (target: 80%)
- [ ] All analyzers have ≥8 unit tests
- [ ] ≥10 property-based tests implemented
- [ ] CI passes on Python 3.9-3.12
- [ ] Codecov badge shows ≥70%
- [ ] Self-hosting workflow runs successfully
- [ ] No critical security issues (bandit/safety)
- [ ] Documentation updated with testing guide

---

## Commands Cheat Sheet

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=repoq --cov-report=term-missing --cov-report=html

# Run specific test file
pytest tests/analyzers/test_structure.py -v

# Run property tests only
pytest tests/properties/ -v

# Run integration tests
pytest tests/integration/ -v

# Run with verbose output
pytest -vv --tb=short

# Run failed tests only
pytest --lf

# Parallel execution (faster)
pytest -n auto

# Generate coverage report
coverage report -m
coverage html

# Type checking
mypy repoq/

# Linting
ruff check .
ruff check . --fix

# Formatting
black .
black --check .

# Security scan
bandit -r repoq/
safety check
```

---

## Dependencies to Install

```bash
# Core testing
pip install pytest pytest-cov pytest-mock pytest-xdist

# Property-based testing
pip install hypothesis

# Coverage
pip install coverage[toml]

# Linting & formatting
pip install ruff black mypy types-PyYAML

# Security
pip install bandit safety

# Full dev environment
pip install -e ".[full,dev]"
```

---

## Next Phase Preview

After Phase 1 (testing ≥70%), proceed to **Phase 2: Formalization**:
- Week 5-6: OML ontology specification
- Week 7-8: Lean4 soundness proofs
- Week 9: Stratification of reflection levels
- Week 10: Confluence verification

**Status tracking**: Update this checklist daily. Mark ✅ when item is completed and verified.

**Last updated**: 2025-10-20 (Phase 0)
