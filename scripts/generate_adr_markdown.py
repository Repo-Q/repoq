"""Generate Markdown documentation from ADR RDF (ADR-014 SSoT).

Single Source of Truth: .repoq/adr/*.ttl → docs/adr/*.md

Traceability:
- ADR-014: Single Source of Truth
- FR-10: Reproducible documentation
- V07: Observability
"""

from __future__ import annotations

from pathlib import Path

from rdflib import RDF, Graph, Namespace

# Namespaces
ADR = Namespace("https://repoq.dev/ontology/adr#")


def generate_adr_markdown(rdf_path: Path, output_path: Path) -> int:
    """Generate ADR Markdown from RDF.

    Args:
        rdf_path: Path to .repoq/adr/adr-XXX.ttl
        output_path: Path to docs/adr/adr-XXX.md

    Returns:
        Number of lines written

    Example:
        >>> lines = generate_adr_markdown(
        ...     Path(".repoq/adr/adr-014.ttl"),
        ...     Path("docs/adr/adr-014.md")
        ... )
    """
    # Load RDF
    graph = Graph()
    graph.parse(rdf_path, format="turtle")

    # Extract ADR (assume single ADR per file)
    adr_uri = next(graph.subjects(RDF.type, ADR.ArchitectureDecisionRecord))

    adr_id = str(graph.value(adr_uri, ADR.id, default=""))
    title = str(graph.value(adr_uri, ADR.title, default=""))
    status_uri = graph.value(adr_uri, ADR.status)
    status = str(status_uri).split("#")[-1].capitalize() if status_uri else "Unknown"
    date = str(graph.value(adr_uri, ADR.date, default=""))

    # Extract context
    context_node = graph.value(adr_uri, ADR.context)
    problem = ""
    constraints = []
    if context_node:
        problem = str(graph.value(context_node, ADR.problem, default=""))
        constraints = [str(c) for c in graph.objects(context_node, ADR.constraint)]

    # Extract decision
    decision_node = graph.value(adr_uri, ADR.decision)
    decision_desc = ""
    if decision_node:
        decision_desc = str(graph.value(decision_node, ADR.description, default=""))

    # Extract consequences
    consequence_node = graph.value(adr_uri, ADR.consequence)
    pros = []
    cons = []
    if consequence_node:
        pros = [str(p) for p in graph.objects(consequence_node, ADR.pros)]
        cons = [str(c) for c in graph.objects(consequence_node, ADR.cons)]

    # Extract alternatives
    alternatives = []
    for alt_node in graph.objects(adr_uri, ADR.alternative):
        alt_name = str(graph.value(alt_node, ADR.alternativeName, default=""))
        alt_rationale = str(graph.value(alt_node, ADR.alternativeRationale, default=""))
        if alt_name:
            alternatives.append((alt_name, alt_rationale))

    # Extract related ADRs
    related_adrs = []
    for related_uri in graph.objects(adr_uri, ADR.relatedTo):
        related_id = str(related_uri).split("#")[-1] if related_uri else ""
        if related_id:
            related_adrs.append(related_id)

    # Generate Markdown
    lines = []

    # Header
    lines.append(f"# {adr_id.upper()}: {title}\n\n")
    lines.append(f"**Status**: {status}  \n")
    lines.append(f"**Date**: {date}  \n\n")
    lines.append(
        "> **Generated from RDF**: This document is auto-generated from `.repoq/adr/{adr_id}.ttl`.\n"
    )
    lines.append("> Single Source of Truth: Edit RDF, regenerate Markdown.\n\n")

    # Context
    if problem or constraints:
        lines.append("## Проблема\n\n")
        if problem:
            lines.append(f"{problem}\n\n")
        if constraints:
            lines.append("**Ограничения**:\n")
            for constraint in constraints:
                lines.append(f"- {constraint}\n")
            lines.append("\n")

    # Decision
    if decision_desc:
        lines.append("## Решение\n\n")
        lines.append(f"{decision_desc}\n\n")

    # Consequences
    if pros or cons:
        lines.append("## Последствия\n\n")

        if pros:
            lines.append("### ✅ Pros\n\n")
            for i, pro in enumerate(pros, 1):
                lines.append(f"{i}. {pro}\n")
            lines.append("\n")

        if cons:
            lines.append("### ⚠️ Cons\n\n")
            for i, con in enumerate(cons, 1):
                lines.append(f"{i}. {con}\n")
            lines.append("\n")

    # Alternatives
    if alternatives:
        lines.append("## Альтернативы\n\n")
        for alt_name, alt_rationale in alternatives:
            lines.append(f"### {alt_name}\n\n")
            if alt_rationale:
                lines.append(f"{alt_rationale}\n\n")

    # Related ADRs
    if related_adrs:
        lines.append("## Связанные ADR\n\n")
        for related_id in related_adrs:
            lines.append(f"- {related_id.upper()}\n")
        lines.append("\n")

    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(lines))

    return len(lines)


if __name__ == "__main__":
    import sys

    # Generate ADR-014 as example
    rdf_path = Path(".repoq/adr/adr-014.ttl")
    output_path = Path("docs/adr/adr-014-single-source-of-truth-generated.md")

    if not rdf_path.exists():
        print(f"❌ RDF file not found: {rdf_path}")
        sys.exit(1)

    try:
        lines = generate_adr_markdown(rdf_path, output_path)
        print(f"✅ Generated ADR Markdown: {output_path}")
        print(f"   Lines: {lines}")
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        raise
