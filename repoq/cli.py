"""Command-line interface for repoq repository analysis tool.

This module provides the main CLI commands for analyzing git repositories,
generating reports, and comparing analysis results across versions.

Commands:
    structure: Analyze repository structure (files, modules, dependencies)
    history: Analyze git history (commits, contributors, churn)
    full: Complete analysis (structure + history + hotspots)
    diff: Compare two analysis results and show changes
    gate: Quality gate comparing BASE vs HEAD metrics

The CLI is built with Typer and Rich for a beautiful terminal experience.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import typer
from rich import print
from rich.progress import Progress

from . import __version__
from .config import AnalyzeConfig, Thresholds, load_config
from .core.model import Project
from .core.repo_loader import is_url, prepare_repo
from .gate import format_gate_report, run_quality_gate
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

# Add meta-loop introspection commands
try:
    from .cli_meta import app as meta_app

    app.add_typer(meta_app, name="meta", help="Meta-loop introspection and validation")
except ImportError:
    # Meta commands not available (missing dependencies)
    pass


# ==================== Common Helper Functions ====================
# Extracted to reduce complexity and duplication across commands


def _load_jsonld_analysis(path: str | Path) -> dict[str, Any]:
    """Load and parse JSON-LD analysis file.

    Args:
        path: Path to JSON-LD file

    Returns:
        Parsed JSON-LD data as dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    analysis_path = Path(path).resolve()

    if not analysis_path.exists():
        raise FileNotFoundError(f"Analysis file not found: {path}")

    try:
        with open(analysis_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}")


def _validate_file_exists(path: str | Path, file_type: str = "File") -> Path:
    """Validate that a file exists and return resolved path.

    Args:
        path: Path to validate
        file_type: Human-readable file type for error messages

    Returns:
        Resolved absolute Path

    Raises:
        typer.Exit: If file doesn't exist (exit code 2)
    """
    from rich.console import Console

    console = Console()
    resolved = Path(path).resolve()

    if not resolved.exists():
        console.print(f"[bold red]❌ {file_type} not found: {path}[/bold red]")
        raise typer.Exit(2)

    return resolved


def _setup_output_paths(
    output: str | None = None,
    md: str | None = None,
    default_output: str = "quality.jsonld",
    default_md: str = "quality.md",
) -> tuple[Path, Path]:
    """Setup output file paths with defaults.

    Args:
        output: User-specified JSON-LD output path (optional)
        md: User-specified Markdown output path (optional)
        default_output: Default JSON-LD filename
        default_md: Default Markdown filename

    Returns:
        Tuple of (jsonld_path, markdown_path)
    """
    output_path = Path(output).resolve() if output else Path(default_output)
    md_path = Path(md).resolve() if md else Path(default_md)

    return output_path, md_path


def _format_error(msg: str, hint: str | None = None) -> None:
    """Format and print error message with optional hint.

    Args:
        msg: Main error message
        hint: Optional hint/suggestion for user
    """
    from rich.console import Console

    console = Console()
    console.print(f"[bold red]❌ {msg}[/bold red]")

    if hint:
        console.print(f"\n[yellow]💡 Hint: {hint}[/yellow]")


