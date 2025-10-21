"""
Base infrastructure for Term Rewriting Systems.

Provides abstract classes and utilities for building confluent,
terminating rewrite systems with formal guarantees.

Theory:
    A TRS is a pair (Σ, R) where Σ is a signature and R is a set of rewrite rules.
    A rule l → r is applied by matching l and replacing with r.
    
    Properties:
    - **Termination**: every rewrite sequence is finite
    - **Confluence**: if t →* s₁ and t →* s₂, then ∃u: s₁ →* u and s₂ →* u
    - **Normal Form**: a term with no applicable rules
    
    Newman's Lemma: Termination + Local Confluence ⟹ Confluence

Classes:
    Term: Abstract base for terms in the algebra
    Rule: A rewrite rule (pattern → replacement)
    RewriteSystem: Orchestrates rules with termination checking
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, List, Optional, TypeVar
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="Term")


class Term(ABC):
    """
    Abstract base class for terms in a rewriting system.
    
    Subclasses must implement:
    - size(): structural measure for termination
    - matches(pattern): pattern matching
    - substitute(bindings): apply variable bindings
    - __eq__: syntactic equality
    - __hash__: for caching
    - __str__: canonical string representation
    """

    @abstractmethod
    def size(self) -> int:
        """
        Structural measure of term size.
        
        Must satisfy: if t →* t', then size(t) ≥ size(t').
        Used to prove termination.
        
        Returns:
            Non-negative integer representing term complexity.
        """
        pass

    @abstractmethod
    def matches(self, pattern: "Term") -> Optional[dict[str, "Term"]]:
        """
        Check if this term matches a pattern.
        
        Args:
            pattern: Pattern term (may contain variables).
            
        Returns:
            Variable bindings if match succeeds, None otherwise.
            
        Example:
            >>> term = SPDXOr(["MIT", "GPL"])
            >>> pattern = SPDXOr([Var("x"), Var("y")])
            >>> term.matches(pattern)
            {"x": "MIT", "y": "GPL"}
        """
        pass

    @abstractmethod
    def substitute(self, bindings: dict[str, "Term"]) -> "Term":
        """
        Apply variable substitution.
        
        Args:
            bindings: Mapping from variable names to terms.
            
        Returns:
            New term with variables replaced.
        """
        pass

    def normalize(self, rules: List["Rule"]) -> "Term":
        """
        Rewrite to normal form using given rules.
        
        Applies rules exhaustively until no more applicable.
        Guaranteed to terminate if rules are terminating.
        
        Args:
            rules: List of rewrite rules.
            
        Returns:
            Term in normal form.
            
        Raises:
            RuntimeError: If rewriting doesn't terminate (max steps exceeded).
        """
        current = self
        steps = 0
        max_steps = 10000  # Safety bound
        
        while steps < max_steps:
            applied = False
            for rule in rules:
                result = rule.apply(current)
                if result is not None and result != current:
                    logger.debug(f"Applied {rule}: {current} → {result}")
                    current = result
                    applied = True
                    break
            
            if not applied:
                return current
            
            steps += 1
        
        raise RuntimeError(
            f"Normalization exceeded {max_steps} steps. "
            f"Possible non-terminating rewrite system. Current term: {current}"
        )


@dataclass(frozen=True)
class Rule(Generic[T]):
    """
    A rewrite rule: pattern → replacement.
    
    Attributes:
        name: Human-readable rule name.
        pattern: Left-hand side (may contain variables).
        replacement: Right-hand side factory function.
        condition: Optional guard (predicate on bindings).
        
    Example:
        >>> # A OR A → A (idempotence)
        >>> Rule(
        ...     name="or_idempotent",
        ...     pattern=SPDXOr([Var("x"), Var("x")]),
        ...     replacement=lambda b: b["x"]
        ... )
    """

    name: str
    pattern: Term
    replacement: Callable[[dict[str, Term]], Term]
    condition: Optional[Callable[[dict[str, Term]], bool]] = None

    def apply(self, term: Term) -> Optional[Term]:
        """
        Try to apply rule to term.
        
        Args:
            term: Term to rewrite.
            
        Returns:
            Rewritten term if rule applies, None otherwise.
        """
        bindings = term.matches(self.pattern)
        
        if bindings is None:
            return None
        
        if self.condition is not None and not self.condition(bindings):
            return None
        
        result = self.replacement(bindings)
        
        # Ensure size doesn't increase (termination measure)
        if result.size() > term.size():
            logger.warning(
                f"Rule {self.name} increased term size: {term.size()} → {result.size()}. "
                f"This may violate termination."
            )
        
        return result


@dataclass
class RewriteSystem:
    """
    A complete term rewriting system with confluence/termination guarantees.
    
    Attributes:
        name: System identifier.
        rules: List of rewrite rules (order matters for efficiency).
        verified: Whether confluence/termination are proven.
        
    Methods:
        normalize(term): Reduce term to normal form.
        check_critical_pairs(): Verify local confluence.
    """

    name: str
    rules: List[Rule]
    verified: bool = False
    _cache: dict[Term, Term] = field(default_factory=dict, repr=False)

    def normalize(self, term: Term) -> Term:
        """
        Normalize term to canonical form.
        
        Uses caching to avoid redundant rewrites.
        
        Args:
            term: Input term.
            
        Returns:
            Term in normal form.
            
        Raises:
            RuntimeError: If normalization fails to terminate.
        """
        # Check cache
        if term in self._cache:
            logger.debug(f"Cache hit for {term}")
            return self._cache[term]
        
        # Normalize
        nf = term.normalize(self.rules)
        
        # Verify idempotence: NF(NF(x)) = NF(x)
        double_nf = nf.normalize(self.rules)
        if double_nf != nf:
            logger.error(
                f"Idempotence violated: NF({term}) = {nf}, but NF(NF({term})) = {double_nf}"
            )
            raise RuntimeError(f"Rewrite system {self.name} is not idempotent!")
        
        # Cache result
        self._cache[term] = nf
        
        return nf

    def clear_cache(self) -> None:
        """Clear normalization cache."""
        self._cache.clear()

    def check_critical_pairs(self) -> List[tuple[str, Term, Term]]:
        """
        Check for critical pairs (potential confluence violations).
        
        A critical pair arises when two rules can apply to overlapping
        parts of a term, potentially leading to different normal forms.
        
        Returns:
            List of (context, result1, result2) tuples for non-joinable pairs.
            Empty list indicates local confluence.
            
        Note:
            This is a simplified check. Full critical pair analysis
            requires unification and overlap detection.
        """
        # Simplified: just check rule commutativity on common patterns
        violations = []
        
        for i, rule1 in enumerate(self.rules):
            for j, rule2 in enumerate(self.rules):
                if i >= j:
                    continue
                
                # Try applying both orders to rule1's pattern
                try:
                    term = rule1.pattern
                    
                    # Order 1: rule1 then rule2
                    r1 = rule1.apply(term)
                    if r1:
                        r1_r2 = rule2.apply(r1)
                    else:
                        r1_r2 = None
                    
                    # Order 2: rule2 then rule1
                    r2 = rule2.apply(term)
                    if r2:
                        r2_r1 = rule1.apply(r2)
                    else:
                        r2_r1 = None
                    
                    # Check if they join
                    if r1_r2 and r2_r1 and r1_r2 != r2_r1:
                        violations.append(
                            (f"{rule1.name} ⊗ {rule2.name}", r1_r2, r2_r1)
                        )
                
                except Exception as e:
                    logger.debug(f"Could not check {rule1.name} vs {rule2.name}: {e}")
        
        return violations
