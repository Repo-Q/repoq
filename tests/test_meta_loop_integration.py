"""
TDD Cycle 3 - RED Phase: MetaLoop Integration Tests

Integration tests for:
- OntologyManager + StratificationGuard
- tmp/meta-loop artifacts (meta_context.jsonld, meta_loop.ttl)
- RDF level metadata tracking
- SHACL validation with stratification rules
"""

import pytest
from pathlib import Path
from rdflib import URIRef, Literal, Namespace


class TestOntologyManagerWithGuard:
    """Test OntologyManager integration with StratificationGuard."""
    
    def test_add_triple_with_level_metadata(self):
        """RED: Add RDF triple with meta:level metadata."""
        from repoq.ontologies.manager import OntologyManager
        from repoq.core.stratification_guard import StratificationGuard
        
        manager = OntologyManager()
        guard = StratificationGuard()
        
        # Add triple with level metadata
        subject = URIRef("http://example.org/Module1")
        predicate = URIRef("http://example.org/vocab/meta#level")
        obj = Literal(1)
        
        # Check transition is safe
        result = guard.check_transition(from_level=0, to_level=1)
        assert result.is_safe is True
        
        # Add triple
        manager.add_triple(subject, predicate, obj)
        
        # Query level metadata
        query = """
        PREFIX mq: <http://example.org/vocab/meta#>
        SELECT ?subject ?level
        WHERE {
            ?subject mq:level ?level .
        }
        """
        results = manager.query(query)
        assert len(results) == 1
        assert results[0]['level'] == Literal(1)
    
    def test_stratified_pattern_detection(self):
        """RED: Pattern detection respects stratification levels."""
        from repoq.ontologies.manager import OntologyManager
        from repoq.core.stratification_guard import StratificationGuard
        
        manager = OntologyManager()
        guard = StratificationGuard()
        
        # Add MVC pattern at L1
        controller = URIRef("http://example.org/UserController")
        model = URIRef("http://example.org/UserModel")
        view = URIRef("http://example.org/user_view.html")
        
        CODE = Namespace("http://repoq.io/ontology/code#")
        MQ = Namespace("http://example.org/vocab/meta#")
        
        # Add triples with level metadata
        manager.add_triple(controller, CODE.name, Literal("UserController"))
        manager.add_triple(controller, MQ.level, Literal(1))
        manager.add_triple(model, CODE.name, Literal("UserModel"))
        manager.add_triple(model, MQ.level, Literal(1))
        
        # Detect MVC pattern
        patterns = manager.detect_pattern("mvc")
        
        # Verify stratification: all components at same level
        query = """
        PREFIX mq: <http://example.org/vocab/meta#>
        SELECT ?component ?level
        WHERE {
            ?component mq:level ?level .
        }
        """
        results = manager.query(query)
        levels = [r['level'] for r in results]
        assert all(level == Literal(1) for level in levels)
    
    def test_guard_prevents_unsafe_ontology_transitions(self):
        """RED: Guard prevents downward transitions in ontology."""
        from repoq.ontologies.manager import OntologyManager
        from repoq.core.stratification_guard import StratificationGuard
        
        manager = OntologyManager()
        guard = StratificationGuard()
        
        # Simulate: Component at L2 trying to reference L1 (downward)
        component_l2 = URIRef("http://example.org/MetaAnalyzer")
        component_l1 = URIRef("http://example.org/Analyzer")
        
        MQ = Namespace("http://example.org/vocab/meta#")
        
        manager.add_triple(component_l2, MQ.level, Literal(2))
        manager.add_triple(component_l1, MQ.level, Literal(1))
        
        # Check transition L2 → L1 (should be unsafe)
        result = guard.check_transition(from_level=2, to_level=1)
        assert result.is_safe is False
        assert "downward" in result.reason.lower()


class TestMetaContextIntegration:
    """Test integration with tmp/meta-loop meta_context.jsonld."""
    
    def test_load_meta_context(self):
        """RED: Load meta_context.jsonld into OntologyManager."""
        from repoq.ontologies.manager import OntologyManager
        
        manager = OntologyManager()
        
        # Load meta_context.jsonld (from tmp/repoq-meta-loop-addons)
        context_path = Path("tmp/repoq-meta-loop-addons/ontologies/meta_context.jsonld")
        
        if not context_path.exists():
            pytest.skip(f"Meta context not found: {context_path}")
        
        # Parse JSON-LD context (simplified for RED phase)
        import json
        context = json.loads(context_path.read_text())
        
        # Verify required namespaces
        ctx = context['@context']
        assert 'mq' in ctx  # meta-quality namespace
        assert 'code' in ctx  # code namespace
        assert 'c4' in ctx  # C4 namespace
        assert 'level' in ctx  # stratification level
    
    def test_self_analysis_level_constraint(self):
        """RED: Self-analysis must use levels 0..2 only (from SHACL policy)."""
        from repoq.core.stratification_guard import StratificationGuard
        
        guard = StratificationGuard()
        
        # L0 → L2: SAFE (self-analysis range)
        result = guard.check_transition(from_level=0, to_level=2)
        assert result.is_safe is True
        
        # L0 → L3: Should be allowed by guard (upward transition)
        # But SHACL policy would reject it (level > 2 forbidden for self-analysis)
        result = guard.check_transition(from_level=0, to_level=3)
        assert result.is_safe is True  # Guard allows, SHACL rejects
        
        # Note: SHACL validation tested separately


