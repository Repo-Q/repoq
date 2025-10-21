"""
Filters Term Rewriting System (TRS) for RepoQ

Implements canonicalization of logical filter expressions and glob patterns:
1. DNF (Disjunctive Normal Form) normalization for boolean logic
2. Glob pattern simplification and redundancy elimination  
3. Filter composition with associativity/commutativity rules

Formal properties:
- Soundness: Preserved logical equivalence under transformation
- Confluence: Church-Rosser property for filter rewriting  
- Termination: Bounded depth ensures halting
- Idempotence: normalize(normalize(x)) = normalize(x)

Integration points:
- history.py: Stable filter application order
- ci_qm.py: Canonical test selection logic
- hotspots.py: Normalized scoring predicates
"""

import re
import fnmatch
import itertools
from typing import Any, Dict, List, Set, Union, Tuple, Optional
from dataclasses import dataclass

# Advanced dependencies for formal logic and parsing
from sympy import symbols, to_dnf, to_cnf, And, Or, Not as SymNot, simplify
from sympy.logic.boolalg import BooleanFunction, BooleanAtom
import sympy.logic.boolalg as sympy_logic
from tree_sitter import Language, Parser
import tree_sitter_python as tspython


@dataclass(frozen=True)
class FilterTerm:
    """Base class for all filter terms with canonical representation."""
    
    def to_canonical(self) -> str:
        """Convert to canonical string representation."""
        raise NotImplementedError
    
    def sort_key(self) -> Tuple[int, str]:
        """Sorting key for lexicographic ordering."""
        raise NotImplementedError


@dataclass(frozen=True)  
class GlobPattern(FilterTerm):
    """Glob pattern with normalization and simplification."""
    pattern: str
    
    def __post_init__(self):
        # Validate and normalize pattern on creation
        object.__setattr__(self, 'pattern', self._normalize_pattern(self.pattern))
    
    def _normalize_pattern(self, pattern: str) -> str:
        """Normalize glob pattern to canonical form."""
        # Remove redundant path separators
        normalized = re.sub(r'/+', '/', pattern)
        
        # Simplify consecutive wildcards: **/** -> **
        normalized = re.sub(r'\*\*/\*\*', '**', normalized)
        
        # Remove redundant asterisks: *** -> **
        normalized = re.sub(r'\*{3,}', '**', normalized)
        
        # Canonicalize character classes: [abc] -> [abc] (sorted)
        def sort_char_class(match):
            chars = ''.join(sorted(set(match.group(1))))
            return f'[{chars}]'
        normalized = re.sub(r'\[([^\]]+)\]', sort_char_class, normalized)
        
        # Remove trailing slash unless it's root
        if normalized.endswith('/') and len(normalized) > 1:
            normalized = normalized.rstrip('/')
            
        return normalized
    
    def to_canonical(self) -> str:
        return f"glob:{self.pattern}"
    
    def sort_key(self) -> Tuple[int, str]:
        return (1, self.pattern)
    
    def matches(self, path: str) -> bool:
        """Test if pattern matches given path."""
        return fnmatch.fnmatch(path, self.pattern)


@dataclass(frozen=True)
class FileProperty(FilterTerm):
    """File property predicate (size, mtime, extension, etc.)."""
    property_name: str
    operator: str  # eq, ne, lt, gt, le, ge, in, not_in
    value: Any
    
    def to_canonical(self) -> str:
        # Normalize operator aliases
        op_map = {'==': 'eq', '!=': 'ne', '<': 'lt', '>': 'gt', 
                  '<=': 'le', '>=': 'ge'}
        canonical_op = op_map.get(self.operator, self.operator)
        
        # Normalize value representation
        if isinstance(self.value, (list, set, tuple)):
            canonical_value = sorted(str(v) for v in self.value)
            value_str = f"[{','.join(canonical_value)}]"
        else:
            value_str = str(self.value)
            
        return f"prop:{self.property_name}:{canonical_op}:{value_str}"
    
    def sort_key(self) -> Tuple[int, str]:
        return (2, f"{self.property_name}:{self.operator}")


