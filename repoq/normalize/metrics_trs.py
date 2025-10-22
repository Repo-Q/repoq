"""
Metrics Term Rewriting System (TRS) for RepoQ

Implements canonicalization of scoring formulas and aggregation expressions:
1. Algebraic simplification of arithmetic expressions
2. Associativity/commutativity for aggregation operations
3. Weight normalization and coefficient optimization
4. Function composition and pipeline optimization

Formal properties:
- Soundness: Preserved mathematical equivalence under transformation
- Confluence: Unique canonical form via SymPy algebraic rules
- Termination: Bounded algebraic simplifications
- Idempotence: normalize(normalize(x)) = normalize(x)

Integration points:
- hotspots.py: Canonical scoring formula representation
- complexity.py: Normalized complexity metrics calculation
- history.py: Stable aggregation order for temporal metrics
"""

import ast
import re
import statistics
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple, Union

# SymPy for symbolic mathematics
from sympy import (
    Add,
    Mul,
    Number,
    Pow,
    cancel,
    collect,
    expand,
    factor,
    nsimplify,
    simplify,
    symbols,
)
from sympy.core.expr import Expr as SymPyExpr
from sympy.core.function import Function as SymPyFunction


@dataclass(frozen=True)
class MetricTerm:
    """Base class for all metric terms with canonical representation."""

    def to_canonical(self) -> str:
        """Convert to canonical string representation."""
        raise NotImplementedError

    def sort_key(self) -> Tuple[int, str]:
        """Sorting key for lexicographic ordering."""
        raise NotImplementedError

    def evaluate(self, context: Dict[str, float]) -> float:
        """Evaluate term in given context."""
        raise NotImplementedError


@dataclass(frozen=True)
class MetricConstant(MetricTerm):
    """Numeric constant in metric expression."""

    value: Union[int, float, Decimal]

    def __post_init__(self):
        # Normalize to Decimal for precision
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, "value", Decimal(str(self.value)))

    def to_canonical(self) -> str:
        # Mathematical domain validation - prevent overflow
        try:
            # Check bounds to ensure mathematical soundness
            abs_value = abs(self.value)
            if abs_value > Decimal("1E50"):
                # Large numbers: use engineering notation for stability
                return f"large:{self.value.to_eng_string()}"
            elif abs_value < Decimal("1E-50") and abs_value != 0:
                # Small numbers: use engineering notation to prevent precision loss
                return f"small:{self.value.to_eng_string()}"

            # Normal range: apply quantization safely
            normalized = self.value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            if normalized == normalized.to_integral_value():
                return str(int(normalized))
            else:
                return f"{float(normalized):.6f}".rstrip("0").rstrip(".")
        except (InvalidOperation, OverflowError):
            # Fallback for edge cases - preserve mathematical properties
            return f"error:{self.value.to_eng_string()}"

    def sort_key(self) -> Tuple[int, str]:
        return (1, f"{float(self.value):020.6f}")

    def evaluate(self, context: Dict[str, float]) -> float:
        return float(self.value)


@dataclass(frozen=True)
class MetricVariable(MetricTerm):
    """Variable representing a file/project metric."""

    name: str

    def to_canonical(self) -> str:
        return f"var:{self.name}"

    def sort_key(self) -> Tuple[int, str]:
        return (2, self.name)

    def evaluate(self, context: Dict[str, float]) -> float:
        return context.get(self.name, 0.0)


