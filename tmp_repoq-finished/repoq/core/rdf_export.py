from __future__ import annotations
import json, os
from typing import Optional

def export_ttl(project, ttl_path: str, *, context_file: Optional[str]=None, field33_context: Optional[str]=None):
    try:
        import rdflib
    except Exception as e:
        raise RuntimeError("Install repoq[full] to export TTL") from e
    from .jsonld import dump_jsonld
    tmp = ttl_path + ".jsonld"
    dump_jsonld(project, tmp, context_file=context_file, field33_context=field33_context)
    g = rdflib.Graph()
    g.parse(tmp, format="json-ld")
    g.serialize(destination=ttl_path, format="turtle")
    os.remove(tmp)

def validate_shapes(project, shapes_dir: str, *, context_file: Optional[str]=None, field33_context: Optional[str]=None):
    from pyshacl import validate
    import rdflib, os, json
    from .jsonld import dump_jsonld
    tmp = "tmp_validate.jsonld"
    dump_jsonld(project, tmp, context_file=context_file, field33_context=field33_context)
    data_g = rdflib.Graph().parse(tmp, format="json-ld")
    sh_g = rdflib.Graph()
    for root,_,files in os.walk(shapes_dir):
        for fn in files:
            if fn.endswith(".ttl"):
                sh_g.parse(os.path.join(root, fn), format="turtle")
    conforms, results_graph, results_text = validate(data_g, shacl_graph=sh_g, inference="rdfs", debug=False)
    os.remove(tmp)
    return {"conforms": bool(conforms), "report": results_text}
