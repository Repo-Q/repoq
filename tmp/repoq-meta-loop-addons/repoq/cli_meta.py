from __future__ import annotations
import os, json, typer
from rich import print

app = typer.Typer(add_completion=False, help="RepoQ Meta CLI (self-analysis, TRS, inference)")

@app.command()
def meta_self(level: int = typer.Option(2, "--level"),
              out: str = typer.Option("out/meta_quality.jsonld", "--out")):
    if level > 2:
        print("[red]Level > 2 is not allowed for self-analysis[/red]"); raise typer.Exit(2)
    # Dummy JSON-LD output for demonstration
    data = {"@context": "ontologies/meta_context.jsonld", "@type": "mq:SelfAnalysisResult", "mq:level": level, "mq:analyzeTarget": "mq:Self"}
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[green]Self-analysis (level={level}) emitted[/green] {out}")

@app.command()
def trs_verify(rules_dir: str = typer.Argument("trs")):
    from .trs.engine import TRSEngine
    ok = True
    for fn in os.listdir(rules_dir):
        if fn.endswith('.json'):
            try:
                TRSEngine.load(os.path.join(rules_dir, fn))
                print(f"[green]Loaded rules:[/green] {fn}")
            except Exception as e:
                ok = False; print(f"[red]Failed:[/red] {fn} — {e}")
    if not ok: raise typer.Exit(2)

@app.command()
def infer_ontology(src_jsonld: str = typer.Argument("out/quality.jsonld"),
                   construct_path: str = typer.Option("sparql/inference_construct.rq", "--construct")):
    # Placeholder: in production use RDFLib/Jena
    print(f"Would run SPARQL CONSTRUCT on {src_jsonld} with {construct_path}")

if __name__ == "__main__":
    app()