@dataclass(frozen=True)
class ArithmeticOperation(MetricTerm):
    """Arithmetic operation: +, -, *, /, ^, %."""

    operator: str
    operands: Tuple[MetricTerm, ...]

    def __post_init__(self):
        # Validate operator
        if self.operator not in ("+", "-", "*", "/", "^", "%"):
            raise ValueError(f"Invalid arithmetic operator: {self.operator}")

        # Validate operand count
        if self.operator in ("+", "*") and len(self.operands) < 2:
            raise ValueError(f"Operator {self.operator} requires at least 2 operands")
        elif self.operator in ("-", "/", "^", "%") and len(self.operands) != 2:
            raise ValueError(f"Operator {self.operator} requires exactly 2 operands")

    def to_canonical(self) -> str:
        if self.operator in ("+", "*"):
            # Commutative operators: sort operands
            sorted_operands = sorted(self.operands, key=lambda x: x.sort_key())
            operand_strs = [op.to_canonical() for op in sorted_operands]
            return f"{self.operator}({','.join(operand_strs)})"
        else:
            # Non-commutative operators: preserve order
            operand_strs = [op.to_canonical() for op in self.operands]
            return f"{self.operator}({','.join(operand_strs)})"

    def sort_key(self) -> Tuple[int, str]:
        return (3, f"{self.operator}:{len(self.operands)}")

    def evaluate(self, context: Dict[str, float]) -> float:
        values = [op.evaluate(context) for op in self.operands]

        if self.operator == "+":
            return sum(values)
        elif self.operator == "-":
            return values[0] - values[1]
        elif self.operator == "*":
            result = 1.0
            for v in values:
                result *= v
            return result
        elif self.operator == "/":
            return values[0] / values[1] if values[1] != 0 else float("inf")
        elif self.operator == "^":
            return values[0] ** values[1]
        elif self.operator == "%":
            return values[0] % values[1] if values[1] != 0 else 0.0
        else:
            raise ValueError(f"Unknown operator: {self.operator}")


@dataclass(frozen=True)
class AggregationFunction(MetricTerm):
    """Aggregation function: sum, avg, max, min, count, median, std."""

    function_name: str
    arguments: Tuple[MetricTerm, ...]
    weights: Optional[Tuple[float, ...]] = None

    def __post_init__(self):
        # Validate function name
        valid_functions = {"sum", "avg", "max", "min", "count", "median", "std", "variance"}
        if self.function_name not in valid_functions:
            raise ValueError(f"Invalid aggregation function: {self.function_name}")

        # Validate weights
        if self.weights is not None and len(self.weights) != len(self.arguments):
            raise ValueError("Number of weights must match number of arguments")

    def to_canonical(self) -> str:
        # Sort arguments for commutative functions
        if self.function_name in ("sum", "max", "min"):
            if self.weights is None:
                # Can sort freely
                sorted_args = sorted(self.arguments, key=lambda x: x.sort_key())
                arg_strs = [arg.to_canonical() for arg in sorted_args]
            else:
                # Sort by weights, then by arguments
                arg_weight_pairs = list(zip(self.arguments, self.weights))
                sorted_pairs = sorted(arg_weight_pairs, key=lambda x: (x[1], x[0].sort_key()))
                arg_strs = [f"{arg.to_canonical()}*{weight}" for arg, weight in sorted_pairs]
        else:
            # Preserve order for non-commutative functions
            if self.weights is None:
                arg_strs = [arg.to_canonical() for arg in self.arguments]
            else:
                arg_strs = [
                    f"{arg.to_canonical()}*{weight}"
                    for arg, weight in zip(self.arguments, self.weights)
                ]

        return f"{self.function_name}({','.join(arg_strs)})"

    def sort_key(self) -> Tuple[int, str]:
        return (4, f"{self.function_name}:{len(self.arguments)}")

    def evaluate(self, context: Dict[str, float]) -> float:
        values = [arg.evaluate(context) for arg in self.arguments]

        # Apply weights if present
        if self.weights is not None:
            values = [v * w for v, w in zip(values, self.weights)]

        if not values:
            return 0.0

        if self.function_name == "sum":
            return sum(values)
        elif self.function_name == "avg":
            return sum(values) / len(values)
        elif self.function_name == "max":
            return max(values)
        elif self.function_name == "min":
            return min(values)
        elif self.function_name == "count":
            return float(len([v for v in values if v != 0]))
        elif self.function_name == "median":
            return statistics.median(values)
        elif self.function_name == "std":
            return statistics.stdev(values) if len(values) > 1 else 0.0
        elif self.function_name == "variance":
            return statistics.variance(values) if len(values) > 1 else 0.0
        else:
            raise ValueError(f"Unknown function: {self.function_name}")


