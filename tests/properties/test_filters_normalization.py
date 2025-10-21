"""
Property-based tests for Filters TRS

Tests formal properties:
1. Idempotence: canonicalize(canonicalize(x)) = canonicalize(x)
2. Determinism: Multiple canonicalization runs produce same result
3. DNF form: Logical equivalence under transformation
4. Glob simplification: Pattern reduction preserves semantics
5. Sort stability: Operand ordering is consistent
"""

import pytest
from hypothesis import given, strategies as st
from typing import Any, Dict, List

from repoq.normalize.filters_trs import (
    canonicalize_filter, FilterExpression, GlobPattern, FileProperty, 
    LogicalFilter, simplify_glob_patterns, _parse_filter_dict,
    normalize_filter_expression, canonicalize_filter_advanced,
    check_filter_equivalence, ADVANCED_PARSER
)


# Hypothesis strategies for generating test data
@st.composite
def glob_pattern_strategy(draw):
    """Generate valid glob patterns."""
    patterns = [
        "*.py", "*.js", "*.txt", "**/*.py", "src/**", "test_*",
        "**/*.{py,js}", "**/test_*.py", "*.log", "docs/**/*.md",
        "[abc]*.txt", "file?.py", "**", "*"
    ]
    return draw(st.sampled_from(patterns))


@st.composite
def file_property_strategy(draw):
    """Generate file property predicates."""
    properties = ["size", "mtime", "extension", "type", "permissions"]
    operators = ["eq", "ne", "lt", "gt", "le", "ge", "in", "not_in"]
    values = [100, "py", ["py", "js"], "file", 644]
    
    return {
        "property": draw(st.sampled_from(properties)),
        "operator": draw(st.sampled_from(operators)),
        "value": draw(st.sampled_from(values))
    }


@st.composite
def simple_filter_strategy(draw):
    """Generate simple filter terms (patterns or properties)."""
    return draw(st.one_of(
        st.builds(dict, pattern=glob_pattern_strategy()),
        file_property_strategy()
    ))


@st.composite
def logical_filter_strategy(draw, max_depth=3):
    """Generate nested logical filter expressions."""
    if max_depth <= 0:
        return draw(simple_filter_strategy())
    
    operator = draw(st.sampled_from(["and", "or", "not"]))
    
    if operator == "not":
        operand = draw(logical_filter_strategy(max_depth - 1))
        return {"operator": operator, "operands": [operand]}
    else:
        num_operands = draw(st.integers(min_value=2, max_value=4))
        operands = [draw(logical_filter_strategy(max_depth - 1)) for _ in range(num_operands)]
        return {"operator": operator, "operands": operands}


class TestFilterTerms:
    """Test individual filter term classes."""
    
    def test_glob_pattern_normalization(self):
        """Test glob pattern canonical normalization."""
        # Path separator normalization
        pattern = GlobPattern("src///**///*.py")
        assert pattern.pattern == "src/**/*.py"
        
        # Wildcard simplification
        pattern = GlobPattern("***/*.txt")
        assert pattern.pattern == "**/*.txt"
        
        # Character class sorting
        pattern = GlobPattern("[cba]*.txt")
        assert pattern.pattern == "[abc]*.txt"
        
        # Trailing slash removal
        pattern = GlobPattern("src/")
        assert pattern.pattern == "src"
    
    def test_file_property_canonical_form(self):
        """Test file property canonical representation."""
        prop = FileProperty("size", "==", 100)
        assert prop.to_canonical() == "prop:size:eq:100"
        
        prop = FileProperty("extension", "in", ["py", "js"])
        canonical = prop.to_canonical()
        # Should sort values in lists
        assert "js,py" in canonical or "py,js" in canonical
    
    def test_logical_filter_operand_sorting(self):
        """Test that logical filter operands are sorted canonically."""
        # Create filter with operands in different order
        pattern1 = GlobPattern("*.py")
        pattern2 = GlobPattern("*.js")
        prop = FileProperty("size", "gt", 100)
        
        filter1 = LogicalFilter("and", (pattern1, pattern2, prop))
        filter2 = LogicalFilter("and", (prop, pattern2, pattern1))
        
        assert filter1.to_canonical() == filter2.to_canonical()