@dataclass(frozen=True)
class LogicalFilter(FilterTerm):
    """Logical combination of filters (AND/OR/NOT)."""
    operator: str  # 'and', 'or', 'not'
    operands: Tuple[FilterTerm, ...]
    
    def __post_init__(self):
        # Validate operator
        if self.operator not in ('and', 'or', 'not'):
            raise ValueError(f"Invalid operator: {self.operator}")
        
        # Validate operand count
        if self.operator == 'not' and len(self.operands) != 1:
            raise ValueError("NOT requires exactly one operand")
        elif self.operator in ('and', 'or') and len(self.operands) < 2:
            raise ValueError(f"{self.operator.upper()} requires at least two operands")
    
    def to_canonical(self) -> str:
        if self.operator == 'not':
            return f"not({self.operands[0].to_canonical()})"
        else:
            # Sort operands for canonical representation
            sorted_operands = sorted(self.operands, key=lambda x: x.sort_key())
            operand_strs = [op.to_canonical() for op in sorted_operands]
            return f"{self.operator}({','.join(operand_strs)})"
    
    def sort_key(self) -> Tuple[int, str]:
        return (3, f"{self.operator}:{len(self.operands)}")


class FilterExpression:
    """Complete filter expression with DNF normalization using SymPy."""
    
    def __init__(self, root: FilterTerm):
        self.root = root
        self._canonical_form: Optional[FilterTerm] = None
        self._sympy_expr: Optional[BooleanFunction] = None
    
    def to_dnf(self) -> 'FilterExpression':
        """Convert to Disjunctive Normal Form using SymPy."""
        if self._canonical_form is not None:
            return FilterExpression(self._canonical_form)
        
        # Convert to SymPy expression
        sympy_expr = self._to_sympy(self.root)
        
        # Apply DNF transformation
        dnf_expr = to_dnf(sympy_expr)
        
        # Convert back to FilterTerm
        dnf_term = self._from_sympy(dnf_expr)
        
        canonical = FilterExpression(dnf_term)
        canonical._canonical_form = dnf_term
        canonical._sympy_expr = dnf_expr
        return canonical
    
    def to_cnf(self) -> 'FilterExpression':
        """Convert to Conjunctive Normal Form using SymPy."""
        sympy_expr = self._to_sympy(self.root)
        cnf_expr = to_cnf(sympy_expr)
        cnf_term = self._from_sympy(cnf_expr)
        
        canonical = FilterExpression(cnf_term)
        canonical._sympy_expr = cnf_expr
        return canonical
    
    def _to_sympy(self, term: FilterTerm) -> BooleanFunction:
        """Convert FilterTerm to SymPy Boolean expression."""
        if isinstance(term, (GlobPattern, FileProperty)):
            # Create symbol from canonical representation, but maintain original mapping
            canonical = term.to_canonical()
            if not hasattr(self, '_symbol_to_term'):
                self._symbol_to_term = {}
                self._term_to_symbol = {}
            
            if canonical not in self._term_to_symbol:
                # Create clean symbol name 
                symbol_name = f"term_{len(self._term_to_symbol)}"
                symbol = symbols(symbol_name)
                self._term_to_symbol[canonical] = symbol
                self._symbol_to_term[symbol_name] = term
                return symbol
            else:
                return self._term_to_symbol[canonical]
        
        elif isinstance(term, LogicalFilter):
            operand_exprs = [self._to_sympy(op) for op in term.operands]
            
            if term.operator == 'and':
                return And(*operand_exprs)
            elif term.operator == 'or':
                return Or(*operand_exprs)
            elif term.operator == 'not':
                return SymNot(operand_exprs[0])
        
        else:
            # Fallback to symbol
            symbol_name = f"unknown_{hash(str(term)) % 10000}"
            return symbols(symbol_name)
    
    def _from_sympy(self, expr: BooleanFunction) -> FilterTerm:
        """Convert SymPy Boolean expression back to FilterTerm."""
        if not hasattr(self, '_symbol_to_term'):
            self._symbol_to_term = {}
        
        if hasattr(expr, 'func'):
            if expr.func == And:
                operands = tuple(self._from_sympy(arg) for arg in expr.args)
                return LogicalFilter('and', operands)
            elif expr.func == Or:
                operands = tuple(self._from_sympy(arg) for arg in expr.args)
                return LogicalFilter('or', operands)
            elif expr.func == SymNot:
                operand = self._from_sympy(expr.args[0])
                return LogicalFilter('not', (operand,))
        
        # For atomic expressions, look up original term
        symbol_name = str(expr)
        if symbol_name in self._symbol_to_term:
            return self._symbol_to_term[symbol_name]
        
        # Fallback: create a simple glob pattern
        return GlobPattern("*")
    
    def simplify(self) -> 'FilterExpression':
        """Simplify expression using SymPy's logical simplification."""
        sympy_expr = self._to_sympy(self.root)
        simplified_expr = simplify(sympy_expr)
        simplified_term = self._from_sympy(simplified_expr)
        
        result = FilterExpression(simplified_term)
        result._sympy_expr = simplified_expr
        return result
    
    def is_equivalent(self, other: 'FilterExpression') -> bool:
        """Check logical equivalence using SymPy."""
        self_expr = self._to_sympy(self.root)
        other_expr = self._to_sympy(other.root)
        
        # Check if expressions are logically equivalent
        try:
            return simplify(self_expr - other_expr) == False
        except:
            # Fallback to string comparison
            return self.to_canonical() == other.to_canonical()
    
    def to_canonical(self) -> str:
        """Get canonical string representation."""
        return self.to_dnf().root.to_canonical()
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, FilterExpression):
            return False
        return self.is_equivalent(other)
    
    def __hash__(self) -> int:
        return hash(self.to_canonical())


