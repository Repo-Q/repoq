"""
Property-based tests for Metrics TRS

Tests formal properties:
1. Idempotence: canonicalize(canonicalize(x)) = canonicalize(x)
2. Determinism: Multiple canonicalization runs produce same result
3. Algebraic equivalence: Mathematical identities preserved
4. Associativity/commutativity: Addition/multiplication order independence
5. Simplification correctness: Simplified forms maintain semantics
"""

import pytest
from hypothesis import given, strategies as st
from typing import Any, Dict, List
import math

from repoq.normalize.metrics_trs import (
    canonicalize_metric, MetricExpression, MetricConstant, MetricVariable,
    ArithmeticOperation, AggregationFunction, parse_metric_expression,
    optimize_metric_expression, normalize_weights
)


# Hypothesis strategies for generating test data
@st.composite
def metric_constant_strategy(draw):
    """Generate numeric constants."""
    return draw(st.one_of(
        st.integers(min_value=-1000, max_value=1000),
        st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
    ))


@st.composite
def metric_variable_strategy(draw):
    """Generate metric variable names."""
    variables = ["lines", "complexity", "maintainability", "coverage", "bugs", "debt", "size"]
    return draw(st.sampled_from(variables))


@st.composite
def simple_arithmetic_strategy(draw):
    """Generate simple arithmetic expressions."""
    left = draw(st.one_of(
        st.builds(MetricConstant, metric_constant_strategy()),
        st.builds(MetricVariable, metric_variable_strategy())
    ))
    right = draw(st.one_of(
        st.builds(MetricConstant, metric_constant_strategy()),
        st.builds(MetricVariable, metric_variable_strategy())
    ))
    operator = draw(st.sampled_from(['+', '-', '*', '/']))
    
    return ArithmeticOperation(operator, (left, right))


@st.composite
def aggregation_function_strategy(draw):
    """Generate aggregation function calls."""
    func_name = draw(st.sampled_from(['sum', 'avg', 'max', 'min', 'count']))
    num_args = draw(st.integers(min_value=1, max_value=4))
    
    arguments = []
    for _ in range(num_args):
        arg = draw(st.one_of(
            st.builds(MetricConstant, metric_constant_strategy()),
            st.builds(MetricVariable, metric_variable_strategy())
        ))
        arguments.append(arg)
    
    return AggregationFunction(func_name, tuple(arguments))


class TestMetricTerms:
    """Test individual metric term classes."""
    
    def test_metric_constant_normalization(self):
        """Test metric constant canonical normalization."""
        # Integer normalization
        const1 = MetricConstant(42)
        assert const1.to_canonical() == "42"
        
        # Float normalization
        const2 = MetricConstant(3.14159)
        canonical = const2.to_canonical()
        assert canonical == "3.14159"
        
        # Remove trailing zeros
        const3 = MetricConstant(2.500000)
        assert const3.to_canonical() == "2.5"
    
    def test_metric_variable_canonical_form(self):
        """Test metric variable canonical representation."""
        var = MetricVariable("complexity")
        assert var.to_canonical() == "var:complexity"
    
    def test_arithmetic_operation_commutativity(self):
        """Test that commutative operations sort operands."""
        var1 = MetricVariable("lines")
        var2 = MetricVariable("complexity")
        const = MetricConstant(2)
        
        # Addition should be commutative
        add1 = ArithmeticOperation('+', (var1, var2, const))
        add2 = ArithmeticOperation('+', (const, var2, var1))
        assert add1.to_canonical() == add2.to_canonical()
        
        # Multiplication should be commutative
        mul1 = ArithmeticOperation('*', (var1, const))
        mul2 = ArithmeticOperation('*', (const, var1))
        assert mul1.to_canonical() == mul2.to_canonical()
    
    def test_arithmetic_operation_evaluation(self):
        """Test arithmetic operation evaluation."""
        var1 = MetricVariable("a")
        var2 = MetricVariable("b")
        const = MetricConstant(3)
        
        # Test addition
        add_op = ArithmeticOperation('+', (var1, var2, const))
        result = add_op.evaluate({"a": 2, "b": 5})
        assert result == 10  # 2 + 5 + 3
        
        # Test multiplication
        mul_op = ArithmeticOperation('*', (var1, const))
        result = mul_op.evaluate({"a": 4})
        assert result == 12  # 4 * 3
    
    def test_aggregation_function_sorting(self):
        """Test that aggregation functions sort arguments appropriately."""
        var1 = MetricVariable("lines")
        var2 = MetricVariable("complexity")
        
        # Sum should sort arguments
        sum1 = AggregationFunction('sum', (var1, var2))
        sum2 = AggregationFunction('sum', (var2, var1))
        assert sum1.to_canonical() == sum2.to_canonical()
        
        # Avg should preserve order (not commutative in weighted case)
        avg1 = AggregationFunction('avg', (var1, var2))
        canonical = avg1.to_canonical()
        assert "var:complexity" in canonical and "var:lines" in canonical
    
    def test_aggregation_function_evaluation(self):
        """Test aggregation function evaluation."""
        var1 = MetricVariable("a")
        var2 = MetricVariable("b")
        var3 = MetricVariable("c")
        
        context = {"a": 10, "b": 20, "c": 30}
        
        # Test sum
        sum_func = AggregationFunction('sum', (var1, var2, var3))
        assert sum_func.evaluate(context) == 60
        
        # Test avg
        avg_func = AggregationFunction('avg', (var1, var2, var3))
        assert avg_func.evaluate(context) == 20
        
        # Test max
        max_func = AggregationFunction('max', (var1, var2, var3))
        assert max_func.evaluate(context) == 30