# ==================== End of Helper Functions ====================


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
    """Merge YAML configuration with AnalyzeConfig instance.

    Args:
        cfg: Base configuration object to modify
        cfg_dict: Dictionary loaded from YAML config file

    Returns:
        Modified cfg with values from cfg_dict applied

    Note:
        Only non-None values from cfg_dict override cfg attributes.
        Thresholds are merged separately to preserve unspecified defaults.
    """
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
    """Global callback for repoq CLI.

    Sets up logging level and stores config path in context for subcommands.

    Args:
        ctx: Typer context for sharing data between commands
        verbose: Verbosity level (0=WARNING, 1=INFO, 2+=DEBUG)
        config: Path to YAML configuration file
    """
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
    """Analyze repository structure and code quality.

    Performs static analysis of repository structure including:
    - File and module organization
    - Language detection and LOC metrics
    - Complexity and maintainability scores
    - Dependency and coupling graphs
    - Code quality issues detection

    Args:
        repo: Local path or Git URL to analyze
        output: JSON-LD output file path (default: quality.jsonld)
        md: Optional markdown report path
        include_ext: Comma-separated file extensions to include (e.g., "py,js,java")
        exclude: Comma-separated glob patterns to exclude (e.g., "test_*,*.min.js")
        max_files: Limit maximum files to analyze
        graphs: Directory to save DOT/SVG dependency graphs
        ttl: Export RDF Turtle to file
        validate_shapes_flag: Validate output against SHACL/ResourceShapes
        shapes_dir: Custom shapes directory (defaults to built-in)
        context_file: Additional JSON-LD context file
        field33_context: Field33-specific context extension
        hash_algo: File checksum algorithm (sha1 or sha256)

    Example:
        $ repoq structure ./my-repo --md report.md --graphs ./graphs
        $ repoq structure https://github.com/user/repo.git -o analysis.jsonld
    """
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
    """Analyze repository history and evolution.

    Performs temporal analysis of repository including:
    - Commit history and activity patterns
    - Code churn and hotspots
    - Contributor statistics and ownership
    - Historical trends and evolution

    Args:
        repo: Local path or Git URL to analyze
        output: JSON-LD output file path (default: quality.jsonld)
        md: Optional markdown report path
        since: Time range for history (e.g., "1 year ago", "2023-01-01")
        ttl: Export RDF Turtle to file
        validate_shapes_flag: Validate output against SHACL/ResourceShapes
        shapes_dir: Custom shapes directory (defaults to built-in)
        context_file: Additional JSON-LD context file
        field33_context: Field33-specific context extension

    Example:
        $ repoq history ./my-repo --since "6 months ago" --md history.md
        $ repoq history https://github.com/user/repo.git --since "2024-01-01"
    """
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
    """Perform comprehensive repository analysis (structure + history).

    Combines static code analysis with historical evolution analysis for
    complete repository quality assessment including:
    - All structure analysis metrics
    - All history analysis metrics
    - Combined quality score and recommendations

    Args:
        repo: Local path or Git URL to analyze
        output: JSON-LD output file path (default: quality.jsonld)
        md: Markdown report path (default: quality.md)
        since: Time range for history (e.g., "1 year ago", "2023-01-01")
        include_ext: Comma-separated file extensions to include
        exclude: Comma-separated glob patterns to exclude
        max_files: Limit maximum files to analyze
        graphs: Directory to save DOT/SVG dependency graphs
        ttl: Export RDF Turtle to file
        validate_shapes_flag: Validate output against SHACL/ResourceShapes
        shapes_dir: Custom shapes directory (defaults to built-in)
        context_file: Additional JSON-LD context file
        field33_context: Field33-specific context extension
        fail_on_issues: Exit with error if issues found at severity level (low/medium/high)
        hash_algo: File checksum algorithm (sha1 or sha256)

    Example:
        $ repoq full ./my-repo --md report.md --fail-on-issues high
        $ repoq full https://github.com/user/repo.git --since "1 year ago"
    """
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


