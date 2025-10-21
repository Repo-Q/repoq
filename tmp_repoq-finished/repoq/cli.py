from __future__ import annotations
import os, json, typer
from rich import print
from rich.progress import Progress
from .logging import setup_logging
from .config import AnalyzeConfig, Thresholds, load_config
from .core.model import Project
from .core.jsonld import dump_jsonld
from .core.repo_loader import prepare_repo, is_url
from .reporting.markdown import render_markdown
from .reporting.graphviz import export_graphs
from .reporting.diff import diff_jsonld
from .core.rdf_export import export_ttl, validate_shapes

app = typer.Typer(add_completion=False, help="repoq 3.0 — Repository Quality CLI (JSON-LD, VC, ZAG)")

def _infer_project_id_name(path_or_url: str) -> tuple[str, str]:
    if is_url(path_or_url):
        name = path_or_url.rstrip('/').split('/')[-1].replace('.git',''); pid = path_or_url
    else:
        name = os.path.basename(os.path.abspath(path_or_url)); pid = os.path.abspath(path_or_url)
    return pid, name

def _save_md(md: str, path: str):
    with open(path, 'w', encoding='utf-8') as f: f.write(md)

def _apply_config(cfg: AnalyzeConfig, cfg_dict: dict) -> AnalyzeConfig:
    th = cfg_dict.get("thresholds") or {}
    if th:
        cfg.thresholds = Thresholds(
            complexity_high=th.get("complexity_high", cfg.thresholds.complexity_high),
            hotspot_top_n=th.get("hotspot_top_n", cfg.thresholds.hotspot_top_n),
            ownership_owner_threshold=th.get("ownership_owner_threshold", cfg.thresholds.ownership_owner_threshold),
            fail_on_issues=th.get("fail_on_issues", cfg.thresholds.fail_on_issues),
        )
    for k in ("since","include_extensions","exclude_globs","max_files","jsonld_path","md_path","graphs_dir","branch","depth","hash_algo","ttl_path","validate_shapes","shapes_dir","context_file","field33_context","fail_on_issues"):
        if k in cfg_dict and cfg_dict[k] is not None:
            setattr(cfg, k, cfg_dict[k])
    return cfg

@app.callback()
def main(ctx: typer.Context, verbose: int = typer.Option(0, "--verbose", "-v", count=True), config: str = typer.Option(None, "--config", help="YAML-конфиг")):
    setup_logging(verbose); ctx.obj = {"config_path": config}

