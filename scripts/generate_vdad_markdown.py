"""Generate Markdown documentation from VDAD RDF (Phase 5.6).

Single Source of Truth: .repoq/ stores RDF, docs/ contains generated Markdown.
This script generates human-readable docs from machine-readable RDF.

**Phase 5.6 Integration**: VDAD as single source of truth.

Traceability:
- V07: Observability (VDAD → multiple formats)
- FR-10: Reproducible analysis (RDF → Markdown deterministic)
- ADR-013: Incremental migration (Phase 2 generation POC)
"""

from __future__ import annotations

from pathlib import Path

from rdflib import RDF, RDFS, Graph, Namespace

# Namespaces
VDAD = Namespace("https://repoq.io/vdad#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")


def generate_phase2_markdown(rdf_path: Path, output_path: Path) -> int:
    """Generate Phase 2 Values Markdown from RDF.

    Single Source of Truth: RDF in .repoq/ → Markdown in docs/

    Args:
        rdf_path: Path to .repoq/vdad/phase2-values.ttl
        output_path: Path to docs/vdad/phase2-values.md

    Returns:
        Number of lines written

    Example:
        >>> lines = generate_phase2_markdown(
        ...     Path(".repoq/vdad/phase2-values.ttl"),
        ...     Path("docs/vdad/phase2-values.md")
        ... )
        >>> print(f"Generated {lines} lines")
        Generated 120 lines
    """
    # Load RDF
    graph = Graph()
    graph.parse(rdf_path, format="turtle")

    # Extract values (sorted by ID)
    values = []
    for value_uri in graph.subjects(RDF.type, VDAD.Tier1Value):
        value_id = str(value_uri).split("#")[-1]  # e.g., "v01"
        label = str(graph.value(value_uri, RDFS.label, default=""))
        description = str(graph.value(value_uri, VDAD.description, default=""))
        tier = int(graph.value(value_uri, VDAD.tier, default=1))
        priority_uri = graph.value(value_uri, VDAD.priority)
        priority = str(priority_uri).split("#")[-1] if priority_uri else "P2"

        # Extract stakeholders
        stakeholder_names = []
        for stakeholder_uri in graph.objects(value_uri, VDAD.stakeholder):
            name = str(graph.value(stakeholder_uri, FOAF.name, default=""))
            if name:
                stakeholder_names.append(name)

        # Extract requirements
        requirements = []
        for req_uri in graph.objects(value_uri, VDAD.satisfiedBy):
            req_id = str(req_uri).split("#")[-1].upper()  # fr-01 → FR-01
            requirements.append(req_id.replace("-", "-"))

        values.append(
            {
                "id": value_id,
                "label": label,
                "description": description,
                "tier": tier,
                "priority": priority,
                "stakeholders": stakeholder_names,
                "requirements": requirements,
            }
        )

    values.sort(key=lambda v: v["id"])  # type: ignore[arg-type, return-value]

    # Extract stakeholders (sorted by name)
    stakeholders = []
    for stakeholder_uri in graph.subjects(RDF.type, VDAD.Stakeholder):
        stakeholder_id = str(stakeholder_uri).split("#")[-1]
        name = str(graph.value(stakeholder_uri, FOAF.name, default=""))
        role = str(graph.value(stakeholder_uri, VDAD.role, default=""))

        # Extract interests
        interests = [str(interest) for interest in graph.objects(stakeholder_uri, VDAD.interests)]

        # Extract concerns
        concerns = [str(concern) for concern in graph.objects(stakeholder_uri, VDAD.concerns)]

        stakeholders.append(
            {
                "id": stakeholder_id,
                "name": name,
                "role": role,
                "interests": interests,
                "concerns": concerns,
            }
        )

    stakeholders.sort(key=lambda s: s["name"])  # type: ignore[arg-type, return-value]

    # Generate Markdown
    lines = []
    lines.append("# Phase 2: Value Register\n")
    lines.append(
        "\n> **Generated from RDF**: This document is auto-generated from `.repoq/vdad/phase2-values.ttl`.\n"
    )
    lines.append("> Single Source of Truth: Edit RDF, regenerate Markdown.\n\n")

    # Values section
    for value in values:
        lines.append(f"## {value['label']}\n\n")
        lines.append(f"{value['description']}\n\n")
        lines.append(f"**Tier**: {value['tier']}\n")
        lines.append(f"**Priority**: {value['priority']}\n")

        if value["stakeholders"]:
            stakeholders_str = ", ".join(value["stakeholders"])
            lines.append(f"**Stakeholders**: {stakeholders_str}\n\n")

        if value["requirements"]:
            reqs_str = ", ".join(value["requirements"])
            lines.append(f"Satisfied by: {reqs_str}\n\n")
        else:
            lines.append("\n")

    # Stakeholders section
    if stakeholders:
        lines.append("## Stakeholder Profiles\n\n")

        for stakeholder in stakeholders:
            lines.append(f"### {stakeholder['name']} ({stakeholder['role']})\n\n")

            if stakeholder["interests"]:
                lines.append("**Interests**:\n")
                for interest in stakeholder["interests"]:
                    lines.append(f"- {interest}\n")
                lines.append("\n")

            if stakeholder["concerns"]:
                lines.append("**Concerns**:\n")
                for concern in stakeholder["concerns"]:
                    lines.append(f"- {concern}\n")
                lines.append("\n")

    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(lines))

    return len(lines)


if __name__ == "__main__":
    import sys

    # Generate Phase 2 Markdown from RDF
    rdf_path = Path(".repoq/vdad/phase2-values.ttl")
    output_path = Path("docs/vdad/phase2-values-generated.md")

    if not rdf_path.exists():
        print(f"❌ RDF file not found: {rdf_path}")
        print("   Run: python scripts/extract_vdad_rdf.py")
        sys.exit(1)

    try:
        lines = generate_phase2_markdown(rdf_path, output_path)
        print(f"✅ Generated Markdown: {output_path}")
        print(f"   Lines: {lines}")
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        raise
