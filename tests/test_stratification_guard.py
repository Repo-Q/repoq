"""
TDD Cycle 2 - RED Phase: StratificationGuard Tests

Tests for safe self-application guard (Theorem F from Phase 4).

Test strategy:
- Level transitions (L0 → L1, L1 → L2, etc.)
- Paradox prevention (L1 → L0 forbidden)
- Quote/Unquote safety (with level tracking)
- MetaEval safety (no cycles)
- Integration with OntologyManager (deferred to Phase 5.3)
"""

import pytest
from rdflib import URIRef, Literal


class TestStratificationGuardBasics:
    """Test basic level transitions and paradox detection."""
    
    def test_level_0_to_level_1_allowed(self):
        """RED: L0 → L1 transition is allowed (quote operation)."""
        from repoq.core.stratification_guard import StratificationGuard
        
        guard = StratificationGuard()
        result = guard.check_transition(from_level=0, to_level=1)
        
        assert result.is_safe is True
        assert result.reason is None
    
    def test_level_1_to_level_2_allowed(self):
        """RED: L1 → L2 transition is allowed (meta-meta operation)."""
        from repoq.core.stratification_guard import StratificationGuard
        
        guard = StratificationGuard()
        result = guard.check_transition(from_level=1, to_level=2)
        
        assert result.is_safe is True
        assert result.reason is None
    
    def test_level_1_to_level_0_forbidden(self):
        """RED: L1 → L0 transition is FORBIDDEN (paradox risk)."""
        from repoq.core.stratification_guard import StratificationGuard
        
        guard = StratificationGuard()
        result = guard.check_transition(from_level=1, to_level=0)
        
        assert result.is_safe is False
        assert "paradox" in result.reason.lower()
    
    def test_same_level_transition_forbidden(self):
        """RED: L1 → L1 transition is FORBIDDEN (self-reference without stratification)."""
        from repoq.core.stratification_guard import StratificationGuard
        
        guard = StratificationGuard()
        result = guard.check_transition(from_level=1, to_level=1)
        
        assert result.is_safe is False
        assert "same level" in result.reason.lower()
    
    def test_skip_level_allowed(self):
        """RED: L0 → L2 transition is allowed (skip L1)."""
        from repoq.core.stratification_guard import StratificationGuard
        
        guard = StratificationGuard()
        result = guard.check_transition(from_level=0, to_level=2)
        
        assert result.is_safe is True
        assert result.reason is None


class TestStratificationGuardQuoteUnquote:
    """Test quote/unquote operations with level tracking."""
    
    def test_quote_increases_level(self):
        """RED: quote(expr, level=0) returns level=1."""
        from repoq.core.stratification_guard import StratificationGuard
        
        guard = StratificationGuard()
        expr = "Module1.analyze()"
        quoted = guard.quote(expr, level=0)
        
        assert quoted.level == 1
        assert quoted.value == expr
    
    def test_unquote_decreases_level_safely(self):
        """RED: unquote(quoted_expr, level=1) returns level=0 if safe."""
        from repoq.core.stratification_guard import StratificationGuard
        
        guard = StratificationGuard()
        quoted = guard.quote("Module1.analyze()", level=0)
        unquoted = guard.unquote(quoted, target_level=0)
        
        assert unquoted.level == 0
        assert unquoted.value == "Module1.analyze()"
    
    def test_unquote_to_higher_level_forbidden(self):
        """RED: unquote cannot increase level (L1 → L2 via unquote is forbidden)."""
        from repoq.core.stratification_guard import StratificationGuard
        
        guard = StratificationGuard()
        quoted = guard.quote("Module1.analyze()", level=0)
        
        with pytest.raises(ValueError, match="cannot increase level"):
            guard.unquote(quoted, target_level=2)
    
    def test_unquote_below_zero_forbidden(self):
        """RED: unquote cannot go below L0 (base level)."""
        from repoq.core.stratification_guard import StratificationGuard
        
        guard = StratificationGuard()
        expr = guard.quote("test", level=0)
        
        with pytest.raises(ValueError, match="below base level"):
            guard.unquote(expr, target_level=-1)


