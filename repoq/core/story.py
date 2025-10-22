"""Story generation - Development provenance and traceability (Phase 1 POC).

This module generates RDF/Turtle representations of development history:
- VDAD phases with commits, artifacts, and gates
- Git commits with semantic annotations
- Traceability to requirements (FR-10, V07, etc.) and ADRs

**Phase 5 Integration**: Story generation for reproducibility (Theorem A).

Traceability:
- FR-10: Reproducible analysis results (full provenance)
- V07: Observability (transparent development history)
- Theorem A: Reproducibility (checksums + story graph)
- ADR-013: Incremental migration (story tracks phases)
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from rdflib import RDF, XSD, Graph, Literal, Namespace, URIRef

# Namespaces
STORY = Namespace("https://repoq.io/story#")
VDAD = Namespace("https://repoq.io/vdad#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")


@dataclass
class PhaseInfo:
    """Information about a VDAD phase execution."""

    name: str  # e.g., "phase1"
    label: str  # e.g., "Phase 1: Workspace Foundation"
    status: str  # not-started, in-progress, completed, blocked
    start_date: datetime | None
    end_date: datetime | None
    author: str
    commits: list[str]  # commit SHAs
    artifacts: list[ArtifactInfo]
    requirements: list[str]  # e.g., ["fr-10", "v07", "theorem-a"]
    adrs: list[str]  # e.g., ["adr-008", "adr-013"]
    gates: list[GateInfo]


@dataclass
class ArtifactInfo:
    """Information about a produced artifact."""

    type: str  # implementation, test, documentation
    path: str  # relative path
    lines: int
    language: str  # Python, Markdown, etc.
    commit: str  # commit SHA


@dataclass
class GateInfo:
    """Information about a quality gate check."""

    name: str  # soundness, performance, etc.
    status: str  # passed, failed, skipped, warning
    evidence: str  # e.g., "18/18 tests passing"


def get_git_commit_info(commit_sha: str, repo_dir: Path) -> dict[str, Any]:
    """Get git commit information.

    Args:
        commit_sha: Commit SHA (full or short)
        repo_dir: Repository root directory

    Returns:
        Dict with keys: sha, author, email, date, subject, body, files

    Example:
        >>> info = get_git_commit_info("857cc79", Path("/repo"))
        >>> print(info["subject"])
        'feat(workspace): implement RepoQWorkspace'
    """
    # Get commit metadata
    result = subprocess.run(
        ["git", "show", "--format=%H%n%an%n%ae%n%ai%n%s%n%b", "-s", commit_sha],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=True,
    )

    lines = result.stdout.strip().split("\n")
    sha, author_name, author_email, date_str, subject = lines[:5]
    body = "\n".join(lines[5:]) if len(lines) > 5 else ""

    # Get modified files
    files_result = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_sha],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=True,
    )
    files = [f for f in files_result.stdout.strip().split("\n") if f]

    return {
        "sha": sha,
        "author": f"{author_name} <{author_email}>",
        "date": date_str,
        "subject": subject,
        "body": body,
        "files": files,
    }


def extract_requirements(text: str) -> list[str]:
    """Extract requirement IDs from commit message or description.

    Looks for patterns like:
    - FR-10, FR10, fr-10
    - V07, V7
    - NFR-01, NFR01
    - Theorem A, TheoremA
    - ADR-013, ADR013

    Args:
        text: Commit message or phase description

    Returns:
        List of normalized requirement IDs (e.g., ["fr-10", "v07", "theorem-a"])

    Example:
        >>> extract_requirements("Implements FR-10 and V07")
        ['fr-10', 'v07']
    """
    requirements = []

    # FR-XX pattern
    for match in re.finditer(r"\bFR-?(\d+)\b", text, re.IGNORECASE):
        requirements.append(f"fr-{match.group(1)}")

    # VXX pattern
    for match in re.finditer(r"\bV-?(\d+)\b", text, re.IGNORECASE):
        requirements.append(f"v{match.group(1).lstrip('0')}")  # V07 → v7

    # NFR-XX pattern
    for match in re.finditer(r"\bNFR-?(\d+)\b", text, re.IGNORECASE):
        requirements.append(f"nfr-{match.group(1)}")

    # Theorem X pattern
    for match in re.finditer(r"\bTheorem\s*([A-Z])\b", text, re.IGNORECASE):
        requirements.append(f"theorem-{match.group(1).lower()}")

    # ADR-XXX pattern
    for match in re.finditer(r"\bADR-?(\d+)\b", text, re.IGNORECASE):
        requirements.append(f"adr-{match.group(1).zfill(3)}")  # ADR-13 → adr-013

    return list(set(requirements))  # deduplicate


def generate_phase_story(phase: PhaseInfo, repo_dir: Path) -> Graph:
    """Generate RDF graph for a VDAD phase story.

    Args:
        phase: Phase information
        repo_dir: Repository root directory

    Returns:
        RDF graph with phase story

    Traceability:
        - FR-10: Full provenance for reproducibility
        - V07: Transparent development history
        - Theorem A: Story graph complements manifest.json

    Example:
        >>> phase = PhaseInfo(name="phase1", label="Phase 1: Workspace", ...)
        >>> g = generate_phase_story(phase, Path("/repo"))
        >>> print(len(g))  # number of triples
        42
    """
    g = Graph()
    g.bind("story", STORY)
    g.bind("vdad", VDAD)
    g.bind("rdfs", RDFS)

    # Phase node (use STORY namespace)
    phase_uri = STORY[f"phases/{phase.name}"]
    g.add((phase_uri, RDF.type, STORY.Phase))
    g.add((phase_uri, RDFS.label, Literal(phase.label)))
    g.add((phase_uri, STORY.status, Literal(phase.status)))
    g.add((phase_uri, STORY.author, Literal(phase.author)))

    # Dates
    if phase.start_date:
        g.add((phase_uri, STORY.startDate, Literal(phase.start_date, datatype=XSD.dateTime)))
    if phase.end_date:
        g.add((phase_uri, STORY.endDate, Literal(phase.end_date, datatype=XSD.dateTime)))

    # Duration (if both dates present)
    if phase.start_date and phase.end_date:
        duration = phase.end_date - phase.start_date
        # Format as ISO 8601 duration (PT4H30M)
        hours = duration.total_seconds() // 3600
        minutes = (duration.total_seconds() % 3600) // 60
        duration_str = f"PT{int(hours)}H{int(minutes)}M"
        g.add((phase_uri, STORY.duration, Literal(duration_str, datatype=XSD.duration)))

    # Commits
    for commit_sha in phase.commits:
        commit_uri = STORY[f"commits/{commit_sha[:7]}"]
        g.add((phase_uri, STORY.hasCommit, commit_uri))
        g.add((commit_uri, RDF.type, STORY.Commit))
        g.add((commit_uri, STORY.sha, Literal(commit_sha[:7])))

        # Get commit details
        try:
            info = get_git_commit_info(commit_sha, repo_dir)
            g.add((commit_uri, STORY.message, Literal(info["subject"])))
            g.add((commit_uri, STORY.commitAuthor, Literal(info["author"])))
            g.add((commit_uri, STORY.commitDate, Literal(info["date"], datatype=XSD.dateTime)))

            # Modified files
            for file in info["files"]:
                g.add((commit_uri, STORY.modifies, Literal(file)))

            # Extract requirements from commit message
            for req in extract_requirements(info["subject"] + " " + info["body"]):
                g.add((commit_uri, VDAD.satisfies, VDAD[req]))

        except subprocess.CalledProcessError:
            # Commit not found (skip details)
            pass

    # Artifacts
    for artifact in phase.artifacts:
        artifact_uri = STORY[f"artifacts/{artifact.path.replace('/', '-')}"]
        g.add((phase_uri, STORY.produces, artifact_uri))
        g.add((artifact_uri, RDF.type, STORY.Artifact))

        # Artifact type
        if artifact.type == "implementation":
            g.add((artifact_uri, RDF.type, STORY.Implementation))
        elif artifact.type == "test":
            g.add((artifact_uri, RDF.type, STORY.TestSuite))
        elif artifact.type == "documentation":
            g.add((artifact_uri, RDF.type, STORY.Documentation))

        g.add((artifact_uri, STORY.path, Literal(artifact.path)))
        g.add((artifact_uri, STORY.lines, Literal(artifact.lines, datatype=XSD.integer)))
        g.add((artifact_uri, STORY.language, Literal(artifact.language)))
        g.add((artifact_uri, STORY.commit, Literal(artifact.commit)))

    # Requirements
    for req in phase.requirements:
        g.add((phase_uri, VDAD.satisfies, VDAD[req]))

    # ADRs
    for adr in phase.adrs:
        g.add((phase_uri, VDAD.implements, VDAD[adr]))

    # Gates
    for gate in phase.gates:
        gate_uri = STORY[f"gates/{phase.name}-{gate.name}"]
        g.add((phase_uri, STORY.hasGate, gate_uri))
        g.add((gate_uri, RDF.type, STORY.Gate))
        g.add((gate_uri, STORY.gateName, Literal(gate.name)))
        g.add((gate_uri, STORY.gateStatus, Literal(gate.status)))
        g.add((gate_uri, STORY.gateEvidence, Literal(gate.evidence)))

    return g


def save_story(graph: Graph, output_path: Path) -> None:
    """Save story graph to Turtle file.

    Args:
        graph: RDF graph
        output_path: Output file path (.ttl)

    Example:
        >>> g = generate_phase_story(phase, repo_dir)
        >>> save_story(g, Path(".repoq/story/phase1.ttl"))
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=output_path, format="turtle")