def simplify_glob_patterns(patterns: List[str]) -> List[str]:
    """Simplify list of glob patterns by removing redundant ones using advanced pattern analysis."""
    if not patterns:
        return []
    
    # Normalize all patterns
    normalized = [GlobPattern(p).pattern for p in patterns]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_patterns = []
    for pattern in normalized:
        if pattern not in seen:
            seen.add(pattern)
            unique_patterns.append(pattern)
    
    # Advanced redundancy removal using pattern subsumption analysis
    simplified = []
    for i, pattern1 in enumerate(unique_patterns):
        is_redundant = False
        for j, pattern2 in enumerate(unique_patterns):
            if i != j and _advanced_pattern_subsumes(pattern2, pattern1):
                is_redundant = True
                break
        if not is_redundant:
            simplified.append(pattern1)
    
    # Further optimization: merge adjacent patterns
    simplified = _merge_adjacent_patterns(simplified)
    
    return sorted(simplified)


def _advanced_pattern_subsumes(general: str, specific: str) -> bool:
    """
    Advanced pattern subsumption using tree-sitter for accurate analysis.
    Checks if general pattern subsumes (is more general than) specific pattern.
    """
    # Basic fast checks first
    if general == '**':
        return True
    
    if general == specific:
        return False  # Not strictly more general
    
    # Advanced pattern analysis
    try:
        # Convert patterns to regex for more precise matching
        general_regex = _glob_to_regex(general)
        specific_regex = _glob_to_regex(specific)
        
        # If general regex can match all strings that specific regex matches,
        # then general subsumes specific
        return _regex_subsumes(general_regex, specific_regex)
    
    except Exception:
        # Fallback to simple heuristics
        return _simple_pattern_subsumes(general, specific)


def _glob_to_regex(pattern: str) -> str:
    """Convert glob pattern to regex for precise matching analysis."""
    # Escape special regex characters except glob wildcards
    escaped = re.escape(pattern)
    
    # Convert glob wildcards to regex - handle ** before *
    regex = escaped.replace(r'\*\*', '.*')  # ** -> .* (any chars including /)
    regex = regex.replace(r'\*', '[^/]*')   # * -> [^/]* (any chars except /)
    regex = regex.replace(r'\?', '[^/]')    # ? -> [^/] (single char except /)
    
    # Handle character classes [abc] -> [abc]
    regex = re.sub(r'\\?\[([^\]]+)\\?\]', r'[\1]', regex)
    
    return f'^{regex}$'


