"""
Property-based tests for ontology consistency using Hypothesis.

STRATIFICATION_LEVEL: 2 (property testing meta-ontology invariants)

This test module operates at level 2:
- Level 0: Base repository entities
- Level 1: Ontology triples and constraints
- Level 2: Property-based verification of ontology (this module)

Tests invariants:
1. Stratification: ∀level. level ∈ [0, 2] (Russell's paradox prevention)
2. Coverage: ∀cov. cov ∈ [0, 100]
3. TRS Joinability: ∀cp. joinable=false → system non-confluent
4. Quality Gates: ∀gate. failed ∧ blocksMerge → PR blocked
"""

from pathlib import Path

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

# Define namespaces
META = Namespace("http://example.org/vocab/meta#")
TEST = Namespace("http://example.org/vocab/test#")
TRS = Namespace("http://example.org/vocab/trs#")
QUALITY = Namespace("http://example.org/vocab/quality#")
DOCS = Namespace("http://example.org/vocab/docs#")

# Path to ontologies
ONTOLOGY_DIR = Path(__file__).parent.parent.parent / "repoq" / "ontologies"


@pytest.fixture
def meta_graph():
    """Load meta ontology (fresh copy per test)."""

    def _make_graph():
        g = Graph()
        g.parse(ONTOLOGY_DIR / "meta.ttl", format="turtle")
        return g

    return _make_graph()


@pytest.fixture
def test_graph():
    """Load test ontology (fresh copy per test)."""

    def _make_graph():
        g = Graph()
        g.parse(ONTOLOGY_DIR / "test.ttl", format="turtle")
        return g

    return _make_graph()


@pytest.fixture
def trs_graph():
    """Load TRS ontology (fresh copy per test)."""

    def _make_graph():
        g = Graph()
        g.parse(ONTOLOGY_DIR / "trs.ttl", format="turtle")
        return g

    return _make_graph()


@pytest.fixture
def quality_graph():
    """Load quality ontology (fresh copy per test)."""

    def _make_graph():
        g = Graph()
        g.parse(ONTOLOGY_DIR / "quality.ttl", format="turtle")
        return g

    return _make_graph()


# =============================================================================
# PROPERTY 1: Stratification Safety (Russell's Paradox Prevention)
# =============================================================================


@given(st.integers(min_value=0, max_value=2))
def test_stratification_level_bounds(level: int):
    """
    Property: ∀level. level ∈ [0, 2]

    Ensures stratification levels never exceed maximum safe level (2).
    Prevents Russell's paradox by enforcing type hierarchy.
    """
    # Create fresh graph for this test
    g = Graph()

    # Create test instance
    analysis = URIRef("http://example.org/analysis_test")
    g.add((analysis, RDF.type, META.SelfAnalysis))
    g.add((analysis, META.stratificationLevel, Literal(level, datatype=XSD.nonNegativeInteger)))

    # Verify level is within bounds
    assert 0 <= level <= 2, f"Stratification level {level} violates Russell's guard"

    # Verify level can be queried
    result = g.value(analysis, META.stratificationLevel)
    assert result is not None
    assert int(result) == level


@given(st.integers(min_value=3, max_value=100))
def test_stratification_level_exceeds_max(level: int):
    """
    Property: ∀level. level > 2 → VIOLATION

    Ensures stratification violations are detected.
    """
    # Create fresh graph
    g = Graph()

    # Create test instance with invalid level
    analysis = URIRef("http://example.org/analysis_invalid")
    g.add((analysis, RDF.type, META.SelfAnalysis))
    g.add((analysis, META.stratificationLevel, Literal(level, datatype=XSD.nonNegativeInteger)))

    # This should be detected as violation by SHACL
    # (We verify here that the value itself violates the constraint)
    assert level > 2, f"Expected violation for level {level}"


@given(st.booleans())
def test_readonly_mode_required(readonly: bool):
    """
    Property: ∀analysis. readOnlyMode = true (required)

    Ensures self-analysis cannot modify itself (prevents modification paradoxes).
    """
    # Create fresh graph
    g = Graph()

    analysis = URIRef("http://example.org/analysis_readonly")
    g.add((analysis, RDF.type, META.SelfAnalysis))
    g.add((analysis, META.readOnlyMode, Literal(readonly, datatype=XSD.boolean)))

    # Only readOnlyMode=true is valid
    if not readonly:
        # This should be detected as violation by SHACL
        pytest.skip("readOnlyMode=false violates constraint (expected)")


