"""
Meta-loop introspection and validation commands.

Commands:
- meta-inspect: Inspect meta-loop safety properties
- validate-ontology: Validate ontology against SHACL shapes
"""

from pathlib import Path
from typing import Optional

import typer
from pyshacl import validate as shacl_validate
from rdflib import Graph
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Meta-loop introspection and validation")
console = Console()

# Paths
ONTOLOGY_DIR = Path(__file__).parent / "ontologies"
SHAPE_DIR = Path(__file__).parent / "shapes"


@app.command()
def meta_inspect(
    stratification: bool = typer.Option(
        False, "--stratification", help="Check stratification safety (Russell's guard)"
    ),
    quote_unquote: bool = typer.Option(
        False, "--quote-unquote", help="Check quote/unquote level transitions"
    ),
    all_checks: bool = typer.Option(False, "--all", "-a", help="Run all meta-level safety checks"),
):
    """
    Inspect meta-loop safety properties.

    Verifies:
    - Stratification levels ∈ [0, 2] (Russell's paradox prevention)
    - Read-only mode enforcement (modification paradox prevention)
    - Quote/unquote level transitions (must increase/decrease correctly)
    """
    if all_checks:
        stratification = True
        quote_unquote = True

    if not (stratification or quote_unquote):
        console.print("[yellow]No checks specified. Use --help for options.[/yellow]")
        raise typer.Exit(1)

    # Load meta ontology
    console.print("[bold]Loading meta ontology...[/bold]")
    data_graph = Graph()
    try:
        data_graph.parse(ONTOLOGY_DIR / "meta.ttl", format="turtle")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to load meta.ttl: {e}")
        raise typer.Exit(1)

    # Load SHACL shape
    shacl_graph = Graph()
    try:
        shacl_graph.parse(SHAPE_DIR / "meta_shape.ttl", format="turtle")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to load meta_shape.ttl: {e}")
        raise typer.Exit(1)

    console.print("[green]✓[/green] Loaded ontology and shapes")
    console.print()

    # Run SHACL validation
    console.print("[bold]Running SHACL validation...[/bold]")
    conforms, results_graph, results_text = shacl_validate(
        data_graph, shacl_graph=shacl_graph, inference="rdfs", abort_on_first=False
    )

    if conforms:
        console.print("[green]✓ Meta-loop safety: PASS[/green]")
        console.print("  All stratification constraints satisfied")
        console.print("  No Russell's paradox risks detected")
        console.print("  Read-only mode enforced")
    else:
        console.print("[red]✗ Meta-loop safety: FAIL[/red]")
        console.print()
        console.print("[bold]Validation Report:[/bold]")
        console.print(results_text)
        raise typer.Exit(1)

    # Additional specific checks
    if stratification:
        console.print()
        console.print("[bold]Stratification Check:[/bold]")
        # Query for stratification levels
        query = """
        PREFIX meta: <http://example.org/vocab/meta#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?analysis ?level WHERE {
            ?analysis rdf:type meta:SelfAnalysis .
            ?analysis meta:stratificationLevel ?level .
        }
        """
        results = data_graph.query(query)

        if len(results) == 0:
            console.print("  [yellow]No SelfAnalysis instances found[/yellow]")
        else:
            table = Table(title="Stratification Levels")
            table.add_column("Analysis", style="cyan")
            table.add_column("Level", style="green")
            table.add_column("Status", style="bold")

            for row in results:
                level = int(row.level)
                status = "✓ SAFE" if 0 <= level <= 2 else "✗ VIOLATION"
                color = "green" if 0 <= level <= 2 else "red"
                table.add_row(str(row.analysis), str(level), f"[{color}]{status}[/{color}]")

            console.print(table)

    if quote_unquote:
        console.print()
        console.print("[bold]Quote/Unquote Check:[/bold]")
        # Query for quote/unquote operations
        query = """
        PREFIX meta: <http://example.org/vocab/meta#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?operation ?level ?type WHERE {
            {
                ?operation rdf:type meta:Quote .
                ?operation meta:quotedAtLevel ?level .
                BIND("quote" AS ?type)
            }
            UNION
            {
                ?operation rdf:type meta:Unquote .
                ?operation meta:unquotedAtLevel ?level .
                BIND("unquote" AS ?type)
            }
        }
        """
        results = data_graph.query(query)

        if len(results) == 0:
            console.print("  [yellow]No Quote/Unquote operations found[/yellow]")
        else:
            table = Table(title="Quote/Unquote Operations")
            table.add_column("Operation", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Level", style="green")

            for row in results:
                table.add_row(str(row.operation), str(row.type), str(row.level))

            console.print(table)


@app.command()
def validate_ontology(
    ontology_file: Path = typer.Argument(..., help="Path to ontology file (.ttl)"),
    shape_file: Optional[Path] = typer.Option(
        None, "--shape", help="Path to SHACL shape file (auto-detected if not provided)"
    ),
    inference: str = typer.Option(
        "rdfs", "--inference", help="Inference mode: none, rdfs, owlrl, both"
    ),
):
    """
    Validate ontology file against SHACL shapes.

    Examples:
      repoq validate-ontology repoq/ontologies/meta.ttl
      repoq validate-ontology repoq/ontologies/test.ttl --shape repoq/shapes/test_shape.ttl
    """
    # Load data graph
    console.print(f"[bold]Loading ontology:[/bold] {ontology_file}")
    data_graph = Graph()
    try:
        data_graph.parse(ontology_file, format="turtle")
        console.print(f"[green]✓[/green] Loaded {len(data_graph)} triples")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to load ontology: {e}")
        raise typer.Exit(1)

    # Auto-detect shape file if not provided
    if shape_file is None:
        # Try to find corresponding shape file
        ontology_name = ontology_file.stem  # e.g., "meta" from "meta.ttl"
        shape_file = SHAPE_DIR / f"{ontology_name}_shape.ttl"

        if not shape_file.exists():
            console.print(f"[yellow]⚠[/yellow] No shape file found at {shape_file}")
            console.print("[yellow]Skipping SHACL validation[/yellow]")
            raise typer.Exit(0)

    # Load shape graph
    console.print(f"[bold]Loading SHACL shapes:[/bold] {shape_file}")
    shacl_graph = Graph()
    try:
        shacl_graph.parse(shape_file, format="turtle")
        console.print(f"[green]✓[/green] Loaded {len(shacl_graph)} triples")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to load shapes: {e}")
        raise typer.Exit(1)

    console.print()

    # Run SHACL validation
    console.print("[bold]Running SHACL validation...[/bold]")
    conforms, results_graph, results_text = shacl_validate(
        data_graph, shacl_graph=shacl_graph, inference=inference, abort_on_first=False
    )

    console.print()

    if conforms:
        console.print("[green bold]✓ VALIDATION PASSED[/green bold]")
        console.print("  Ontology conforms to all SHACL constraints")
    else:
        console.print("[red bold]✗ VALIDATION FAILED[/red bold]")
        console.print()
        console.print("[bold]Validation Report:[/bold]")
        console.print(results_text)
        console.print()

        # Count violations
        query = """
        PREFIX sh: <http://www.w3.org/ns/shacl#>

        SELECT (COUNT(?result) AS ?count) ?severity WHERE {
            ?result a sh:ValidationResult .
            ?result sh:resultSeverity ?severity .
        }
        GROUP BY ?severity
        """
        severity_counts = results_graph.query(query)

        table = Table(title="Violations by Severity")
        table.add_column("Severity", style="bold")
        table.add_column("Count", style="red")

        for row in severity_counts:
            severity_name = str(row.severity).split("#")[-1]
            table.add_row(severity_name, str(row.count))

        console.print(table)
        raise typer.Exit(1)


@app.command()
def coverage_ontology(
    repo_path: Path = typer.Option(".", "--repo", help="Path to repository root"),
):
    """
    Map code coverage to ontology concepts.

    Shows which ontology concepts are tested and which are not.
    """
    console.print("[bold]Coverage-Ontology Mapping[/bold]")
    console.print(f"Repository: {repo_path}")
    console.print()

    # Load test ontology
    console.print("[bold]Loading test ontology...[/bold]")
    test_graph = Graph()
    try:
        test_graph.parse(ONTOLOGY_DIR / "test.ttl", format="turtle")
        console.print("[green]✓[/green] Loaded test ontology")
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to load test ontology: {e}")
        raise typer.Exit(1)

    # Query for test-concept mappings
    query = """
    PREFIX test: <http://example.org/vocab/test#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?testCase ?concept ?coverage WHERE {
        ?testCase rdf:type test:TestCase .
        ?testCase test:testedConcept ?concept .
        OPTIONAL {
            ?testCase test:coveragePercentage ?coverage .
        }
    }
    """
    results = test_graph.query(query)

    if len(results) == 0:
        console.print("[yellow]No test-concept mappings found in ontology[/yellow]")
        console.print("[yellow]Run tests to populate test metadata[/yellow]")
    else:
        table = Table(title="Test Coverage by Concept")
        table.add_column("Test Case", style="cyan")
        table.add_column("Tested Concept", style="magenta")
        table.add_column("Coverage %", style="green")

        for row in results:
            coverage_str = f"{float(row.coverage):.1f}%" if row.coverage else "N/A"
            table.add_row(
                str(row.testCase).split("/")[-1], str(row.concept).split("#")[-1], coverage_str
            )

        console.print(table)

    console.print()
    console.print("[bold]Recommendations:[/bold]")
    console.print("  • Add test:testedConcept annotations to test cases")
    console.print("  • Track test:coveragePercentage for each concept")
    console.print("  • Use property tests for ontology-level invariants")


if __name__ == "__main__":
    app()