class TestFilterExpressions:
    """Test complete filter expression processing."""
    
    def test_dnf_conversion_simple(self):
        """Test basic DNF conversion."""
        # NOT (A AND B) should become (NOT A) OR (NOT B)
        filter_dict = {
            "operator": "not",
            "operands": [{
                "operator": "and",
                "operands": [
                    {"pattern": "*.py"},
                    {"pattern": "*.js"}
                ]
            }]
        }
        
        term = _parse_filter_dict(filter_dict)
        expr = FilterExpression(term)
        dnf = expr.to_dnf()
        canonical = dnf.to_canonical()
        
        # Should be in DNF form with OR at top level
        assert canonical.startswith("or(")
        assert "not(glob:*.js)" in canonical
        assert "not(glob:*.py)" in canonical
    
    def test_dnf_distribution(self):
        """Test AND distribution over OR."""
        # A AND (B OR C) should become (A AND B) OR (A AND C)
        filter_dict = {
            "operator": "and",
            "operands": [
                {"pattern": "*.py"},
                {
                    "operator": "or",
                    "operands": [
                        {"pattern": "src/**"},
                        {"pattern": "test/**"}
                    ]
                }
            ]
        }
        
        term = _parse_filter_dict(filter_dict)
        expr = FilterExpression(term)
        dnf = expr.to_dnf()
        canonical = dnf.to_canonical()
        
        # Should distribute A over (B OR C)
        assert canonical.startswith("or(")
        assert "and(glob:*.py,glob:src/**)" in canonical
        assert "and(glob:*.py,glob:test/**)" in canonical
    
    def test_double_negation_elimination(self):
        """Test that NOT NOT A becomes A."""
        filter_dict = {
            "operator": "not",
            "operands": [{
                "operator": "not", 
                "operands": [{"pattern": "*.py"}]
            }]
        }
        
        term = _parse_filter_dict(filter_dict)
        expr = FilterExpression(term)
        dnf = expr.to_dnf()
        canonical = dnf.to_canonical()
        
        assert canonical == "glob:*.py"


class TestGlobSimplification:
    """Test glob pattern simplification and redundancy removal."""
    
    def test_duplicate_removal(self):
        """Test removal of duplicate patterns."""
        patterns = ["*.py", "*.js", "*.py", "*.txt"]
        simplified = simplify_glob_patterns(patterns)
        
        assert len(simplified) == 3
        assert "*.py" in simplified
        assert "*.js" in simplified  
        assert "*.txt" in simplified
    
    def test_redundancy_removal(self):
        """Test removal of redundant patterns."""
        patterns = ["**", "*.py", "src/**"]
        simplified = simplify_glob_patterns(patterns)
        
        # ** should subsume everything else
        assert simplified == ["**"]
    
    def test_empty_pattern_list(self):
        """Test handling of empty pattern lists."""
        simplified = simplify_glob_patterns([])
        assert simplified == []


class TestCanonicalization:
    """Test main canonicalization API."""
    
    def test_string_input(self):
        """Test canonicalization of string inputs."""
        # Simple glob pattern
        result = canonicalize_filter("*.py")
        assert result == "glob:*.py"
        
        # Already canonical form
        canonical_form = "and(glob:*.py,glob:*.js)"
        result = canonicalize_filter(canonical_form)
        assert result == canonical_form
    
    def test_dict_input(self):
        """Test canonicalization of dictionary inputs."""
        filter_dict = {
            "operator": "and",
            "operands": [
                {"pattern": "*.py"},
                {"property": "size", "operator": "gt", "value": 1000}
            ]
        }
        
        result = canonicalize_filter(filter_dict)
        expected = "and(glob:*.py,prop:size:gt:1000)"
        assert result == expected
    
    def test_invalid_input_type(self):
        """Test handling of invalid input types."""
        with pytest.raises(TypeError):
            canonicalize_filter(123)