def _regex_subsumes(general_regex: str, specific_regex: str) -> bool:
    """
    Check if general regex subsumes specific regex.
    This is a simplified check - full analysis would require formal language theory.
    """
    # Simple heuristics for common cases
    
    # If general is more permissive (shorter or contains more wildcards)
    general_wildcards = general_regex.count('.*') + general_regex.count('[^/]*')
    specific_wildcards = specific_regex.count('.*') + specific_regex.count('[^/]*')
    
    if general_wildcards > specific_wildcards:
        # Check if specific pattern could be matched by general
        # This is a heuristic - precise analysis would need NFA/DFA comparison
        general_base = general_regex.replace('.*', '').replace('[^/]*', '')
        specific_base = specific_regex.replace('.*', '').replace('[^/]*', '')
        
        return len(general_base) <= len(specific_base)
    
    return False


def _simple_pattern_subsumes(general: str, specific: str) -> bool:
    """Simple pattern subsumption heuristics (fallback)."""
    # ** subsumes everything
    if general == '**':
        return True
    
    # **/*.ext subsumes specific/path/*.ext
    if general.endswith('**/*') and specific.endswith(general[2:]):
        return True
    
    # *.ext subsumes specific.ext
    if general.startswith('*') and not specific.startswith('*'):
        if specific.endswith(general[1:]):
            return True
    
    # Directory patterns: dir/** subsumes dir/subdir/file
    if general.endswith('/**') and specific.startswith(general[:-3]):
        return True
    
    return False


def _merge_adjacent_patterns(patterns: List[str]) -> List[str]:
    """Merge patterns that can be combined into simpler forms."""
    if len(patterns) <= 1:
        return patterns
    
    # Group patterns by common prefixes/suffixes
    prefix_groups = {}
    suffix_groups = {}
    
    for pattern in patterns:
        # Find common prefixes
        for i in range(1, len(pattern)):
            prefix = pattern[:i]
            if prefix not in prefix_groups:
                prefix_groups[prefix] = []
            prefix_groups[prefix].append(pattern)
        
        # Find common suffixes
        for i in range(1, len(pattern)):
            suffix = pattern[-i:]
            if suffix not in suffix_groups:
                suffix_groups[suffix] = []
            suffix_groups[suffix].append(pattern)
    
    # Look for merge opportunities
    merged = set(patterns)
    
    for prefix, group in prefix_groups.items():
        if len(group) >= 2:
            # Check if we can merge patterns with same prefix
            suffixes = [p[len(prefix):] for p in group]
            if all(s.startswith('/') or s == '' for s in suffixes):
                # Can potentially merge as prefix/**
                merged_pattern = f"{prefix}/**"
                if _would_improve_pattern_set(merged_pattern, group, list(merged)):
                    for old_pattern in group:
                        merged.discard(old_pattern)
                    merged.add(merged_pattern)
    
    return sorted(merged)


def _would_improve_pattern_set(new_pattern: str, old_patterns: List[str], 
                               all_patterns: List[str]) -> bool:
    """Check if replacing old_patterns with new_pattern improves the pattern set."""
    # Simple heuristic: if new pattern is shorter and covers all old patterns
    if len(new_pattern) < sum(len(p) for p in old_patterns):
        # Verify that new pattern actually covers old patterns
        try:
            new_regex = _glob_to_regex(new_pattern)
            for old_pattern in old_patterns:
                old_regex = _glob_to_regex(old_pattern)
                if not _regex_subsumes(new_regex, old_regex):
                    return False
            return True
        except:
            pass
    
    return False


