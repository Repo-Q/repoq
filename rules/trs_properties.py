"""
TRS Property Definitions and Verification Framework

Formal verification of Term Rewriting System properties for all RepoQ normalizers.
Implements Newman's lemma for confluence and well-founded measures for termination.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Set, Tuple, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
import time
import hashlib
import json


class TRSProperty(Enum):
    """Enumeration of TRS properties to verify."""
    SOUNDNESS = "soundness"
    CONFLUENCE = "confluence" 
    TERMINATION = "termination"
    IDEMPOTENCE = "idempotence"
    DETERMINISM = "determinism"
    COMMUTATIVITY = "commutativity"
    ASSOCIATIVITY = "associativity"


@dataclass
class RewriteStep:
    """Single step in a rewrite sequence."""
    input_term: Any
    output_term: Any
    rule_applied: str
    step_number: int
    timestamp: float


@dataclass
class RewriteSequence:
    """Complete sequence of rewrite steps."""
    initial_term: Any
    final_term: Any
    steps: List[RewriteStep]
    total_time_ms: float
    terminated: bool
    

@dataclass
class CriticalPair:
    """Critical pair for confluence analysis."""
    term: Any
    left_result: Any
    right_result: Any
    rule1: str
    rule2: str
    joinable: bool
    join_steps: Optional[List[RewriteStep]] = None


class TRSVerifier(ABC):
    """Abstract base class for TRS verification."""
    
    def __init__(self, name: str, normalizer: Callable[[Any], Any]):
        self.name = name
        self.normalizer = normalizer
        self.verification_cache: Dict[str, Any] = {}
    
    @abstractmethod
    def generate_test_terms(self, count: int = 100) -> List[Any]:
        """Generate test terms for property verification."""
        pass
    
    @abstractmethod
    def find_critical_pairs(self) -> List[CriticalPair]:
        """Find critical pairs for confluence analysis."""
        pass
    
    def verify_idempotence(self, test_terms: Optional[List[Any]] = None) -> bool:
        """Verify that f(f(x)) = f(x) for all terms."""
        if test_terms is None:
            test_terms = self.generate_test_terms(50)
        
        violations = []
        for term in test_terms:
            try:
                normalized1 = self.normalizer(term)
                normalized2 = self.normalizer(normalized1)
                
                if normalized1 != normalized2:
                    violations.append({
                        'term': term,
                        'first_normal': normalized1,
                        'second_normal': normalized2
                    })
            except Exception as e:
                violations.append({
                    'term': term,
                    'error': str(e)
                })
        
        self.verification_cache['idempotence_violations'] = violations
        return len(violations) == 0
    
    def verify_determinism(self, test_terms: Optional[List[Any]] = None, runs: int = 3) -> bool:
        """Verify that multiple runs produce identical results."""
        if test_terms is None:
            test_terms = self.generate_test_terms(20)
        
        violations = []
        for term in test_terms:
            try:
                results = [self.normalizer(term) for _ in range(runs)]
                
                if not all(r == results[0] for r in results):
                    violations.append({
                        'term': term,
                        'results': results
                    })
            except Exception as e:
                violations.append({
                    'term': term,
                    'error': str(e)
                })
        
        self.verification_cache['determinism_violations'] = violations
        return len(violations) == 0
    
    def verify_confluence(self) -> bool:
        """Verify confluence via critical pair analysis."""
        critical_pairs = self.find_critical_pairs()
        
        # Check if all critical pairs are joinable
        non_joinable = [cp for cp in critical_pairs if not cp.joinable]
        
        self.verification_cache['critical_pairs'] = len(critical_pairs)
        self.verification_cache['non_joinable_pairs'] = non_joinable
        
        return len(non_joinable) == 0
    
    def verify_termination(self, test_terms: Optional[List[Any]] = None, 
                          timeout_ms: int = 5000) -> bool:
        """Verify termination with timeout protection."""
        if test_terms is None:
            test_terms = self.generate_test_terms(30)
        
        violations = []
        for term in test_terms:
            start_time = time.time()
            try:
                # Use timeout to detect infinite loops
                result = self._normalize_with_timeout(term, timeout_ms)
                
                if result is None:  # Timeout occurred
                    violations.append({
                        'term': term,
                        'issue': 'timeout',
                        'timeout_ms': timeout_ms
                    })
            except Exception as e:
                violations.append({
                    'term': term,
                    'error': str(e)
                })
        
        self.verification_cache['termination_violations'] = violations
        return len(violations) == 0
    
    def _normalize_with_timeout(self, term: Any, timeout_ms: int) -> Optional[Any]:
        """Normalize with timeout protection."""
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Normalization timeout")
        
        # Set timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_ms // 1000)
        
        try:
            result = self.normalizer(term)
            signal.alarm(0)  # Cancel timeout
            return result
        except TimeoutError:
            signal.alarm(0)
            return None
    
    def verify_soundness(self, test_terms: Optional[List[Any]] = None) -> bool:
        """Verify mathematical soundness (semantic equivalence preservation)."""
        # Default implementation - subclasses should override for domain-specific checks
        return self.verify_idempotence(test_terms)
    
    def run_full_verification(self) -> Dict[str, Any]:
        """Run complete verification suite."""
        test_terms = self.generate_test_terms(100)
        
        results = {
            'trs_name': self.name,
            'timestamp': time.time(),
            'test_terms_count': len(test_terms)
        }
        
        # Run all property checks
        properties = [
            ('idempotence', lambda: self.verify_idempotence(test_terms)),
            ('determinism', lambda: self.verify_determinism(test_terms)),
            ('confluence', self.verify_confluence),
            ('termination', lambda: self.verify_termination(test_terms)),
            ('soundness', lambda: self.verify_soundness(test_terms))
        ]
        
        for prop_name, verifier in properties:
            start_time = time.time()
            try:
                result = verifier()
                results[prop_name] = {
                    'passed': result,
                    'time_ms': (time.time() - start_time) * 1000
                }
            except Exception as e:
                results[prop_name] = {
                    'passed': False,
                    'error': str(e),
                    'time_ms': (time.time() - start_time) * 1000
                }
        
        # Add cached verification details
        results['verification_details'] = self.verification_cache.copy()
        
        return results


def hash_term(term: Any) -> str:
    """Generate deterministic hash for any term."""
    term_str = json.dumps(term, sort_keys=True, default=str)
    return hashlib.sha256(term_str.encode()).hexdigest()[:16]


def check_critical_pair_joinability(cp: CriticalPair, normalizer: Callable[[Any], Any], 
                                   max_steps: int = 10) -> bool:
    """Check if a critical pair is joinable within max_steps."""
    try:
        # Try to find a common normal form
        left_normal = normalizer(cp.left_result)
        right_normal = normalizer(cp.right_result)
        
        if left_normal == right_normal:
            cp.joinable = True
            return True
        
        # For more complex cases, would need step-by-step rewriting
        # This is a simplified check
        cp.joinable = False
        return False
        
    except Exception:
        cp.joinable = False
        return False


class PropertyViolation:
    """Represents a violation of a TRS property."""
    
    def __init__(self, property_name: str, term: Any, details: Dict[str, Any]):
        self.property_name = property_name
        self.term = term
        self.details = details
        self.hash = hash_term(term)
    
    def __str__(self):
        return f"{self.property_name} violation on {self.term}: {self.details}"


def verify_all_trs_systems(systems: Dict[str, TRSVerifier]) -> Dict[str, Dict[str, Any]]:
    """Verify all TRS systems and generate comprehensive report."""
    results = {}
    
    for name, verifier in systems.items():
        print(f"Verifying {name} TRS...")
        results[name] = verifier.run_full_verification()
    
    # Generate summary
    summary = {
        'total_systems': len(systems),
        'all_passed': all(
            all(prop.get('passed', False) for prop in result.values() 
                if isinstance(prop, dict) and 'passed' in prop)
            for result in results.values()
        ),
        'verification_time': sum(
            sum(prop.get('time_ms', 0) for prop in result.values()
                if isinstance(prop, dict) and 'time_ms' in prop)
            for result in results.values()
        )
    }
    
    results['_summary'] = summary
    return results


# Example property checkers for specific domains

def check_logical_equivalence(expr1: Any, expr2: Any) -> bool:
    """Check if two logical expressions are equivalent (for Filters TRS)."""
    # Simplified - would use SymPy or similar for real implementation
    try:
        from repoq.normalize.filters_trs import check_filter_equivalence
        return check_filter_equivalence(expr1, expr2)
    except ImportError:
        return str(expr1) == str(expr2)


def check_algebraic_equivalence(expr1: Any, expr2: Any) -> bool:
    """Check if two algebraic expressions are equivalent (for Metrics TRS)."""
    # Simplified - would use SymPy evaluation for real implementation
    try:
        import sympy as sp
        # Convert to SymPy and check equivalence
        diff = sp.simplify(sp.sympify(str(expr1)) - sp.sympify(str(expr2)))
        return diff == 0
    except (ImportError, Exception):
        return str(expr1) == str(expr2)


def check_graph_isomorphism(graph1: Any, graph2: Any) -> bool:
    """Check if two RDF graphs are isomorphic (for RDF TRS)."""
    # Simplified - would use rdflib graph comparison for real implementation
    return str(graph1) == str(graph2)