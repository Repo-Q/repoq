"""Tests for Field33 architecture metrics integration.

Tests Field33 software_architecture_metric ontology export:
- Adaptability (cohesion)
- Reliability (1 - instability)
- PerformanceEfficiency (1 - coupling)
"""

import pytest
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF

from repoq.analyzers.architecture import (
    ArchitectureMetrics,
    ArchitectureModel,
    C4Container,
    C4Model,
    C4System,
    Component,
    export_architecture_rdf,
    export_field33_metrics,
)


@pytest.fixture
def sample_metrics():
    """Sample architecture metrics for testing."""
    return ArchitectureMetrics(
        cohesion=0.85,
        coupling=0.23,
        instability={"Core": 0.15, "CLI": 0.65, "Analyzers": 0.42},
        abstractness={"Core": 0.0, "CLI": 0.0, "Analyzers": 0.0},
        distance_from_main_sequence={"Core": 0.85, "CLI": 0.35, "Analyzers": 0.58},
    )


@pytest.fixture
def sample_arch_model(sample_metrics):
    """Sample architecture model with metrics."""
    return ArchitectureModel(
        layers=[],
        components=[
            Component(name="Core", files=["repoq/core/model.py"]),
            Component(name="CLI", files=["repoq/cli.py"]),
        ],
        layering_violations=[],
        circular_dependencies=[],
        metrics=sample_metrics,
        c4_model=C4Model(
            system=C4System(name="RepoQ", description="Test system"),
            containers=[C4Container(name="Core", technology="Python")],
        ),
    )


def test_export_field33_metrics_basic(sample_metrics):
    """Test basic Field33 metrics export."""
    graph = Graph()
    export_field33_metrics(graph, sample_metrics, "repo:test")

    # Check namespace bindings
    assert "swarch" in [prefix for prefix, _ in graph.namespaces()]
    assert "methodology" in [prefix for prefix, _ in graph.namespaces()]

    # Check metric types
    SWARCH = Namespace("http://field33.com/ontologies/@fld33_domain/software_architecture_metric/")

    adaptability_uri = URIRef("repo:test/arch/metric/adaptability")
    reliability_uri = URIRef("repo:test/arch/metric/reliability")
    performance_uri = URIRef("repo:test/arch/metric/performance_efficiency")

    assert (adaptability_uri, RDF.type, SWARCH.Adaptability) in graph
    assert (reliability_uri, RDF.type, SWARCH.Reliability) in graph
    assert (performance_uri, RDF.type, SWARCH.PerformanceEfficiency) in graph


def test_field33_adaptability_mapping(sample_metrics):
    """Test Adaptability = cohesion mapping."""
    graph = Graph()
    export_field33_metrics(graph, sample_metrics, "repo:test")

    METHODOLOGY = Namespace("http://field33.com/ontologies/@fld33/methodology/")
    adaptability_uri = URIRef("repo:test/arch/metric/adaptability")

    # Check value
    values = list(graph.objects(adaptability_uri, METHODOLOGY.value))
    assert len(values) == 1
    assert float(values[0]) == pytest.approx(0.85, rel=0.01)

    # Check unit
    units = list(graph.objects(adaptability_uri, METHODOLOGY.unit))
    assert len(units) == 1
    assert str(units[0]) == "score"


def test_field33_reliability_mapping(sample_metrics):
    """Test Reliability = 1 - instability_avg mapping."""
    graph = Graph()
    export_field33_metrics(graph, sample_metrics, "repo:test")

    METHODOLOGY = Namespace("http://field33.com/ontologies/@fld33/methodology/")
    reliability_uri = URIRef("repo:test/arch/metric/reliability")

    # Calculate expected value: 1 - avg(0.15, 0.65, 0.42) = 1 - 0.4067 = 0.5933
    instability_avg = (0.15 + 0.65 + 0.42) / 3
    expected_reliability = 1.0 - instability_avg

    values = list(graph.objects(reliability_uri, METHODOLOGY.value))
    assert len(values) == 1
    assert float(values[0]) == pytest.approx(expected_reliability, rel=0.01)


