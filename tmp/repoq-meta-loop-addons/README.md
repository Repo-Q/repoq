# RepoQ Meta-Quality Add-on

This pack provides:
- docs/META_QUALITY.md — concept + how-to
- ontologies/ — minimal Code/C4/DDD + JSON-LD context + mappings
- shapes/meta_loop.ttl — SHACL policies (self-analysis guard, certs)
- trs/*.json — TRS rule sets + repoq/trs/engine.py
- repoq/cli_meta.py — CLI add-ons (meta-self, trs-verify, infer-ontology)
- tests/* — sample tests

## Merge steps
1. Copy folders into your repo root, or vendor as a submodule.
2. Add `ontologies/meta_context.jsonld` to your JSON-LD output context chain.
3. Run SHACL over your meta JSON-LD to enforce self-analysis policy.
4. (Optional) Hook `repoq/cli_meta.py` into your main CLI (Typer app) or run standalone.