def _run(repo: str, mode: str, output: str, md: str | None, since: str | None = None, include_ext: str | None = None, exclude: str | None = None, max_files: int | None = None, graphs: str | None = None, ttl: str | None = None, validate_shapes_flag: bool = False, shapes_dir: str | None = None, context_file: str | None = None, field33_context: str | None = None, fail_on_issues: str | None = None, hash_algo: str | None = None, certs: str | None = None, cert_valid_days: int = 90, cert_profile: str = "STANDARD", sign_secret: str | None = None, sign_key: str | None = None, zag_out: str | None = None, zag_level: str = "module", zag_U: str = "[0,1]", zag_aggregator: str = "min", zag_tau: float = 0.8, zag_budget: float = 1.0, zag_boundary: str | None = None, zag_kmax: int = 8, zag_validate_kit: str | None = None):
    cfg_dict = load_config(typer.get_current_context().obj.get("config_path")) if typer.get_current_context().obj else {}
    cfg = AnalyzeConfig(mode=mode, since=since, jsonld_path=output, md_path=md, max_files=max_files, graphs_dir=graphs, ttl_path=ttl, validate_shapes=validate_shapes_flag, shapes_dir=shapes_dir, context_file=context_file, field33_context=field33_context, fail_on_issues=fail_on_issues, hash_algo=hash_algo)
    cfg = _apply_config(cfg, cfg_dict)
    if include_ext: cfg.include_extensions = [e.strip().lstrip('.') for e in include_ext.split(',') if e.strip()]
    if exclude: cfg.exclude_globs.extend([p.strip() for p in exclude.split(',') if p.strip()])

    pid, name = _infer_project_id_name(repo)
    project = Project(id=pid, name=name, repository_url=pid if pid.startswith("http") else None)
    repo_dir, cleanup = prepare_repo(repo, depth=cfg.depth, branch=cfg.branch)
    try:
        with Progress() as progress:
            t = progress.add_task("Анализ...", total=6 if (mode=="full" and certs) else 5 if mode=="full" else 4)
            if mode in ("structure","full"):
                from .analyzers.structure import StructureAnalyzer
                StructureAnalyzer().run(project, repo_dir, cfg)
                from .analyzers.complexity import ComplexityAnalyzer
                ComplexityAnalyzer().run(project, repo_dir, cfg)
                from .analyzers.weakness import WeaknessAnalyzer
                WeaknessAnalyzer().run(project, repo_dir, cfg)
                from .analyzers.ci_qm import CIQualityAnalyzer
                CIQualityAnalyzer().run(project, repo_dir, cfg)
            progress.advance(t)

            if mode in ("history","full"):
                from .analyzers.history import HistoryAnalyzer
                HistoryAnalyzer().run(project, repo_dir, cfg)
            progress.advance(t)

            if mode in ("full",):
                from .analyzers.hotspots import HotspotsAnalyzer
                HotspotsAnalyzer().run(project, repo_dir, cfg)
            progress.advance(t)

            if graphs:
                try:
                    from .reporting.graphviz import export_graphs
                    export_graphs(project, graphs)
                except Exception as e:
                    print(f"[yellow]Graphviz недоступен: {e}[/yellow]")
            progress.advance(t)

            from .core.jsonld import dump_jsonld
            dump_jsonld(project, output, context_file=cfg.context_file, field33_context=cfg.field33_context)
            print(f"[green]JSON‑LD сохранён в[/green] {output}")
            if md:
                from .reporting.markdown import render_markdown
                _save_md(render_markdown(project), md)
                print(f"[green]Markdown‑отчёт сохранён в[/green] {md}")
            if ttl:
                from .core.rdf_export import export_ttl, validate_shapes
                export_ttl(project, ttl, context_file=cfg.context_file, field33_context=cfg.field33_context)
                print(f"[green]TTL сохранён в[/green] {ttl}")
                if cfg.validate_shapes:
                    shapes = cfg.shapes_dir or os.path.join(os.path.dirname(__file__), "shapes")
                    res = validate_shapes(project, shapes, context_file=cfg.context_file, field33_context=cfg.field33_context)
                    print(f"[bold]{'✔' if res['conforms'] else '✖'} SHACL/Shapes validation[/bold]")
                    print(res["report"])
            progress.advance(t)

            if certs:
                from .certs.generator import generate_certificates
                idx = generate_certificates(project, certs, issuer="did:repoq:tool", profile=cert_profile, valid_days=cert_valid_days, sign_secret=sign_secret, sign_key=sign_key)
                print(f"[green]Сертификаты выпущены в[/green] {certs}")
                # ZAG bundle
                if zag_out:
                    from .integrations.zag import write_zag_bundle
                    info = write_zag_bundle(project, zag_out, level=zag_level, U=zag_U, aggregator=zag_aggregator, tau=zag_tau, budget=zag_budget, boundary=(zag_boundary.split(',') if zag_boundary else None), kmax=zag_kmax, model_name=project.name, version='dev')
                    print(f"[green]ZAG bundle сохранён в[/green] {zag_out}")
                    if zag_validate_kit:
                        import subprocess, sys
                        man = os.path.join(zag_out, "manifest.json")
                        valid_script = os.path.join(zag_validate_kit, "tools", "zag_validate.py")
                        if os.path.exists(valid_script):
                            try:
                                pr = subprocess.run([sys.executable, valid_script, man], capture_output=True, text=True, check=False)
                                out = pr.stdout + "\n" + pr.stderr
                                verdict = "ZAG:REJECT"
                                if "ACCEPT" in out:
                                    verdict = "ZAG:ACCEPT"
                                from .certs.linker import annotate_certs_assurance
                                annotate_certs_assurance(certs, verdict)
                                print(f"[bold]ZAG verdict:[/bold] {verdict}")
                            except Exception as e:
                                print(f"[yellow]Не удалось выполнить zag_validate.py: {e}[/yellow]")
                        else:
                            print(f"[yellow]Не найден zag_validate.py в {zag_validate_kit}[/yellow]")
                # Link & pack
                try:
                    from .certs.linker import link_certs_into_jsonld
                    from .certs.pack import write_markdown_pack
                    link_certs_into_jsonld(output, certs)
                    pack_md = write_markdown_pack(certs, os.path.join(certs, "README.md"))
                    print(f"[green]Сборка сертификатов (Markdown) сохранена в[/green] {pack_md}")
                except Exception as e:
                    print(f"[yellow]Аннотация JSON-LD сертификатами не выполнена: {e}[/yellow]")

            progress.advance(t)

            if cfg.fail_on_issues:
                sev_order = {"low": 1, "medium": 2, "high": 3}
                min_level = sev_order.get(cfg.fail_on_issues, 3)
                worst = 0
                for issue in project.issues.values():
                    worst = max(worst, sev_order.get(issue.severity, 1))
                if worst >= min_level:
                    print(f"[red]Достигнут уровень проблем: {cfg.fail_on_issues}. Завершаем с ошибкой.[/red]")
                    raise typer.Exit(code=2)

    finally:
        if cleanup and os.path.isdir(cleanup):
            import shutil; shutil.rmtree(cleanup, ignore_errors=True)