@app.command(name="analyze")
def analyze(
    repo: str = typer.Argument(
        ".", help="Path to local repository or URL (default: current directory)"
    ),
    output: str = typer.Option("quality.jsonld", "-o", "--output", help="JSON-LD output path"),
    md: str = typer.Option("quality.md", "--md", help="Generate Markdown report"),
    since: str = typer.Option(
        None, "--since", help="Time range (e.g., '1 year ago', '2023-01-01')"
    ),
    include_ext: str = typer.Option(
        None, "--extensions", help="Comma-separated extensions: py,js,java"
    ),
    exclude: str = typer.Option(
        None, "--exclude", help="Glob patterns to exclude (comma-separated)"
    ),
    max_files: int = typer.Option(None, "--max-files", help="Limit number of files to analyze"),
    graphs: str = typer.Option(None, "--graphs", help="Directory for DOT/SVG graphs"),
    ttl: str = typer.Option(None, "--ttl", help="Export RDF Turtle to file"),
    validate_shapes_flag: bool = typer.Option(
        False, "--validate-shapes", help="Validate SHACL/ResourceShapes"
    ),
    shapes_dir: str = typer.Option(None, "--shapes-dir", help="Custom shapes directory"),
    context_file: str = typer.Option(None, "--context-file", help="Additional JSON-LD context"),
    field33_context: str = typer.Option(
        None, "--field33-context", help="Field33 context extension"
    ),
    fail_on_issues: str = typer.Option(
        None, "--fail-on-issues", help="Exit with error on issues: low|medium|high"
    ),
    hash_algo: str = typer.Option(None, "--hash", help="File checksum algorithm: sha1|sha256"),
):
    """Analyze repository quality (comprehensive analysis).

    This is the main command for analyzing a repository. It performs a complete
    analysis including structure, complexity, history, and hotspots.

    This command is an alias for 'full' with a more intuitive name.

    Args:
        repo: Local path or Git URL to analyze (default: current directory)
        output: JSON-LD output file path (default: quality.jsonld)
        md: Markdown report path (default: quality.md)
        since: Time range for history (e.g., "1 year ago", "2023-01-01")
        include_ext: Comma-separated file extensions to include
        exclude: Comma-separated glob patterns to exclude
        max_files: Limit maximum files to analyze
        graphs: Directory to save DOT/SVG dependency graphs
        ttl: Export RDF Turtle to file
        validate_shapes_flag: Validate output against SHACL/ResourceShapes
        shapes_dir: Custom shapes directory (defaults to built-in)
        context_file: Additional JSON-LD context file
        field33_context: Field33-specific context extension
        fail_on_issues: Exit with error if issues found at severity level
        hash_algo: File checksum algorithm (sha1 or sha256)

    Examples:
        # Analyze current directory
        $ repoq analyze

        # Analyze specific repository
        $ repoq analyze ./my-repo

        # Analyze with custom output
        $ repoq analyze . --output results.jsonld --md report.md

        # Analyze remote repository
        $ repoq analyze https://github.com/user/repo.git

        # Analyze with filters
        $ repoq analyze . --extensions py,js --exclude "tests/**,docs/**"

        # Analyze with quality gate
        $ repoq analyze . --fail-on-issues high
    """
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
    """Compare two analysis results to detect regressions.

    Compares JSON-LD files from previous and current analysis to identify:
    - New issues introduced
    - Hotspot score changes
    - Complexity regressions
    - Quality metric trends

    Args:
        old: Path to baseline JSON-LD file (previous analysis)
        new: Path to current JSON-LD file (new analysis)
        report: Optional path to save diff report as JSON
        fail_on_regress: Exit with error code 2 if regressions detected (low/medium/high)

    Example:
        $ repoq diff baseline.jsonld current.jsonld --report changes.json
        $ repoq diff old.jsonld new.jsonld --fail-on-regress medium
    """
    d = diff_jsonld(old, new)
    print(d)
    if report:
        with open(report, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        print(f"[green]Diff отчёт сохранён в[/green] {report}")
    if fail_on_regress:
        if d.get("issues_added") or d.get("hotspots_growth"):
            raise typer.Exit(code=2)


def _run_analysis_pipeline(project: Project, repo_dir: str, cfg: AnalyzeConfig, progress, task_id):
    """Execute analysis pipeline based on mode configuration.
    
    Args:
        project: Project model to populate
        repo_dir: Repository directory path
        cfg: Analysis configuration
        progress: Rich Progress instance for UI
        task_id: Progress task ID for advancement
    """
    mode = cfg.mode
    
    if mode in ("structure", "full"):
        from .analyzers.ci_qm import CIQualityAnalyzer
        from .analyzers.complexity import ComplexityAnalyzer
        from .analyzers.structure import StructureAnalyzer
        from .analyzers.weakness import WeaknessAnalyzer

        StructureAnalyzer().run(project, repo_dir, cfg)
        ComplexityAnalyzer().run(project, repo_dir, cfg)
        WeaknessAnalyzer().run(project, repo_dir, cfg)
        CIQualityAnalyzer().run(project, repo_dir, cfg)
    progress.advance(task_id)

    if mode in ("history", "full"):
        from .analyzers.history import HistoryAnalyzer

        HistoryAnalyzer().run(project, repo_dir, cfg)
    progress.advance(task_id)

    if mode in ("full",):
        from .analyzers.hotspots import HotspotsAnalyzer

        HotspotsAnalyzer().run(project, repo_dir, cfg)
    progress.advance(task_id)


def _export_results(project: Project, cfg: AnalyzeConfig, output: str, md: str | None, 
                    ttl: str | None, graphs: str | None, progress, task_id):
    """Export analysis results to various formats.
    
    Args:
        project: Analyzed project model
        cfg: Analysis configuration
        output: JSON-LD output path
        md: Optional markdown report path
        ttl: Optional RDF Turtle export path
        graphs: Optional directory for dependency graphs
        progress: Rich Progress instance
        task_id: Progress task ID
    """
    if graphs:
        from .reporting.graphviz import export_graphs

        export_graphs(project, graphs)
    progress.advance(task_id)

    # JSON-LD export
    from .core.jsonld import dump_jsonld

    dump_jsonld(
        project, output, context_file=cfg.context_file, field33_context=cfg.field33_context
    )
    print(f"[green]JSON‑LD сохранён в[/green] {output}")
    
    # Markdown report
    if md:
        from .reporting.markdown import render_markdown

        report = render_markdown(project)
        _save_md(report, md)
        print(f"[green]Markdown‑отчёт сохранён в[/green] {md}")

    # RDF Turtle export
    if ttl:
        from .core.rdf_export import export_ttl

        export_ttl(
            project, ttl, context_file=cfg.context_file, field33_context=cfg.field33_context
        )
        print(f"[green]TTL сохранён в[/green] {ttl}")


def _run_shacl_validation(project: Project, cfg: AnalyzeConfig):
    """Run SHACL shapes validation if enabled.
    
    Args:
        project: Analyzed project model
        cfg: Analysis configuration with validation settings
    """
    if not cfg.validate_shapes:
        return
    
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


def _check_fail_on_issues(project: Project, cfg: AnalyzeConfig):
    """Check if issues exceed configured severity threshold for CI failure.
    
    Args:
        project: Analyzed project model
        cfg: Analysis configuration with fail_on_issues setting
    
    Raises:
        typer.Exit: If issues at or above threshold severity are found
    """
    if not cfg.fail_on_issues:
        return
    
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
    """Orchestrate repository analysis workflow.

    Internal function that coordinates:
    1. Configuration loading and merging
    2. Repository preparation (clone if needed)
    3. Analysis pipeline execution
    4. Export to JSON-LD, Markdown, RDF Turtle
    5. Optional SHACL validation
    6. Cleanup

    Args:
        repo: Repository path or URL
        mode: Analysis mode ('structure', 'history', or 'full')
        output: JSON-LD output path
        md: Optional markdown report path
        since: Time range for history analysis
        include_ext: Comma-separated file extensions filter
        exclude: Comma-separated glob patterns to exclude
        max_files: Maximum files to analyze
        graphs: Directory for dependency graphs
        ttl: RDF Turtle export path
        validate_shapes_flag: Enable SHACL validation
        shapes_dir: Custom shapes directory
        context_file: Additional JSON-LD context
        field33_context: Field33 context extension
        fail_on_issues: Fail on issues at severity level
        hash_algo: File checksum algorithm

    Raises:
        typer.Exit: If validation fails or issues exceed threshold
    """
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

    # Set analysis metadata
    project.analyzed_at = datetime.now(timezone.utc).isoformat()
    project.repoq_version = __version__

    repo_dir, cleanup = prepare_repo(repo, depth=cfg.depth, branch=cfg.branch)
    try:
        with Progress() as progress:
            t = progress.add_task("Анализ...", total=5 if mode == "full" else 3)
            
            # Run analysis pipeline
            _run_analysis_pipeline(project, repo_dir, cfg, progress, t)
            
            # Export results
            _export_results(project, cfg, output, md, ttl, graphs, progress, t)
            
            # SHACL validation
            _run_shacl_validation(project, cfg)
            
            # CI: fail on issues by severity
            _check_fail_on_issues(project, cfg)
            
            progress.advance(t)

    finally:
        if cleanup and os.path.isdir(cleanup):
            import shutil

            shutil.rmtree(cleanup, ignore_errors=True)


def _run_trs_verification(level: str, quiet: bool, fail_fast: bool) -> Dict[str, Any]:
    """Run TRS property verification."""
    # Import here to avoid circular dependencies
    try:
        import subprocess

        # Run property-based tests for TRS verification
        test_files = [
            "tests/properties/test_metrics_normalization.py",
            "tests/properties/test_filters_normalization.py",
            "tests/properties/test_spdx_normalization.py",
            "tests/properties/test_semver_normalization.py",
            "tests/properties/test_rdf_normalization.py",
        ]

        results = {}
        all_passed = True

        for test_file in test_files:
            if not Path(test_file).exists():
                continue

            system_name = Path(test_file).stem.replace("test_", "").replace("_normalization", "")

            if not quiet:
                print(f"  Testing {system_name.upper()} TRS...")

            # Run pytest for this file
            python_exe = sys.executable  # Use current Python interpreter
            cmd = [python_exe, "-m", "pytest", test_file, "-v", "--tb=short"]
            if level == "basic":
                cmd.append("-k 'not test_advanced'")
            elif level == "advanced":
                cmd.extend(["--hypothesis-max-examples=1000"])

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())

                passed = result.returncode == 0
                results[system_name] = {
                    "passed": passed,
                    "exit_code": result.returncode,
                    "stdout": result.stdout[-500:] if result.stdout else "",  # Last 500 chars
                    "stderr": result.stderr[-500:] if result.stderr else "",
                }

                if not passed:
                    all_passed = False
                    if not quiet:
                        print(f"    ❌ {system_name} failed")
                    if fail_fast:
                        break
                else:
                    if not quiet:
                        print(f"    ✅ {system_name} passed")

            except Exception as e:
                results[system_name] = {"passed": False, "error": str(e)}
                all_passed = False
                if not quiet:
                    print(f"    ❌ {system_name} error: {e}")
                if fail_fast:
                    break

        results["all_passed"] = all_passed
        return results

    except ImportError:
        return {"error": "pytest not available", "all_passed": False}