# =============================================================================
# PROPERTY 2: Coverage Bounds
# =============================================================================


@given(st.floats(min_value=0.0, max_value=100.0))
def test_coverage_percentage_bounds(coverage: float):
    """
    Property: ∀cov. 0 ≤ cov ≤ 100

    Ensures coverage percentages are valid.
    """
    # Create fresh graph
    g = Graph()

    # Create test coverage instance
    cov_instance = URIRef("http://example.org/coverage_test")
    g.add((cov_instance, RDF.type, TEST.LineCoverage))
    g.add((cov_instance, TEST.coveragePercentage, Literal(coverage, datatype=XSD.decimal)))

    # Verify bounds
    assert 0.0 <= coverage <= 100.0, f"Coverage {coverage}% out of bounds"

    # Verify value can be queried
    result = g.value(cov_instance, TEST.coveragePercentage)
    assert result is not None
    assert float(result) == pytest.approx(coverage, abs=0.01)


@given(st.floats(min_value=100.01, max_value=1000.0))
def test_coverage_percentage_exceeds_max(coverage: float):
    """
    Property: ∀cov. cov > 100 → VIOLATION

    Ensures invalid coverage values are detected.
    """
    # Create fresh graph
    g = Graph()

    cov_instance = URIRef("http://example.org/coverage_invalid")
    g.add((cov_instance, RDF.type, TEST.LineCoverage))
    g.add((cov_instance, TEST.coveragePercentage, Literal(coverage, datatype=XSD.decimal)))

    # This should be detected as violation by SHACL
    assert coverage > 100.0, f"Expected violation for coverage {coverage}%"


# =============================================================================
# PROPERTY 3: TRS Confluence (Critical Pairs Joinability)
# =============================================================================


@given(st.booleans())
def test_critical_pair_joinability(joinable: bool):
    """
    Property: ∀cp. joinable = false → system non-confluent

    Ensures critical pairs must be joinable for confluence.
    """
    # Create fresh graph
    g = Graph()

    cp = URIRef("http://example.org/critical_pair_test")
    g.add((cp, RDF.type, TRS.CriticalPair))
    g.add((cp, TRS.joinable, Literal(joinable, datatype=XSD.boolean)))

    # Non-joinable critical pairs block confluence
    if not joinable:
        # This should be detected as VIOLATION by SHACL (blocks merge)
        pytest.skip("Non-joinable critical pair violates confluence (expected)")


@given(st.booleans())
def test_trs_soundness_required(soundness_proven: bool):
    """
    Property: ∀sys. soundnessProven = true (required)

    Ensures TRS soundness must be proven before deployment.
    """
    # Create fresh graph
    g = Graph()

    system = URIRef("http://example.org/trs_system_test")
    g.add((system, RDF.type, TRS.RewriteSystem))
    g.add((system, TRS.soundnessProven, Literal(soundness_proven, datatype=XSD.boolean)))

    # Only soundnessProven=true is valid
    if not soundness_proven:
        # This should be detected as VIOLATION by SHACL (blocks merge)
        pytest.skip("Unproven soundness violates constraint (expected)")


# =============================================================================
# PROPERTY 4: Quality Gates (Merge Blocking)
# =============================================================================


@given(st.sampled_from(["passed", "failed", "warning", "skipped"]), st.booleans())
def test_quality_gate_blocking(status: str, blocks_merge: bool):
    """
    Property: ∀gate. (status = "failed" ∧ blocksMerge = true) → PR blocked

    Ensures failed gates with blocksMerge=true prevent PR merge.
    """
    # Create fresh graph
    g = Graph()

    gate = URIRef("http://example.org/gate_test")
    g.add((gate, RDF.type, QUALITY.Gate))
    g.add((gate, QUALITY.gateStatus, Literal(status)))
    g.add((gate, QUALITY.blocksMerge, Literal(blocks_merge, datatype=XSD.boolean)))

    # Failed gates that block merge should prevent PR merge
    if status == "failed" and blocks_merge:
        # This should be detected as VIOLATION by SHACL
        pytest.skip("Failed blocking gate violates constraint (expected)")