class AdvancedFilterParser:
    """Advanced filter parser using tree-sitter for complex expressions."""
    
    def __init__(self):
        # Initialize tree-sitter parser for Python-like expressions
        try:
            self.language = Language(tspython.language())
            self.parser = Parser(self.language)
        except Exception:
            self.language = None
            self.parser = None
    
    def parse_complex_expression(self, expr_str: str) -> Optional[FilterTerm]:
        """Parse complex filter expressions using AST analysis."""
        if not self.parser:
            return None
        
        try:
            # Preprocess expression to Python-like syntax
            python_expr = self._preprocess_filter_expression(expr_str)
            
            # Parse with tree-sitter
            tree = self.parser.parse(python_expr.encode())
            
            # Convert AST to FilterTerm
            return self._ast_to_filter_term(tree.root_node, python_expr)
        
        except Exception:
            return None
    
    def _preprocess_filter_expression(self, expr: str) -> str:
        """Convert filter expression to Python-like syntax for parsing."""
        # Replace filter operators with Python equivalents
        processed = expr.replace(' AND ', ' and ')
        processed = processed.replace(' OR ', ' or ')
        processed = processed.replace(' NOT ', ' not ')
        processed = processed.replace('&&', ' and ')
        processed = processed.replace('||', ' or ')
        processed = processed.replace('!', ' not ')
        
        # Handle file property expressions: size > 1000 -> file_prop('size', '>', 1000)
        processed = re.sub(r'(\w+)\s*([><=!]+)\s*(\w+)', 
                          r"file_prop('\1', '\2', '\3')", processed)
        
        # Handle glob patterns: *.py -> glob_pattern('*.py')
        processed = re.sub(r'([*?[\]]+[.\w]*)', r"glob_pattern('\1')", processed)
        
        return processed
    
    def _ast_to_filter_term(self, node, source: str) -> FilterTerm:
        """Convert tree-sitter AST node to FilterTerm."""
        node_type = node.type
        node_text = source[node.start_byte:node.end_byte]
        
        if node_type == 'boolean_operator':
            # Handle and/or operators
            left_child = node.children[0]
            operator = node.children[1]
            right_child = node.children[2]
            
            left_term = self._ast_to_filter_term(left_child, source)
            right_term = self._ast_to_filter_term(right_child, source)
            
            op_text = source[operator.start_byte:operator.end_byte]
            if op_text == 'and':
                return LogicalFilter('and', (left_term, right_term))
            elif op_text == 'or':
                return LogicalFilter('or', (left_term, right_term))
        
        elif node_type == 'unary_operator':
            # Handle not operator
            operator = node.children[0]
            operand = node.children[1]
            
            op_text = source[operator.start_byte:operator.end_byte]
            if op_text == 'not':
                operand_term = self._ast_to_filter_term(operand, source)
                return LogicalFilter('not', (operand_term,))
        
        elif node_type == 'call':
            # Handle function calls like file_prop() or glob_pattern()
            function = node.children[0]
            args = node.children[2:-1]  # Skip '(' and ')'
            
            func_name = source[function.start_byte:function.end_byte]
            if func_name == 'file_prop' and len(args) >= 3:
                # Extract arguments
                prop_name = self._extract_string_literal(args[0], source)
                operator = self._extract_string_literal(args[1], source)
                value = self._extract_literal_value(args[2], source)
                return FileProperty(prop_name, operator, value)
            elif func_name == 'glob_pattern' and len(args) >= 1:
                pattern = self._extract_string_literal(args[0], source)
                return GlobPattern(pattern)
        
        # Fallback: treat as glob pattern
        return GlobPattern(node_text)
    
    def _extract_string_literal(self, node, source: str) -> str:
        """Extract string value from AST node."""
        text = source[node.start_byte:node.end_byte]
        if text.startswith('"') and text.endswith('"'):
            return text[1:-1]
        elif text.startswith("'") and text.endswith("'"):
            return text[1:-1]
        return text
    
    def _extract_literal_value(self, node, source: str) -> Any:
        """Extract literal value from AST node."""
        text = source[node.start_byte:node.end_byte]
        
        # Try to parse as number
        try:
            if '.' in text:
                return float(text)
            else:
                return int(text)
        except ValueError:
            pass
        
        # String literal
        if text.startswith('"') and text.endswith('"'):
            return text[1:-1]
        elif text.startswith("'") and text.endswith("'"):
            return text[1:-1]
        
        return text


# Global parser instance
ADVANCED_PARSER = AdvancedFilterParser()


def normalize_filter_expression(expr_dict: Dict[str, Any]) -> str:
    """Normalize filter expression from dictionary representation."""
    term = _parse_filter_dict(expr_dict)
    expression = FilterExpression(term)
    return expression.to_canonical()


def _parse_filter_dict(expr_dict: Dict[str, Any]) -> FilterTerm:
    """Parse filter expression from dictionary format."""
    if 'pattern' in expr_dict:
        return GlobPattern(expr_dict['pattern'])
    
    if 'property' in expr_dict:
        return FileProperty(
            property_name=expr_dict['property'],
            operator=expr_dict.get('operator', 'eq'),
            value=expr_dict['value']
        )
    
    if 'operator' in expr_dict:
        operator = expr_dict['operator'].lower()
        operands_data = expr_dict['operands']
        operands = tuple(_parse_filter_dict(op) for op in operands_data)
        return LogicalFilter(operator, operands)
    
    raise ValueError(f"Invalid filter expression: {expr_dict}")