def test_field33_performance_efficiency_mapping(sample_metrics):
    """Test PerformanceEfficiency = 1 - coupling mapping."""
    graph = Graph()
    export_field33_metrics(graph, sample_metrics, "repo:test")

    METHODOLOGY = Namespace("http://field33.com/ontologies/@fld33/methodology/")
    performance_uri = URIRef("repo:test/arch/metric/performance_efficiency")

    # Calculate expected value: 1 - 0.23 = 0.77
    expected_performance = 1.0 - 0.23

    values = list(graph.objects(performance_uri, METHODOLOGY.value))
    assert len(values) == 1
    assert float(values[0]) == pytest.approx(expected_performance, rel=0.01)


def test_field33_metrics_have_timestamps(sample_metrics):
    """Test that all Field33 metrics have ISO timestamps."""
    graph = Graph()
    export_field33_metrics(graph, sample_metrics, "repo:test")

    METHODOLOGY = Namespace("http://field33.com/ontologies/@fld33/methodology/")

    metrics_uris = [
        URIRef("repo:test/arch/metric/adaptability"),
        URIRef("repo:test/arch/metric/reliability"),
        URIRef("repo:test/arch/metric/performance_efficiency"),
    ]

    for metric_uri in metrics_uris:
        timestamps = list(graph.objects(metric_uri, METHODOLOGY.timestamp))
        assert len(timestamps) == 1
        # Check ISO 8601 format (basic validation)
        # Note: RDFLib normalizes 'Z' → '+00:00' for xsd:dateTime
        timestamp_str = str(timestamps[0])
        assert "T" in timestamp_str
        assert "+00:00" in timestamp_str or "Z" in timestamp_str


def test_field33_metrics_have_descriptions(sample_metrics):
    """Test that all Field33 metrics have descriptions."""
    graph = Graph()
    export_field33_metrics(graph, sample_metrics, "repo:test")

    METHODOLOGY = Namespace("http://field33.com/ontologies/@fld33/methodology/")

    metrics_uris = [
        URIRef("repo:test/arch/metric/adaptability"),
        URIRef("repo:test/arch/metric/reliability"),
        URIRef("repo:test/arch/metric/performance_efficiency"),
    ]

    for metric_uri in metrics_uris:
        descriptions = list(graph.objects(metric_uri, METHODOLOGY.description))
        assert len(descriptions) == 1
        assert len(str(descriptions[0])) > 10  # Non-empty description


def test_field33_architecture_model_links(sample_metrics):
    """Test that Architecture model links to all metrics via swarch:hasMetric."""
    graph = Graph()
    export_field33_metrics(graph, sample_metrics, "repo:test")

    SWARCH = Namespace("http://field33.com/ontologies/@fld33_domain/software_architecture_metric/")
    arch_uri = URIRef("repo:test/arch/model")

    # Check Architecture type
    assert (arch_uri, RDF.type, SWARCH["Architecture"]) in graph

    # Check hasMetric links
    metrics = list(graph.objects(arch_uri, SWARCH.hasMetric))
    assert len(metrics) == 3

    expected_metrics = {
        URIRef("repo:test/arch/metric/adaptability"),
        URIRef("repo:test/arch/metric/reliability"),
        URIRef("repo:test/arch/metric/performance_efficiency"),
    }
    assert set(metrics) == expected_metrics


def test_field33_integration_in_export_architecture_rdf(sample_arch_model):
    """Test that Field33 metrics are exported as part of export_architecture_rdf."""
    graph = Graph()
    export_architecture_rdf(graph, sample_arch_model, "repo:test")

    # Check that Field33 metrics are present
    SWARCH = Namespace("http://field33.com/ontologies/@fld33_domain/software_architecture_metric/")

    adaptability_uri = URIRef("repo:test/arch/metric/adaptability")
    reliability_uri = URIRef("repo:test/arch/metric/reliability")
    performance_uri = URIRef("repo:test/arch/metric/performance_efficiency")

    assert (adaptability_uri, RDF.type, SWARCH.Adaptability) in graph
    assert (reliability_uri, RDF.type, SWARCH.Reliability) in graph
    assert (performance_uri, RDF.type, SWARCH.PerformanceEfficiency) in graph