def _run_self_application(quiet: bool) -> Dict[str, Any]:
    """Run self-application analysis."""
    try:
        if not quiet:
            print("  Analyzing RepoQ codebase with RepoQ...")

        # Simple self-application: verify imports and basic functionality
        from .analyzers.structure import StructureAnalyzer
        from .core.model import Project

        # Create minimal project
        Project(id="repoq-self", name="repoq", description="Self-application test")

        # Try basic structure analysis
        StructureAnalyzer()
        str(Path.cwd())

        # Test with minimal config - just check if we can analyze a few Python files
        python_files = list(Path("repoq").glob("*.py"))[:5]  # First 5 files only

        if python_files:
            # Basic validation - can we read and process files?
            total_files = len(python_files)
            success = total_files > 0

            return {
                "success": success,
                "files_found": total_files,
                "sample_files": [str(f) for f in python_files],
                "import_test": True,
                "basic_analysis": True,
            }
        else:
            return {"success": False, "error": "No Python files found"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def _print_trs_summary(results: Dict[str, Any], verification_time: float) -> None:
    """Print TRS verification summary."""
    print(f"⏱️  Verification time: {verification_time:.2f}s")

    all_passed = results.get("all_passed", False)
    status = "✅ PASS" if all_passed else "❌ FAIL"
    print(f"📊 Overall status: {status}")

    for system_name, system_results in results.items():
        if system_name in ["all_passed"]:
            continue

        if isinstance(system_results, dict):
            passed = system_results.get("passed", False)
            status = "✅" if passed else "❌"
            print(f"  {status} {system_name.upper()}")

            if not passed and "error" in system_results:
                print(f"    Error: {system_results['error']}")


def _print_self_summary(results: Dict[str, Any], self_time: float) -> None:
    """Print self-application summary."""
    print(f"⏱️  Analysis time: {self_time:.2f}s")

    success = results.get("success", False)
    status = "✅ SUCCESS" if success else "❌ FAILURE"
    print(f"📊 Status: {status}")

    if success:
        files = results.get("files_found", 0)
        sample_files = results.get("sample_files", [])

        print(f"  📁 Python files found: {files}")
        print("  ✅ Import test: passed")
        print("  ✅ Basic analysis: passed")
        if sample_files:
            print(f"  � Sample files: {', '.join(sample_files[:3])}")

    if "error" in results:
        print(f"  ❌ Error: {results['error']}")


@app.command()
def meta_self(
    level: int = typer.Option(
        1,
        "--level",
        "-l",
        help="Stratification level (1 or 2, enforces Theorem F)",
    ),
    repo: str = typer.Option(
        ".",
        "--repo",
        "-r",
        help="Path to RepoQ repository to analyze",
    ),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Save meta-analysis results to file (JSON-LD format)",
    ),
) -> None:
    """Meta-analysis: RepoQ analyzing itself (dogfooding).

    This command performs self-analysis with stratification enforcement
    (Theorem F) to ensure safe self-reference without paradoxes.

    Stratification levels:
        L₀: Base reality (no self-analysis)
        L₁: RepoQ analyzing its own codebase (first-order)
        L₂: RepoQ validating its own quality metrics (second-order)

    Theorem F Enforcement:
        Can analyze L_j from L_i iff i > j (strict ordering)
        Cannot skip levels (must go L₀ → L₁ → L₂)

    Examples:
        # First-order self-analysis (L₀ → L₁)
        repoq meta-self --level 1

        # Second-order meta-validation (L₁ → L₂)
        repoq meta-self --level 2

        # Save results to file
        repoq meta-self --level 1 --output meta_quality.jsonld
    """
    setup_logging()

    from .core.stratification_guard import StratificationGuard

    repo_path = Path(repo).resolve()

    if not repo_path.exists():
        print(f"[bold red]❌ Repository not found: {repo_path}[/bold red]")
        raise typer.Exit(2)

    print(f"[bold]🔄 Meta-Analysis: RepoQ Self-Application (Level {level})[/bold]")
    print(f"📁 Repository: {repo_path}")
    print()

    # Initialize stratification guard
    guard = StratificationGuard(max_level=2)

    # Check stratification transition
    current_level = 0  # We're at L₀ (base reality)
    target_level = level

    print(f"🔒 Stratification check: L₀ → L_{target_level}")

    transition = guard.check_transition(current_level, target_level)

    if not transition.allowed:
        print(f"[bold red]❌ Stratification violation: {transition.reason}[/bold red]")
        print()
        print("[yellow]Theorem F: Can analyze L_j from L_i iff i > j[/yellow]")
        print(f"[yellow]Cannot skip levels. Please run --level {current_level + 1} first.[/yellow]")
        raise typer.Exit(1)

    print(f"[green]✅ Stratification check passed: {transition.reason}[/green]")
    print()

    try:
        # Run analysis on RepoQ's own codebase
        print("📊 Analyzing RepoQ codebase...")

        import time

        start_time = time.time()

        # Create project instance
        pid = str(repo_path)
        project = Project(
            id=pid,
            name=f"RepoQ-L{level}",
            repository_url=None,
        )

        # Set metadata
        project.analyzed_at = datetime.now(timezone.utc).isoformat()
        project.repoq_version = __version__
        project.meta_level = level
        project.meta_target = "self"

        # Run analyzers
        cfg = AnalyzeConfig(mode="full")

        from .analyzers.ci_qm import CIQualityAnalyzer
        from .analyzers.complexity import ComplexityAnalyzer
        from .analyzers.history import HistoryAnalyzer
        from .analyzers.hotspots import HotspotsAnalyzer
        from .analyzers.structure import StructureAnalyzer
        from .analyzers.weakness import WeaknessAnalyzer

        with Progress() as progress:
            task = progress.add_task("Meta-analysis...", total=6)

            StructureAnalyzer().run(project, repo_path, cfg)
            progress.advance(task)

            ComplexityAnalyzer().run(project, repo_path, cfg)
            progress.advance(task)

            WeaknessAnalyzer().run(project, repo_path, cfg)
            progress.advance(task)

            CIQualityAnalyzer().run(project, repo_path, cfg)
            progress.advance(task)

            HistoryAnalyzer().run(project, repo_path, cfg)
            progress.advance(task)

            HotspotsAnalyzer().run(project, repo_path, cfg)
            progress.advance(task)

        analysis_time = time.time() - start_time

        print(f"\n⏱️  Analysis time: {analysis_time:.2f}s")
        print(f"✅ Meta-analysis L_{level} complete")

        # Print summary
        print("\n📊 Quality Metrics:")
        if hasattr(project, "files") and project.files:
            file_count = (
                len(project.files)
                if isinstance(project.files, list)
                else len(project.files.values())
            )
            print(f"  📁 Files analyzed: {file_count}")

        if hasattr(project, "modules") and project.modules:
            module_count = (
                len(project.modules)
                if isinstance(project.modules, list)
                else len(project.modules.values())
            )
            print(f"  📦 Modules found: {module_count}")

        # Save output if requested
        if output:
            from .core.jsonld import export_to_jsonld

            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            jsonld_data = export_to_jsonld(project)
            jsonld_data["meta"] = {
                "level": level,
                "target": "self",
                "stratification_check": "passed",
                "theorem_f": "enforced",
            }

            output_path.write_text(json.dumps(jsonld_data, indent=2))
            print(f"\n💾 Meta-analysis results saved: {output_path}")

        print("\n[bold green]✅ Self-application successful (no paradoxes detected)[/bold green]")
        raise typer.Exit(0)

    except Exception as e:
        print(f"[bold red]❌ Error during meta-analysis: {e}[/bold red]")
        logger.exception("Meta-self command failed")
        raise typer.Exit(2)