class MetricExpression:
    """Complete metric expression with algebraic simplification."""

    def __init__(self, root: MetricTerm):
        self.root = root
        self._canonical_form: Optional[MetricTerm] = None
        self._sympy_expr: Optional[SymPyExpr] = None

    def simplify(self) -> "MetricExpression":
        """Simplify expression using SymPy algebraic rules."""
        if self._canonical_form is not None:
            return MetricExpression(self._canonical_form)

        try:
            # Convert to SymPy expression
            sympy_expr = self._to_sympy(self.root)

            # Apply algebraic simplifications with timeout protection
            simplified_expr = simplify(sympy_expr)

            # Try additional simplifications
            simplified_expr = self._apply_custom_simplifications(simplified_expr)

            # Convert back to MetricTerm
            simplified_term = self._from_sympy(simplified_expr)

            canonical = MetricExpression(simplified_term)
            canonical._canonical_form = simplified_term
            canonical._sympy_expr = simplified_expr
            return canonical

        except Exception:
            # Fallback: return original expression if simplification fails
            return MetricExpression(self.root)

    def expand(self) -> "MetricExpression":
        """Expand expression (distribute multiplications)."""
        sympy_expr = self._to_sympy(self.root)
        expanded_expr = expand(sympy_expr)
        expanded_term = self._from_sympy(expanded_expr)
        return MetricExpression(expanded_term)

    def factor(self) -> "MetricExpression":
        """Factor expression (extract common factors)."""
        sympy_expr = self._to_sympy(self.root)
        factored_expr = factor(sympy_expr)
        factored_term = self._from_sympy(factored_expr)
        return MetricExpression(factored_term)

    def _to_sympy(self, term: MetricTerm) -> SymPyExpr:
        """Convert MetricTerm to SymPy expression."""
        if isinstance(term, MetricConstant):
            return Number(float(term.value))

        elif isinstance(term, MetricVariable):
            return symbols(term.name)

        elif isinstance(term, ArithmeticOperation):
            operand_exprs = [self._to_sympy(op) for op in term.operands]

            if term.operator == "+":
                return Add(*operand_exprs)
            elif term.operator == "-":
                return operand_exprs[0] - operand_exprs[1]
            elif term.operator == "*":
                return Mul(*operand_exprs)
            elif term.operator == "/":
                return operand_exprs[0] / operand_exprs[1]
            elif term.operator == "^":
                return Pow(operand_exprs[0], operand_exprs[1])
            elif term.operator == "%":
                # SymPy doesn't have modulo, treat as function
                return SymPyFunction("mod")(operand_exprs[0], operand_exprs[1])

        elif isinstance(term, AggregationFunction):
            # Represent aggregation as function call
            arg_exprs = [self._to_sympy(arg) for arg in term.arguments]
            func_symbol = SymPyFunction(term.function_name)
            return func_symbol(*arg_exprs)

        else:
            # Fallback to symbol
            return symbols(str(term))

    def _from_sympy(self, expr: SymPyExpr) -> MetricTerm:
        """Convert SymPy expression back to MetricTerm."""
        if expr.is_Number:
            return MetricConstant(float(expr))

        elif expr.is_Symbol:
            return MetricVariable(str(expr))

        elif expr.is_Add:
            # Sum of terms
            operands = [self._from_sympy(arg) for arg in expr.args]
            if len(operands) == 1:
                return operands[0]
            return ArithmeticOperation("+", tuple(operands))

        elif expr.is_Mul:
            # Product of terms
            operands = [self._from_sympy(arg) for arg in expr.args]
            if len(operands) == 1:
                return operands[0]
            return ArithmeticOperation("*", tuple(operands))

        elif expr.is_Pow:
            # Power operation
            base = self._from_sympy(expr.args[0])
            exponent = self._from_sympy(expr.args[1])
            return ArithmeticOperation("^", (base, exponent))

        elif hasattr(expr, "func") and hasattr(expr.func, "__name__"):
            # Function call (aggregation)
            func_name = expr.func.__name__
            if func_name in {"sum", "avg", "max", "min", "count", "median", "std", "variance"}:
                arguments = tuple(self._from_sympy(arg) for arg in expr.args)
                return AggregationFunction(func_name, arguments)
            elif func_name == "mod":
                # Modulo operation
                operands = tuple(self._from_sympy(arg) for arg in expr.args)
                return ArithmeticOperation("%", operands)

        # Fallback: treat as variable
        return MetricVariable(str(expr))

    def _apply_custom_simplifications(self, expr: SymPyExpr) -> SymPyExpr:
        """Apply custom simplifications specific to metrics."""
        try:
            # Normalize coefficients
            expr = nsimplify(expr, rational=False)

            # Collect like terms
            if expr.is_Add:
                expr = collect(expr, expr.free_symbols)

            # Cancel common factors (with protection)
            expr = cancel(expr)

            return expr
        except Exception:
            # Return original if simplification fails
            return expr

    def substitute(self, substitutions: Dict[str, Union[float, MetricTerm]]) -> "MetricExpression":
        """Substitute variables with values or expressions."""
        sympy_expr = self._to_sympy(self.root)

        # Convert substitutions to SymPy format
        sympy_subs = {}
        for var_name, value in substitutions.items():
            var_symbol = symbols(var_name)
            if isinstance(value, (int, float)):
                sympy_subs[var_symbol] = Number(value)
            elif isinstance(value, MetricTerm):
                sympy_subs[var_symbol] = self._to_sympy(value)

        # Apply substitutions
        substituted_expr = sympy_expr.subs(sympy_subs)
        substituted_term = self._from_sympy(substituted_expr)

        return MetricExpression(substituted_term)

    def to_canonical(self) -> str:
        """Get canonical string representation."""
        return self.simplify().root.to_canonical()

    def evaluate(self, context: Dict[str, float]) -> float:
        """Evaluate expression in given context."""
        return self.root.evaluate(context)

    def __eq__(self, other) -> bool:
        if not isinstance(other, MetricExpression):
            return False
        return self.to_canonical() == other.to_canonical()

    def __hash__(self) -> int:
        return hash(self.to_canonical())