@app.command()
def structure(repo: str = typer.Argument(..., help="Путь к локальному репо или URL"),
    output: str = typer.Option("quality.jsonld", "-o", "--output"),
    md: str = typer.Option(None, "--md"),
    include_ext: str = typer.Option(None, "--extensions"),
    exclude: str = typer.Option(None, "--exclude"),
    max_files: int = typer.Option(None, "--max-files"),
    graphs: str = typer.Option(None, "--graphs"),
    ttl: str = typer.Option(None, "--ttl"),
    validate_shapes_flag: bool = typer.Option(False, "--validate-shapes"),
    shapes_dir: str = typer.Option(None, "--shapes-dir"),
    context_file: str = typer.Option(None, "--context-file"),
    field33_context: str = typer.Option(None, "--field33-context"),
    hash_algo: str = typer.Option(None, "--hash"),
    certs: str = typer.Option(None, "--certs"),
    cert_valid_days: int = typer.Option(90, "--cert-valid-days"),
    cert_profile: str = typer.Option("STANDARD", "--cert-profile"),
    sign_secret: str = typer.Option(None, "--sign-secret"),
    sign_key: str = typer.Option(None, "--sign-key"),
    zag_out: str = typer.Option(None, "--zag-out"),
    zag_level: str = typer.Option("module", "--zag-level"),
    zag_U: str = typer.Option("[0,1]", "--zag-U"),
    zag_aggregator: str = typer.Option("min", "--zag-aggregator"),
    zag_tau: float = typer.Option(0.8, "--zag-tau"),
    zag_budget: float = typer.Option(1.0, "--zag-budget"),
    zag_boundary: str = typer.Option(None, "--zag-boundary"),
    zag_kmax: int = typer.Option(8, "--zag-kmax"),
    zag_validate_kit: str = typer.Option(None, "--zag-validate-kit"),
):
    _run(repo, "structure", output, md, None, include_ext, exclude, max_files, graphs, ttl, validate_shapes_flag, shapes_dir, context_file, field33_context, None, hash_algo, certs, cert_valid_days, cert_profile, sign_secret, sign_key, zag_out, zag_level, zag_U, zag_aggregator, zag_tau, zag_budget, zag_boundary, zag_kmax, zag_validate_kit)

