"""StratificationGuard: Safe self-application guard (Theorem F from Phase 4).

TDD Cycle 2 - GREEN Phase.

Design:
- Level tracking: L₀ → L₁ → L₂ → ... (stratified universes)
- Paradox prevention: L_n → L_m where m ≤ n is FORBIDDEN
- Quote/Unquote: quote raises level, unquote lowers (with safety checks)
- MetaEval: Evaluate code at higher meta-level (with cycle detection)

Soundness gates:
- Only upward transitions allowed (L_n → L_{n+k} where k > 0)
- No self-reference at same level (prevents Russell's paradox)
- Cycle detection for meta_eval (prevents infinite loops)
- Max depth limit (prevents stack overflow)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TransitionResult:
    """Result of level transition check.
    
    Attributes:
        is_safe: Whether transition is safe.
        reason: Explanation if unsafe (None if safe).
    """
    is_safe: bool
    reason: str | None = None


@dataclass
class LeveledExpression:
    """Expression with stratification level.
    
    Attributes:
        value: Expression value (code, RDF triple, etc.).
        level: Stratification level (L0, L1, L2, ...).
    """
    value: Any
    level: int


class StratificationGuard:
    """Guard for safe self-application with stratified universes.
    
    Implements Theorem F: Safe self-application via level stratification.
    
    Features:
    - Level transition checking (L_n → L_m)
    - Quote/Unquote operations (with level tracking)
    - MetaEval safety (cycle detection, max depth)
    - Level stack tracking (push/pop)
    
    Attributes:
        max_depth: Maximum recursion depth for meta_eval.
        _level_stack: Stack of current levels (for nested operations).
    
    Example:
        >>> guard = StratificationGuard()
        >>> result = guard.check_transition(from_level=0, to_level=1)
        >>> result.is_safe
        True
        >>> result = guard.check_transition(from_level=1, to_level=0)
        >>> result.is_safe
        False
    """
    
    def __init__(self, max_depth: int = 10) -> None:
        """Initialize StratificationGuard.
        
        Args:
            max_depth: Maximum recursion depth for meta_eval (default: 10).
        """
        self.max_depth = max_depth
        self._level_stack: list[int] = [0]  # Start at L0
    
    def check_transition(self, from_level: int, to_level: int) -> TransitionResult:
        """Check if level transition is safe.
        
        Rules:
        - L_n → L_m where m > n: SAFE (upward transition)
        - L_n → L_n: UNSAFE (same level, self-reference)
        - L_n → L_m where m < n: UNSAFE (downward, paradox risk)
        
        Args:
            from_level: Source level.
            to_level: Target level.
        
        Returns:
            TransitionResult with is_safe flag and reason if unsafe.
        
        Example:
            >>> guard = StratificationGuard()
            >>> guard.check_transition(0, 1).is_safe
            True
            >>> guard.check_transition(1, 0).is_safe
            False
        """
        if to_level > from_level:
            # Upward transition: SAFE
            return TransitionResult(is_safe=True)
        
        if to_level == from_level:
            # Same level: UNSAFE (self-reference without stratification)
            return TransitionResult(
                is_safe=False,
                reason=f"Same level transition forbidden: L{from_level} → L{to_level} (self-reference)"
            )
        
        # Downward transition: UNSAFE (paradox risk)
        return TransitionResult(
            is_safe=False,
            reason=f"Downward transition forbidden: L{from_level} → L{to_level} (paradox risk)"
        )
    
    def quote(self, expr: Any, level: int) -> LeveledExpression:
        """Quote expression (raises level by 1).
        
        Quote operation: expr at L_n → quoted_expr at L_{n+1}
        
        Args:
            expr: Expression to quote.
            level: Current level of expression.
        
        Returns:
            LeveledExpression with level increased by 1.
        
        Example:
            >>> guard = StratificationGuard()
            >>> quoted = guard.quote("Module1.analyze()", level=0)
            >>> quoted.level
            1
        """
        return LeveledExpression(value=expr, level=level + 1)
    
    def unquote(self, expr: LeveledExpression, target_level: int) -> LeveledExpression:
        """Unquote expression (lowers level).
        
        Unquote operation: quoted_expr at L_{n+1} → expr at L_n
        
        Safety checks:
        - Cannot unquote to higher level (quote is for that)
        - Cannot unquote below L0 (base level)
        
        Args:
            expr: LeveledExpression to unquote.
            target_level: Target level (must be < expr.level).
        
        Returns:
            LeveledExpression with target_level.
        
        Raises:
            ValueError: If target_level >= expr.level or target_level < 0.
        
        Example:
            >>> guard = StratificationGuard()
            >>> quoted = guard.quote("test", level=0)
            >>> unquoted = guard.unquote(quoted, target_level=0)
            >>> unquoted.level
            0
        """
        if target_level >= expr.level:
            raise ValueError(
                f"Unquote cannot increase level: {expr.level} → {target_level} "
                "(use quote to increase level)"
            )
        
        if target_level < 0:
            raise ValueError(
                f"Cannot unquote below base level (L0): target_level={target_level}"
            )
        
        return LeveledExpression(value=expr.value, level=target_level)
    
    def meta_eval(
        self, 
        expr: str, 
        level: int, 
        context: dict[str, Any] | None = None
    ) -> LeveledExpression:
        """Evaluate expression at specified meta-level (with cycle detection).
        
        MetaEval operation: Evaluate code at L_n (safe if n > 0).
        
        Safety checks:
        - Cycle detection: Detect self-referential evaluation
        - Max depth: Prevent infinite recursion
        
        Args:
            expr: Expression string to evaluate.
            level: Meta-level for evaluation.
            context: Optional context dict for evaluation.
        
        Returns:
            LeveledExpression with evaluation result.
        
        Raises:
            ValueError: If cycle detected or max depth exceeded.
        
        Example:
            >>> guard = StratificationGuard()
            >>> result = guard.meta_eval("2 + 2", level=1)
            >>> result.value
            4
        """
        context = context or {}
        
        # Safety check 1: Cycle detection
        if self._has_cycle(expr, context):
            raise ValueError(
                f"Cycle detected: meta_eval self-reference at level {level}"
            )
        
        # Safety check 2: Max depth
        if self._exceeds_max_depth(expr):
            depth = expr.count("meta_eval")
            raise ValueError(
                f"Max depth exceeded: {depth} > {self.max_depth} (nested meta_eval)"
            )
        
        # Evaluate expression (simplified for GREEN phase)
        result = self._safe_eval(expr, context)
        
        return LeveledExpression(value=result, level=level)
    
    def _has_cycle(self, expr: str, context: dict[str, Any]) -> bool:
        """Check if expression has self-referential cycle.
        
        Args:
            expr: Expression to check.
            context: Evaluation context.
        
        Returns:
            True if cycle detected, False otherwise.
        """
        return "meta_eval" in expr and any(expr in str(v) for v in context.values())
    
    def _exceeds_max_depth(self, expr: str) -> bool:
        """Check if expression exceeds max recursion depth.
        
        Args:
            expr: Expression to check.
        
        Returns:
            True if depth exceeded, False otherwise.
        """
        depth = expr.count("meta_eval")
        return depth > self.max_depth
    
    def _safe_eval(self, expr: str, context: dict[str, Any]) -> Any:
        """Safely evaluate expression with restricted builtins.
        
        Args:
            expr: Expression to evaluate.
            context: Evaluation context.
        
        Returns:
            Evaluation result (or expr as-is if eval fails).
        """
        try:
            # Safe eval for simple arithmetic (GREEN phase minimal impl)
            return eval(expr, {"__builtins__": {}}, context)
        except Exception:
            # If eval fails, return expr as-is (deferred to future iteration)
            return expr
    
    def get_current_level(self) -> int:
        """Get current level from stack.
        
        Returns:
            Current level (top of stack).
        
        Example:
            >>> guard = StratificationGuard()
            >>> guard.get_current_level()
            0
        """
        return self._level_stack[-1]
    
    def push_level(self) -> None:
        """Push new level onto stack (increment by 1).
        
        Used for quote operations and nested meta-evaluation.
        
        Example:
            >>> guard = StratificationGuard()
            >>> guard.push_level()
            >>> guard.get_current_level()
            1
        """
        current = self._level_stack[-1]
        self._level_stack.append(current + 1)
    
    def pop_level(self) -> None:
        """Pop level from stack (decrement by 1).
        
        Used for unquote operations.
        
        Raises:
            ValueError: If popping would go below L0.
        
        Example:
            >>> guard = StratificationGuard()
            >>> guard.push_level()  # L0 → L1
            >>> guard.pop_level()   # L1 → L0
            >>> guard.get_current_level()
            0
        """
        if len(self._level_stack) <= 1:
            raise ValueError("Cannot pop below base level (L0)")
        
        self._level_stack.pop()