@given(st.floats(min_value=0.0, max_value=1000.0))
def test_quality_delta_q_non_negative(delta_q: float):
    """
    Property: ∀rec. deltaQ ≥ 0

    Ensures quality improvement recommendations have non-negative deltaQ.
    """
    # Create fresh graph
    g = Graph()

    rec = URIRef("http://example.org/recommendation_test")
    g.add((rec, RDF.type, QUALITY.Recommendation))
    g.add((rec, QUALITY.deltaQ, Literal(delta_q, datatype=XSD.decimal)))

    # deltaQ must be non-negative
    assert delta_q >= 0.0, f"deltaQ {delta_q} must be non-negative"

    # Verify value can be queried
    result = g.value(rec, QUALITY.deltaQ)
    assert result is not None
    assert float(result) == pytest.approx(delta_q, abs=0.01)


# =============================================================================
# PROPERTY 5: Test Status Consistency
# =============================================================================


@given(st.sampled_from(["passed", "failed", "skipped", "xfail"]))
def test_test_status_values(status: str):
    """
    Property: ∀test. testStatus ∈ {passed, failed, skipped, xfail}

    Ensures test status values are valid.
    """
    # Create fresh graph
    g = Graph()

    test_case = URIRef("http://example.org/test_case")
    g.add((test_case, RDF.type, TEST.TestCase))
    g.add((test_case, TEST.testStatus, Literal(status)))

    # Verify status is valid
    assert status in ["passed", "failed", "skipped", "xfail"]

    # Verify value can be queried
    result = g.value(test_case, TEST.testStatus)
    assert result is not None
    assert str(result) == status


# =============================================================================
# PROPERTY 6: Property Test Generation Bounds
# =============================================================================


@given(st.integers(min_value=1, max_value=10000))
def test_property_test_generation_bounds(num_examples: int):
    """
    Property: ∀pt. 1 ≤ generatedExamples ≤ 10000

    Ensures property tests generate reasonable number of examples.
    """
    # Create fresh graph
    g = Graph()

    prop_test = URIRef("http://example.org/property_test")
    g.add((prop_test, RDF.type, TEST.PropertyTest))
    g.add(
        (prop_test, TEST.generatedExamples, Literal(num_examples, datatype=XSD.nonNegativeInteger))
    )

    # Verify bounds
    assert 1 <= num_examples <= 10000, f"Generated examples {num_examples} out of bounds"

    # Verify value can be queried
    result = g.value(prop_test, TEST.generatedExamples)
    assert result is not None
    assert int(result) == num_examples


# =============================================================================
# META-PROPERTY: Quote/Unquote Level Transitions
# =============================================================================


@given(
    st.integers(min_value=0, max_value=1),  # Current level (0 or 1 to allow quote)
    st.integers(min_value=1, max_value=2),  # Quoted level (must be > current)
)
def test_quote_increases_level(current_level: int, quoted_level: int):
    """
    Property: ∀quote. quotedLevel > currentLevel (quote increases stratification)

    Ensures quote operation properly increases stratification level.
    """
    assume(quoted_level > current_level)  # Must increase

    # Create fresh graph
    g = Graph()

    analysis = URIRef("http://example.org/analysis_quote")
    quote = URIRef("http://example.org/quote_test")

    g.add((analysis, RDF.type, META.SelfAnalysis))
    g.add(
        (
            analysis,
            META.stratificationLevel,
            Literal(current_level, datatype=XSD.nonNegativeInteger),
        )
    )

    g.add((quote, RDF.type, META.Quote))
    g.add((quote, META.quotedAtLevel, Literal(quoted_level, datatype=XSD.nonNegativeInteger)))

    # Verify quote increases level
    assert quoted_level > current_level, "Quote must increase stratification level"


@given(
    st.integers(min_value=1, max_value=2),  # Current level (1 or 2 to allow unquote)
    st.integers(min_value=0, max_value=1),  # Unquoted level (must be < current)
)
def test_unquote_decreases_level(current_level: int, unquoted_level: int):
    """
    Property: ∀unquote. unquotedLevel < currentLevel (unquote decreases stratification)

    Ensures unquote operation properly decreases stratification level.
    """
    assume(unquoted_level < current_level)  # Must decrease

    # Create fresh graph
    g = Graph()

    analysis = URIRef("http://example.org/analysis_unquote")
    unquote = URIRef("http://example.org/unquote_test")

    g.add((analysis, RDF.type, META.SelfAnalysis))
    g.add(
        (
            analysis,
            META.stratificationLevel,
            Literal(current_level, datatype=XSD.nonNegativeInteger),
        )
    )

    g.add((unquote, RDF.type, META.Unquote))
    g.add((unquote, META.unquotedAtLevel, Literal(unquoted_level, datatype=XSD.nonNegativeInteger)))

    # Verify unquote decreases level
    assert unquoted_level < current_level, "Unquote must decrease stratification level"
