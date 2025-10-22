"""
TDD Cycle 1 - RED Phase: OntologyManager Tests

STRATIFICATION_LEVEL: 2 (testing ontology manager)

This test module operates at level 2:
- Level 0: Base RDF triples (repository entities)
- Level 1: OntologyManager operations (add/query triples)
- Level 2: Testing OntologyManager (this module)

SAFETY NOTE: These tests MUST NOT trigger self-analysis of OntologyManager
to prevent universe collision. Tests operate on mock data only.

Following Test-Driven Development:
1. RED: Write failing tests (this file)
2. GREEN: Minimal implementation to pass tests
3. REFACTOR: Improve code quality

Test Coverage for OntologyManager (from Phase 4 architecture):
- Add triples (subject, predicate, object)
- Query triples (SPARQL)
- Support for RDFLib (default) and Oxigraph (optional)
- Pattern detection (MVC, Layered, etc.)
"""

import pytest
from rdflib import RDF, Literal, Namespace, URIRef


class TestOntologyManagerBasics:
    """Test basic triple operations (add, query)."""

    def test_add_single_triple(self):
        """RED: Test adding a single RDF triple."""
        from repoq.ontologies.manager import OntologyManager

        manager = OntologyManager()

        # Triple: <function:login> rdf:type code:Function
        CODE = Namespace("http://repoq.io/ontology/code#")
        subject = URIRef("http://repoq.io/function/login")
        predicate = RDF.type
        obj = CODE.Function

        manager.add_triple(subject, predicate, obj)

        # Query: Should return the triple
        results = manager.query("SELECT ?s ?p ?o WHERE { ?s ?p ?o }")
        assert len(results) == 1

    def test_add_multiple_triples(self):
        """RED: Test adding multiple triples."""
        from repoq.ontologies.manager import OntologyManager

        manager = OntologyManager()
        CODE = Namespace("http://repoq.io/ontology/code#")

        # Triple 1: <function:login> rdf:type code:Function
        manager.add_triple(URIRef("http://repoq.io/function/login"), RDF.type, CODE.Function)

        # Triple 2: <function:login> code:name "login"
        manager.add_triple(URIRef("http://repoq.io/function/login"), CODE.name, Literal("login"))

        # Triple 3: <function:login> code:complexity "8"
        manager.add_triple(URIRef("http://repoq.io/function/login"), CODE.complexity, Literal(8))

        results = manager.query("SELECT ?s ?p ?o WHERE { ?s ?p ?o }")
        assert len(results) == 3


class TestOntologyManagerSPARQL:
    """Test SPARQL query capabilities."""

    def test_sparql_filter(self):
        """RED: Test SPARQL with FILTER clause."""
        from repoq.ontologies.manager import OntologyManager

        manager = OntologyManager()
        CODE = Namespace("http://repoq.io/ontology/code#")

        # Add functions with different complexities
        for name, complexity in [("login", 12), ("logout", 3), ("register", 8)]:
            func_uri = URIRef(f"http://repoq.io/function/{name}")
            manager.add_triple(func_uri, RDF.type, CODE.Function)
            manager.add_triple(func_uri, CODE.name, Literal(name))
            manager.add_triple(func_uri, CODE.complexity, Literal(complexity))

        # Query: Functions with complexity > 10
        query = """
        PREFIX code: <http://repoq.io/ontology/code#>
        SELECT ?name ?complexity
        WHERE {
            ?func code:name ?name .
            ?func code:complexity ?complexity .
            FILTER (?complexity > 10)
        }
        """

        results = list(manager.query(query))
        assert len(results) == 1
        assert str(results[0]["name"]) == "login"
        assert int(results[0]["complexity"]) == 12

    def test_sparql_pattern_matching(self):
        """RED: Test SPARQL pattern matching (detect MVC pattern)."""
        from repoq.ontologies.manager import OntologyManager

        manager = OntologyManager()
        CODE = Namespace("http://repoq.io/ontology/code#")

        # Add MVC pattern: Controller calls Model
        controller = URIRef("http://repoq.io/class/AuthController")
        model = URIRef("http://repoq.io/class/UserModel")

        manager.add_triple(controller, RDF.type, CODE.Class)
        manager.add_triple(controller, CODE.name, Literal("AuthController"))
        manager.add_triple(controller, CODE.calls, model)

        manager.add_triple(model, RDF.type, CODE.Class)
        manager.add_triple(model, CODE.name, Literal("UserModel"))

        # Query: Detect MVC pattern (Controller calls Model)
        query = """
        PREFIX code: <http://repoq.io/ontology/code#>
        SELECT ?controller ?model
        WHERE {
            ?controller rdf:type code:Class .
            ?controller code:name ?controller_name .
            FILTER(CONTAINS(?controller_name, "Controller"))

            ?controller code:calls ?model .
            ?model rdf:type code:Class .
            ?model code:name ?model_name .
            FILTER(CONTAINS(?model_name, "Model"))
        }
        """

        results = list(manager.query(query))
        assert len(results) == 1
        assert "Controller" in str(results[0]["controller"])
        assert "Model" in str(results[0]["model"])


