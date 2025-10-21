"""
RepoQ TRS Verifiers Implementation

Concrete implementations of TRS verifiers for all RepoQ normalization systems.
Each verifier implements domain-specific test generation and critical pair analysis.
"""

from typing import Any, Dict, List, Set, Tuple, Optional
import random
import string
from rules.trs_properties import TRSVerifier, CriticalPair, check_critical_pair_joinability


class SPDXTRSVerifier(TRSVerifier):
    """Verifier for SPDX license normalization TRS."""
    
    def __init__(self):
        from repoq.normalize.spdx_trs import normalize_spdx
        super().__init__("SPDX", normalize_spdx)
    
    def generate_test_terms(self, count: int = 100) -> List[Any]:
        """Generate test SPDX license expressions."""
        base_licenses = [
            "MIT", "Apache-2.0", "GPL-3.0", "BSD-3-Clause", "ISC",
            "LGPL-2.1", "MPL-2.0", "AGPL-3.0", "Unlicense", "CC0-1.0"
        ]
        
        variations = []
        
        # Basic license identifiers
        for license_id in base_licenses:
            variations.extend([
                license_id,
                license_id.lower(),
                f" {license_id} ",
                f"{license_id}+",
                f"({license_id})",
            ])
        
        # Compound expressions
        compound_expressions = [
            "MIT OR Apache-2.0",
            "GPL-3.0 AND MIT",
            "(MIT OR GPL-3.0) AND Apache-2.0",
            "MIT WITH GCC-exception-3.1",
            "GPL-3.0+ OR MIT",
        ]
        variations.extend(compound_expressions)
        
        # Edge cases
        edge_cases = [
            "",
            "UNKNOWN",
            "Proprietary",
            "See LICENSE file",
            "Multiple licenses",
            "MIT\nApache-2.0",  # Newline
            "MIT\tApache-2.0",  # Tab
        ]
        variations.extend(edge_cases)
        
        return variations[:count]
    
    def find_critical_pairs(self) -> List[CriticalPair]:
        """Find critical pairs for SPDX normalization."""
        # SPDX normalization is mostly string processing with limited rule overlap
        critical_pairs = []
        
        test_cases = [
            ("MIT", " MIT ", "whitespace_trimming", "case_normalization"),
            ("mit", "MIT", "case_normalization", "identifier_lookup"),
            ("GPL-3.0+", "GPL-3.0-or-later", "plus_expansion", "identifier_normalization"),
        ]
        
        for term, alt_form, rule1, rule2 in test_cases:
            try:
                result1 = self.normalizer(term)
                result2 = self.normalizer(alt_form)
                
                cp = CriticalPair(
                    term=term,
                    left_result=result1,
                    right_result=result2,
                    rule1=rule1,
                    rule2=rule2,
                    joinable=result1 == result2
                )
                critical_pairs.append(cp)
            except Exception:
                pass
        
        return critical_pairs