def test_field33_quality_gate_adaptability():
    """Test Field33 quality gate: Adaptability > 0.7."""
    # High cohesion → pass
    high_cohesion_metrics = ArchitectureMetrics(
        cohesion=0.85,
        coupling=0.2,
        instability={},
        abstractness={},
        distance_from_main_sequence={},
    )
    graph_high = Graph()
    export_field33_metrics(graph_high, high_cohesion_metrics, "repo:test")

    METHODOLOGY = Namespace("http://field33.com/ontologies/@fld33/methodology/")
    adaptability_uri = URIRef("repo:test/arch/metric/adaptability")
    value_high = float(list(graph_high.objects(adaptability_uri, METHODOLOGY.value))[0])
    assert value_high > 0.7  # PASS gate

    # Low cohesion → fail
    low_cohesion_metrics = ArchitectureMetrics(
        cohesion=0.50,
        coupling=0.2,
        instability={},
        abstractness={},
        distance_from_main_sequence={},
    )
    graph_low = Graph()
    export_field33_metrics(graph_low, low_cohesion_metrics, "repo:test")
    value_low = float(list(graph_low.objects(adaptability_uri, METHODOLOGY.value))[0])
    assert value_low < 0.7  # FAIL gate


def test_field33_quality_gate_coupling():
    """Test Field33 quality gate: Coupling < 0.3."""
    # Low coupling → pass
    low_coupling_metrics = ArchitectureMetrics(
        cohesion=0.8,
        coupling=0.2,
        instability={},
        abstractness={},
        distance_from_main_sequence={},
    )
    graph_low = Graph()
    export_field33_metrics(graph_low, low_coupling_metrics, "repo:test")

    METHODOLOGY = Namespace("http://field33.com/ontologies/@fld33/methodology/")
    performance_uri = URIRef("repo:test/arch/metric/performance_efficiency")
    value_low_coupling = float(list(graph_low.objects(performance_uri, METHODOLOGY.value))[0])
    # PerformanceEfficiency = 1 - coupling = 1 - 0.2 = 0.8
    # Coupling < 0.3 means PerformanceEfficiency > 0.7
    assert value_low_coupling > 0.7  # PASS gate

    # High coupling → fail
    high_coupling_metrics = ArchitectureMetrics(
        cohesion=0.8,
        coupling=0.5,
        instability={},
        abstractness={},
        distance_from_main_sequence={},
    )
    graph_high = Graph()
    export_field33_metrics(graph_high, high_coupling_metrics, "repo:test")
    value_high_coupling = float(list(graph_high.objects(performance_uri, METHODOLOGY.value))[0])
    # PerformanceEfficiency = 1 - 0.5 = 0.5
    assert value_high_coupling < 0.7  # FAIL gate


def test_field33_sparql_query_example():
    """Test SPARQL query for Field33 metrics."""
    graph = Graph()
    metrics = ArchitectureMetrics(
        cohesion=0.85,
        coupling=0.23,
        instability={"Core": 0.15},
        abstractness={},
        distance_from_main_sequence={},
    )
    export_field33_metrics(graph, metrics, "repo:test")

    # SPARQL query: get all metrics with values
    query = """
    PREFIX swarch: <http://field33.com/ontologies/@fld33_domain/software_architecture_metric/>
    PREFIX methodology: <http://field33.com/ontologies/@fld33/methodology/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?metric ?type ?value
    WHERE {
        ?metric rdf:type ?type .
        ?metric methodology:value ?value .
        FILTER (
            ?type = swarch:Adaptability ||
            ?type = swarch:Reliability ||
            ?type = swarch:PerformanceEfficiency
        )
    }
    ORDER BY ?type
    """

    results = list(graph.query(query))
    assert len(results) == 3

    # Check result structure
    for row in results:
        assert row.metric is not None
        assert row.type is not None
        assert row.value is not None
        assert float(row.value) >= 0.0
        assert float(row.value) <= 1.0
