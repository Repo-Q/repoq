# CRITICAL TRS Violations Emergency Fix Plan

## Immediate Action Required - Mathematical Soundness Compromised

### 🚨 Critical Issue 1: Metrics TRS Idempotence Violation

**Problem**: `DecimalInvalidOperation` при больших числах нарушает idempotence
```python
# FAIL: canonicalize_metric(x) != canonicalize_metric(canonicalize_metric(x))
canonical1 = "-1"  
canonical2 = "error:-1"  # VIOLATION!
```

**Root Cause**: 
- `Decimal.quantize()` fails on extreme values (>10^87)
- No bounds checking in `MetricConstant.to_canonical()`
- Error propagation breaks mathematical properties

**Fix Priority**: P0 - blocks all metric analysis

### 🚨 Critical Issue 2: Filters TRS Confluence Violation  

**Problem**: Multiple canonical forms for same semantic input
```python
# EXPECTED: "glob:*.py"
# ACTUAL:   "glob:glob_pattern('*.py')"  # VIOLATION!
```

**Root Cause**:
- Inconsistent canonicalization in `canonicalize_filter()`
- Pattern subsumption logic errors
- Glob-to-regex conversion mismatch

**Fix Priority**: P0 - breaks filter semantic equivalence

### 🚨 Critical Issue 3: Mathematical Domain Violations

**Problem**: Division operations without domain validation
```python
# FAIL: Division by very small numbers causes overflow
result = lines / 3.3615777941063735E-88  # → Decimal overflow
```

**Root Cause**:
- No validation of arithmetic domain bounds
- SymPy integration without error handling
- Precision loss in canonical representations

## Emergency Fix Implementation

### Week 1 Critical Path:

1. **Metrics TRS Soundness** (Days 1-2):
   ```python
   # Add bounded canonical form
   def to_canonical(self) -> str:
       if abs(self.value) > Decimal("1E50"):
           return f"large:{self.value.to_eng_string()}"
       # ... existing logic
   ```

2. **Filters TRS Confluence** (Days 3-4):
   ```python  
   # Fix canonical form consistency
   def canonicalize_filter(pattern: str) -> str:
       # Ensure single canonical representation
       return f"glob:{_normalize_glob_pattern(pattern)}"
   ```

3. **Domain Validation** (Day 5):
   ```python
   # Add arithmetic bounds checking
   def _validate_arithmetic_domain(operands: List[MetricTerm]) -> bool:
       # Check for division by near-zero, overflow conditions
   ```

### Verification Strategy:

```bash
# Property-based testing with controlled domains
@given(bounded_decimal_strategy(min_value=-1E10, max_value=1E10))
def test_metrics_idempotence_bounded(value):
    # Ensure idempotence within safe domain
    
@given(valid_glob_pattern_strategy())  
def test_filters_confluence_controlled(pattern):
    # Test confluence with known-good patterns
```

## Mathematical Verification Requirements:

1. **Idempotence**: ∀x: f(f(x)) = f(x)
2. **Confluence**: ∀x,y: x ≡ y ⟹ f(x) = f(y)  
3. **Termination**: All rewriting chains must halt
4. **Domain Safety**: No undefined operations

## Success Criteria:

- ✅ All property-based tests pass with 0 failures
- ✅ Bounded domain arithmetic with explicit overflow handling
- ✅ Single canonical form per semantic equivalence class
- ✅ Mathematical proofs of TRS properties

**ETA**: 5 days for critical path, then proceed with test coverage expansion.

This is a PRODUCTION BLOCKER - no deployment until mathematical soundness is restored.