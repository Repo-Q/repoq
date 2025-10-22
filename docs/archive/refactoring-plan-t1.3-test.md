# 🔧 Refactoring Plan

## Executive Summary

- **Current Q-score**: 0.00
- **Projected Q-score**: 100.00
- **Total ΔQ**: +407.0
- **Tasks**: 3

## Priority Breakdown

- **Critical**: 3 tasks

## Tasks

### Task #1: repoq/analyzers/history.py

**Priority**: 🔴 CRITICAL
**Expected ΔQ**: +153.0 points
**Estimated effort**: 4-8 hours (complex refactoring)

**Current metrics**:

- Complexity: 35.0
- LOC: 311
- TODOs: 0
- Issues: 1

**Issues**:

- High cyclomatic complexity (35.0)

**Recommendations**:

1. 🔴 Refactor function `_run_pydriller` (CCN=35, LOC=90, lines 89-203)
   → Expected ΔQ: +181.6 points (54% of file's potential)
   → Estimated effort: 3-4 hours
2. 🔴 Refactor function `_run_git` (CCN=30, LOC=102, lines 205-311)
   → Expected ΔQ: +151.2 points (45% of file's potential)
   → Estimated effort: 3-4 hours

### Task #2: repoq/core/jsonld.py

**Priority**: 🔴 CRITICAL
**Expected ΔQ**: +146.0 points
**Estimated effort**: 4-8 hours (complex refactoring)

**Current metrics**:

- Complexity: 33.0
- LOC: 396
- TODOs: 0
- Issues: 2

**Issues**:

- High cyclomatic complexity (33.0)

**Recommendations**:

1. 🔴 Refactor function `to_jsonld` (CCN=33, LOC=187, lines 68-336)
   → Expected ΔQ: +199.7 points (100% of file's potential)
   → Estimated effort: 3-4 hours

### Task #3: repoq/cli.py

**Priority**: 🔴 CRITICAL
**Expected ΔQ**: +108.0 points
**Estimated effort**: 4-8 hours (complex refactoring)

**Current metrics**:

- Complexity: 26.0
- LOC: 1535
- TODOs: 0
- Issues: 1

**Issues**:

- High cyclomatic complexity (26.0)
- Large file size (1535 LOC)

**Recommendations**:

1. 🔴 Refactor function `_run_command` (CCN=26, LOC=122, lines 593-772)
   → Expected ΔQ: +249.2 points (51% of file's potential)
   → Estimated effort: 3-4 hours
2. 🔴 Refactor function `_run_trs_verification` (CCN=16, LOC=53, lines 775-843)
   → Expected ΔQ: +96.2 points (20% of file's potential)
   → Estimated effort: 2-3 hours
3. 🟠 Refactor function `_handle_refactor_plan_output` (CCN=13, LOC=63, lines 1446-1530)
   → Expected ΔQ: +62.0 points (12% of file's potential)
   → Estimated effort: 1-2 hours
4. 📏 Consider splitting file (1535 LOC) into smaller modules (<300 LOC)

---

## Execution Strategy

1. **Critical tasks**: Fix immediately (blocking issues)
2. **High priority**: Include in current sprint
3. **Medium priority**: Plan for next sprint
4. **Low priority**: Backlog for future iterations

**Success criteria**:

- ✅ Q-score ≥ 100.00
- ✅ All critical tasks resolved
- ✅ No regression in test coverage
- ✅ PCQ ≥ 0.8 (gaming resistance)