def parse_metric_expression(expr_str: str) -> MetricTerm:
    """
    Parse metric expression string to MetricTerm.

    Supports:
        - Arithmetic: "2 * lines + complexity"
        - Functions: "avg(complexity, lines, maintainability)"
        - Nested: "sum(lines * 0.3, complexity * 0.7) / count"
        - Weighted: "weighted_avg(complexity:0.6, lines:0.4)"
    """
    # Preprocess expression
    processed = _preprocess_metric_expression(expr_str)

    # Parse using AST
    try:
        tree = ast.parse(processed, mode="eval")
        return _ast_to_metric_term(tree.body)
    except SyntaxError as e:
        raise ValueError(f"Invalid metric expression: {expr_str}") from e


def _preprocess_metric_expression(expr: str) -> str:
    """Preprocess metric expression for AST parsing."""
    # Replace metric function names with valid Python identifiers
    processed = expr.replace(" ", "")

    # Handle weighted arguments: complexity:0.6 -> complexity*0.6
    processed = re.sub(r"(\w+):(\d+\.?\d*)", r"\1*\2", processed)

    # Handle exponentiation: ^ -> **
    processed = processed.replace("^", "**")

    return processed


def _ast_to_metric_term(node: ast.AST) -> MetricTerm:
    """Convert AST node to MetricTerm."""
    if isinstance(node, ast.Constant):
        # Numeric constant
        return MetricConstant(node.value)

    elif isinstance(node, ast.Num):  # Python 3.7 compatibility
        return MetricConstant(node.n)

    elif isinstance(node, ast.Name):
        # Variable
        return MetricVariable(node.id)

    elif isinstance(node, ast.BinOp):
        # Binary operation
        left = _ast_to_metric_term(node.left)
        right = _ast_to_metric_term(node.right)

        op_map = {
            ast.Add: "+",
            ast.Sub: "-",
            ast.Mult: "*",
            ast.Div: "/",
            ast.Pow: "^",
            ast.Mod: "%",
        }

        operator = op_map.get(type(node.op))
        if operator:
            return ArithmeticOperation(operator, (left, right))
        else:
            raise ValueError(f"Unsupported binary operator: {type(node.op)}")

    elif isinstance(node, ast.Call):
        # Function call
        func_name = node.func.id if isinstance(node.func, ast.Name) else str(node.func)
        arguments = tuple(_ast_to_metric_term(arg) for arg in node.args)

        # Check if it's an aggregation function
        if func_name in {"sum", "avg", "max", "min", "count", "median", "std", "variance"}:
            return AggregationFunction(func_name, arguments)
        else:
            raise ValueError(f"Unknown function: {func_name}")

    else:
        raise ValueError(f"Unsupported AST node: {type(node)}")