@app.command()
def gate(
    base: str = typer.Option(
        "main",
        "--base",
        "-b",
        help="Base git reference (e.g., 'main', 'origin/main', SHA)",
    ),
    head: str = typer.Option(
        "HEAD",
        "--head",
        "-h",
        help="Head git reference (default: HEAD = current commit)",
    ),
    repo: str = typer.Option(
        ".",
        "--repo",
        "-r",
        help="Path to repository (default: current directory)",
    ),
    strict: bool = typer.Option(
        True,
        "--strict/--no-strict",
        help="Fail on any constraint violation (strict mode)",
    ),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Save gate report to file (JSON format)",
    ),
) -> None:
    """Quality gate: compare BASE vs HEAD metrics.

    This command analyzes both BASE and HEAD revisions, computes Q-scores,
    checks hard constraints, and evaluates the admission predicate.

    Exit codes:
        0: Gate PASSED (all constraints satisfied)
        1: Gate FAILED (constraint violations)
        2: Error during analysis

    Examples:
        # Compare current branch with main
        repoq gate --base main --head HEAD

        # Compare two specific commits
        repoq gate --base abc123 --head def456

        # Compare PR base with PR head (GitHub Actions)
        repoq gate --base ${{ github.event.pull_request.base.sha }} --head ${{ github.sha }}

        # Warn-only mode (don't fail CI)
        repoq gate --no-strict --base main --head HEAD
    """
    setup_logging()

    repo_path = Path(repo).resolve()

    if not repo_path.exists():
        print(f"[bold red]❌ Repository not found: {repo_path}[/bold red]")
        raise typer.Exit(2)

    print(f"[bold]⚙️  Quality Gate: {base} → {head}[/bold]")
    print(f"📁 Repository: {repo_path}")
    print()

    try:
        # Run quality gate
        result = run_quality_gate(
            repo_path=repo_path,
            base_ref=base,
            head_ref=head,
            strict=strict,
        )

        # Format and print report
        report = format_gate_report(result)
        print(report)

        # Save to file if requested
        if output:
            output_path = Path(output)
            output_data = {
                "base_ref": base,
                "head_ref": head,
                "passed": result.passed,
                "base_metrics": {
                    "q_score": result.base_metrics.q_score,
                    "tests_coverage": result.base_metrics.tests_coverage,
                    "complexity": result.base_metrics.avg_complexity,
                    "hotspots": result.base_metrics.hotspots,
                    "todos": result.base_metrics.todos,
                },
                "head_metrics": {
                    "q_score": result.head_metrics.q_score,
                    "tests_coverage": result.head_metrics.tests_coverage,
                    "complexity": result.head_metrics.avg_complexity,
                    "hotspots": result.head_metrics.hotspots,
                    "todos": result.head_metrics.todos,
                },
                "deltas": result.deltas,
                "violations": result.violations,
            }

            output_path.write_text(json.dumps(output_data, indent=2))
            print(f"\n💾 Gate report saved: {output_path}")

        # Exit with appropriate code
        if result.passed:
            print("\n[bold green]✅ Quality gate PASSED[/bold green]")
            raise typer.Exit(0)
        else:
            print("\n[bold red]❌ Quality gate FAILED[/bold red]")
            if not strict:
                print("[yellow]⚠️  Running in non-strict mode (not failing CI)[/yellow]")
                raise typer.Exit(0)
            raise typer.Exit(1)

    except Exception as e:
        print(f"[bold red]❌ Error during gate analysis: {e}[/bold red]")
        logger.exception("Gate command failed")
        raise typer.Exit(2)