class TestStratificationGuardMetaEval:
    """Test MetaEval safety (no cycles)."""
    
    def test_meta_eval_at_higher_level(self):
        """RED: meta_eval(expr, level=1) evaluates at L1 (safe)."""
        from repoq.core.stratification_guard import StratificationGuard
        
        guard = StratificationGuard()
        expr = "2 + 2"
        result = guard.meta_eval(expr, level=1)
        
        assert result.value == 4
        assert result.level == 1
    
    def test_meta_eval_detects_cycle(self):
        """RED: meta_eval detects self-referential cycle."""
        from repoq.core.stratification_guard import StratificationGuard
        
        guard = StratificationGuard()
        # Simulate: "meta_eval(meta_eval(x))" at same level
        expr = "meta_eval('x', level=1)"
        
        with pytest.raises(ValueError, match="(?i)cycle detected"):  # Case-insensitive
            guard.meta_eval(expr, level=1, context={"x": expr})
    
    def test_meta_eval_max_depth_limit(self):
        """RED: meta_eval enforces max recursion depth."""
        from repoq.core.stratification_guard import StratificationGuard
        
        guard = StratificationGuard(max_depth=3)
        
        # Create nested meta_eval chain: meta_eval(meta_eval(meta_eval(meta_eval(...))))
        expr = "1"
        for _ in range(5):  # 5 levels (exceeds max_depth=3)
            expr = f"meta_eval('{expr}', level={_})"
        
        with pytest.raises(ValueError, match="(?i)max depth exceeded"):  # Case-insensitive
            guard.meta_eval(expr, level=0)


class TestStratificationGuardLevelTracking:
    """Test level tracking API."""
    
    def test_get_current_level(self):
        """RED: Guard tracks current level."""
        from repoq.core.stratification_guard import StratificationGuard
        
        guard = StratificationGuard()
        assert guard.get_current_level() == 0  # Start at L0
    
    def test_push_level(self):
        """RED: push_level increments level (for quote)."""
        from repoq.core.stratification_guard import StratificationGuard
        
        guard = StratificationGuard()
        guard.push_level()
        assert guard.get_current_level() == 1
        guard.push_level()
        assert guard.get_current_level() == 2
    
    def test_pop_level(self):
        """RED: pop_level decrements level (for unquote)."""
        from repoq.core.stratification_guard import StratificationGuard
        
        guard = StratificationGuard()
        guard.push_level()  # L0 → L1
        guard.pop_level()   # L1 → L0
        assert guard.get_current_level() == 0
    
    def test_pop_level_below_zero_forbidden(self):
        """RED: Cannot pop below L0."""
        from repoq.core.stratification_guard import StratificationGuard
        
        guard = StratificationGuard()
        with pytest.raises(ValueError, match="below base level"):
            guard.pop_level()


class TestStratificationGuardIntegration:
    """Test integration scenarios (deferred to Phase 5.3)."""
    
    @pytest.mark.skip(reason="Integration with OntologyManager in Phase 5.3")
    def test_integration_with_ontology_manager(self):
        """RED: StratificationGuard integrates with OntologyManager for RDF level tracking."""
        from repoq.core.stratification_guard import StratificationGuard
        from repoq.ontologies.manager import OntologyManager
        
        guard = StratificationGuard()
        manager = OntologyManager()
        
        # Add triple with level metadata
        subject = URIRef("http://example.org/Module1")
        predicate = URIRef("http://repoq.io/ontology/meta#level")
        manager.add_triple(subject, predicate, Literal(1))
        
        # Check level transition
        result = guard.check_transition_for_uri(manager, subject, target_level=2)
        assert result.is_safe is True