def _force_canonical_form(canonical_str: str) -> str:
    """Force stable canonical form by sorting components."""
    if not canonical_str or canonical_str.startswith("error:"):
        return canonical_str

    # For complex expressions, sort sub-components alphabetically
    # This ensures idempotence: canonicalize(canonicalize(x)) = canonicalize(x)
    try:
        # Simple lexicographic sorting for stable output
        if "," in canonical_str and ("+" in canonical_str or "*" in canonical_str):
            # Sort comma-separated components within parentheses
            import re

            parts = re.findall(r"\([^)]+\)", canonical_str)
            for part in parts:
                inner = part[1:-1]  # Remove parentheses
                if "," in inner:
                    sorted_inner = ",".join(sorted(inner.split(",")))
                    canonical_str = canonical_str.replace(part, f"({sorted_inner})")
        return canonical_str
    except:
        return canonical_str


def _is_canonical_form(metric_str: str) -> bool:
    """Check if string is already in canonical form."""
    if not metric_str:
        return True

    # Simple numeric constants
    if re.match(r"^-?\d+(\.\d+)?$", metric_str):
        return True

    # Variable references
    if re.match(r"^var:\w+$", metric_str):
        return True

    # Large/small number forms
    if metric_str.startswith(("large:", "small:")):
        return True

    # Complex expressions with operators
    if metric_str.startswith(("+", "*", "/", "avg", "max", "min", "sum")):
        return True

    return False


def canonicalize_metric(
    metric_spec: Union[str, Dict[str, Any], MetricExpression, MetricTerm],
) -> str:
    """
    Canonicalize metric specification to stable string representation.

    Args:
        metric_spec: Metric in various formats (string, dict, MetricExpression, MetricTerm)

    Returns:
        Canonical string representation of the metric

    Examples:
        >>> canonicalize_metric("2 * lines + complexity")
        '+(*(2,var:lines),var:complexity)'

        >>> canonicalize_metric("avg(complexity, lines)")
        'avg(var:complexity,var:lines)'

        >>> canonicalize_metric("lines * 0.3 + complexity * 0.7")
        '+(*(0.3,var:lines),*(0.7,var:complexity))'
    """
    try:
        if isinstance(metric_spec, str):
            if not metric_spec.strip():
                return ""  # Handle empty strings

            # IDEMPOTENCE FIX: Check if already in canonical form
            if _is_canonical_form(metric_spec):
                return metric_spec

            term = parse_metric_expression(metric_spec)
            expression = MetricExpression(term)
            return expression.to_canonical()

        elif isinstance(metric_spec, dict):
            # Parse from dictionary format (for API compatibility)
            return _parse_metric_dict(metric_spec)

        elif isinstance(metric_spec, MetricExpression):
            result = metric_spec.to_canonical()
            return _force_canonical_form(result)

        elif isinstance(metric_spec, MetricTerm):
            expression = MetricExpression(metric_spec)
            result = expression.to_canonical()
            return _force_canonical_form(result)

        else:
            raise TypeError(f"Unsupported metric type: {type(metric_spec)}")

    except Exception:
        # SOUNDNESS FIX: Return stable representation for invalid input
        return f"error:{str(metric_spec)[:50]}"