@app.command()
def history(repo: str = typer.Argument(...), output: str = typer.Option("quality.jsonld", "-o", "--output"),
    md: str = typer.Option(None, "--md"), since: str = typer.Option(None, "--since"),
    ttl: str = typer.Option(None, "--ttl"), validate_shapes_flag: bool = typer.Option(False, "--validate-shapes"),
    shapes_dir: str = typer.Option(None, "--shapes-dir"), context_file: str = typer.Option(None, "--context-file"),
    field33_context: str = typer.Option(None, "--field33-context"),
    certs: str = typer.Option(None, "--certs"),
    cert_valid_days: int = typer.Option(90, "--cert-valid-days"),
    cert_profile: str = typer.Option("STANDARD", "--cert-profile"),
    sign_secret: str = typer.Option(None, "--sign-secret"),
    sign_key: str = typer.Option(None, "--sign-key"),
    zag_out: str = typer.Option(None, "--zag-out"),
    zag_level: str = typer.Option("module", "--zag-level"),
    zag_U: str = typer.Option("[0,1]", "--zag-U"),
    zag_aggregator: str = typer.Option("min", "--zag-aggregator"),
    zag_tau: float = typer.Option(0.8, "--zag-tau"),
    zag_budget: float = typer.Option(1.0, "--zag-budget"),
    zag_boundary: str = typer.Option(None, "--zag-boundary"),
    zag_kmax: int = typer.Option(8, "--zag-kmax"),
    zag_validate_kit: str = typer.Option(None, "--zag-validate-kit"),
):
    _run(repo, "history", output, md, since, None, None, None, None, ttl, validate_shapes_flag, shapes_dir, context_file, field33_context, None, None, certs, cert_valid_days, cert_profile, sign_secret, sign_key, zag_out, zag_level, zag_U, zag_aggregator, zag_tau, zag_budget, zag_boundary, zag_kmax, zag_validate_kit)

@app.command()
def full(repo: str = typer.Argument(...), output: str = typer.Option("quality.jsonld", "-o", "--output"),
    md: str = typer.Option("quality.md", "--md"),
    since: str = typer.Option(None, "--since"), include_ext: str = typer.Option(None, "--extensions"),
    exclude: str = typer.Option(None, "--exclude"), max_files: int = typer.Option(None, "--max-files"),
    graphs: str = typer.Option(None, "--graphs"),
    ttl: str = typer.Option(None, "--ttl"), validate_shapes_flag: bool = typer.Option(False, "--validate-shapes"),
    shapes_dir: str = typer.Option(None, "--shapes-dir"), context_file: str = typer.Option(None, "--context-file"),
    field33_context: str = typer.Option(None, "--field33-context"), fail_on_issues: str = typer.Option(None, "--fail-on-issues"),
    hash_algo: str = typer.Option(None, "--hash"),
    certs: str = typer.Option(None, "--certs"),
    cert_valid_days: int = typer.Option(90, "--cert-valid-days"),
    cert_profile: str = typer.Option("STANDARD", "--cert-profile"),
    sign_secret: str = typer.Option(None, "--sign-secret"),
    sign_key: str = typer.Option(None, "--sign-key"),
    zag_out: str = typer.Option(None, "--zag-out"),
    zag_level: str = typer.Option("module", "--zag-level"),
    zag_U: str = typer.Option("[0,1]", "--zag-U"),
    zag_aggregator: str = typer.Option("min", "--zag-aggregator"),
    zag_tau: float = typer.Option(0.8, "--zag-tau"),
    zag_budget: float = typer.Option(1.0, "--zag-budget"),
    zag_boundary: str = typer.Option(None, "--zag-boundary"),
    zag_kmax: int = typer.Option(8, "--zag-kmax"),
    zag_validate_kit: str = typer.Option(None, "--zag-validate-kit"),
):
    _run(repo, "full", output, md, since, include_ext, exclude, max_files, graphs, ttl, validate_shapes_flag, shapes_dir, context_file, field33_context, fail_on_issues, hash_algo, certs, cert_valid_days, cert_profile, sign_secret, sign_key, zag_out, zag_level, zag_U, zag_aggregator, zag_tau, zag_budget, zag_boundary, zag_kmax, zag_validate_kit)

@app.command()
def diff(old: str = typer.Argument(...), new: str = typer.Argument(...), report: str = typer.Option(None, "--report"), fail_on_regress: str = typer.Option(None, "--fail-on-regress")):
    d = diff_jsonld(old, new)
    print(d)
    if report:
        with open(report, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, indent=2)
        print(f"[green]Diff отчёт сохранён в[/green] {report}")
    if fail_on_regress and (d.get("issues_added") or d.get("hotspots_growth")):
        raise typer.Exit(code=2)

if __name__ == "__main__":
    app()
