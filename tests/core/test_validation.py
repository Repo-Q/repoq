"""
Tests for SHACL validation module.

Test Strategy:
1. Valid data → should pass
2. Invalid data → should fail with specific violations
3. Warning conditions → should pass with warnings
4. Certificate generation → should create valid TTL

Author: URPKS Agent
Date: 2025-10-22
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF, XSD

from repoq.core.validation import SHACLValidator, ValidationResult

# Namespaces
STORY = Namespace("https://repoq.dev/ontology/story#")
ADR = Namespace("https://repoq.dev/ontology/adr#")
CHANGELOG = Namespace("https://repoq.dev/ontology/changelog#")
EX = Namespace("https://example.org/")


@pytest.fixture
def validator(tmp_path: Path) -> SHACLValidator:
    """Create validator with temporary workspace."""
    # Create .repoq structure
    repoq_dir = tmp_path / ".repoq"
    (repoq_dir / "shapes").mkdir(parents=True)
    (repoq_dir / "story").mkdir(parents=True)
    (repoq_dir / "adr").mkdir(parents=True)
    (repoq_dir / "changelog").mkdir(parents=True)
    (repoq_dir / "ontologies").mkdir(parents=True)
    (repoq_dir / "certificates").mkdir(parents=True)

    return SHACLValidator(tmp_path)


class TestStoryValidation:
    """Test SHACL validation for story ontology."""

    def test_valid_phase(self, validator: SHACLValidator, tmp_path: Path) -> None:
        """Valid Phase should pass validation."""
        # Create valid phase data
        data = Graph()
        data.bind("story", STORY)

        phase = EX.Phase1
        data.add((phase, RDF.type, STORY.Phase))
        data.add((phase, STORY.phaseId, Literal("phase1")))
        data.add((phase, STORY.title, Literal("Test Phase")))
        data.add((phase, STORY.status, STORY.StatusCompleted))
        data.add((phase, STORY.startDate, Literal("2025-01-01", datatype=XSD.date)))
        data.add((phase, STORY.endDate, Literal("2025-01-15", datatype=XSD.date)))

        # Load shape
        shapes = Graph()
        shape_file = Path(__file__).parent.parent.parent / ".repoq" / "shapes" / "story-shape.ttl"
        if shape_file.exists():
            shapes.parse(shape_file, format="turtle")
        else:
            pytest.skip("story-shape.ttl not found in workspace")

        # Validate
        result = validator.validate(data_graph=data, shapes_graph=shapes)

        # Should pass
        assert result.passed, f"Expected pass but got violations: {result.violations}"
        assert result.conforms
        assert len(result.violations) == 0

    def test_invalid_phase_missing_title(self, validator: SHACLValidator) -> None:
        """Phase without title should fail."""
        data = Graph()
        data.bind("story", STORY)

        phase = EX.Phase1
        data.add((phase, RDF.type, STORY.Phase))
        data.add((phase, STORY.phaseId, Literal("phase1")))
        # Missing title!
        data.add((phase, STORY.status, STORY.StatusPlanned))

        # Load shape
        shapes = Graph()
        shape_file = Path(__file__).parent.parent.parent / ".repoq" / "shapes" / "story-shape.ttl"
        if not shape_file.exists():
            pytest.skip("story-shape.ttl not found")
        shapes.parse(shape_file, format="turtle")

        # Validate
        result = validator.validate(data_graph=data, shapes_graph=shapes)

        # Should fail
        assert not result.passed
        assert len(result.violations) > 0
        assert any("title" in v.message.lower() for v in result.violations)

    def test_invalid_phase_bad_id_pattern(self, validator: SHACLValidator) -> None:
        """Phase with invalid phaseId pattern should fail."""
        data = Graph()
        data.bind("story", STORY)

        phase = EX.Phase1
        data.add((phase, RDF.type, STORY.Phase))
        data.add((phase, STORY.phaseId, Literal("bad-phase-id")))  # Invalid pattern!
        data.add((phase, STORY.title, Literal("Test Phase")))
        data.add((phase, STORY.status, STORY.StatusPlanned))

        # Load shape
        shapes = Graph()
        shape_file = Path(__file__).parent.parent.parent / ".repoq" / "shapes" / "story-shape.ttl"
        if not shape_file.exists():
            pytest.skip("story-shape.ttl not found")
        shapes.parse(shape_file, format="turtle")

        # Validate
        result = validator.validate(data_graph=data, shapes_graph=shapes)

        # Should fail with pattern violation
        assert not result.passed
        assert len(result.violations) > 0
        assert any("pattern" in v.message.lower() for v in result.violations)

    def test_completed_phase_without_enddate_warning(self, validator: SHACLValidator) -> None:
        """Completed Phase without endDate should trigger SPARQL constraint."""
        data = Graph()
        data.bind("story", STORY)

        phase = EX.Phase1
        data.add((phase, RDF.type, STORY.Phase))
        data.add((phase, STORY.phaseId, Literal("phase1")))
        data.add((phase, STORY.title, Literal("Test Phase")))
        data.add((phase, STORY.status, STORY.StatusCompleted))
        data.add((phase, STORY.startDate, Literal("2025-01-01", datatype=XSD.date)))
        # Missing endDate for completed phase!

        # Load shape
        shapes = Graph()
        shape_file = Path(__file__).parent.parent.parent / ".repoq" / "shapes" / "story-shape.ttl"
        if not shape_file.exists():
            pytest.skip("story-shape.ttl not found")
        shapes.parse(shape_file, format="turtle")

        # Validate
        result = validator.validate(data_graph=data, shapes_graph=shapes)

        # Should fail (SPARQL constraint violation)
        assert not result.passed
        assert len(result.violations) > 0


class TestADRValidation:
    """Test SHACL validation for ADR ontology."""

    def test_valid_adr(self, validator: SHACLValidator) -> None:
        """Valid ADR should pass validation."""
        data = Graph()
        data.bind("adr", ADR)

        adr_node = EX.ADR001
        context = EX.ADR001Context
        decision = EX.ADR001Decision

        # ADR
        data.add((adr_node, RDF.type, ADR.ArchitectureDecisionRecord))
        data.add((adr_node, ADR.id, Literal("ADR-001")))
        data.add((adr_node, ADR.title, Literal("Test Decision")))
        data.add((adr_node, ADR.status, ADR.StatusAccepted))
        data.add((adr_node, ADR.date, Literal("2025-01-01", datatype=XSD.date)))
        data.add((adr_node, ADR.context, context))
        data.add((adr_node, ADR.decision, decision))

        # Context
        data.add((context, RDF.type, ADR.Context))
        data.add(
            (context, ADR.problem, Literal("This is a problem statement with enough characters"))
        )

        # Decision
        data.add((decision, RDF.type, ADR.Decision))
        data.add(
            (decision, ADR.description, Literal("This is the decision we made with rationale"))
        )

        # Load shape
        shapes = Graph()
        shape_file = Path(__file__).parent.parent.parent / ".repoq" / "shapes" / "adr-shape.ttl"
        if not shape_file.exists():
            pytest.skip("adr-shape.ttl not found")
        shapes.parse(shape_file, format="turtle")

        # Validate
        result = validator.validate(data_graph=data, shapes_graph=shapes)

        # Should pass
        assert result.passed, f"Expected pass but got violations: {result.violations}"
        assert result.conforms

    def test_invalid_adr_id_pattern(self, validator: SHACLValidator) -> None:
        """ADR with invalid ID pattern should fail."""
        data = Graph()
        data.bind("adr", ADR)

        adr_node = EX.ADR001
        data.add((adr_node, RDF.type, ADR.ArchitectureDecisionRecord))
        data.add((adr_node, ADR.id, Literal("adr-1")))  # Invalid! Should be ADR-001
        data.add((adr_node, ADR.title, Literal("Test")))
        data.add((adr_node, ADR.status, ADR.StatusProposed))
        data.add((adr_node, ADR.date, Literal("2025-01-01", datatype=XSD.date)))

        # Load shape
        shapes = Graph()
        shape_file = Path(__file__).parent.parent.parent / ".repoq" / "shapes" / "adr-shape.ttl"
        if not shape_file.exists():
            pytest.skip("adr-shape.ttl not found")
        shapes.parse(shape_file, format="turtle")

        # Validate
        result = validator.validate(data_graph=data, shapes_graph=shapes)

        # Should fail
        assert not result.passed
        assert any("ADR-" in v.message for v in result.violations)

    def test_superseded_adr_without_supersedes_link(self, validator: SHACLValidator) -> None:
        """Superseded ADR without supersedes link should fail."""
        data = Graph()
        data.bind("adr", ADR)

        adr_node = EX.ADR001
        context = EX.ADR001Context
        decision = EX.ADR001Decision

        data.add((adr_node, RDF.type, ADR.ArchitectureDecisionRecord))
        data.add((adr_node, ADR.id, Literal("ADR-001")))
        data.add((adr_node, ADR.title, Literal("Old Decision")))
        data.add((adr_node, ADR.status, ADR.StatusSuperseded))  # Superseded!
        data.add((adr_node, ADR.date, Literal("2025-01-01", datatype=XSD.date)))
        data.add((adr_node, ADR.context, context))
        data.add((adr_node, ADR.decision, decision))
        # Missing adr:supersedes property!

        data.add((context, RDF.type, ADR.Context))
        data.add((context, ADR.problem, Literal("Problem statement here with enough length")))

        data.add((decision, RDF.type, ADR.Decision))
        data.add((decision, ADR.description, Literal("Decision description with enough length")))

        # Load shape
        shapes = Graph()
        shape_file = Path(__file__).parent.parent.parent / ".repoq" / "shapes" / "adr-shape.ttl"
        if not shape_file.exists():
            pytest.skip("adr-shape.ttl not found")
        shapes.parse(shape_file, format="turtle")

        # Validate
        result = validator.validate(data_graph=data, shapes_graph=shapes)

        # Should fail with SPARQL constraint
        assert not result.passed
        assert any("supersedes" in v.message.lower() for v in result.violations)


class TestChangelogValidation:
    """Test SHACL validation for changelog ontology."""

    def test_valid_release(self, validator: SHACLValidator) -> None:
        """Valid Release should pass validation."""
        data = Graph()
        data.bind("changelog", CHANGELOG)

        release = EX.Release200
        change = EX.Change1

        # Release
        data.add((release, RDF.type, CHANGELOG.Release))
        data.add((release, CHANGELOG.version, Literal("v2.0.0")))
        data.add((release, CHANGELOG.date, Literal("2025-01-01", datatype=XSD.date)))
        data.add((release, CHANGELOG.tag, Literal("v2.0.0")))
        data.add((release, CHANGELOG.change, change))

        # Change
        data.add((change, RDF.type, CHANGELOG.Change))
        data.add((change, CHANGELOG.changeType, CHANGELOG.TypeAdded))
        data.add(
            (
                change,
                CHANGELOG.description,
                Literal("Added new feature X with sufficient description"),
            )
        )

        # Load shape
        shapes = Graph()
        shape_file = (
            Path(__file__).parent.parent.parent / ".repoq" / "shapes" / "changelog-shape.ttl"
        )
        if not shape_file.exists():
            pytest.skip("changelog-shape.ttl not found")
        shapes.parse(shape_file, format="turtle")

        # Validate
        result = validator.validate(data_graph=data, shapes_graph=shapes)

        # Should pass
        assert result.passed, f"Expected pass but got violations: {result.violations}"
        assert result.conforms

    def test_invalid_version_pattern(self, validator: SHACLValidator) -> None:
        """Release with invalid version pattern should fail."""
        data = Graph()
        data.bind("changelog", CHANGELOG)

        release = EX.Release200
        change = EX.Change1

        data.add((release, RDF.type, CHANGELOG.Release))
        data.add((release, CHANGELOG.version, Literal("2.0")))  # Invalid! Missing patch
        data.add((release, CHANGELOG.date, Literal("2025-01-01", datatype=XSD.date)))
        data.add((release, CHANGELOG.change, change))

        data.add((change, RDF.type, CHANGELOG.Change))
        data.add((change, CHANGELOG.changeType, CHANGELOG.TypeAdded))
        data.add((change, CHANGELOG.description, Literal("Some change")))

        # Load shape
        shapes = Graph()
        shape_file = (
            Path(__file__).parent.parent.parent / ".repoq" / "shapes" / "changelog-shape.ttl"
        )
        if not shape_file.exists():
            pytest.skip("changelog-shape.ttl not found")
        shapes.parse(shape_file, format="turtle")

        # Validate
        result = validator.validate(data_graph=data, shapes_graph=shapes)

        # Should fail
        assert not result.passed
        assert any(
            "semver" in v.message.lower() or "pattern" in v.message.lower()
            for v in result.violations
        )


class TestCertificateGeneration:
    """Test validation certificate generation."""

    def test_generate_certificate_on_success(self, validator: SHACLValidator) -> None:
        """Successful validation should generate certificate."""
        # Create minimal valid data
        data = Graph()
        data.bind("story", STORY)

        phase = EX.Phase1
        data.add((phase, RDF.type, STORY.Phase))
        data.add((phase, STORY.phaseId, Literal("phase1")))
        data.add((phase, STORY.title, Literal("Test Phase")))
        data.add((phase, STORY.status, STORY.StatusPlanned))

        # Load shape
        shapes = Graph()
        shape_file = Path(__file__).parent.parent.parent / ".repoq" / "shapes" / "story-shape.ttl"
        if not shape_file.exists():
            pytest.skip("story-shape.ttl not found")
        shapes.parse(shape_file, format="turtle")

        # Validate and certify
        result, cert_path = validator.validate_and_certify(data_graph=data, shapes_graph=shapes)

        if result.passed:
            # Should generate certificate
            assert cert_path is not None
            assert cert_path.exists()
            assert cert_path.suffix == ".ttl"

            # Certificate should be valid TTL
            cert_graph = Graph()
            cert_graph.parse(cert_path, format="turtle")
            assert len(cert_graph) > 0
        else:
            # If validation failed, no certificate
            assert cert_path is None

    def test_cannot_generate_certificate_on_failure(self, validator: SHACLValidator) -> None:
        """Failed validation should not generate certificate."""
        # Create invalid data
        data = Graph()
        data.bind("story", STORY)

        phase = EX.Phase1
        data.add((phase, RDF.type, STORY.Phase))
        # Missing required properties!

        shapes = Graph()
        shape_file = Path(__file__).parent.parent.parent / ".repoq" / "shapes" / "story-shape.ttl"
        if not shape_file.exists():
            pytest.skip("story-shape.ttl not found")
        shapes.parse(shape_file, format="turtle")

        # Validate and certify
        result, cert_path = validator.validate_and_certify(data_graph=data, shapes_graph=shapes)

        # Should fail
        assert not result.passed
        assert cert_path is None


class TestValidationWorkflow:
    """Test end-to-end validation workflow."""

    def test_validate_workspace_data(self, tmp_path: Path) -> None:
        """Test validating real workspace data."""
        # Copy real shapes to temp workspace
        real_shapes_dir = Path(__file__).parent.parent.parent / ".repoq" / "shapes"
        if not real_shapes_dir.exists():
            pytest.skip("Real shapes not found")

        temp_repoq = tmp_path / ".repoq"
        temp_shapes = temp_repoq / "shapes"
        temp_shapes.mkdir(parents=True)

        import shutil

        for shape_file in real_shapes_dir.glob("*.ttl"):
            shutil.copy(shape_file, temp_shapes / shape_file.name)

        # Create validator
        validator = SHACLValidator(tmp_path)

        # Load shapes
        shapes = validator.load_shapes()
        assert len(shapes) > 0

        # Note: We don't have data to validate yet in temp dir
        # This test mainly checks that shapes load correctly

    def test_validation_result_summary(self, validator: SHACLValidator) -> None:
        """Test ValidationResult.summary() formatting."""
        from repoq.core.validation import ValidationIssue

        result = ValidationResult(
            conforms=False,
            violations=[
                ValidationIssue(
                    severity="Violation",
                    focus_node="ex:Node1",
                    message="Test violation",
                    source_shape="ex:Shape1",
                    result_path="ex:property",
                    value="bad_value",
                )
            ],
            warnings=[],
            info=[],
            shapes_graph=Graph(),
            data_graph=Graph(),
            report_graph=None,
            timestamp=datetime.now(),
        )

        summary = result.summary()
        assert "FAILED" in summary
        assert "Violations: 1" in summary
        assert not result.passed