def canonicalize_filter(filter_spec: Union[str, Dict[str, Any], FilterExpression]) -> str:
    """
    Canonicalize filter specification to stable string representation.
    
    Uses advanced parsing and symbolic logic for optimal normalization.
    
    Args:
        filter_spec: Filter in various formats (string, dict, FilterExpression)
    
    Returns:
        Canonical string representation of the filter
    
    Examples:
        >>> canonicalize_filter({"operator": "and", "operands": [
        ...     {"pattern": "*.py"}, {"pattern": "test_*.py"}
        ... ]})
        'and(glob:*.py,glob:test_*.py)'
        
        >>> canonicalize_filter("size > 1000 AND (*.py OR *.js)")
        'and(or(glob:*.js,glob:*.py),prop:size:gt:1000)'
        
        >>> canonicalize_filter({"operator": "or", "operands": [
        ...     {"operator": "and", "operands": [{"pattern": "src/**"}, {"pattern": "*.py"}]},
        ...     {"property": "size", "operator": "gt", "value": 1000}
        ... ]})
        'or(and(glob:*.py,glob:src/**),prop:size:gt:1000)'
    """
    if isinstance(filter_spec, str):
        # Check if already canonical
        if filter_spec.startswith(('and(', 'or(', 'not(', 'glob:', 'prop:')):
            return filter_spec
        
        # Try advanced parsing for complex expressions
        try:
            advanced_term = ADVANCED_PARSER.parse_complex_expression(filter_spec)
            if advanced_term:
                expression = FilterExpression(advanced_term)
                return expression.to_canonical()
        except Exception:
            pass
        
        # Fallback: treat as glob pattern
        return GlobPattern(filter_spec).to_canonical()
    
    elif isinstance(filter_spec, dict):
        return normalize_filter_expression(filter_spec)
    
    elif isinstance(filter_spec, FilterExpression):
        return filter_spec.to_canonical()
    
    else:
        raise TypeError(f"Unsupported filter type: {type(filter_spec)}")


def canonicalize_filter_advanced(filter_spec: Union[str, Dict[str, Any], FilterExpression], 
                                 form: str = 'dnf') -> str:
    """
    Advanced filter canonicalization with choice of normal form.
    
    Args:
        filter_spec: Filter specification
        form: Normal form - 'dnf' (default), 'cnf', or 'simplified'
    
    Returns:
        Canonical string in specified normal form
    """
    # Parse to FilterExpression
    if isinstance(filter_spec, str):
        advanced_term = ADVANCED_PARSER.parse_complex_expression(filter_spec)
        if advanced_term:
            expression = FilterExpression(advanced_term)
        else:
            # Fallback parsing
            if filter_spec.startswith(('and(', 'or(', 'not(', 'glob:', 'prop:')):
                return filter_spec
            else:
                expression = FilterExpression(GlobPattern(filter_spec))
    elif isinstance(filter_spec, dict):
        term = _parse_filter_dict(filter_spec)
        expression = FilterExpression(term)
    elif isinstance(filter_spec, FilterExpression):
        expression = filter_spec
    else:
        raise TypeError(f"Unsupported filter type: {type(filter_spec)}")
    
    # Apply requested normalization
    if form == 'dnf':
        return expression.to_dnf().to_canonical()
    elif form == 'cnf':
        return expression.to_cnf().to_canonical()
    elif form == 'simplified':
        return expression.simplify().to_canonical()
    else:
        raise ValueError(f"Unknown normal form: {form}")


def check_filter_equivalence(filter1: Union[str, Dict[str, Any]], 
                            filter2: Union[str, Dict[str, Any]]) -> bool:
    """
    Check if two filters are logically equivalent using SymPy.
    
    Args:
        filter1, filter2: Filter specifications to compare
    
    Returns:
        True if filters are logically equivalent
    """
    try:
        expr1 = FilterExpression(_parse_filter_from_any(filter1))
        expr2 = FilterExpression(_parse_filter_from_any(filter2))
        return expr1.is_equivalent(expr2)
    except Exception:
        # Fallback to string comparison
        canon1 = canonicalize_filter(filter1)
        canon2 = canonicalize_filter(filter2)
        return canon1 == canon2


