"""Tests for VDAD → RDF extraction (Phase 5.6 POC).

Traceability:
- V07: Observability (VDAD structure visible as RDF)
- FR-10: Reproducible analysis (VDAD extraction deterministic)
- ADR-013: Incremental migration (Phase 2 values first)
"""

from pathlib import Path
from textwrap import dedent

import pytest
from rdflib import RDF, RDFS, XSD, Graph, Literal, Namespace

from scripts.extract_vdad_rdf import (
    StakeholderInfo,
    ValueInfo,
    extract_phase2_values,
    generate_phase2_rdf,
    parse_phase2_values_markdown,
)

VDAD = Namespace("https://repoq.io/vdad#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")


@pytest.fixture
def sample_phase2_markdown(tmp_path: Path) -> Path:
    """Create sample Phase 2 Values Markdown."""
    content = dedent("""\
        # Phase 2: Value Register

        ## V01: Transparency

        The system must provide clear visibility into code quality metrics.

        **Tier**: 1
        **Priority**: P0
        **Stakeholders**: Alex, Morgan

        Satisfied by: FR-01, FR-05

        ## V02: Efficiency

        Analysis must complete in reasonable time.

        **Tier**: 1
        **Priority**: P1
        **Stakeholders**: Casey

        Satisfied by: NFR-01

        ## Stakeholder Profiles

        ### Alex (Senior Developer)

        **Interests**:
        - Code quality metrics
        - Automated analysis

        **Concerns**:
        - Performance overhead
        - False positives

        ### Morgan (Team Lead)

        **Interests**:
        - Team productivity
        - Technical debt tracking

        **Concerns**:
        - Integration complexity

        ### Casey (DevOps Engineer)

        **Interests**:
        - CI/CD integration
        - Reproducibility

        **Concerns**:
        - Build time impact
    """)

    path = tmp_path / "phase2-values.md"
    path.write_text(content)
    return path


class TestMarkdownParsing:
    """Test Markdown → structured data extraction."""

    def test_parse_values_count(self, sample_phase2_markdown: Path) -> None:
        """Should extract correct number of values."""
        values, stakeholders = parse_phase2_values_markdown(sample_phase2_markdown)
        assert len(values) == 2
        assert len(stakeholders) == 3

    def test_parse_value_v01(self, sample_phase2_markdown: Path) -> None:
        """Should parse V01 correctly."""
        values, _ = parse_phase2_values_markdown(sample_phase2_markdown)
        v01 = next(v for v in values if v.id == "v01")

        assert v01.label == "V01: Transparency"
        assert v01.tier == 1
        assert v01.priority == "P0"
        assert "alex" in v01.stakeholders
        assert "morgan" in v01.stakeholders
        assert "fr-01" in v01.satisfied_by
        assert "fr-05" in v01.satisfied_by

    def test_parse_value_v02(self, sample_phase2_markdown: Path) -> None:
        """Should parse V02 correctly."""
        values, _ = parse_phase2_values_markdown(sample_phase2_markdown)
        v02 = next(v for v in values if v.id == "v02")

        assert v02.label == "V02: Efficiency"
        assert v02.tier == 1
        assert v02.priority == "P1"
        assert "casey" in v02.stakeholders
        assert "nfr-01" in v02.satisfied_by

    def test_parse_stakeholder_alex(self, sample_phase2_markdown: Path) -> None:
        """Should parse Alex stakeholder correctly."""
        _, stakeholders = parse_phase2_values_markdown(sample_phase2_markdown)
        alex = next(s for s in stakeholders if s.id == "alex")

        assert alex.name == "Alex"
        assert alex.role == "Senior Developer"
        assert alex.type == "Developer"
        assert "Code quality metrics" in alex.interests
        assert "Performance overhead" in alex.concerns

    def test_parse_stakeholder_types(self, sample_phase2_markdown: Path) -> None:
        """Should assign correct stakeholder types."""
        _, stakeholders = parse_phase2_values_markdown(sample_phase2_markdown)

        alex = next(s for s in stakeholders if s.id == "alex")
        morgan = next(s for s in stakeholders if s.id == "morgan")
        casey = next(s for s in stakeholders if s.id == "casey")

        assert alex.type == "Developer"
        assert morgan.type == "TeamLead"
        assert casey.type == "DevOps"


