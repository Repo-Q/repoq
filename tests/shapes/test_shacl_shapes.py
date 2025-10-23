"""Tests for SHACL quality constraint shapes.

This module validates that SHACL shapes correctly detect quality violations
while respecting fairness principles (V06) and providing actionable feedback (FR-02).

References:
- FR-01: Detailed Gate Output
- FR-02: Actionable Feedback
- V06: Fairness (complexity doesn't penalize legitimate patterns)
- ADR-002: RDFLib + pySHACL
"""

from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

# Namespaces
REPO = Namespace("https://repoq.dev/ontology/repo#")
CODE = Namespace("http://field33.com/ontologies/CODE/")
C4 = Namespace("http://field33.com/ontologies/C4/")
DDD = Namespace("http://field33.com/ontologies/DDD/")


@pytest.fixture
def shapes_graph():
    """Load quality constraint shapes."""
    g = Graph()
    shapes_dir = Path(__file__).parent.parent.parent / "repoq" / "shapes"
    g.parse(shapes_dir / "quality_constraints.ttl", format="turtle")
    return g


@pytest.fixture
def ddd_shapes_graph():
    """Load DDD constraint shapes."""
    g = Graph()
    shapes_dir = Path(__file__).parent.parent.parent / "repoq" / "shapes"
    g.parse(shapes_dir / "ddd_constraints.ttl", format="turtle")
    return g


class TestComplexityShape:
    """Test complexity constraint shape (CC ≤ 15)."""

    def test_complexity_shape_detects_violation(self, shapes_graph):
        """Test that CC > 15 triggers violation."""
        # Arrange: Create data graph with high complexity file
        data_graph = Graph()
        file_uri = URIRef("https://example.com/repo/file/bad.py")
        data_graph.add((file_uri, RDF.type, REPO.File))
        data_graph.add((file_uri, REPO.cyclomaticComplexity, Literal(20, datatype=XSD.integer)))

        # Act: Validate
        conforms, results_graph, results_text = validate(
            data_graph=data_graph, shacl_graph=shapes_graph, inference="rdfs", abort_on_first=False
        )

        # Assert
        assert not conforms, "Should detect complexity violation"
        assert "exceeds threshold" in results_text.lower()
        assert "20" in results_text  # Should mention actual value

    def test_complexity_shape_allows_state_machine(self, shapes_graph):
        """Test that state machines with CC ≤ 30 are allowed (V06 Fairness)."""
        # Arrange: Create state machine with CC = 25
        data_graph = Graph()
        file_uri = URIRef("https://example.com/repo/file/state_machine.py")
        data_graph.add((file_uri, RDF.type, REPO.File))
        data_graph.add((file_uri, REPO.cyclomaticComplexity, Literal(25, datatype=XSD.integer)))
        data_graph.add((file_uri, REPO.isStateMachine, Literal(True, datatype=XSD.boolean)))

        # Act: Validate
        conforms, results_graph, results_text = validate(
            data_graph=data_graph, shacl_graph=shapes_graph, inference="rdfs", abort_on_first=False
        )

        # Assert
        assert conforms, "State machine with CC=25 should be allowed (fairness)"

    def test_complexity_shape_rejects_excessive_state_machine(self, shapes_graph):
        """Test that even state machines fail if CC > 30."""
        # Arrange: Create state machine with CC = 35
        data_graph = Graph()
        file_uri = URIRef("https://example.com/repo/file/huge_state_machine.py")
        data_graph.add((file_uri, RDF.type, REPO.File))
        data_graph.add((file_uri, REPO.cyclomaticComplexity, Literal(35, datatype=XSD.integer)))
        data_graph.add((file_uri, REPO.isStateMachine, Literal(True, datatype=XSD.boolean)))

        # Act: Validate
        conforms, results_graph, results_text = validate(
            data_graph=data_graph, shacl_graph=shapes_graph, inference="rdfs", abort_on_first=False
        )

        # Assert
        assert not conforms, "Even state machines should fail if CC > 30"


class TestHotspotShape:
    """Test hotspot constraint shape (churn > 20 AND CC > 10)."""

    def test_hotspot_shape_triggers_on_high_churn_and_complexity(self, shapes_graph):
        """Test that files with high churn AND high complexity are flagged."""
        # Arrange: Create hotspot file
        data_graph = Graph()
        file_uri = URIRef("https://example.com/repo/file/hotspot.py")
        data_graph.add((file_uri, RDF.type, REPO.File))
        data_graph.add((file_uri, REPO.commitCount, Literal(25, datatype=XSD.integer)))
        data_graph.add((file_uri, REPO.cyclomaticComplexity, Literal(12, datatype=XSD.integer)))

        # Act: Validate
        conforms, results_graph, results_text = validate(
            data_graph=data_graph, shacl_graph=shapes_graph, inference="rdfs", abort_on_first=False
        )

        # Assert
        assert not conforms, "Hotspot should be detected"
        assert "hotspot" in results_text.lower()

    def test_hotspot_shape_allows_high_churn_low_complexity(self, shapes_graph):
        """Test that high churn with low complexity is acceptable."""
        # Arrange: Create file with high churn but low complexity
        data_graph = Graph()
        file_uri = URIRef("https://example.com/repo/file/config.py")
        data_graph.add((file_uri, RDF.type, REPO.File))
        data_graph.add((file_uri, REPO.commitCount, Literal(30, datatype=XSD.integer)))
        data_graph.add((file_uri, REPO.cyclomaticComplexity, Literal(5, datatype=XSD.integer)))

        # Act: Validate
        conforms, results_graph, results_text = validate(
            data_graph=data_graph, shacl_graph=shapes_graph, inference="rdfs", abort_on_first=False
        )

        # Assert
        assert conforms, "High churn with low complexity is not a hotspot"