class TestPropertyBasedTesting:
    """Property-based tests using Hypothesis."""
    
    @given(simple_filter_strategy())
    def test_idempotence_simple_filters(self, filter_dict):
        """Test that canonicalizing twice gives same result."""
        canonical1 = canonicalize_filter(filter_dict)
        canonical2 = canonicalize_filter(canonical1)
        assert canonical1 == canonical2
    
    @given(logical_filter_strategy(max_depth=2))
    def test_idempotence_complex_filters(self, filter_dict):
        """Test idempotence for complex logical expressions."""
        try:
            canonical1 = canonicalize_filter(filter_dict)
            canonical2 = canonicalize_filter(canonical1)
            assert canonical1 == canonical2
        except (ValueError, KeyError):
            # Skip invalid filter structures
            pass
    
    @given(logical_filter_strategy(max_depth=2))
    def test_determinism(self, filter_dict):
        """Test that multiple canonicalization runs are deterministic."""
        try:
            results = [canonicalize_filter(filter_dict) for _ in range(3)]
            assert all(r == results[0] for r in results)
        except (ValueError, KeyError):
            # Skip invalid filter structures
            pass
    
    @given(st.lists(glob_pattern_strategy(), min_size=1, max_size=10))
    def test_glob_simplification_idempotence(self, patterns):
        """Test that glob simplification is idempotent."""
        simplified1 = simplify_glob_patterns(patterns)
        simplified2 = simplify_glob_patterns(simplified1)
        assert simplified1 == simplified2
    
    @given(st.lists(glob_pattern_strategy(), min_size=1, max_size=10))
    def test_glob_simplification_reduces_size(self, patterns):
        """Test that simplification doesn't increase pattern count."""
        simplified = simplify_glob_patterns(patterns)
        assert len(simplified) <= len(set(patterns))