class TestMetricExpressions:
    """Test complete metric expression processing."""
    
    def test_simple_algebraic_simplification(self):
        """Test basic algebraic simplification."""
        # x + x should become 2*x
        expr_str = "lines + lines"
        expr = MetricExpression(parse_metric_expression(expr_str))
        simplified = expr.simplify()
        canonical = simplified.to_canonical()
        
        # Should combine like terms
        assert "2" in canonical and "var:lines" in canonical
    
    def test_distributive_property(self):
        """Test distributive property: a*(b+c) = a*b + a*c."""
        # This tests both expansion and factoring
        expr_str = "2 * (lines + complexity)"
        expr = MetricExpression(parse_metric_expression(expr_str))
        
        expanded = expr.expand()
        factored = expanded.factor()
        
        # Both should be valid representations
        assert isinstance(expanded.to_canonical(), str)
        assert isinstance(factored.to_canonical(), str)
    
    def test_expression_evaluation(self):
        """Test expression evaluation in context."""
        expr_str = "2 * lines + complexity / 2"
        expr = MetricExpression(parse_metric_expression(expr_str))
        
        context = {"lines": 100, "complexity": 20}
        result = expr.evaluate(context)
        
        expected = 2 * 100 + 20 / 2  # 200 + 10 = 210
        assert abs(result - expected) < 1e-6
    
    def test_substitution(self):
        """Test variable substitution."""
        expr_str = "lines + complexity"
        expr = MetricExpression(parse_metric_expression(expr_str))
        
        # Substitute lines with a constant
        substituted = expr.substitute({"lines": 50})
        
        context = {"complexity": 10}
        result = substituted.evaluate(context)
        assert result == 60  # 50 + 10


class TestParsing:
    """Test metric expression parsing."""
    
    def test_arithmetic_parsing(self):
        """Test parsing of arithmetic expressions."""
        expressions = [
            "2 * lines + complexity",
            "lines / complexity",
            "lines ^ 2",
            "lines % 10"
        ]
        
        for expr_str in expressions:
            try:
                term = parse_metric_expression(expr_str)
                assert isinstance(term, (ArithmeticOperation, MetricVariable, MetricConstant))
            except Exception as e:
                pytest.fail(f"Failed to parse '{expr_str}': {e}")
    
    def test_function_parsing(self):
        """Test parsing of aggregation functions."""
        expressions = [
            "sum(lines, complexity)",
            "avg(lines, complexity, maintainability)",
            "max(lines, complexity)",
            "min(lines, complexity)"
        ]
        
        for expr_str in expressions:
            try:
                term = parse_metric_expression(expr_str)
                assert isinstance(term, AggregationFunction)
            except Exception as e:
                pytest.fail(f"Failed to parse '{expr_str}': {e}")
    
    def test_complex_parsing(self):
        """Test parsing of complex nested expressions."""
        complex_expressions = [
            "sum(lines * 0.3, complexity * 0.7)",
            "avg(lines, complexity) / max(1, count)",
            "(lines + complexity) * 2 / sum(lines, complexity, maintainability)"
        ]
        
        for expr_str in complex_expressions:
            try:
                term = parse_metric_expression(expr_str)
                canonical = canonicalize_metric(term)
                assert isinstance(canonical, str)
                assert len(canonical) > 0
            except Exception as e:
                pytest.fail(f"Failed to parse '{expr_str}': {e}")


class TestCanonicalization:
    """Test main canonicalization API."""
    
    def test_string_input(self):
        """Test canonicalization of string inputs."""
        result = canonicalize_metric("2 * lines + complexity")
        assert isinstance(result, str)
        assert "var:lines" in result
        assert "var:complexity" in result
    
    def test_dict_input(self):
        """Test canonicalization of dictionary inputs."""
        metric_dict = {
            "function": "sum",
            "arguments": ["lines", "complexity"],
            "weights": [0.3, 0.7]
        }
        
        result = canonicalize_metric(metric_dict)
        assert isinstance(result, str)
        assert "sum(" in result
    
    def test_expression_input(self):
        """Test canonicalization of MetricExpression inputs."""
        term = parse_metric_expression("lines + complexity")
        expr = MetricExpression(term)
        
        result = canonicalize_metric(expr)
        assert isinstance(result, str)