class TestTodoLimitShape:
    """Test TODO comment limit shape (≤100)."""

    def test_todo_constraint_hard_limit(self, shapes_graph):
        """Test that TODO count > 100 triggers violation."""
        # Arrange: Create repository with excessive TODOs
        data_graph = Graph()
        repo_uri = URIRef("https://example.com/repo")
        data_graph.add((repo_uri, RDF.type, REPO.Repository))
        data_graph.add((repo_uri, REPO.todoCount, Literal(150, datatype=XSD.integer)))

        # Act: Validate
        conforms, results_graph, results_text = validate(
            data_graph=data_graph, shacl_graph=shapes_graph, inference="rdfs", abort_on_first=False
        )

        # Assert
        assert not conforms, "Should detect excessive TODOs"
        assert "150" in results_text
        assert "100" in results_text  # Mention limit

    def test_todo_constraint_within_limit(self, shapes_graph):
        """Test that TODO count ≤ 100 is acceptable."""
        # Arrange: Create repository with acceptable TODOs
        data_graph = Graph()
        repo_uri = URIRef("https://example.com/repo")
        data_graph.add((repo_uri, RDF.type, REPO.Repository))
        data_graph.add((repo_uri, REPO.todoCount, Literal(80, datatype=XSD.integer)))

        # Act: Validate
        conforms, results_graph, results_text = validate(
            data_graph=data_graph, shacl_graph=shapes_graph, inference="rdfs", abort_on_first=False
        )

        # Assert
        assert conforms, "TODO count ≤ 100 should be acceptable"


class TestCoverageShape:
    """Test test coverage constraint shape (≥80%)."""

    def test_coverage_constraint_below_threshold(self, shapes_graph):
        """Test that coverage < 80% triggers violation."""
        # Arrange: Create module with low coverage
        data_graph = Graph()
        module_uri = URIRef("https://example.com/repo/module/auth.py")
        data_graph.add((module_uri, RDF.type, REPO.Module))
        data_graph.add((module_uri, REPO.testCoverage, Literal(0.65, datatype=XSD.decimal)))

        # Act: Validate
        conforms, results_graph, results_text = validate(
            data_graph=data_graph, shacl_graph=shapes_graph, inference="rdfs", abort_on_first=False
        )

        # Assert
        assert not conforms, "Should detect low coverage"
        assert "80" in results_text or "0.80" in results_text

    def test_coverage_constraint_allows_legacy_modules(self, shapes_graph):
        """Test that legacy modules can have lower coverage (exception)."""
        # Arrange: Create legacy module with low coverage
        data_graph = Graph()
        module_uri = URIRef("https://example.com/repo/module/legacy_auth.py")
        data_graph.add((module_uri, RDF.type, REPO.Module))
        data_graph.add((module_uri, REPO.testCoverage, Literal(0.50, datatype=XSD.decimal)))
        data_graph.add((module_uri, REPO.isLegacyModule, Literal(True, datatype=XSD.boolean)))

        # Act: Validate
        conforms, results_graph, results_text = validate(
            data_graph=data_graph, shacl_graph=shapes_graph, inference="rdfs", abort_on_first=False
        )

        # Assert
        assert conforms, "Legacy modules should be exempt from coverage requirement"


class TestLayeringShape:
    """Test C4 layer violation shape (no upward dependencies)."""

    def test_c4_layering_violation_detected(self, shapes_graph):
        """Test that Data → Presentation dependency is flagged."""
        # Arrange: Create layer violation
        data_graph = Graph()

        # Data layer module
        data_module = URIRef("https://example.com/repo/module/database.py")
        data_graph.add((data_module, RDF.type, REPO.Module))
        data_graph.add((data_module, C4.layer, C4.DataLayer))

        # Presentation layer module
        ui_module = URIRef("https://example.com/repo/module/ui.py")
        data_graph.add((ui_module, RDF.type, REPO.Module))
        data_graph.add((ui_module, C4.layer, C4.PresentationLayer))

        # Violation: Data depends on Presentation
        data_graph.add((data_module, REPO.dependsOn, ui_module))

        # Act: Validate
        conforms, results_graph, results_text = validate(
            data_graph=data_graph, shacl_graph=shapes_graph, inference="rdfs", abort_on_first=False
        )

        # Assert
        assert not conforms, "Should detect layer violation"
        assert "layer violation" in results_text.lower() or "violation" in results_text.lower()

    def test_c4_valid_dependency_allowed(self, shapes_graph):
        """Test that Presentation → Business → Data is valid."""
        # Arrange: Create valid layered architecture
        data_graph = Graph()

        # Data layer
        data_module = URIRef("https://example.com/repo/module/database.py")
        data_graph.add((data_module, RDF.type, REPO.Module))
        data_graph.add((data_module, C4.layer, C4.DataLayer))

        # Business layer
        business_module = URIRef("https://example.com/repo/module/service.py")
        data_graph.add((business_module, RDF.type, REPO.Module))
        data_graph.add((business_module, C4.layer, C4.BusinessLayer))

        # Valid: Business depends on Data (downward)
        data_graph.add((business_module, REPO.dependsOn, data_module))

        # Act: Validate
        conforms, results_graph, results_text = validate(
            data_graph=data_graph, shacl_graph=shapes_graph, inference="rdfs", abort_on_first=False
        )

        # Assert
        assert conforms, "Downward dependencies should be allowed"