class TestAdvancedFeatures:
    """Test advanced features with SymPy and tree-sitter."""
    
    def test_sympy_dnf_conversion(self):
        """Test DNF conversion using SymPy."""
        # (A OR B) AND (C OR D) should become (A AND C) OR (A AND D) OR (B AND C) OR (B AND D)
        filter_dict = {
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
                    "operator": "or", 
                    "operands": [
                        {"pattern": "src/**"},
                        {"pattern": "test/**"}
                    ]
                }
            ]
        }
        
        term = _parse_filter_dict(filter_dict)
        expr = FilterExpression(term)
        dnf = expr.to_dnf()
        canonical = dnf.to_canonical()
        
        # Should be in DNF form with OR at top level
        assert canonical.startswith("or(")
        # Should contain all combinations
        assert "and(glob:*.py,glob:src/**)" in canonical
        assert "and(glob:*.py,glob:test/**)" in canonical
        assert "and(glob:*.js,glob:src/**)" in canonical
        assert "and(glob:*.js,glob:test/**)" in canonical
    
    def test_sympy_cnf_conversion(self):
        """Test CNF conversion using SymPy."""
        # (A AND B) OR (C AND D) should stay in CNF
        filter_dict = {
            "operator": "or",
            "operands": [
                {
                    "operator": "and",
                    "operands": [
                        {"pattern": "*.py"},
                        {"pattern": "src/**"}
                    ]
                },
                {
                    "operator": "and",
                    "operands": [
                        {"pattern": "*.js"},
                        {"pattern": "test/**"}
                    ]
                }
            ]
        }
        
        term = _parse_filter_dict(filter_dict)
        expr = FilterExpression(term)
        cnf = expr.to_cnf()
        canonical = cnf.to_canonical()
        
        assert isinstance(canonical, str)
        assert len(canonical) > 0
    
    def test_logical_equivalence(self):
        """Test logical equivalence checking."""
        filter1 = {
            "operator": "and",
            "operands": [
                {"pattern": "*.py"},
                {"pattern": "src/**"}
            ]
        }
        
        filter2 = {
            "operator": "and", 
            "operands": [
                {"pattern": "src/**"},
                {"pattern": "*.py"}
            ]
        }
        
        # Should be equivalent (commutativity)
        assert check_filter_equivalence(filter1, filter2)
        
        filter3 = {
            "operator": "or",
            "operands": [
                {"pattern": "*.py"},
                {"pattern": "*.js"}
            ]
        }
        
        # Should not be equivalent
        assert not check_filter_equivalence(filter1, filter3)
    
    def test_advanced_canonicalization_forms(self):
        """Test different canonical forms."""
        filter_dict = {
            "operator": "and",
            "operands": [
                {
                    "operator": "or",
                    "operands": [
                        {"pattern": "*.py"},
                        {"pattern": "*.js"}
                    ]
                },
                {"property": "size", "operator": "gt", "value": 1000}
            ]
        }
        
        dnf_form = canonicalize_filter_advanced(filter_dict, 'dnf')
        cnf_form = canonicalize_filter_advanced(filter_dict, 'cnf') 
        simp_form = canonicalize_filter_advanced(filter_dict, 'simplified')
        
        assert isinstance(dnf_form, str)
        assert isinstance(cnf_form, str)
        assert isinstance(simp_form, str)
        
        # All forms should be valid
        assert len(dnf_form) > 0
        assert len(cnf_form) > 0
        assert len(simp_form) > 0
    
    def test_advanced_glob_simplification(self):
        """Test advanced glob pattern simplification."""
        patterns = [
            "src/**/*.py",
            "src/module1/*.py", 
            "src/module2/*.py",
            "**/*.txt",
            "docs/*.txt",
            "*.log"
        ]
        
        simplified = simplify_glob_patterns(patterns)
        
        # Should remove redundant patterns
        assert len(simplified) <= len(patterns)
        # Should still contain essential patterns
        assert any("**" in p for p in simplified)
    
    def test_tree_sitter_parsing(self):
        """Test tree-sitter parsing capabilities."""
        if ADVANCED_PARSER.parser is None:
            pytest.skip("Tree-sitter not available")
        
        # Simple expression
        expr = "*.py AND size > 1000"
        term = ADVANCED_PARSER.parse_complex_expression(expr)
        
        if term:  # Parser may not handle all cases
            assert isinstance(term, (LogicalFilter, GlobPattern, FileProperty))
    
    def test_pattern_subsumption(self):
        """Test advanced pattern subsumption."""
        from repoq.normalize.filters_trs import _advanced_pattern_subsumes
        
        # Basic subsumption
        assert _advanced_pattern_subsumes("**", "src/*.py")
        assert _advanced_pattern_subsumes("src/**", "src/module/*.py")
        assert _advanced_pattern_subsumes("*.py", "main.py")
        
        # Non-subsumption
        assert not _advanced_pattern_subsumes("*.py", "*.js")
        assert not _advanced_pattern_subsumes("src/*.py", "test/*.py")
    
    def test_regex_conversion(self):
        """Test glob to regex conversion."""
        from repoq.normalize.filters_trs import _glob_to_regex
        
        # Basic patterns
        assert _glob_to_regex("*.py") == "^[^/]*\\.py$"
        assert _glob_to_regex("**/*.py") == "^.*/[^/]*\\.py$"  # ** keeps the / separator
        assert _glob_to_regex("test_?.py") == "^test_[^/]\\.py$"
        
        # Character classes
        regex = _glob_to_regex("[abc]*.txt")
        assert "[abc]" in regex
        assert "\\.txt" in regex


class TestIntegration:
    """Integration tests with existing components."""
    
    def test_backward_compatibility(self):
        """Test backward compatibility with normalize_filter."""
        from repoq.normalize.filters_trs import normalize_filter
        
        # Simple case
        result = normalize_filter("*.py")
        assert result == "glob:*.py"
    
    def test_complex_real_world_filter(self):
        """Test complex filter that might appear in real usage."""
        complex_filter = {
            "operator": "and",
            "operands": [
                {
                    "operator": "or",
                    "operands": [
                        {"pattern": "*.py"},
                        {"pattern": "*.js"},
                        {"pattern": "*.ts"}
                    ]
                },
                {
                    "operator": "not",
                    "operands": [{
                        "operator": "or",
                        "operands": [
                            {"pattern": "test_*"},
                            {"pattern": "*/test/*"},
                            {"property": "size", "operator": "lt", "value": 10}
                        ]
                    }]
                },
                {"property": "mtime", "operator": "gt", "value": "2024-01-01"}
            ]
        }
        
        canonical = canonicalize_filter(complex_filter)
        
        # Should be valid and consistent
        assert isinstance(canonical, str)
        assert len(canonical) > 0
        
        # Test idempotence
        canonical2 = canonicalize_filter(canonical)
        assert canonical == canonical2


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])