class TestSHACLValidationWithStratification:
    """Test SHACL validation with stratification rules."""
    
    def test_validate_self_analysis_request(self):
        """RED: Validate SelfAnalysisRequest with SHACL (level <= 2)."""
        from repoq.ontologies.manager import OntologyManager
        
        manager = OntologyManager()
        
        # Add SelfAnalysisRequest with level=2 (VALID)
        request = URIRef("http://example.org/request1")
        MQ = Namespace("http://example.org/vocab/meta#")
        
        manager.add_triple(request, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), MQ.SelfAnalysisRequest)
        manager.add_triple(request, MQ.analyzeTarget, MQ.Self)
        manager.add_triple(request, MQ.level, Literal(2))
        
        # Load SHACL shape from tmp/
        shapes_path = Path("tmp/repoq-meta-loop-addons/shapes/meta_loop.ttl")
        
        if not shapes_path.exists():
            pytest.skip(f"SHACL shapes not found: {shapes_path}")
        
        # Parse shapes (placeholder for GREEN phase)
        # In GREEN phase: use pyshacl to validate
        assert manager.count() == 3
    
    def test_validate_self_analysis_invalid_level(self):
        """RED: SelfAnalysisRequest with level > 2 should FAIL SHACL."""
        from repoq.ontologies.manager import OntologyManager
        
        manager = OntologyManager()
        
        # Add SelfAnalysisRequest with level=3 (INVALID per SHACL)
        request = URIRef("http://example.org/request2")
        MQ = Namespace("http://example.org/vocab/meta#")
        
        manager.add_triple(request, URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), MQ.SelfAnalysisRequest)
        manager.add_triple(request, MQ.analyzeTarget, MQ.Self)
        manager.add_triple(request, MQ.level, Literal(3))  # INVALID
        
        # SHACL validation would fail (placeholder for GREEN phase)
        assert manager.count() == 3


class TestQuoteUnquoteWithRDF:
    """Test quote/unquote operations with RDF triples."""
    
    def test_quote_rdf_triple(self):
        """RED: Quote RDF triple (raises level)."""
        from repoq.core.stratification_guard import StratificationGuard
        from rdflib import Graph
        
        guard = StratificationGuard()
        
        # Original triple at L0
        triple = (
            URIRef("http://example.org/Module1"),
            URIRef("http://repoq.io/ontology/code#complexity"),
            Literal(15)
        )
        
        # Quote triple (L0 → L1)
        quoted = guard.quote(triple, level=0)
        
        assert quoted.level == 1
        assert quoted.value == triple
    
    def test_unquote_rdf_triple(self):
        """RED: Unquote RDF triple (lowers level safely)."""
        from repoq.core.stratification_guard import StratificationGuard
        
        guard = StratificationGuard()
        
        # Quoted triple at L1
        triple = (
            URIRef("http://example.org/Module1"),
            URIRef("http://repoq.io/ontology/code#complexity"),
            Literal(15)
        )
        quoted = guard.quote(triple, level=0)
        
        # Unquote (L1 → L0)
        unquoted = guard.unquote(quoted, target_level=0)
        
        assert unquoted.level == 0
        assert unquoted.value == triple


class TestMetaLoopCLIIntegration:
    """Test CLI integration with meta-loop commands."""
    
    @pytest.mark.skip(reason="CLI integration in Phase 5.4")
    def test_meta_self_command(self):
        """RED: Test `repoq meta-self` command integration."""
        # Placeholder for Phase 5.4 (CLI integration)
        pass
    
    @pytest.mark.skip(reason="TRS engine integration in Phase 5.4")
    def test_trs_verify_command(self):
        """RED: Test `repoq trs-verify` command integration."""
        # Placeholder for Phase 5.4 (TRS engine)
        pass


class TestOntologyManagerHelperMethods:
    """Test helper methods added to OntologyManager for integration."""
    
    def test_add_triple_with_guard(self):
        """RED: Add triple with guard validation."""
        from repoq.ontologies.manager import OntologyManager
        from repoq.core.stratification_guard import StratificationGuard
        
        manager = OntologyManager()
        guard = StratificationGuard()
        
        # Helper method: add_triple_with_guard(subject, predicate, object, from_level, to_level)
        # Should check transition before adding
        subject = URIRef("http://example.org/Module1")
        predicate = URIRef("http://example.org/vocab/meta#level")
        obj = Literal(1)
        
        # This should succeed (L0 → L1)
        manager.add_triple_with_guard(guard, subject, predicate, obj, from_level=0, to_level=1)
        
        assert manager.count() == 1
    
    def test_add_triple_with_guard_rejects_unsafe(self):
        """RED: add_triple_with_guard rejects unsafe transitions."""
        from repoq.ontologies.manager import OntologyManager
        from repoq.core.stratification_guard import StratificationGuard
        
        manager = OntologyManager()
        guard = StratificationGuard()
        
        subject = URIRef("http://example.org/Module1")
        predicate = URIRef("http://example.org/vocab/meta#level")
        obj = Literal(0)
        
        # This should fail (L1 → L0 downward)
        with pytest.raises(ValueError, match="(?i)unsafe transition"):
            manager.add_triple_with_guard(guard, subject, predicate, obj, from_level=1, to_level=0)
    
    def test_count_method(self):
        """RED: OntologyManager.count() returns triple count."""
        from repoq.ontologies.manager import OntologyManager
        
        manager = OntologyManager()
        assert manager.count() == 0
        
        manager.add_triple(
            URIRef("http://example.org/Module1"),
            URIRef("http://repoq.io/ontology/code#complexity"),
            Literal(15)
        )
        assert manager.count() == 1
