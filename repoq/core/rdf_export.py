from __future__ import annotations

import json
from typing import Optional

from .jsonld import to_jsonld
from .model import Project


def export_ttl(
    project: Project,
    ttl_path: str,
    context_file: Optional[str] = None,
    field33_context: Optional[str] = None,
) -> None:
    try:
        from rdflib import Graph
    except Exception as e:
        raise RuntimeError("rdflib is required for TTL export (pip install repoq[full])") from e

    g = Graph()
    data = to_jsonld(project, context_file=context_file, field33_context=field33_context)
    g.parse(data=json.dumps(data), format="json-ld")
    g.serialize(destination=ttl_path, format="turtle")


def validate_shapes(
    project: Project,
    shapes_dir: str,
    context_file: Optional[str] = None,
    field33_context: Optional[str] = None,
) -> dict:
    try:
        from pyshacl import validate
        from rdflib import Graph
    except Exception as e:
        raise RuntimeError(
            "pyshacl and rdflib required for validation (pip install repoq[full])"
        ) from e

    data_graph = Graph()
    data = to_jsonld(project, context_file=context_file, field33_context=field33_context)
    data_graph.parse(data=json.dumps(data), format="json-ld")

    shapes_graph = Graph()
    import os

    for fn in os.listdir(shapes_dir):
        if fn.endswith(".ttl") or fn.endswith(".rdf") or fn.endswith(".nt"):
            shapes_graph.parse(os.path.join(shapes_dir, fn))

    conforms, report_graph, report_text = validate(
        data_graph, shacl_graph=shapes_graph, inference="rdfs", debug=False
    )
    return {"conforms": bool(conforms), "report": str(report_text)}