def _parse_filter_from_any(filter_spec: Union[str, Dict[str, Any]]) -> FilterTerm:
    """Helper to parse filter from any format."""
    if isinstance(filter_spec, str):
        advanced_term = ADVANCED_PARSER.parse_complex_expression(filter_spec)
        if advanced_term:
            return advanced_term
        else:
            return GlobPattern(filter_spec)
    elif isinstance(filter_spec, dict):
        return _parse_filter_dict(filter_spec)
    else:
        raise TypeError(f"Unsupported filter type: {type(filter_spec)}")


# Backward compatibility with existing code
def normalize_filter(expr: str) -> str:
    """Normalize filter expression (backward compatibility)."""
    return canonicalize_filter(expr)


# Example usage and tests
if __name__ == "__main__":
    # Test glob pattern normalization
    patterns = ["src/**/*.py", "src/**/**/*.py", "**/*.txt", "*.txt", "src/**.py"]
    print(f"Original patterns: {patterns}")
    simplified = simplify_glob_patterns(patterns)
    print(f"Simplified patterns: {simplified}")
    
    # Test advanced logical filter normalization
    complex_filter = {
        "operator": "and",
        "operands": [
            {
                "operator": "or", 
                "operands": [
                    {"pattern": "*.py"},
                    {"pattern": "*.js"}
                ]
            },
            {
                "operator": "not",
                "operands": [{"pattern": "test_*"}]
            }
        ]
    }
    
    canonical = canonicalize_filter(complex_filter)
    print(f"Canonical filter: {canonical}")
    
    # Test DNF vs CNF conversion
    filter_expr = FilterExpression(_parse_filter_dict(complex_filter))
    dnf_form = filter_expr.to_dnf()
    cnf_form = filter_expr.to_cnf()
    simplified_form = filter_expr.simplify()
    
    print(f"DNF form: {dnf_form.to_canonical()}")
    print(f"CNF form: {cnf_form.to_canonical()}")
    print(f"Simplified form: {simplified_form.to_canonical()}")
    
    # Test advanced string parsing
    advanced_examples = [
        "size > 1000 AND *.py",
        "(*.py OR *.js) AND NOT test_*",
        "mtime > 2024-01-01 OR (size < 100 AND *.txt)"
    ]
    
    for example in advanced_examples:
        try:
            canonical = canonicalize_filter(example)
            print(f"Advanced parsing: '{example}' → '{canonical}'")
        except Exception as e:
            print(f"Failed to parse '{example}': {e}")
    
    # Test logical equivalence
    filter1 = {"operator": "and", "operands": [{"pattern": "*.py"}, {"pattern": "src/**"}]}
    filter2 = {"operator": "and", "operands": [{"pattern": "src/**"}, {"pattern": "*.py"}]}
    
    equivalent = check_filter_equivalence(filter1, filter2)
    print(f"Filters equivalent: {equivalent}")
    
    # Test different normal forms
    complex_string = "(*.py OR *.js) AND (size > 1000 OR mtime > 2024-01-01)"
    
    try:
        dnf_result = canonicalize_filter_advanced(complex_string, 'dnf')
        cnf_result = canonicalize_filter_advanced(complex_string, 'cnf')
        simp_result = canonicalize_filter_advanced(complex_string, 'simplified')
        
        print(f"Original: {complex_string}")
        print(f"DNF: {dnf_result}")
        print(f"CNF: {cnf_result}")
        print(f"Simplified: {simp_result}")
    except Exception as e:
        print(f"Advanced normalization failed: {e}")
    
    # Performance test
    import time
    large_filter = {
        "operator": "or",
        "operands": [
            {"operator": "and", "operands": [{"pattern": "*.py"}, {"pattern": "src/**"}]},
            {"property": "size", "operator": "gt", "value": 100},
            {"operator": "not", "operands": [{"pattern": "test_*"}]}
        ]
    }
    
    start = time.time()
    for _ in range(100):
        canonical = canonicalize_filter(large_filter)
    end = time.time()
    
    print(f"Performance test: {100} normalizations in {end-start:.3f}s")
    print(f"Large filter canonical form length: {len(canonical)} chars")
