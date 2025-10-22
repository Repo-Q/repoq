"""Tests for VDAD RDF → Markdown generation (Phase 5.6).

Single Source of Truth: .repoq/vdad/*.ttl (hand-edited) → docs/vdad/*.md (generated)

Traceability:
- V07: Observability (VDAD as queryable RDF)
- FR-10: Reproducibility (RDF → Markdown deterministic)
- ADR-014: Single Source of Truth (.repoq/ for RDF)
"""

from pathlib import Path

from rdflib import RDF, RDFS, XSD, Graph, Literal, Namespace

from scripts.generate_vdad_markdown import generate_phase2_markdown

VDAD = Namespace("https://repoq.io/vdad#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")


class TestMarkdownGeneration:
    """Test RDF → Markdown generation (Single Source of Truth)."""

    def test_generate_markdown_from_rdf(self, tmp_path: Path) -> None:
        """Should generate Markdown from RDF (SSoT: RDF → Markdown)."""
        # Create test RDF
        rdf_path = tmp_path / "test.ttl"
        graph = Graph()
        graph.bind("vdad", VDAD)
        graph.bind("foaf", FOAF)

        # Add test value
        v01 = VDAD["v01"]
        graph.add((v01, RDF.type, VDAD.Tier1Value))
        graph.add((v01, RDF.type, VDAD.Value))
        graph.add((v01, RDFS.label, Literal("V01: Test Value")))
        graph.add((v01, VDAD.description, Literal("Test description")))
        graph.add((v01, VDAD.tier, Literal(1, datatype=XSD.integer)))
        graph.add((v01, VDAD.priority, VDAD["P0"]))

        # Add test stakeholder
        alex = VDAD["alex"]
        graph.add((alex, RDF.type, VDAD.Developer))
        graph.add((alex, RDF.type, VDAD.Stakeholder))
        graph.add((alex, FOAF.name, Literal("Alex")))
        graph.add((alex, VDAD.role, Literal("Developer")))
        graph.add((alex, VDAD.interests, Literal("Quality")))

        # Link value → stakeholder
        graph.add((v01, VDAD.stakeholder, alex))

        # Save RDF
        graph.serialize(destination=rdf_path, format="turtle")

        # Generate Markdown
        md_path = tmp_path / "test.md"
        lines = generate_phase2_markdown(rdf_path, md_path)

        assert md_path.exists()
        assert lines > 0

        # Verify content
        content = md_path.read_text()
        assert "# Phase 2: Value Register" in content
        assert "V01: Test Value" in content
        assert "Test description" in content
        assert "**Tier**: 1" in content
        assert "**Priority**: P0" in content
        assert "Alex" in content
        assert "Generated from RDF" in content  # SSoT marker

    def test_ssot_principle_enforced(self, tmp_path: Path) -> None:
        """Should enforce SSoT principle: RDF in .repoq/, Markdown in docs/."""
        # Create minimal RDF
        rdf_path = tmp_path / ".repoq" / "vdad" / "test.ttl"
        rdf_path.parent.mkdir(parents=True, exist_ok=True)

        graph = Graph()
        graph.bind("vdad", VDAD)
        v01 = VDAD["v01"]
        graph.add((v01, RDF.type, VDAD.Tier1Value))
        graph.add((v01, RDFS.label, Literal("V01: Test")))
        graph.add((v01, VDAD.description, Literal("Test")))
        graph.add((v01, VDAD.tier, Literal(1, datatype=XSD.integer)))
        graph.serialize(destination=rdf_path, format="turtle")

        # Generate to docs/
        md_path = tmp_path / "docs" / "vdad" / "test.md"
        lines = generate_phase2_markdown(rdf_path, md_path)

        # Verify paths follow SSoT principle
        assert ".repoq" in str(rdf_path)  # Source in .repoq/
        assert "docs" in str(md_path)  # Generated in docs/
        assert lines > 0

    def test_multiple_values(self, tmp_path: Path) -> None:
        """Should handle multiple values correctly."""
        rdf_path = tmp_path / "test.ttl"
        graph = Graph()
        graph.bind("vdad", VDAD)

        # Add 3 values
        for i in range(1, 4):
            vid = f"v0{i}"
            v = VDAD[vid]
            graph.add((v, RDF.type, VDAD.Tier1Value))
            graph.add((v, RDFS.label, Literal(f"V0{i}: Value {i}")))
            graph.add((v, VDAD.description, Literal(f"Description {i}")))
            graph.add((v, VDAD.tier, Literal(1, datatype=XSD.integer)))

        graph.serialize(destination=rdf_path, format="turtle")

        # Generate
        md_path = tmp_path / "test.md"
        lines = generate_phase2_markdown(rdf_path, md_path)

        content = md_path.read_text()
        assert "V01: Value 1" in content
        assert "V02: Value 2" in content
        assert "V03: Value 3" in content

    def test_stakeholder_interests_and_concerns(self, tmp_path: Path) -> None:
        """Should render stakeholder interests and concerns."""
        rdf_path = tmp_path / "test.ttl"
        graph = Graph()
        graph.bind("vdad", VDAD)
        graph.bind("foaf", FOAF)

        # Add stakeholder with multiple interests/concerns
        alex = VDAD["alex"]
        graph.add((alex, RDF.type, VDAD.Stakeholder))
        graph.add((alex, FOAF.name, Literal("Alex")))
        graph.add((alex, VDAD.role, Literal("Developer")))
        graph.add((alex, VDAD.interests, Literal("Code quality")))
        graph.add((alex, VDAD.interests, Literal("Performance")))
        graph.add((alex, VDAD.concerns, Literal("Technical debt")))

        graph.serialize(destination=rdf_path, format="turtle")

        # Generate
        md_path = tmp_path / "test.md"
        generate_phase2_markdown(rdf_path, md_path)

        content = md_path.read_text()
        assert "### Alex (Developer)" in content
        assert "**Interests**:" in content
        assert "- Code quality" in content
        assert "- Performance" in content
        assert "**Concerns**:" in content
        assert "- Technical debt" in content