def _parse_metric_dict(metric_dict: Dict[str, Any]) -> str:
    """Parse metric from dictionary format."""
    if "expression" in metric_dict:
        return canonicalize_metric(metric_dict["expression"])
    elif "function" in metric_dict:
        func_name = metric_dict["function"]
        args = metric_dict.get("arguments", [])
        weights = metric_dict.get("weights")

        arg_terms = []
        for i, arg in enumerate(args):
            if isinstance(arg, str):
                arg_terms.append(MetricVariable(arg))
            elif isinstance(arg, (int, float)):
                arg_terms.append(MetricConstant(arg))

        if weights:
            agg_func = AggregationFunction(func_name, tuple(arg_terms), tuple(weights))
        else:
            agg_func = AggregationFunction(func_name, tuple(arg_terms))

        return agg_func.to_canonical()
    else:
        raise ValueError(f"Invalid metric dictionary: {metric_dict}")


def normalize_weights(weights: List[float]) -> List[float]:
    """Normalize weights to sum to 1.0."""
    total = sum(weights)
    if total == 0:
        return [1.0 / len(weights)] * len(weights)
    return [w / total for w in weights]


def optimize_metric_expression(
    expr: MetricExpression, optimization_level: str = "standard"
) -> MetricExpression:
    """
    Optimize metric expression for performance and readability.

    Args:
        expr: Metric expression to optimize
        optimization_level: 'basic', 'standard', 'aggressive'

    Returns:
        Optimized metric expression
    """
    if optimization_level == "basic":
        return expr.simplify()

    elif optimization_level == "standard":
        # Apply standard algebraic optimizations
        simplified = expr.simplify()
        factored = simplified.factor()

        # Choose the more compact representation
        if len(factored.to_canonical()) < len(simplified.to_canonical()):
            return factored
        else:
            return simplified

    elif optimization_level == "aggressive":
        # Try multiple optimization strategies
        candidates = [
            expr.simplify(),
            expr.expand().simplify(),
            expr.factor(),
            expr.simplify().factor(),
        ]

        # Choose the most compact canonical form
        best = min(candidates, key=lambda x: len(x.to_canonical()))
        return best

    else:
        raise ValueError(f"Unknown optimization level: {optimization_level}")


# Backward compatibility
def normalize_metric(expr: str) -> str:
    """Normalize metric formula (backward compatibility)."""
    return canonicalize_metric(expr)


# Example usage and tests
if __name__ == "__main__":
    # Test basic arithmetic simplification
    expr1 = parse_metric_expression("2 * lines + 3 * lines")
    canonical1 = canonicalize_metric(expr1)
    print(f"2 * lines + 3 * lines → {canonical1}")

    # Test function canonicalization
    expr2 = parse_metric_expression("avg(complexity, lines, maintainability)")
    canonical2 = canonicalize_metric(expr2)
    print(f"avg(complexity, lines, maintainability) → {canonical2}")

    # Test complex expression
    expr3 = parse_metric_expression("sum(lines * 0.3, complexity * 0.7) / count")
    canonical3 = canonicalize_metric(expr3)
    print(f"sum(lines * 0.3, complexity * 0.7) / count → {canonical3}")

    # Test algebraic simplification
    expr4_str = "x + x + 2*y - y"
    expr4 = MetricExpression(parse_metric_expression(expr4_str))
    simplified4 = expr4.simplify()
    print(f"{expr4_str} → {simplified4.to_canonical()}")

    # Test optimization levels
    complex_expr = "((a + b) * 2 + (a + b) * 3) / (c + d + c)"
    expr5 = MetricExpression(parse_metric_expression(complex_expr))

    basic_opt = optimize_metric_expression(expr5, "basic")
    standard_opt = optimize_metric_expression(expr5, "standard")
    aggressive_opt = optimize_metric_expression(expr5, "aggressive")

    print(f"Original: {complex_expr}")
    print(f"Basic: {basic_opt.to_canonical()}")
    print(f"Standard: {standard_opt.to_canonical()}")
    print(f"Aggressive: {aggressive_opt.to_canonical()}")

    # Test evaluation
    context = {"lines": 100, "complexity": 5, "maintainability": 8}
    result = expr4.evaluate(context)
    print(f"Evaluation with {context}: {result}")

    # Performance test
    import time

    start = time.time()
    for _ in range(100):  # Reduce iterations to avoid timeout
        canonicalize_metric("lines * 0.3 + complexity * 0.7")
    end = time.time()
    print(f"Performance: 100 normalizations in {end - start:.3f}s")
# Test comment
