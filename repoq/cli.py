"""Command-line interface for repoq repository analysis tool.

This module provides the main CLI commands for analyzing git repositories,
generating reports, and comparing analysis results across versions.

Commands:
    structure: Analyze repository structure (files, modules, dependencies)
    history: Analyze git history (commits, contributors, churn)
    full: Complete analysis (structure + history + hotspots)
    diff: Compare two analysis results and show changes

The CLI is built with Typer and Rich for a beautiful terminal experience.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import typer
from rich import print
from rich.progress import Progress

from .config import AnalyzeConfig, Thresholds, load_config
from .core.model import Project
from .core.repo_loader import is_url, prepare_repo
from .logging import setup_logging
from .reporting.diff import diff_jsonld

logger = logging.getLogger(__name__)

app = typer.Typer(
    add_completion=False,
    help="""
[bold]repoq[/bold] 3.0 — Repository quality analysis with semantic ontology export.

Analyze git repositories for code quality metrics, generate reports in multiple formats
(JSON-LD, Turtle RDF, Markdown), and track quality evolution over time.
""",
)


def _infer_project_id_name(path_or_url: str) -> tuple[str, str]:
    """Infer project ID and name from repository path or URL.

    Args:
        path_or_url: Local file path or git URL (http/https/ssh)

    Returns:
        Tuple of (project_id, project_name). For URLs, both are derived from URL.
        For local paths, ID is absolute path and name is directory basename.

    Example:
        >>> _infer_project_id_name("https://github.com/user/repo.git")
        ('https://github.com/user/repo.git', 'repo')
        >>> _infer_project_id_name("./my-project")
        ('/absolute/path/to/my-project', 'my-project')
    """
    if is_url(path_or_url):
        name = path_or_url.rstrip("/").split("/")[-1].replace(".git", "")
        pid = path_or_url
    else:
        abs_path = os.path.abspath(path_or_url)
        name = os.path.basename(abs_path)
        pid = abs_path
    return pid, name


def _save_md(md: str, path: str) -> None:
    """Save markdown content to file.

    Args:
        md: Markdown content string
        path: Output file path

    Raises:
        OSError: If file cannot be written
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with output_path.open("w", encoding="utf-8") as f:
            f.write(md)
    except OSError as e:
        logger.error(f"Failed to write markdown file {path}: {e}")
        raise


def _apply_config(cfg: AnalyzeConfig, cfg_dict: dict) -> AnalyzeConfig:
    th = cfg_dict.get("thresholds") or {}
    if th:
        cfg.thresholds = Thresholds(
            complexity_high=th.get("complexity_high", cfg.thresholds.complexity_high),
            hotspot_top_n=th.get("hotspot_top_n", cfg.thresholds.hotspot_top_n),
            ownership_owner_threshold=th.get(
                "ownership_owner_threshold", cfg.thresholds.ownership_owner_threshold
            ),
            fail_on_issues=th.get("fail_on_issues", cfg.thresholds.fail_on_issues),
        )
    for k in (
        "since",
        "include_extensions",
        "exclude_globs",
        "max_files",
        "jsonld_path",
        "md_path",
        "graphs_dir",
        "branch",
        "depth",
        "hash_algo",
        "ttl_path",
        "validate_shapes",
        "shapes_dir",
        "context_file",
        "field33_context",
        "fail_on_issues",
    ):
        if k in cfg_dict and cfg_dict[k] is not None:
            setattr(cfg, k, cfg_dict[k])
    return cfg


@app.callback()
def main(
    ctx: typer.Context,
    verbose: int = typer.Option(0, "--verbose", "-v", count=True),
    config: str = typer.Option(None, "--config", help="YAML-конфиг"),
):
    setup_logging(verbose)
    ctx.obj = {"config_path": config}


@app.command()
def structure(
    repo: str = typer.Argument(..., help="Путь к локальному репо или URL"),
    output: str = typer.Option("quality.jsonld", "-o", "--output", help="JSON-LD output path"),
    md: str = typer.Option(None, "--md", help="Сгенерировать Markdown отчёт"),
    include_ext: str = typer.Option(None, "--extensions", help="Через запятую: py,js,java"),
    exclude: str = typer.Option(None, "--exclude", help="Глоб‑шаблоны исключений, через запятую"),
    max_files: int = typer.Option(
        None, "--max-files", help="Ограничить число обрабатываемых файлов"
    ),
    graphs: str = typer.Option(None, "--graphs", help="Директория для DOT/SVG графов"),
    ttl: str = typer.Option(None, "--ttl", help="Экспорт Turtle в файл"),
    validate_shapes_flag: bool = typer.Option(
        False, "--validate-shapes", help="Валидировать SHACL/ResourceShapes"
    ),
    shapes_dir: str = typer.Option(
        None, "--shapes-dir", help="Директория с *.ttl шейпами (по умолчанию встроенная)"
    ),
    context_file: str = typer.Option(None, "--context-file", help="Доп. JSON-LD контекст"),
    field33_context: str = typer.Option(
        None, "--field33-context", help="Подключить Field33 контекст"
    ),
    hash_algo: str = typer.Option(None, "--hash", help="sha1|sha256"),
):
    _run_command(
        repo,
        mode="structure",
        output=output,
        md=md,
        include_ext=include_ext,
        exclude=exclude,
        max_files=max_files,
        graphs=graphs,
        ttl=ttl,
        validate_shapes_flag=validate_shapes_flag,
        shapes_dir=shapes_dir,
        context_file=context_file,
        field33_context=field33_context,
        hash_algo=hash_algo,
    )