class TestGateVDADGeneration:
    """Test Γ gates for VDAD generation."""

    def test_gate_deterministic_output(self, tmp_path: Path) -> None:
        """Gate: Generation must be deterministic (reproducibility)."""
        rdf_path = tmp_path / "test.ttl"
        graph = Graph()
        graph.bind("vdad", VDAD)
        v01 = VDAD["v01"]
        graph.add((v01, RDF.type, VDAD.Tier1Value))
        graph.add((v01, RDFS.label, Literal("V01: Test")))
        graph.add((v01, VDAD.description, Literal("Test")))
        graph.add((v01, VDAD.tier, Literal(1, datatype=XSD.integer)))
        graph.serialize(destination=rdf_path, format="turtle")

        # Generate twice
        md1 = tmp_path / "out1.md"
        md2 = tmp_path / "out2.md"

        lines1 = generate_phase2_markdown(rdf_path, md1)
        lines2 = generate_phase2_markdown(rdf_path, md2)

        assert lines1 == lines2
        assert md1.read_text() == md2.read_text()

    def test_gate_ssot_marker_present(self, tmp_path: Path) -> None:
        """Gate: Generated Markdown must have SSoT marker."""
        rdf_path = tmp_path / "test.ttl"
        graph = Graph()
        graph.bind("vdad", VDAD)
        v01 = VDAD["v01"]
        graph.add((v01, RDF.type, VDAD.Tier1Value))
        graph.add((v01, RDFS.label, Literal("V01: Test")))
        graph.add((v01, VDAD.description, Literal("Test")))
        graph.add((v01, VDAD.tier, Literal(1, datatype=XSD.integer)))
        graph.serialize(destination=rdf_path, format="turtle")

        md_path = tmp_path / "test.md"
        generate_phase2_markdown(rdf_path, md_path)

        content = md_path.read_text()
        assert "Generated from RDF" in content
        assert ".repoq/vdad/" in content
        assert "Single Source of Truth" in content

    def test_gate_no_data_loss(self, tmp_path: Path) -> None:
        """Gate: All RDF data must appear in Markdown."""
        rdf_path = tmp_path / "test.ttl"
        graph = Graph()
        graph.bind("vdad", VDAD)
        graph.bind("foaf", FOAF)

        # Add value with all properties
        v01 = VDAD["v01"]
        graph.add((v01, RDF.type, VDAD.Tier1Value))
        graph.add((v01, RDFS.label, Literal("V01: Comprehensive")))
        graph.add((v01, VDAD.description, Literal("Full description")))
        graph.add((v01, VDAD.tier, Literal(1, datatype=XSD.integer)))
        graph.add((v01, VDAD.priority, VDAD["P0"]))

        # Add stakeholder
        alex = VDAD["alex"]
        graph.add((alex, RDF.type, VDAD.Stakeholder))
        graph.add((alex, FOAF.name, Literal("Alex")))
        graph.add((alex, VDAD.role, Literal("Developer")))
        graph.add((v01, VDAD.stakeholder, alex))

        # Add requirement
        graph.add((v01, VDAD.satisfiedBy, VDAD["fr-01"]))

        graph.serialize(destination=rdf_path, format="turtle")

        md_path = tmp_path / "test.md"
        generate_phase2_markdown(rdf_path, md_path)

        content = md_path.read_text()
        # All data must be present
        assert "V01: Comprehensive" in content
        assert "Full description" in content
        assert "**Tier**: 1" in content
        assert "**Priority**: P0" in content
        assert "Alex" in content
        assert "FR-01" in content