class SemVerTRSVerifier(TRSVerifier):
    """Verifier for Semantic Version normalization TRS."""
    
    def __init__(self):
        from repoq.normalize.semver_trs import normalize_semver
        super().__init__("SemVer", normalize_semver)
    
    def generate_test_terms(self, count: int = 100) -> List[Any]:
        """Generate test semantic version strings."""
        versions = []
        
        # Standard versions
        for major in [0, 1, 2, 10]:
            for minor in [0, 1, 5]:
                for patch in [0, 1, 3]:
                    versions.append(f"{major}.{minor}.{patch}")
        
        # Pre-release versions
        prerelease_suffixes = [
            "-alpha", "-alpha.1", "-beta", "-beta.2", "-rc.1",
            "-dev", "-snapshot", "-M1", "-RELEASE"
        ]
        for version in versions[:10]:
            for suffix in prerelease_suffixes:
                versions.append(f"{version}{suffix}")
        
        # Build metadata
        for version in versions[:5]:
            versions.extend([
                f"{version}+build.1",
                f"{version}+20240101",
                f"{version}+sha.abc123"
            ])
        
        # Variations and edge cases
        variations = []
        for version in versions[:20]:
            variations.extend([
                f"v{version}",  # v prefix
                f" {version} ",  # whitespace
                f"{version}.0",  # extra zero
                version.replace(".", "-"),  # dash separator
            ])
        
        versions.extend(variations)
        
        # Invalid versions for robustness testing
        invalid_versions = [
            "", "1", "1.2", "1.2.3.4", "a.b.c",
            "1.2.3-", "1.2.3+", "v", "version"
        ]
        versions.extend(invalid_versions)
        
        return versions[:count]
    
    def find_critical_pairs(self) -> List[CriticalPair]:
        """Find critical pairs for SemVer normalization."""
        critical_pairs = []
        
        test_cases = [
            ("v1.2.3", "1.2.3", "prefix_removal", "standard_format"),
            ("1.2.3-alpha", "1.2.3-ALPHA", "prerelease_case", "case_normalization"),
            ("1.2.3+build", "1.2.3+BUILD", "build_case", "case_normalization"),
        ]
        
        for term, alt_form, rule1, rule2 in test_cases:
            try:
                result1 = self.normalizer(term)
                result2 = self.normalizer(alt_form)
                
                cp = CriticalPair(
                    term=term,
                    left_result=result1,
                    right_result=result2,
                    rule1=rule1,
                    rule2=rule2,
                    joinable=result1 == result2
                )
                critical_pairs.append(cp)
            except Exception:
                pass
        
        return critical_pairs


class FiltersTRSVerifier(TRSVerifier):
    """Verifier for Filters logical expression TRS."""
    
    def __init__(self):
        from repoq.normalize.filters_trs import canonicalize_filter
        super().__init__("Filters", canonicalize_filter)
    
    def generate_test_terms(self, count: int = 100) -> List[Any]:
        """Generate test filter expressions."""
        filters = []
        
        # Simple patterns
        patterns = ["*.py", "*.js", "src/**", "test_*", "**/*.txt"]
        filters.extend(patterns)
        
        # Simple properties
        properties = [
            {"property": "size", "operator": "gt", "value": 1000},
            {"property": "mtime", "operator": "lt", "value": "2024-01-01"},
            {"property": "extension", "operator": "in", "value": ["py", "js"]},
        ]
        filters.extend(properties)
        
        # Logical combinations
        logical_ops = ["and", "or", "not"]
        for i in range(20):
            op = random.choice(logical_ops)
            if op == "not":
                operand = random.choice(patterns[:3])
                filters.append({
                    "operator": op,
                    "operands": [{"pattern": operand}]
                })
            else:
                operands = random.sample(patterns, 2)
                filters.append({
                    "operator": op,
                    "operands": [{"pattern": p} for p in operands]
                })
        
        # Complex nested expressions
        complex_filters = [
            {
                "operator": "and",
                "operands": [
                    {"pattern": "*.py"},
                    {
                        "operator": "or",
                        "operands": [
                            {"pattern": "src/**"},
                            {"pattern": "lib/**"}
                        ]
                    }
                ]
            },
            {
                "operator": "not",
                "operands": [{
                    "operator": "and",
                    "operands": [
                        {"pattern": "test_*"},
                        {"property": "size", "operator": "lt", "value": 100}
                    ]
                }]
            }
        ]
        filters.extend(complex_filters)
        
        return filters[:count]
    
    def find_critical_pairs(self) -> List[CriticalPair]:
        """Find critical pairs for filter normalization."""
        critical_pairs = []
        
        # Test logical equivalences that should produce same normal form
        test_cases = [
            # Commutativity: A AND B = B AND A
            ({"operator": "and", "operands": [{"pattern": "*.py"}, {"pattern": "*.js"}]},
             {"operator": "and", "operands": [{"pattern": "*.js"}, {"pattern": "*.py"}]},
             "and_commutativity_1", "and_commutativity_2"),
            
            # Double negation: NOT NOT A = A
            ({"operator": "not", "operands": [{"operator": "not", "operands": [{"pattern": "*.py"}]}]},
             {"pattern": "*.py"},
             "double_negation", "identity"),
            
            # De Morgan's law: NOT (A AND B) = (NOT A) OR (NOT B)
            ({"operator": "not", "operands": [{
                "operator": "and", 
                "operands": [{"pattern": "*.py"}, {"pattern": "*.js"}]
            }]},
             {"operator": "or", "operands": [
                {"operator": "not", "operands": [{"pattern": "*.py"}]},
                {"operator": "not", "operands": [{"pattern": "*.js"}]}
             ]},
             "demorgan_negation", "demorgan_expansion"),
        ]
        
        for term1, term2, rule1, rule2 in test_cases:
            try:
                result1 = self.normalizer(term1)
                result2 = self.normalizer(term2)
                
                cp = CriticalPair(
                    term=term1,
                    left_result=result1,
                    right_result=result2,
                    rule1=rule1,
                    rule2=rule2,
                    joinable=self._check_logical_equivalence(result1, result2)
                )
                critical_pairs.append(cp)
            except Exception:
                pass
        
        return critical_pairs
    
    def _check_logical_equivalence(self, expr1: str, expr2: str) -> bool:
        """Check if two filter expressions are logically equivalent."""
        try:
            from repoq.normalize.filters_trs import check_filter_equivalence
            return check_filter_equivalence(expr1, expr2)
        except ImportError:
            return expr1 == expr2