@app.command()
def history(
    repo: str = typer.Argument(..., help="Путь к локальному репо или URL"),
    output: str = typer.Option("quality.jsonld", "-o", "--output", help="JSON-LD output path"),
    md: str = typer.Option(None, "--md", help="Сгенерировать Markdown отчёт"),
    since: str = typer.Option(None, "--since", help="Например: '1 year ago'"),
    ttl: str = typer.Option(None, "--ttl", help="Экспорт Turtle в файл"),
    validate_shapes_flag: bool = typer.Option(
        False, "--validate-shapes", help="Валидировать SHACL/ResourceShapes"
    ),
    shapes_dir: str = typer.Option(
        None, "--shapes-dir", help="Директория с *.ttl шейпами (по умолчанию встроенная)"
    ),
    context_file: str = typer.Option(None, "--context-file", help="Доп. JSON-LD контекст"),
    field33_context: str = typer.Option(
        None, "--field33-context", help="Подключить Field33 контекст"
    ),
):
    _run_command(
        repo,
        mode="history",
        output=output,
        md=md,
        since=since,
        ttl=ttl,
        validate_shapes_flag=validate_shapes_flag,
        shapes_dir=shapes_dir,
        context_file=context_file,
        field33_context=field33_context,
    )


@app.command()
def full(
    repo: str = typer.Argument(..., help="Путь к локальному репо или URL"),
    output: str = typer.Option("quality.jsonld", "-o", "--output", help="JSON-LD output path"),
    md: str = typer.Option("quality.md", "--md", help="Сгенерировать Markdown отчёт"),
    since: str = typer.Option(None, "--since", help="Например: '1 year ago'"),
    include_ext: str = typer.Option(None, "--extensions", help="Через запятую: py,js,java"),
    exclude: str = typer.Option(None, "--exclude", help="Глоб‑шаблоны исключений, через запятую"),
    max_files: int = typer.Option(
        None, "--max-files", help="Ограничить число обрабатываемых файлов"
    ),
    graphs: str = typer.Option(None, "--graphs", help="Директория для DOT/SVG графов"),
    ttl: str = typer.Option(None, "--ttl", help="Экспорт Turtle в файл"),
    validate_shapes_flag: bool = typer.Option(
        False, "--validate-shapes", help="Валидировать SHACL/ResourceShapes"
    ),
    shapes_dir: str = typer.Option(
        None, "--shapes-dir", help="Директория с *.ttl шейпами (по умолчанию встроенная)"
    ),
    context_file: str = typer.Option(None, "--context-file", help="Доп. JSON-LD контекст"),
    field33_context: str = typer.Option(
        None, "--field33-context", help="Подключить Field33 контекст"
    ),
    fail_on_issues: str = typer.Option(
        None, "--fail-on-issues", help="[low|medium|high] — завершить с ошибкой при проблемах"
    ),
    hash_algo: str = typer.Option(None, "--hash", help="sha1|sha256"),
):
    _run_command(
        repo,
        mode="full",
        output=output,
        md=md,
        since=since,
        include_ext=include_ext,
        exclude=exclude,
        max_files=max_files,
        graphs=graphs,
        ttl=ttl,
        validate_shapes_flag=validate_shapes_flag,
        shapes_dir=shapes_dir,
        context_file=context_file,
        field33_context=field33_context,
        fail_on_issues=fail_on_issues,
        hash_algo=hash_algo,
    )