class TestOntologyManagerBackend:
    """Test backend abstraction (RDFLib vs Oxigraph)."""

    def test_default_backend_is_rdflib(self):
        """RED: Test that default backend is RDFLib."""
        from repoq.ontologies.manager import OntologyManager

        manager = OntologyManager()
        assert manager.backend_name == "rdflib"

    def test_explicit_rdflib_backend(self):
        """RED: Test explicit RDFLib backend selection."""
        from repoq.ontologies.manager import OntologyManager

        manager = OntologyManager(backend="rdflib")
        assert manager.backend_name == "rdflib"

    @pytest.mark.skip(reason="Oxigraph optional, test when implemented")
    def test_oxigraph_backend(self):
        """RED: Test Oxigraph backend (optional optimization)."""
        from repoq.ontologies.manager import OntologyManager

        try:
            manager = OntologyManager(backend="oxigraph")
            assert manager.backend_name == "oxigraph"
        except ImportError:
            pytest.skip("Oxigraph not installed")


class TestOntologyManagerPatternDetection:
    """Test pattern detection (high-level API)."""

    def test_detect_mvc_pattern(self):
        """RED: Test MVC pattern detection (high-level API)."""
        from repoq.ontologies.manager import OntologyManager

        manager = OntologyManager()
        CODE = Namespace("http://repoq.io/ontology/code#")

        # Add MVC components
        controller = URIRef("http://repoq.io/class/AuthController")
        model = URIRef("http://repoq.io/class/UserModel")
        view = URIRef("http://repoq.io/template/login.html")

        manager.add_triple(controller, RDF.type, CODE.Class)
        manager.add_triple(controller, CODE.name, Literal("AuthController"))
        manager.add_triple(controller, CODE.calls, model)
        manager.add_triple(controller, CODE.renders, view)

        manager.add_triple(model, RDF.type, CODE.Class)
        manager.add_triple(model, CODE.name, Literal("UserModel"))

        manager.add_triple(view, RDF.type, CODE.Template)

        # High-level API: detect_pattern("mvc")
        patterns = manager.detect_pattern("mvc")
        assert len(patterns) >= 1
        assert patterns[0]["controller"] == controller
        assert patterns[0]["model"] == model
        assert patterns[0]["view"] == view

    def test_detect_layered_architecture(self):
        """RED: Test Layered Architecture pattern detection."""
        from repoq.ontologies.manager import OntologyManager

        manager = OntologyManager()
        CODE = Namespace("http://repoq.io/ontology/code#")

        # Add layers: Presentation -> Business -> Data
        presentation = URIRef("http://repoq.io/module/api")
        business = URIRef("http://repoq.io/module/services")
        data = URIRef("http://repoq.io/module/repositories")

        manager.add_triple(presentation, RDF.type, CODE.Module)
        manager.add_triple(presentation, CODE.layer, Literal("presentation"))
        manager.add_triple(presentation, CODE.depends_on, business)

        manager.add_triple(business, RDF.type, CODE.Module)
        manager.add_triple(business, CODE.layer, Literal("business"))
        manager.add_triple(business, CODE.depends_on, data)

        manager.add_triple(data, RDF.type, CODE.Module)
        manager.add_triple(data, CODE.layer, Literal("data"))

        patterns = manager.detect_pattern("layered")
        assert len(patterns) >= 1
        assert patterns[0]["presentation"] == presentation
        assert patterns[0]["business"] == business
        assert patterns[0]["data"] == data


class TestOntologyManagerPersistence:
    """Test persistence (save/load from disk)."""

    def test_save_to_file(self, tmp_path):
        """RED: Test saving ontology to Turtle file."""
        from repoq.ontologies.manager import OntologyManager

        manager = OntologyManager()
        CODE = Namespace("http://repoq.io/ontology/code#")

        manager.add_triple(URIRef("http://repoq.io/function/test"), RDF.type, CODE.Function)

        # Save to file
        file_path = tmp_path / "ontology.ttl"
        manager.save(str(file_path), format="turtle")

        assert file_path.exists()
        content = file_path.read_text()
        assert "Function" in content

    def test_load_from_file(self, tmp_path):
        """RED: Test loading ontology from Turtle file."""
        from repoq.ontologies.manager import OntologyManager

        # Create and save
        manager1 = OntologyManager()
        CODE = Namespace("http://repoq.io/ontology/code#")

        manager1.add_triple(URIRef("http://repoq.io/function/test"), RDF.type, CODE.Function)

        file_path = tmp_path / "ontology.ttl"
        manager1.save(str(file_path), format="turtle")

        # Load into new manager
        manager2 = OntologyManager()
        manager2.load(str(file_path), format="turtle")

        results = manager2.query("SELECT ?s ?p ?o WHERE { ?s ?p ?o }")
        assert len(results) >= 1


class TestOntologyManagerIntegration:
    """Integration tests with existing RepoQ components."""

    @pytest.mark.skip(reason="Integration with pipeline, test after implementation")
    def test_integration_with_analysis_pipeline(self):
        """RED: Test ontology ingestion from analysis pipeline."""
        from repoq.ontologies.manager import OntologyManager
        from repoq.pipeline import AnalysisPipeline

        # This will be tested after implementation
        manager = OntologyManager()
        pipeline = AnalysisPipeline()

        # Analyze code -> Ingest into ontology
        state = pipeline.analyze("test_repo/")
        manager.ingest_analysis_state(state)

        # Query: Should have functions from test_repo
        results = manager.query("""
            PREFIX code: <http://repoq.io/ontology/code#>
            SELECT ?func WHERE { ?func rdf:type code:Function }
        """)
        assert len(results) > 0