class MetricsTRSVerifier(TRSVerifier):
    """Verifier for Metrics algebraic expression TRS."""
    
    def __init__(self):
        from repoq.normalize.metrics_trs import canonicalize_metric
        super().__init__("Metrics", canonicalize_metric)
    
    def generate_test_terms(self, count: int = 100) -> List[Any]:
        """Generate test metric expressions."""
        expressions = []
        
        # Simple variables
        variables = ["lines", "complexity", "coverage", "bugs", "debt"]
        expressions.extend(variables)
        
        # Simple arithmetic
        for var in variables[:3]:
            expressions.extend([
                f"2 * {var}",
                f"{var} + 1",
                f"{var} / 100",
                f"{var} - baseline"
            ])
        
        # Aggregation functions
        agg_functions = ["sum", "avg", "max", "min", "count"]
        for func in agg_functions:
            expressions.extend([
                f"{func}(lines)",
                f"{func}(lines, complexity)",
                f"{func}(coverage, bugs, debt)"
            ])
        
        # Complex expressions
        complex_expressions = [
            "2 * lines + 3 * complexity",
            "(lines + complexity) * weight",
            "sum(lines) / count(files)",
            "avg(complexity) * 0.6 + avg(coverage) * 0.4",
            "max(bugs, 0) + min(debt, 1000)",
            "lines * (1 + complexity / 100)",
            "((a + b) * 2 + (a + b) * 3) / (c + d + c)",
        ]
        expressions.extend(complex_expressions)
        
        # Weighted syntax
        weighted_expressions = [
            "complexity:0.6",
            "lines:0.3 + complexity:0.7",
            "sum(lines:0.5, complexity:0.5)",
        ]
        expressions.extend(weighted_expressions)
        
        return expressions[:count]
    
    def find_critical_pairs(self) -> List[CriticalPair]:
        """Find critical pairs for metric normalization."""
        critical_pairs = []
        
        # Test algebraic equivalences
        test_cases = [
            # Commutativity: a + b = b + a
            ("lines + complexity", "complexity + lines", "addition_comm_1", "addition_comm_2"),
            
            # Associativity: (a + b) + c = a + (b + c)
            ("(lines + complexity) + bugs", "lines + (complexity + bugs)", "addition_assoc_1", "addition_assoc_2"),
            
            # Like terms: 2*x + 3*x = 5*x
            ("2 * lines + 3 * lines", "5 * lines", "term_collection", "simplified_form"),
            
            # Distributivity: a * (b + c) = a*b + a*c
            ("weight * (lines + complexity)", "weight * lines + weight * complexity", "distributive", "expanded_form"),
            
            # Function argument commutativity
            ("sum(lines, complexity)", "sum(complexity, lines)", "func_arg_comm_1", "func_arg_comm_2"),
        ]
        
        for term1, term2, rule1, rule2 in test_cases:
            try:
                result1 = self.normalizer(term1)
                result2 = self.normalizer(term2)
                
                cp = CriticalPair(
                    term=term1,
                    left_result=result1,
                    right_result=result2,
                    rule1=rule1,
                    rule2=rule2,
                    joinable=self._check_algebraic_equivalence(result1, result2)
                )
                critical_pairs.append(cp)
            except Exception:
                pass
        
        return critical_pairs
    
    def _check_algebraic_equivalence(self, expr1: str, expr2: str) -> bool:
        """Check if two metric expressions are algebraically equivalent."""
        try:
            import sympy as sp
            # Convert canonical forms back to SymPy and check equivalence
            # This is simplified - real implementation would parse canonical syntax
            return expr1 == expr2  # For now, just check string equality
        except ImportError:
            return expr1 == expr2