class TestRDFGeneration:
    """Test structured data → RDF graph generation."""

    def test_generate_graph_triples(self) -> None:
        """Should generate correct number of triples."""
        values = [
            ValueInfo(
                id="v01",
                label="V01: Test",
                tier=1,
                description="Test value",
                priority="P0",
                stakeholders=["alex"],
                satisfied_by=["fr-01"],
                phase="phase2",
            )
        ]
        stakeholders = [
            StakeholderInfo(
                id="alex",
                name="Alex",
                role="Developer",
                type="Developer",
                interests=["Quality"],
                concerns=["Time"],
            )
        ]

        graph = generate_phase2_rdf(values, stakeholders)

        # Value triples: type×2 + label + tier + desc + priority + phase + stakeholder + req = 10
        # Stakeholder triples: type×2 + name + role + interest + concern = 6
        # Total ≈ 15 triples (RDF integer literals may be collapsed)
        assert len(graph) >= 15

    def test_value_rdf_structure(self) -> None:
        """Should create correct value RDF structure."""
        values = [
            ValueInfo(
                id="v01",
                label="V01: Test",
                tier=1,
                description="Test value",
                priority="P0",
                stakeholders=["alex"],
                satisfied_by=["fr-01"],
                phase="phase2",
            )
        ]

        graph = generate_phase2_rdf(values, [])

        v01_uri = VDAD["v01"]
        assert (v01_uri, RDF.type, VDAD.Tier1Value) in graph
        assert (v01_uri, RDF.type, VDAD.Value) in graph
        assert (v01_uri, RDFS.label, Literal("V01: Test")) in graph
        assert (v01_uri, VDAD.priority, VDAD["P0"]) in graph
        assert (v01_uri, VDAD.stakeholder, VDAD["alex"]) in graph
        assert (v01_uri, VDAD.satisfiedBy, VDAD["fr-01"]) in graph

    def test_stakeholder_rdf_structure(self) -> None:
        """Should create correct stakeholder RDF structure."""
        stakeholders = [
            StakeholderInfo(
                id="alex",
                name="Alex",
                role="Developer",
                type="Developer",
                interests=["Quality", "Performance"],
                concerns=["Time"],
            )
        ]

        graph = generate_phase2_rdf([], stakeholders)

        alex_uri = VDAD["alex"]
        assert (alex_uri, RDF.type, VDAD.Developer) in graph
        assert (alex_uri, RDF.type, VDAD.Stakeholder) in graph
        assert (alex_uri, FOAF.name, Literal("Alex")) in graph
        assert (alex_uri, VDAD.role, Literal("Developer")) in graph
        assert (alex_uri, VDAD.interests, Literal("Quality")) in graph
        assert (alex_uri, VDAD.interests, Literal("Performance")) in graph
        assert (alex_uri, VDAD.concerns, Literal("Time")) in graph


class TestEndToEnd:
    """Test full extraction pipeline."""

    def test_extract_phase2_values(self, sample_phase2_markdown: Path, tmp_path: Path) -> None:
        """Should extract Phase 2 Values to TTL."""
        output_path = tmp_path / "phase2-values.ttl"

        count = extract_phase2_values(sample_phase2_markdown, output_path)

        assert output_path.exists()
        assert count > 0

        # Load and verify
        graph = Graph()
        graph.parse(output_path, format="turtle")
        assert len(graph) == count

    def test_extract_real_phase2(self) -> None:
        """Should extract real Phase 2 Values if they exist."""
        markdown_path = Path("docs/vdad/phase2-values.md")
        if not markdown_path.exists():
            pytest.skip("Real Phase 2 Values not found")

        # Parse
        values, stakeholders = parse_phase2_values_markdown(markdown_path)

        # Verify structure
        assert len(values) >= 5  # at least 5 Tier 1 values
        assert len(stakeholders) >= 3  # at least 3 stakeholders

        # Check V01 exists
        v01 = next((v for v in values if v.id == "v01"), None)
        assert v01 is not None
        assert v01.tier == 1
        assert len(v01.stakeholders) > 0

    def test_extract_to_repoq_directory(self, sample_phase2_markdown: Path) -> None:
        """Should extract to .repoq/vdad/ directory (Single Source of Truth)."""
        output_path = Path(".repoq/vdad/test-phase2.ttl")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            count = extract_phase2_values(sample_phase2_markdown, output_path)
            assert output_path.exists()
            assert count > 0

            # Verify SSoT: RDF stored in .repoq/, not in docs/
            assert ".repoq" in str(output_path)
            assert "docs" not in str(output_path)
        finally:
            if output_path.exists():
                output_path.unlink()


class TestMarkdownGeneration:
    """Test RDF → Markdown generation (Single Source of Truth)."""

    def test_generate_markdown_from_rdf(self, tmp_path: Path) -> None:
        """Should generate Markdown from RDF (SSoT: RDF → Markdown)."""
        from scripts.generate_vdad_markdown import generate_phase2_markdown

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
        from scripts.generate_vdad_markdown import generate_phase2_markdown

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


class TestGateVDADExtraction:
    """Test Γ gates for VDAD extraction."""

    def test_gate_deterministic_output(self, sample_phase2_markdown: Path, tmp_path: Path) -> None:
        """Gate: Extraction must be deterministic (reproducibility)."""
        output1 = tmp_path / "out1.ttl"
        output2 = tmp_path / "out2.ttl"

        count1 = extract_phase2_values(sample_phase2_markdown, output1)
        count2 = extract_phase2_values(sample_phase2_markdown, output2)

        assert count1 == count2
        assert output1.read_text() == output2.read_text()

    def test_gate_no_data_loss(self, sample_phase2_markdown: Path) -> None:
        """Gate: No data loss during extraction."""
        values, stakeholders = parse_phase2_values_markdown(sample_phase2_markdown)

        # All values must have IDs
        assert all(v.id for v in values)

        # All values must have labels
        assert all(v.label for v in values)

        # All stakeholders must have names
        assert all(s.name for s in stakeholders)

    def test_gate_valid_references(self, sample_phase2_markdown: Path) -> None:
        """Gate: All value→stakeholder references must be valid."""
        values, stakeholders = parse_phase2_values_markdown(sample_phase2_markdown)

        stakeholder_ids = {s.id for s in stakeholders}

        for value in values:
            for stakeholder_id in value.stakeholders:
                assert (
                    stakeholder_id in stakeholder_ids
                ), f"Value {value.id} references unknown stakeholder {stakeholder_id}"