class TestBoundedContextShape:
    """Test DDD bounded context constraint shapes."""

    def test_ddd_context_violation_without_acl(self, ddd_shapes_graph):
        """Test that cross-context dependency without ACL is flagged."""
        # Arrange: Create two bounded contexts with illegal dependency
        data_graph = Graph()

        # Analysis BC
        analysis_bc = URIRef("https://example.com/ddd/AnalysisBC")
        data_graph.add((analysis_bc, RDF.type, DDD.BoundedContext))

        # Quality BC
        quality_bc = URIRef("https://example.com/ddd/QualityBC")
        data_graph.add((quality_bc, RDF.type, DDD.BoundedContext))

        # Modules
        analysis_module = URIRef("https://example.com/repo/module/analyzer.py")
        data_graph.add((analysis_module, RDF.type, REPO.Module))
        data_graph.add((analysis_module, DDD.inContext, analysis_bc))

        quality_module = URIRef("https://example.com/repo/module/quality.py")
        data_graph.add((quality_module, RDF.type, REPO.Module))
        data_graph.add((quality_module, DDD.inContext, quality_bc))

        # Violation: Analysis depends on Quality without ACL
        data_graph.add((analysis_module, REPO.dependsOn, quality_module))

        # Act: Validate
        conforms, results_graph, results_text = validate(
            data_graph=data_graph,
            shacl_graph=ddd_shapes_graph,
            inference="rdfs",
            abort_on_first=False,
        )

        # Assert
        assert not conforms, "Should detect cross-context violation"

    def test_ddd_context_with_acl_allowed(self, ddd_shapes_graph):
        """Test that cross-context dependency WITH ACL is allowed."""
        # Arrange: Create contexts with explicit ACL
        data_graph = Graph()

        # Use proper URIs matching the shape definition
        analysis_bc = URIRef("https://repoq.dev/ddd/AnalysisBC")
        data_graph.add((analysis_bc, RDF.type, DDD.BoundedContext))

        # Quality BC with ACL allowing Analysis to depend on it
        quality_bc = URIRef("https://repoq.dev/ddd/QualityBC")
        data_graph.add((quality_bc, RDF.type, DDD.BoundedContext))
        data_graph.add((analysis_bc, DDD.allowsDependencyOn, quality_bc))

        # Modules
        analysis_module = URIRef("https://example.com/repo/module/analyzer.py")
        data_graph.add((analysis_module, RDF.type, REPO.Module))
        data_graph.add((analysis_module, DDD.inContext, analysis_bc))

        quality_module = URIRef("https://example.com/repo/module/quality.py")
        data_graph.add((quality_module, RDF.type, REPO.Module))
        data_graph.add((quality_module, DDD.inContext, quality_bc))

        # Valid: Dependency allowed by ACL
        data_graph.add((analysis_module, REPO.dependsOn, quality_module))

        # Act: Validate
        conforms, results_graph, results_text = validate(
            data_graph=data_graph,
            shacl_graph=ddd_shapes_graph,
            inference="rdfs",
            abort_on_first=False,
        )

        # Assert
        assert (
            conforms
        ), f"Cross-context dependency with ACL should be allowed. Results:\n{results_text}"

    def test_bounded_context_enforcement(self, ddd_shapes_graph):
        """Test that modules must belong to one of 4 valid contexts."""
        # Arrange: Create module with invalid context
        data_graph = Graph()
        module_uri = URIRef("https://example.com/repo/module/bad.py")
        data_graph.add((module_uri, RDF.type, REPO.Module))
        # Invalid context (not one of Analysis, Quality, Ontology, Certificate)
        invalid_context = URIRef("https://example.com/ddd/UnknownBC")
        data_graph.add((module_uri, DDD.inContext, invalid_context))

        # Act: Validate
        conforms, results_graph, results_text = validate(
            data_graph=data_graph,
            shacl_graph=ddd_shapes_graph,
            inference="rdfs",
            abort_on_first=False,
        )

        # Assert
        assert not conforms, "Should reject invalid bounded context"