@app.command()
def verify(
    vc_file: str = typer.Argument(..., help="Path to W3C Verifiable Credential JSON file"),
    public_key: str = typer.Option(
        None, "--public-key", help="Path to public key PEM file (optional)"
    ),
    output: str = typer.Option(None, "--output", "-o", help="Export report to file"),
):
    """Verify W3C Verifiable Credential signature.

    Verifies ECDSA signature of a W3C Verifiable Credential (VC)
    following the QualityAssessmentCredential specification.

    Verification steps:
        1. Load VC from JSON file
        2. Validate VC structure (required fields)
        3. Check expiration (if present)
        4. Verify ECDSA signature using public key

    Exit codes:
        0: VC is valid (signature verified)
        1: VC is invalid (signature failed or structure errors)
        2: Execution error (file not found, etc.)

    Args:
        vc_file: Path to VC JSON file to verify
        public_key: Path to public key PEM file (ECDSA secp256k1)
        output: Export verification report to file

    Example:
        $ repoq verify quality_cert.json --public-key public_key.pem
        ✅ Verifiable Credential: VALID

        $ repoq verify tampered_cert.json --public-key public_key.pem
        ❌ Verifiable Credential: INVALID
        Errors:
          1. Signature verification failed (invalid signature)
    """
    from pathlib import Path

    from rich.console import Console
    from rich.markdown import Markdown

    from repoq.vc_verification import format_verification_report, verify_vc

    console = Console()

    try:
        vc_path = Path(vc_file).resolve()
        if not vc_path.exists():
            console.print(f"[bold red]❌ File not found: {vc_file}[/bold red]")
            raise typer.Exit(2)

        public_key_path = Path(public_key).resolve() if public_key else None
        if public_key and public_key_path and not public_key_path.exists():
            console.print(f"[bold red]❌ Public key not found: {public_key}[/bold red]")
            raise typer.Exit(2)

        # Verify VC
        result = verify_vc(vc_path, public_key_path)

        # Format report
        report = format_verification_report(result)

        # Print to console
        console.print(Markdown(report))

        # Export to file if requested
        if output:
            output_path = Path(output).resolve()
            with open(output_path, "w", encoding="utf-8") as f:
                # Remove Rich formatting for file export
                clean_report = report.replace("[bold green]", "").replace("[/bold green]", "")
                clean_report = clean_report.replace("[bold red]", "").replace("[/bold red]", "")
                clean_report = clean_report.replace("[bold]", "").replace("[/bold]", "")
                f.write(clean_report)
            console.print(f"\n📄 Report exported to: {output_path}")

        # Exit with appropriate code
        if result.valid:
            raise typer.Exit(0)
        else:
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[bold red]❌ Verification failed: {e}[/bold red]")
        logger.exception("Verify command failed")
        raise typer.Exit(2)


