"""Generate CHANGELOG.md from RDF (ADR-014 SSoT).

Single Source of Truth: .repoq/changelog/releases.ttl → CHANGELOG.md

Traceability:
- ADR-014: Single Source of Truth
- FR-10: Reproducible documentation
- V07: Observability
"""

from __future__ import annotations

from pathlib import Path

from rdflib import RDF, Graph, Namespace

# Namespaces
CHANGELOG = Namespace("https://repoq.io/changelog#")


def generate_changelog_markdown(rdf_path: Path, output_path: Path) -> int:
    """Generate CHANGELOG.md from RDF.

    Args:
        rdf_path: Path to .repoq/changelog/releases.ttl
        output_path: Path to CHANGELOG.md

    Returns:
        Number of lines written

    Example:
        >>> lines = generate_changelog_markdown(
        ...     Path(".repoq/changelog/releases.ttl"),
        ...     Path("CHANGELOG.md")
        ... )
    """
    # Load RDF
    graph = Graph()
    graph.parse(rdf_path, format="turtle")

    # Extract releases (sorted by version, descending)
    releases = []
    for release_uri in graph.subjects(RDF.type, CHANGELOG.Release):
        version = str(graph.value(release_uri, CHANGELOG.version, default=""))
        date = str(graph.value(release_uri, CHANGELOG.date, default=""))
        tag = str(graph.value(release_uri, CHANGELOG.tag, default=""))
        summary = str(graph.value(release_uri, CHANGELOG.summary, default=""))

        # Extract changes
        changes = []
        for change_node in graph.objects(release_uri, CHANGELOG.change):
            change_type_uri = graph.value(change_node, CHANGELOG.changeType)
            change_type = (
                str(change_type_uri).split("#")[-1].capitalize() if change_type_uri else "Changed"
            )
            description = str(graph.value(change_node, CHANGELOG.description, default=""))
            breaking = bool(graph.value(change_node, CHANGELOG.breakingChange, default=False))
            commit = str(graph.value(change_node, CHANGELOG.commit, default=""))

            changes.append(
                {
                    "type": change_type,
                    "description": description,
                    "breaking": breaking,
                    "commit": commit,
                }
            )

        releases.append(
            {
                "version": version,
                "date": date,
                "tag": tag,
                "summary": summary,
                "changes": changes,
            }
        )

    # Sort releases by version (descending)
    releases.sort(key=lambda r: r["version"], reverse=True)  # type: ignore[arg-type, return-value]

    # Generate Markdown
    lines = []

    # Header
    lines.append("# Changelog\n\n")
    lines.append(
        "> **Generated from RDF**: This document is auto-generated from `.repoq/changelog/releases.ttl`.\n"
    )
    lines.append("> Single Source of Truth: Edit RDF, regenerate CHANGELOG.\n\n")
    lines.append("All notable changes to RepoQ will be documented in this file.\n\n")
    lines.append(
        "The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),\n"
    )
    lines.append(
        "and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).\n\n"
    )

    # Releases
    for release in releases:
        lines.append(f"## [{release['version']}] - {release['date']}\n\n")

        if release["summary"]:
            lines.append(f"**{release['summary']}**\n\n")

        # Group changes by type
        changes_by_type: dict[str, list[dict[str, str | bool]]] = {}
        for change in release["changes"]:  # type: ignore[index]
            change_type = change["type"]  # type: ignore[index]
            if change_type not in changes_by_type:
                changes_by_type[change_type] = []
            changes_by_type[change_type].append(change)

        # Render changes by type
        for change_type in ["Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"]:
            if change_type in changes_by_type:
                lines.append(f"### {change_type}\n\n")

                for change in changes_by_type[change_type]:
                    desc = change["description"]  # type: ignore[index]
                    commit = change["commit"]  # type: ignore[index]
                    breaking = change["breaking"]  # type: ignore[index]

                    if breaking:
                        lines.append(f"- **BREAKING**: {desc}")
                    else:
                        lines.append(f"- {desc}")

                    if commit:
                        lines.append(f" (`{commit}`)")

                    lines.append("\n")

                lines.append("\n")

    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(lines))

    return len(lines)


if __name__ == "__main__":
    import sys

    # Generate CHANGELOG.md
    rdf_path = Path(".repoq/changelog/releases.ttl")
    output_path = Path("CHANGELOG-generated.md")

    if not rdf_path.exists():
        print(f"❌ RDF file not found: {rdf_path}")
        sys.exit(1)

    try:
        lines = generate_changelog_markdown(rdf_path, output_path)
        print(f"✅ Generated CHANGELOG: {output_path}")
        print(f"   Lines: {lines}")
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        raise
