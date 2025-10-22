"""Extract RDF from VDAD Markdown documentation (Phase 5.6 POC).

This module parses VDAD Markdown files and generates RDF/Turtle sidecars.
Focuses on Phase 2 (Value Register) as POC.

**Phase 5.6 Integration**: VDAD as single source of truth.

Traceability:
- V07: Observability (transparent VDAD structure)
- FR-10: Reproducible analysis (VDAD versioning)
- ADR-013: Incremental migration (VDAD tracks phases)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rdflib import RDF, RDFS, XSD, Graph, Literal, Namespace

# Namespaces
VDAD = Namespace("https://repoq.io/vdad#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")


@dataclass
class ValueInfo:
    """Information about a VDAD value."""

    id: str  # e.g., "v01"
    label: str  # e.g., "V01: Transparency"
    tier: int  # 1, 2, or 3
    description: str
    priority: str  # P0, P1, P2
    stakeholders: list[str]  # e.g., ["alex", "morgan"]
    satisfied_by: list[str]  # e.g., ["fr-01", "fr-05"]
    phase: str  # "phase2"


@dataclass
class StakeholderInfo:
    """Information about a stakeholder."""

    id: str  # e.g., "alex"
    name: str  # e.g., "Alex"
    role: str  # e.g., "Senior Developer"
    type: str  # Developer, TeamLead, DevOps, Researcher
    interests: list[str]
    concerns: list[str]


def parse_phase2_values_markdown(
    markdown_path: Path,
) -> tuple[list[ValueInfo], list[StakeholderInfo]]:
    """Parse Phase 2 Values Markdown and extract structured data.

    Args:
        markdown_path: Path to phase2-values.md

    Returns:
        Tuple of (values, stakeholders)

    Example:
        >>> values, stakeholders = parse_phase2_values_markdown(Path("docs/vdad/phase2-values.md"))
        >>> print(len(values))  # 8 Tier 1 values
        8
    """
    content = markdown_path.read_text()
    values = []
    stakeholders = []

    # Extract Tier 1 values (sections starting with ## V)
    value_pattern = r"##\s+(V\d+):\s+(.+?)\n(.+?)(?=##|$)"
    for match in re.finditer(value_pattern, content, re.DOTALL):
        value_id = match.group(1).lower()  # V01 → v01
        value_name = match.group(2).strip()
        value_body = match.group(3)

        # Extract metadata
        tier_match = re.search(r"\*\*Tier\*\*:\s*(\d+)", value_body)
        tier = int(tier_match.group(1)) if tier_match else 1

        priority_match = re.search(r"\*\*Priority\*\*:\s*(P\d+)", value_body)
        priority = priority_match.group(1) if priority_match else "P2"

        # Extract stakeholders
        stakeholder_matches = re.findall(r"\*\*Stakeholders\*\*:\s*(.+)", value_body)
        stakeholders_text = stakeholder_matches[0] if stakeholder_matches else ""
        stakeholder_ids = []
        for name in ["Alex", "Morgan", "Casey", "Jordan", "Taylor"]:
            if name in stakeholders_text:
                stakeholder_ids.append(name.lower())

        # Extract satisfied_by requirements
        satisfied_by = []
        for req_match in re.finditer(r"(FR-\d+|NFR-\d+)", value_body, re.IGNORECASE):
            req_id = req_match.group(1).lower().replace("-", "-")  # FR-01 → fr-01
            satisfied_by.append(req_id)

        # Extract description (first paragraph after header)
        desc_match = re.search(r"\n\n(.+?)(?:\n\n|\*\*)", value_body, re.DOTALL)
        description = desc_match.group(1).strip() if desc_match else ""

        values.append(
            ValueInfo(
                id=value_id,
                label=f"{value_id.upper()}: {value_name}",
                tier=tier,
                description=description,
                priority=priority,
                stakeholders=stakeholder_ids,
                satisfied_by=satisfied_by,
                phase="phase2",
            )
        )

    # Extract stakeholders (from stakeholder section)
    stakeholder_section = re.search(r"##\s+Stakeholder Profiles\s*\n(.+)", content, re.DOTALL)
    if stakeholder_section:
        stakeholder_text = stakeholder_section.group(1)

        # Parse each stakeholder
        stakeholder_pattern = r"###\s+(.+?)\s*\((.+?)\)\s*\n(.+?)(?=\n###|\Z)"
        for match in re.finditer(stakeholder_pattern, stakeholder_text, re.DOTALL):
            name = match.group(1).strip()
            role = match.group(2).strip()
            body = match.group(3)

            # Determine type
            if "developer" in role.lower():
                stype = "Developer"
            elif "lead" in role.lower():
                stype = "TeamLead"
            elif "devops" in role.lower():
                stype = "DevOps"
            elif "research" in role.lower():
                stype = "Researcher"
            else:
                stype = "Stakeholder"

            # Extract interests
            interests = []
            interests_match = re.search(r"\*\*Interests\*\*:(.+?)(?:\*\*|$)", body, re.DOTALL)
            if interests_match:
                for line in interests_match.group(1).strip().split("\n"):
                    if line.strip().startswith("-"):
                        interests.append(line.strip()[1:].strip())

            # Extract concerns
            concerns = []
            concerns_match = re.search(r"\*\*Concerns\*\*:(.+?)(?:\*\*|$)", body, re.DOTALL)
            if concerns_match:
                for line in concerns_match.group(1).strip().split("\n"):
                    if line.strip().startswith("-"):
                        concerns.append(line.strip()[1:].strip())

            stakeholders.append(
                StakeholderInfo(
                    id=name.lower(),
                    name=name,
                    role=role,
                    type=stype,
                    interests=interests,
                    concerns=concerns,
                )
            )

    return values, stakeholders


def generate_phase2_rdf(values: list[ValueInfo], stakeholders: list[StakeholderInfo]) -> Graph:
    """Generate RDF graph for Phase 2 Values.

    Args:
        values: List of values
        stakeholders: List of stakeholders

    Returns:
        RDF graph

    Traceability:
        - V07: Transparent VDAD structure
        - FR-10: Reproducible documentation

    Example:
        >>> values = [ValueInfo(id="v01", label="V01: Transparency", ...)]
        >>> stakeholders = [StakeholderInfo(id="alex", name="Alex", ...)]
        >>> g = generate_phase2_rdf(values, stakeholders)
        >>> print(len(g))  # number of triples
        50
    """
    g = Graph()
    g.bind("vdad", VDAD)
    g.bind("foaf", FOAF)
    g.bind("rdfs", RDFS)

    # Add values
    for value in values:
        value_uri = VDAD[value.id]
        g.add((value_uri, RDF.type, VDAD.Tier1Value))
        g.add((value_uri, RDF.type, VDAD.Value))
        g.add((value_uri, RDFS.label, Literal(value.label)))
        g.add((value_uri, VDAD.tier, Literal(value.tier, datatype=XSD.integer)))
        g.add((value_uri, VDAD.description, Literal(value.description)))
        g.add((value_uri, VDAD.priority, VDAD[value.priority]))
        g.add((value_uri, VDAD.phase, VDAD[value.phase]))

        # Link to stakeholders
        for stakeholder_id in value.stakeholders:
            g.add((value_uri, VDAD.stakeholder, VDAD[stakeholder_id]))

        # Link to requirements
        for req_id in value.satisfied_by:
            g.add((value_uri, VDAD.satisfiedBy, VDAD[req_id]))

    # Add stakeholders
    for stakeholder in stakeholders:
        stakeholder_uri = VDAD[stakeholder.id]
        g.add((stakeholder_uri, RDF.type, VDAD[stakeholder.type]))
        g.add((stakeholder_uri, RDF.type, VDAD.Stakeholder))
        g.add((stakeholder_uri, FOAF.name, Literal(stakeholder.name)))
        g.add((stakeholder_uri, VDAD.role, Literal(stakeholder.role)))

        # Add interests
        for interest in stakeholder.interests:
            g.add((stakeholder_uri, VDAD.interests, Literal(interest)))

        # Add concerns
        for concern in stakeholder.concerns:
            g.add((stakeholder_uri, VDAD.concerns, Literal(concern)))

    return g


def extract_phase2_values(markdown_path: Path, output_path: Path) -> int:
    """Extract Phase 2 Values from Markdown and save as TTL.

    Args:
        markdown_path: Path to phase2-values.md
        output_path: Path to output .ttl file

    Returns:
        Number of triples generated

    Example:
        >>> count = extract_phase2_values(
        ...     Path("docs/vdad/phase2-values.md"),
        ...     Path("docs/vdad/phase2-values.ttl")
        ... )
        >>> print(f"Generated {count} triples")
        Generated 120 triples
    """
    # Parse Markdown
    values, stakeholders = parse_phase2_values_markdown(markdown_path)

    # Generate RDF
    graph = generate_phase2_rdf(values, stakeholders)

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=output_path, format="turtle")

    return len(graph)


if __name__ == "__main__":
    # Extract Phase 2 Values
    markdown_path = Path("docs/vdad/phase2-values.md")
    output_path = Path(".repoq/vdad/phase2-values.ttl")

    if not markdown_path.exists():
        print(f"❌ Markdown file not found: {markdown_path}")
        exit(1)

    try:
        count = extract_phase2_values(markdown_path, output_path)
        print(f"✅ Extracted Phase 2 Values: {output_path}")
        print(f"   Triples: {count}")
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        raise