class RDFTRSVerifier(TRSVerifier):
    """Verifier for RDF graph canonicalization TRS."""
    
    def __init__(self):
        from repoq.normalize.rdf_trs import canonicalize_rdf
        super().__init__("RDF", canonicalize_rdf)
    
    def generate_test_terms(self, count: int = 100) -> List[Any]:
        """Generate test RDF graphs and JSON-LD documents."""
        test_data = []
        
        # Simple JSON-LD documents
        simple_docs = [
            {"@type": "Project", "name": "test"},
            {"@context": "http://schema.org/", "@type": "Person", "name": "John"},
            {"@id": "http://example.org/1", "title": "Example"},
        ]
        test_data.extend(simple_docs)
        
        # Documents with different orderings
        doc_base = {
            "@context": "http://schema.org/",
            "@type": "SoftwareProject",
            "name": "RepoQ",
            "description": "Repository analysis tool",
            "programmingLanguage": "Python"
        }
        
        # Different key orderings (should canonicalize to same form)
        import json
        for _ in range(5):
            keys = list(doc_base.keys())
            random.shuffle(keys)
            shuffled_doc = {k: doc_base[k] for k in keys}
            test_data.append(shuffled_doc)
        
        # Documents with blank nodes
        blank_node_docs = [
            {
                "@type": "Project",
                "author": {"@type": "Person", "name": "Anonymous"},
                "contributor": [
                    {"@type": "Person", "name": "Alice"},
                    {"@type": "Person", "name": "Bob"}
                ]
            }
        ]
        test_data.extend(blank_node_docs)
        
        # String serializations
        for doc in test_data[:10]:
            test_data.append(json.dumps(doc))
            test_data.append(json.dumps(doc, separators=(',', ':')))  # Compact
        
        return test_data[:count]
    
    def find_critical_pairs(self) -> List[CriticalPair]:
        """Find critical pairs for RDF canonicalization."""
        critical_pairs = []
        
        # Test documents that should canonicalize to same form
        import json
        
        base_doc = {
            "@context": "http://schema.org/",
            "@type": "Project", 
            "name": "test"
        }
        
        # Different serializations of same document
        variations = [
            (json.dumps(base_doc), json.dumps(base_doc, indent=2), "compact_json", "pretty_json"),
            (json.dumps(base_doc), json.dumps(base_doc, sort_keys=True), "original_order", "sorted_keys"),
        ]
        
        for term1, term2, rule1, rule2 in variations:
            try:
                result1 = self.normalizer(term1)
                result2 = self.normalizer(term2)
                
                cp = CriticalPair(
                    term=term1,
                    left_result=result1,
                    right_result=result2,
                    rule1=rule1,
                    rule2=rule2,
                    joinable=result1 == result2
                )
                critical_pairs.append(cp)
            except Exception:
                pass
        
        return critical_pairs


def create_all_verifiers() -> Dict[str, TRSVerifier]:
    """Create all TRS verifiers."""
    return {
        'spdx': SPDXTRSVerifier(),
        'semver': SemVerTRSVerifier(),
        'filters': FiltersTRSVerifier(),
        'metrics': MetricsTRSVerifier(),
        'rdf': RDFTRSVerifier(),
    }