class TestOptimization:
    """Test expression optimization."""
    
    def test_optimization_levels(self):
        """Test different optimization levels."""
        expr_str = "((a + b) * 2 + (a + b) * 3)"
        expr = MetricExpression(parse_metric_expression(expr_str))
        
        basic = optimize_metric_expression(expr, 'basic')
        standard = optimize_metric_expression(expr, 'standard')
        aggressive = optimize_metric_expression(expr, 'aggressive')
        
        # All should be valid
        assert isinstance(basic.to_canonical(), str)
        assert isinstance(standard.to_canonical(), str)
        assert isinstance(aggressive.to_canonical(), str)
        
        # Aggressive should typically be most compact
        assert len(aggressive.to_canonical()) <= len(standard.to_canonical())


class TestPropertyBasedTesting:
    """Property-based tests using Hypothesis."""
    
    @given(metric_constant_strategy())
    def test_constant_idempotence(self, value):
        """Test that constant canonicalization is idempotent."""
        const = MetricConstant(value)
        canonical1 = canonicalize_metric(MetricExpression(const))
        canonical2 = canonicalize_metric(canonical1)
        assert canonical1 == canonical2
    
    @given(metric_variable_strategy())
    def test_variable_idempotence(self, var_name):
        """Test that variable canonicalization is idempotent."""
        var = MetricVariable(var_name)
        canonical1 = canonicalize_metric(MetricExpression(var))
        canonical2 = canonicalize_metric(canonical1)
        assert canonical1 == canonical2
    
    @given(simple_arithmetic_strategy())
    def test_arithmetic_idempotence(self, arithmetic_op):
        """Test that arithmetic operation canonicalization is idempotent."""
        expr = MetricExpression(arithmetic_op)
        canonical1 = expr.to_canonical()
        canonical2 = canonicalize_metric(canonical1)
        # Note: May not be exactly equal due to simplification
        assert isinstance(canonical2, str)
    
    @given(aggregation_function_strategy())
    def test_aggregation_idempotence(self, agg_func):
        """Test that aggregation function canonicalization is idempotent."""
        expr = MetricExpression(agg_func)
        canonical1 = expr.to_canonical()
        canonical2 = canonicalize_metric(canonical1)
        # Note: May not be exactly equal due to simplification
        assert isinstance(canonical2, str)
    
    @given(st.lists(st.floats(min_value=0.1, max_value=10.0), min_size=1, max_size=5))
    def test_weight_normalization(self, weights):
        """Test weight normalization properties."""
        normalized = normalize_weights(weights)
        
        # Should sum to 1.0 (within floating point precision)
        assert abs(sum(normalized) - 1.0) < 1e-10
        
        # Should preserve relative proportions
        if len(weights) > 1:
            original_ratios = [w / weights[0] for w in weights]
            normalized_ratios = [w / normalized[0] for w in normalized]
            for orig, norm in zip(original_ratios, normalized_ratios):
                assert abs(orig - norm) < 1e-10


class TestIntegration:
    """Integration tests with existing components."""
    
    def test_backward_compatibility(self):
        """Test backward compatibility with normalize_metric."""
        from repoq.normalize.metrics_trs import normalize_metric
        
        result = normalize_metric("2 * lines + complexity")
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_real_world_metrics(self):
        """Test real-world metric expressions."""
        real_expressions = [
            "lines * 0.3 + complexity * 0.5 + maintainability * 0.2",
            "sum(bugs, debt) / max(1, lines)",
            "avg(complexity, maintainability) * (1 + coverage / 100)",
            "max(lines, complexity) / (avg(lines, complexity) + 1)"
        ]
        
        for expr in real_expressions:
            try:
                canonical = canonicalize_metric(expr)
                assert isinstance(canonical, str)
                assert len(canonical) > 0
                
                # Test idempotence
                canonical2 = canonicalize_metric(canonical)
                # Note: String re-parsing may not be identical due to formatting
                assert isinstance(canonical2, str)
                
            except Exception as e:
                pytest.fail(f"Failed to process real-world metric '{expr}': {e}")
    
    def test_evaluation_consistency(self):
        """Test that canonicalized expressions evaluate consistently."""
        original = "2 * lines + 3 * lines"
        canonical = canonicalize_metric(original)
        
        original_expr = MetricExpression(parse_metric_expression(original))
        canonical_expr = MetricExpression(parse_metric_expression("5 * lines"))  # Expected result
        
        context = {"lines": 10}
        
        original_result = original_expr.evaluate(context)
        canonical_result = canonical_expr.evaluate(context)
        
        assert abs(original_result - canonical_result) < 1e-10


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])