@app.command()
def diff(
    old: str = typer.Argument(...),
    new: str = typer.Argument(...),
    report: str = typer.Option(None, "--report"),
    fail_on_regress: str = typer.Option(None, "--fail-on-regress", help="[low|medium|high]"),
):
    d = diff_jsonld(old, new)
    print(d)
    if report:
        with open(report, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        print(f"[green]Diff отчёт сохранён в[/green] {report}")
    if fail_on_regress:
        if d.get("issues_added") or d.get("hotspots_growth"):
            raise typer.Exit(code=2)


def _run_command(
    repo: str,
    mode: str,
    output: str,
    md: str | None,
    since: str | None = None,
    include_ext: str | None = None,
    exclude: str | None = None,
    max_files: int | None = None,
    graphs: str | None = None,
    ttl: str | None = None,
    validate_shapes_flag: bool = False,
    shapes_dir: str | None = None,
    context_file: str | None = None,
    field33_context: str | None = None,
    fail_on_issues: str | None = None,
    hash_algo: str | None = None,
):
    try:
        ctx = typer.get_current_context()
        cfg_dict = (
            load_config(ctx.obj.get("config_path"))
            if ctx.obj and ctx.obj.get("config_path")
            else {}
        )
    except (RuntimeError, AttributeError):
        # No context available (e.g., when called programmatically)
        cfg_dict = {}

    cfg = AnalyzeConfig(
        mode=mode,
        since=since,
        jsonld_path=output,
        md_path=md,
        max_files=max_files,
        graphs_dir=graphs,
        ttl_path=ttl,
        validate_shapes=validate_shapes_flag,
        shapes_dir=shapes_dir,
        context_file=context_file,
        field33_context=field33_context,
        fail_on_issues=fail_on_issues,
        hash_algo=hash_algo,
    )
    cfg = _apply_config(cfg, cfg_dict)

    if include_ext:
        cfg.include_extensions = [
            e.strip().lstrip(".") for e in include_ext.split(",") if e.strip()
        ]
    if exclude:
        cfg.exclude_globs.extend([p.strip() for p in exclude.split(",") if p.strip()])

    pid, name = _infer_project_id_name(repo)
    project = Project(id=pid, name=name, repository_url=pid if pid.startswith("http") else None)
    repo_dir, cleanup = prepare_repo(repo, depth=cfg.depth, branch=cfg.branch)
    try:
        with Progress() as progress:
            t = progress.add_task("Анализ...", total=5 if mode == "full" else 3)
            if mode in ("structure", "full"):
                from .analyzers.ci_qm import CIQualityAnalyzer
                from .analyzers.complexity import ComplexityAnalyzer
                from .analyzers.structure import StructureAnalyzer
                from .analyzers.weakness import WeaknessAnalyzer

                StructureAnalyzer().run(project, repo_dir, cfg)
                ComplexityAnalyzer().run(project, repo_dir, cfg)
                WeaknessAnalyzer().run(project, repo_dir, cfg)
                CIQualityAnalyzer().run(project, repo_dir, cfg)
            progress.advance(t)

            if mode in ("history", "full"):
                from .analyzers.history import HistoryAnalyzer

                HistoryAnalyzer().run(project, repo_dir, cfg)
            progress.advance(t)

            if mode in ("full",):
                from .analyzers.hotspots import HotspotsAnalyzer

                HotspotsAnalyzer().run(project, repo_dir, cfg)
            progress.advance(t)

            if graphs:
                from .reporting.graphviz import export_graphs

                export_graphs(project, graphs)
            progress.advance(t)

            # Export
            from .core.jsonld import dump_jsonld

            dump_jsonld(
                project, output, context_file=cfg.context_file, field33_context=cfg.field33_context
            )
            print(f"[green]JSON‑LD сохранён в[/green] {output}")
            if md:
                from .reporting.markdown import render_markdown

                report = render_markdown(project)
                _save_md(report, md)
                print(f"[green]Markdown‑отчёт сохранён в[/green] {md}")

            if ttl:
                from .core.rdf_export import export_ttl

                export_ttl(
                    project, ttl, context_file=cfg.context_file, field33_context=cfg.field33_context
                )
                print(f"[green]TTL сохранён в[/green] {ttl}")

            if cfg.validate_shapes:
                shapes = cfg.shapes_dir or os.path.join(os.path.dirname(__file__), "shapes")
                from .core.rdf_export import validate_shapes

                res = validate_shapes(
                    project,
                    shapes,
                    context_file=cfg.context_file,
                    field33_context=cfg.field33_context,
                )
                print(f"[bold]{'✔' if res['conforms'] else '✖'} SHACL/Shapes validation[/bold]")
                print(res["report"])

            # CI: fail on issues by severity
            if cfg.fail_on_issues:
                sev_order = {"low": 1, "medium": 2, "high": 3}
                min_level = sev_order.get(cfg.fail_on_issues, 3)
                worst = 0
                for issue in project.issues.values():
                    worst = max(worst, sev_order.get(issue.severity, 1))
                if worst >= min_level:
                    print(
                        f"[red]Достигнут уровень проблем: {cfg.fail_on_issues}. Завершаем с ошибкой.[/red]"
                    )
                    raise typer.Exit(code=2)

            progress.advance(t)

    finally:
        if cleanup and os.path.isdir(cleanup):
            import shutil

            shutil.rmtree(cleanup, ignore_errors=True)


if __name__ == "__main__":
    app()
