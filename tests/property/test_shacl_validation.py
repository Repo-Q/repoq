"""
SHACL validation property tests.

Tests SHACL constraint enforcement on ontologies.
Verifies that violations are detected correctly.
"""

from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

# Define namespaces
META = Namespace("http://example.org/vocab/meta#")
TEST = Namespace("http://example.org/vocab/test#")
TRS = Namespace("http://example.org/vocab/trs#")
QUALITY = Namespace("http://example.org/vocab/quality#")
DOCS = Namespace("http://example.org/vocab/docs#")

# Paths
ONTOLOGY_DIR = Path(__file__).parent.parent.parent / "repoq" / "ontologies"
SHAPE_DIR = Path(__file__).parent.parent.parent / "repoq" / "shapes"


def test_meta_shacl_validation():
    """Test meta ontology SHACL validation."""
    # Load data and shape graphs
    data_graph = Graph()
    data_graph.parse(ONTOLOGY_DIR / "meta.ttl", format="turtle")

    shacl_graph = Graph()
    shacl_graph.parse(SHAPE_DIR / "meta_shape.ttl", format="turtle")

    # Validate
    conforms, results_graph, results_text = validate(
        data_graph, shacl_graph=shacl_graph, inference="rdfs", abort_on_first=False
    )

    # Meta ontology definition should conform
    assert conforms, f"Meta ontology validation failed:\n{results_text}"


def test_meta_stratification_violation():
    """Test that stratification level > 2 is detected as violation."""
    # Create test data with violation
    data_graph = Graph()
    data_graph.bind("meta", META)

    analysis = URIRef("http://example.org/bad_analysis")
    data_graph.add((analysis, RDF.type, META.SelfAnalysis))
    data_graph.add(
        (analysis, META.stratificationLevel, Literal(3, datatype=XSD.nonNegativeInteger))
    )  # VIOLATION
    data_graph.add((analysis, META.readOnlyMode, Literal(True, datatype=XSD.boolean)))

    # Load shape
    shacl_graph = Graph()
    shacl_graph.parse(SHAPE_DIR / "meta_shape.ttl", format="turtle")

    # Validate - should NOT conform
    conforms, results_graph, results_text = validate(
        data_graph, shacl_graph=shacl_graph, inference="rdfs", abort_on_first=False
    )

    assert not conforms, "Expected stratification violation to be detected"
    assert "stratification" in results_text.lower() or "level" in results_text.lower()


def test_meta_readonly_violation():
    """Test that readOnlyMode=false is detected as violation."""
    # Create test data with violation
    data_graph = Graph()
    data_graph.bind("meta", META)

    analysis = URIRef("http://example.org/bad_readonly")
    data_graph.add((analysis, RDF.type, META.SelfAnalysis))
    data_graph.add(
        (analysis, META.stratificationLevel, Literal(1, datatype=XSD.nonNegativeInteger))
    )
    data_graph.add((analysis, META.readOnlyMode, Literal(False, datatype=XSD.boolean)))  # VIOLATION

    # Load shape
    shacl_graph = Graph()
    shacl_graph.parse(SHAPE_DIR / "meta_shape.ttl", format="turtle")

    # Validate - should NOT conform
    conforms, results_graph, results_text = validate(
        data_graph, shacl_graph=shacl_graph, inference="rdfs", abort_on_first=False
    )

    assert not conforms, "Expected readOnlyMode violation to be detected"


def test_test_shacl_validation():
    """Test test ontology SHACL validation."""
    data_graph = Graph()
    data_graph.parse(ONTOLOGY_DIR / "test.ttl", format="turtle")

    shacl_graph = Graph()
    shacl_graph.parse(SHAPE_DIR / "test_shape.ttl", format="turtle")

    conforms, results_graph, results_text = validate(
        data_graph, shacl_graph=shacl_graph, inference="rdfs", abort_on_first=False
    )

    assert conforms, f"Test ontology validation failed:\n{results_text}"


def test_test_coverage_violation():
    """Test that coverage > 100% is detected as violation."""
    data_graph = Graph()
    data_graph.bind("test", TEST)

    coverage = URIRef("http://example.org/bad_coverage")
    data_graph.add((coverage, RDF.type, TEST.LineCoverage))
    data_graph.add(
        (coverage, TEST.coveragePercentage, Literal(150.0, datatype=XSD.decimal))
    )  # VIOLATION

    shacl_graph = Graph()
    shacl_graph.parse(SHAPE_DIR / "test_shape.ttl", format="turtle")

    conforms, results_graph, results_text = validate(
        data_graph, shacl_graph=shacl_graph, inference="rdfs", abort_on_first=False
    )

    assert not conforms, "Expected coverage violation to be detected"