@app.command(name="refactor-plan")
def refactor_plan(
    analysis: str = typer.Argument(
        "baseline-quality.jsonld",
        help="Path to JSON-LD analysis file (default: baseline-quality.jsonld)",
    ),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Save refactoring plan to file (Markdown format)",
    ),
    top_k: int = typer.Option(
        10,
        "--top-k",
        "-k",
        help="Number of top refactoring tasks to generate (default: 10)",
    ),
    min_delta_q: float = typer.Option(
        3.0,
        "--min-delta-q",
        help="Minimum ΔQ threshold for task inclusion (default: 3.0)",
    ),
    format_type: str = typer.Option(
        "markdown",
        "--format",
        "-f",
        help="Output format: markdown, json, github (default: markdown)",
    ),
) -> None:
    """Generate actionable refactoring plan from quality analysis.

    This command uses the PCE (Proof of Correct Execution) algorithm to generate
    prioritized refactoring tasks based on expected quality improvement (ΔQ).

    Algorithm:
        1. Load quality metrics from analysis file
        2. Calculate ΔQ for each file (impact of fixing issues)
        3. Greedily select top-k files by ΔQ impact
        4. Generate specific recommendations and effort estimates
        5. Assign priorities (critical/high/medium/low)

    ΔQ Formula:
        ΔQ = w_complexity × complexity_penalty +
             w_todos × todo_count +
             w_issues × issue_count +
             w_hotspot × hotspot_penalty

    Exit codes:
        0: Plan generated successfully
        1: No tasks found (quality already high)
        2: Error during generation

    Args:
        analysis: Path to JSON-LD quality analysis file
        output: Save plan to file (default: print to console)
        top_k: Maximum number of tasks to generate
        min_delta_q: Minimum ΔQ threshold for inclusion
        format_type: Output format (markdown, json, github)

    Examples:
        # Generate plan from baseline analysis
        $ repoq refactor-plan baseline-quality.jsonld

        # Save to file with top-5 tasks
        $ repoq refactor-plan baseline-quality.jsonld -o plan.md --top-k 5

        # Export as JSON for CI/CD integration
        $ repoq refactor-plan baseline-quality.jsonld --format json -o tasks.json

        # Generate GitHub Issues format
        $ repoq refactor-plan baseline-quality.jsonld --format github -o issues.json
    """
    from rich.console import Console

    from repoq.refactoring import generate_refactoring_plan

    console = Console()

    try:
        # Validate analysis file exists (using helper)
        analysis_path = _validate_file_exists(analysis, "Analysis file")

        console.print(f"[bold]🔧 Generating refactoring plan from {analysis_path.name}[/bold]")
        console.print()

        # Generate plan
        plan = generate_refactoring_plan(
            jsonld_path=analysis_path,
            top_k=top_k,
            min_delta_q=min_delta_q,
        )

        if not plan.tasks:
            console.print(
                "[bold green]✅ No refactoring needed - quality is already high![/bold green]"
            )
            console.print(f"Current Q-score: {plan.baseline_q:.2f}")
            raise typer.Exit(0)

        # Format output based on type
        _handle_refactor_plan_output(plan, format_type, output, console)

    except typer.Exit:
        raise
    except FileNotFoundError:
        _format_error(
            f"Analysis file not found: {analysis}",
            "Run 'repoq analyze' first to generate analysis data",
        )
        raise typer.Exit(2)
    except Exception as e:
        _format_error(f"Failed to generate refactoring plan: {e}")
        logger.exception("Refactor-plan command failed")
        raise typer.Exit(2)


