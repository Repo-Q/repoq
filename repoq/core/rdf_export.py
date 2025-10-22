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


def export_ttl(
    project: Project,
    ttl_path: str,
    context_file: Optional[str] = None,
    field33_context: Optional[str] = None,
) -> None:
    """Export Project to RDF Turtle format.

    Converts project to JSON-LD, then serializes to Turtle using rdflib.

    Args:
        project: Project model to export
        ttl_path: Output file path for Turtle data
        context_file: Optional JSON-LD context file
        field33_context: Optional Field33 context file

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
) -> dict:
    """Validate Project RDF data against SHACL shapes.

    Converts project to RDF, loads SHACL shapes from directory, and validates.

    Args:
        project: Project model to validate
        shapes_dir: Directory containing .ttl/.rdf/.nt shape files
        context_file: Optional JSON-LD context file
        field33_context: Optional Field33 context file

    Returns:
        Dictionary with keys:
        - 'conforms': bool indicating validation success
        - 'report': str with validation report text

    Raises:
        RuntimeError: If pyshacl or rdflib are not installed
        OSError: If shapes directory cannot be read

    Example:
        >>> result = validate_shapes(project, "shapes/")
        >>> if not result['conforms']:
        ...     print(result['report'])
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

        result = {"conforms": bool(conforms), "report": str(report_text)}
        if conforms:
            logger.info("SHACL validation passed")
        else:
            logger.warning(f"SHACL validation failed:\n{report_text}")

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