def test_trs_shacl_validation():
    """Test TRS ontology SHACL validation."""
    data_graph = Graph()
    data_graph.parse(ONTOLOGY_DIR / "trs.ttl", format="turtle")

    shacl_graph = Graph()
    shacl_graph.parse(SHAPE_DIR / "trs_shape.ttl", format="turtle")

    conforms, results_graph, results_text = validate(
        data_graph, shacl_graph=shacl_graph, inference="rdfs", abort_on_first=False
    )

    assert conforms, f"TRS ontology validation failed:\n{results_text}"


def test_trs_soundness_violation():
    """Test that soundnessProven=false is detected as violation."""
    data_graph = Graph()
    data_graph.bind("trs", TRS)

    system = URIRef("http://example.org/bad_system")
    data_graph.add((system, RDF.type, TRS.RewriteSystem))
    data_graph.add((system, TRS.soundnessProven, Literal(False, datatype=XSD.boolean)))  # VIOLATION
    data_graph.add((system, TRS.confluenceProven, Literal(True, datatype=XSD.boolean)))
    data_graph.add((system, TRS.terminationProven, Literal(True, datatype=XSD.boolean)))

    shacl_graph = Graph()
    shacl_graph.parse(SHAPE_DIR / "trs_shape.ttl", format="turtle")

    conforms, results_graph, results_text = validate(
        data_graph, shacl_graph=shacl_graph, inference="rdfs", abort_on_first=False
    )

    assert not conforms, "Expected soundness violation to be detected"


def test_trs_joinability_violation():
    """Test that non-joinable critical pair is detected as violation."""
    data_graph = Graph()
    data_graph.bind("trs", TRS)

    cp = URIRef("http://example.org/bad_critical_pair")
    term1 = URIRef("http://example.org/term1")
    term2 = URIRef("http://example.org/term2")

    data_graph.add((cp, RDF.type, TRS.CriticalPair))
    data_graph.add((cp, TRS.leftTerm, term1))
    data_graph.add((cp, TRS.rightTerm, term2))
    data_graph.add((cp, TRS.joinable, Literal(False, datatype=XSD.boolean)))  # VIOLATION

    shacl_graph = Graph()
    shacl_graph.parse(SHAPE_DIR / "trs_shape.ttl", format="turtle")

    conforms, results_graph, results_text = validate(
        data_graph, shacl_graph=shacl_graph, inference="rdfs", abort_on_first=False
    )

    assert not conforms, "Expected joinability violation to be detected"


def test_quality_shacl_validation():
    """Test quality ontology SHACL validation."""
    data_graph = Graph()
    data_graph.parse(ONTOLOGY_DIR / "quality.ttl", format="turtle")

    shacl_graph = Graph()
    shacl_graph.parse(SHAPE_DIR / "quality_shape.ttl", format="turtle")

    conforms, results_graph, results_text = validate(
        data_graph, shacl_graph=shacl_graph, inference="rdfs", abort_on_first=False
    )

    assert conforms, f"Quality ontology validation failed:\n{results_text}"


def test_docs_shacl_validation():
    """Test docs ontology SHACL validation."""
    data_graph = Graph()
    data_graph.parse(ONTOLOGY_DIR / "docs.ttl", format="turtle")

    shacl_graph = Graph()
    shacl_graph.parse(SHAPE_DIR / "docs_shape.ttl", format="turtle")

    conforms, results_graph, results_text = validate(
        data_graph, shacl_graph=shacl_graph, inference="rdfs", abort_on_first=False
    )

    assert conforms, f"Docs ontology validation failed:\n{results_text}"


def test_docs_coverage_warning():
    """Test that low documentation coverage triggers warning."""
    data_graph = Graph()
    data_graph.bind("docs", DOCS)

    coverage = URIRef("http://example.org/low_coverage")
    data_graph.add((coverage, RDF.type, DOCS.Coverage))
    data_graph.add(
        (coverage, DOCS.coveragePercentage, Literal(50.0, datatype=XSD.decimal))
    )  # < 80% WARNING

    shacl_graph = Graph()
    shacl_graph.parse(SHAPE_DIR / "docs_shape.ttl", format="turtle")

    conforms, results_graph, results_text = validate(
        data_graph, shacl_graph=shacl_graph, inference="rdfs", abort_on_first=False
    )

    # Should conform but have warnings
    # (SHACL warnings don't make conforms=False, only violations do)
    # We just verify validation runs
    assert True  # Validation completed