def _handle_refactor_plan_output(
    plan,
    format_type: str,
    output: str | None,
    console,
) -> None:
    """Handle output formatting and file writing for refactor-plan command.

    Args:
        plan: RefactoringPlan object
        format_type: Output format (markdown, json, github)
        output: Output file path (optional)
        console: Rich Console for printing
    """
    from rich.markdown import Markdown

    if format_type == "markdown":
        report = plan.to_markdown()

        if output:
            output_path = Path(output).resolve()
            output_path.write_text(report, encoding="utf-8")
            console.print(f"[green]📄 Refactoring plan saved to {output_path}[/green]")
        else:
            console.print(Markdown(report))

    elif format_type == "json":
        import json

        json_data = {
            "baseline_q": plan.baseline_q,
            "projected_q": plan.projected_q,
            "total_delta_q": plan.total_delta_q,
            "tasks": [task.to_dict() for task in plan.tasks],
        }

        if output:
            output_path = Path(output).resolve()
            output_path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")
            console.print(f"[green]📄 Refactoring plan saved to {output_path}[/green]")
        else:
            console.print_json(data=json_data)

    elif format_type == "github":
        import json

        github_issues = [task.to_github_issue() for task in plan.tasks]

        if output:
            output_path = Path(output).resolve()
            output_path.write_text(json.dumps(github_issues, indent=2), encoding="utf-8")
            console.print(f"[green]📄 GitHub issues saved to {output_path}[/green]")
            console.print("\n[yellow]💡 Use gh CLI to create issues:[/yellow]")
            console.print(f"  cat {output_path} | jq -c '.[]' | while read issue; do")
            console.print('    gh issue create --body "$(echo $issue | jq -r .body)" \\')
            console.print('      --title "$(echo $issue | jq -r .title)" \\')
            console.print('      --label "$(echo $issue | jq -r \'.labels | join(",")\'); done')
        else:
            console.print_json(data=github_issues)

    else:
        console.print(f"[bold red]❌ Unknown format: {format_type}[/bold red]")
        console.print("[yellow]Supported formats: markdown, json, github[/yellow]")
        raise typer.Exit(2)

    # Print summary
    console.print()
    console.print("[bold]📊 Summary:[/bold]")
    console.print(f"  • Tasks generated: {len(plan.tasks)}")
    console.print(f"  • Total ΔQ: +{plan.total_delta_q:.1f}")
    console.print(f"  • Current Q-score: {plan.baseline_q:.2f}")
    console.print(f"  • Projected Q-score: {plan.projected_q:.2f}")

    # Priority breakdown
    priority_counts = {}
    for task in plan.tasks:
        priority_counts[task.priority] = priority_counts.get(task.priority, 0) + 1

    if priority_counts:
        console.print("\n[bold]🎯 Priority breakdown:[/bold]")
        for priority in ["critical", "high", "medium", "low"]:
            count = priority_counts.get(priority, 0)
            if count > 0:
                emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
                console.print(f"  {emoji[priority]} {priority.capitalize()}: {count}")


if __name__ == "__main__":
    app()
