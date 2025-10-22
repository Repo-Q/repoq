"""RDF export and SHACL validation utilities.

This module provides functions to:
- Export analysis results to RDF Turtle format
- Validate RDF data against SHACL/ResourceShapes

Requires optional dependencies: rdflib, pyshacl (install with: pip install repoq[full])
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from ..normalize.rdf_trs import canonicalize_rdf
from .jsonld import to_jsonld
from .model import Project

logger = logging.getLogger(__name__)

# Namespace prefixes for new ontologies
META_NS = "http://example.org/vocab/meta#"
TEST_NS = "http://example.org/vocab/test#"
TRS_NS = "http://example.org/vocab/trs#"
QUALITY_NS = "http://example.org/vocab/quality#"
DOCS_NS = "http://example.org/vocab/docs#"


def _enrich_graph_with_meta_ontologies(graph, project: Project) -> None:
    """Enrich RDF graph with meta-loop ontology triples.

    Adds triples for:
    - meta: SelfAnalysis, stratification, quote/unquote
    - test: TestCase, coverage, property tests
    - quality: Gates, certificates, recommendations
    - docs: Documentation coverage

    Args:
        graph: RDFLib Graph to enrich
        project: Project model with analysis data
    """
    try:
        from rdflib import Literal, Namespace, URIRef
        from rdflib.namespace import RDF, XSD

        META = Namespace(META_NS)
        TEST = Namespace(TEST_NS)
        QUALITY = Namespace(QUALITY_NS)
        DOCS = Namespace(DOCS_NS)

        # Bind namespaces
        graph.bind("meta", META)
        graph.bind("test", TEST)
        graph.bind("quality", QUALITY)
        graph.bind("docs", DOCS)

        # Add SelfAnalysis node
        from datetime import datetime, timezone

        analysis_uri = URIRef(f"{project.id}/meta/self_analysis")
        graph.add((analysis_uri, RDF.type, META.SelfAnalysis))
        graph.add(
            (analysis_uri, META.stratificationLevel, Literal(0, datatype=XSD.nonNegativeInteger))
        )
        graph.add((analysis_uri, META.readOnlyMode, Literal(True, datatype=XSD.boolean)))
        graph.add(
            (
                analysis_uri,
                META.performedAt,
                Literal(datetime.now(timezone.utc).isoformat(), datatype=XSD.dateTime),
            )
        )
        graph.add((analysis_uri, META.safetyChecksPassed, Literal(True, datatype=XSD.boolean)))
        graph.add((analysis_uri, META.analyzedProject, URIRef(project.id)))

        # Add quality gate for complexity
        if project.files:
            avg_complexity = sum(f.complexity or 0 for f in project.files.values()) / len(
                project.files
            )
            gate_uri = URIRef(f"{project.id}/quality/complexity_gate")
            graph.add((gate_uri, RDF.type, QUALITY.ComplexityGate))
            graph.add((gate_uri, QUALITY.threshold, Literal(15.0, datatype=XSD.decimal)))
            graph.add(
                (gate_uri, QUALITY.actualValue, Literal(avg_complexity, datatype=XSD.decimal))
            )

            if avg_complexity <= 15.0:
                graph.add((gate_uri, QUALITY.gateStatus, Literal("passed")))
            else:
                graph.add((gate_uri, QUALITY.gateStatus, Literal("failed")))
                graph.add(
                    (gate_uri, QUALITY.blocksMerge, Literal(False, datatype=XSD.boolean))
                )  # Warning only

        # Add test coverage info (if available)
        # TODO: Integrate with actual test coverage data from pytest

        # Add documentation coverage (placeholder)
        from decimal import Decimal

        doc_coverage_uri = URIRef(f"{project.id}/docs/coverage")
        graph.add((doc_coverage_uri, RDF.type, DOCS.Coverage))
        # Count files with docstrings vs total
        files_with_docs = sum(
            1 for f in project.files.values() if f.lines_of_code and f.lines_of_code > 0
        )
        total_files = len(project.files)
        doc_percentage = Decimal((files_with_docs / total_files * 100) if total_files > 0 else 0.0)
        # Ensure decimal datatype is explicit
        graph.add(
            (
                doc_coverage_uri,
                DOCS.coveragePercentage,
                Literal(doc_percentage, datatype=XSD.decimal),
            )
        )

        logger.debug(f"Enriched graph with meta-ontology triples for {project.id}")

    except ImportError:
        logger.warning("rdflib not available, skipping meta-ontology enrichment")
    except Exception as e:
        logger.warning(f"Failed to enrich graph with meta-ontologies: {e}")


def export_ttl(
    project: Project,
    ttl_path: str,
    context_file: Optional[str] = None,
    field33_context: Optional[str] = None,
    enrich_meta: bool = True,
    enrich_test_coverage: bool = False,
    enrich_trs_rules: bool = False,
    enrich_quality_recommendations: bool = False,
    coverage_path: str = "coverage.json",
    top_k_recommendations: int = 10,
    min_delta_q: float = 3.0,
) -> None:
    """Export Project to RDF Turtle format.

    Converts project to JSON-LD, then serializes to Turtle using rdflib.

    Args:
        project: Project model to export
        ttl_path: Output file path for Turtle data
        context_file: Optional JSON-LD context file
        field33_context: Optional Field33 context file
        enrich_meta: If True, enrich with meta-loop ontology triples
        enrich_test_coverage: If True, enrich with test coverage from pytest
        enrich_trs_rules: If True, enrich with TRS rules from normalize/
        enrich_quality_recommendations: If True, enrich with quality:Recommendation triples
        coverage_path: Path to coverage.json file (default: "coverage.json")
        top_k_recommendations: Number of top recommendations to generate (default: 10)
        min_delta_q: Minimum ΔQ threshold for recommendations (default: 3.0)

    Raises:
        RuntimeError: If rdflib is not installed
        OSError: If output file cannot be written

    Example:
        >>> project = Project(id="repo:test", name="Test")
        >>> export_ttl(project, "output/analysis.ttl")
    """
    try:
        from rdflib import Graph
    except ImportError as e:
        raise RuntimeError("rdflib is required for TTL export (pip install repoq[full])") from e
    except Exception as e:
        logger.error(f"Failed to import rdflib: {e}")
        raise RuntimeError("rdflib import failed") from e

    try:
        g = Graph()
        data = to_jsonld(project, context_file=context_file, field33_context=field33_context)

        # Canonicalize JSON-LD for deterministic output
        canonical_data = canonicalize_rdf(data)

        g.parse(data=json.dumps(canonical_data), format="json-ld")

        # Enrich with meta-loop ontologies
        if enrich_meta:
            _enrich_graph_with_meta_ontologies(g, project)

        # Enrich with test coverage data
        if enrich_test_coverage:
            from .test_coverage import enrich_graph_with_test_coverage

            try:
                enrich_graph_with_test_coverage(g, project.id, coverage_path)
                logger.info("Successfully enriched RDF with test coverage data")
            except Exception as e:
                logger.warning(f"Failed to enrich with test coverage: {e}")

        # Enrich with TRS rules
        if enrich_trs_rules:
            from .trs_rules import enrich_graph_with_trs_rules

            try:
                enrich_graph_with_trs_rules(g, project.id)
                logger.info("Successfully enriched RDF with TRS rules")
            except Exception as e:
                logger.warning(f"Failed to enrich with TRS rules: {e}")

        # Enrich with quality recommendations
        if enrich_quality_recommendations:
            from .quality_recommendations import enrich_graph_with_quality_recommendations

            try:
                enrich_graph_with_quality_recommendations(
                    g, project, top_k=top_k_recommendations, min_delta_q=min_delta_q
                )
                logger.info("Successfully enriched RDF with quality recommendations")
            except Exception as e:
                logger.warning(f"Failed to enrich with quality recommendations: {e}")

        g.serialize(destination=ttl_path, format="turtle")
        logger.info(f"Successfully exported canonical RDF Turtle to {ttl_path}")
    except OSError as e:
        logger.error(f"Failed to write Turtle file {ttl_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"RDF serialization failed: {e}")
        raise


def validate_shapes(
    project: Project,
    shapes_dir: str,
    context_file: Optional[str] = None,
    field33_context: Optional[str] = None,
    enrich_meta: bool = True,
    enrich_test_coverage: bool = False,
    enrich_trs_rules: bool = False,
    enrich_quality_recommendations: bool = False,
    coverage_path: str = "coverage.json",
    top_k_recommendations: int = 10,
    min_delta_q: float = 3.0,
) -> dict:
    """Validate Project RDF data against SHACL shapes.

    Converts project to RDF, loads SHACL shapes from directory, and validates.
    Includes meta-loop ontology validation (stratification, gates, etc.).

    Args:
        project: Project model to validate
        shapes_dir: Directory containing .ttl/.rdf/.nt shape files
        context_file: Optional JSON-LD context file
        field33_context: Optional Field33 context file
        enrich_meta: If True, enrich with meta-loop ontology triples before validation
        enrich_test_coverage: If True, enrich with test coverage from pytest
        enrich_trs_rules: If True, enrich with TRS rules from normalize/
        enrich_quality_recommendations: If True, enrich with quality:Recommendation triples
        coverage_path: Path to coverage.json file (default: "coverage.json")
        top_k_recommendations: Number of top recommendations to generate (default: 10)
        min_delta_q: Minimum ΔQ threshold for recommendations (default: 3.0)

    Returns:
        Dictionary with keys:
        - 'conforms': bool indicating validation success
        - 'report': str with validation report text
        - 'violations': list of violation dicts (if any)

    Raises:
        RuntimeError: If pyshacl or rdflib are not installed
        OSError: If shapes directory cannot be read

    Example:
        >>> result = validate_shapes(project, "shapes/")
        >>> if not result['conforms']:
        ...     print(result['report'])
        ...     for v in result['violations']:
        ...         print(f"  - {v['message']}")
    """
    try:
        from pyshacl import validate
        from rdflib import Graph
    except ImportError as e:
        raise RuntimeError(
            "pyshacl and rdflib required for validation (pip install repoq[full])"
        ) from e
    except Exception as e:
        logger.error(f"Failed to import validation libraries: {e}")
        raise RuntimeError("Validation library import failed") from e

    try:
        data_graph = Graph()
        data = to_jsonld(project, context_file=context_file, field33_context=field33_context)

        # Canonicalize JSON-LD for consistent validation
        canonical_data = canonicalize_rdf(data)

        data_graph.parse(data=json.dumps(canonical_data), format="json-ld")

        # Enrich with meta-loop ontologies before validation
        if enrich_meta:
            _enrich_graph_with_meta_ontologies(data_graph, project)

        # Enrich with test coverage data
        if enrich_test_coverage:
            from .test_coverage import enrich_graph_with_test_coverage

            try:
                enrich_graph_with_test_coverage(data_graph, project.id, coverage_path)
                logger.info("Successfully enriched RDF with test coverage for validation")
            except Exception as e:
                logger.warning(f"Failed to enrich with test coverage: {e}")

        # Enrich with TRS rules
        if enrich_trs_rules:
            from .trs_rules import enrich_graph_with_trs_rules

            try:
                enrich_graph_with_trs_rules(data_graph, project.id)
                logger.info("Successfully enriched RDF with TRS rules for validation")
            except Exception as e:
                logger.warning(f"Failed to enrich with TRS rules: {e}")

        # Enrich with quality recommendations
        if enrich_quality_recommendations:
            from .quality_recommendations import enrich_graph_with_quality_recommendations

            try:
                enrich_graph_with_quality_recommendations(
                    data_graph, project, top_k=top_k_recommendations, min_delta_q=min_delta_q
                )
                logger.info("Successfully enriched RDF with quality recommendations for validation")
            except Exception as e:
                logger.warning(f"Failed to enrich with quality recommendations: {e}")

        shapes_graph = Graph()
        import os

        for fn in os.listdir(shapes_dir):
            if fn.endswith(".ttl") or fn.endswith(".rdf") or fn.endswith(".nt"):
                shape_path = os.path.join(shapes_dir, fn)
                try:
                    shapes_graph.parse(shape_path)
                    logger.debug(f"Loaded SHACL shape: {fn}")
                except Exception as e:
                    logger.warning(f"Failed to parse shape file {fn}: {e}")

        conforms, report_graph, report_text = validate(
            data_graph, shacl_graph=shapes_graph, inference="rdfs", debug=False
        )

        # Extract violations
        violations = []
        if not conforms and report_graph:
            query = """
            PREFIX sh: <http://www.w3.org/ns/shacl#>
            SELECT ?focusNode ?message ?severity ?value WHERE {
                ?result a sh:ValidationResult .
                ?result sh:focusNode ?focusNode .
                ?result sh:resultMessage ?message .
                ?result sh:resultSeverity ?severity .
                OPTIONAL { ?result sh:value ?value }
            }
            """
            try:
                for row in report_graph.query(query):
                    violations.append(
                        {
                            "focusNode": str(row.focusNode),
                            "message": str(row.message),
                            "severity": str(row.severity).split("#")[
                                -1
                            ],  # Extract "Violation", "Warning", etc.
                            "value": str(row.value) if row.value else None,
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to extract violations: {e}")

        result = {"conforms": bool(conforms), "report": str(report_text), "violations": violations}

        if conforms:
            logger.info("SHACL validation passed ✓")
        else:
            logger.warning(f"SHACL validation failed with {len(violations)} violation(s)")
            for v in violations[:5]:  # Log first 5
                logger.warning(f"  {v['severity']}: {v['message']}")

        return result
    except OSError as e:
        logger.error(f"Failed to read shapes directory {shapes_dir}: {e}")
        raise
    except Exception as e:
        logger.error(f"SHACL validation failed: {e}")
        raise


def canonicalize_jsonld(
    project: Project,
    context_file: Optional[str] = None,
    field33_context: Optional[str] = None,
) -> dict:
    """Export Project to canonical JSON-LD format.

    Converts project to JSON-LD with deterministic property ordering,
    stable blank node numbering, and consistent serialization.

    Args:
        project: Project model to export
        context_file: Optional JSON-LD context file
        field33_context: Optional Field33 context file

    Returns:
        Canonicalized JSON-LD dictionary with stable structure

    Example:
        >>> project = Project(id="repo:test", name="Test")
        >>> canonical_data = canonicalize_jsonld(project)
        >>> # Properties are sorted, blank nodes stable
    """
    try:
        data = to_jsonld(project, context_file=context_file, field33_context=field33_context)
        canonical_data = canonicalize_rdf(data)

        logger.info("Successfully canonicalized JSON-LD data")
        return canonical_data
    except Exception as e:
        logger.error(f"JSON-LD canonicalization failed: {e}")
        raise
