"""Generate story for Phase 1: Workspace Foundation."""

from datetime import datetime
from pathlib import Path

from repoq.core.story import (
    ArtifactInfo,
    GateInfo,
    PhaseInfo,
    generate_phase_story,
    save_story,
)

# Phase 1 information
phase1 = PhaseInfo(
    name="phase1",
    label="Phase 1: Workspace Foundation",
    status="completed",
    start_date=datetime(2025, 1, 15, 8, 0, 0),
    end_date=datetime(2025, 1, 15, 12, 30, 0),
    author="Kirill",
    commits=[
        "857cc79",  # feat(workspace): implement RepoQWorkspace
        "bed0ea5",  # feat(pipeline): integrate RepoQWorkspace with pipeline
        "f007076",  # docs(phase1): complete Phase 1 documentation
        "3e9de12",  # docs(changelog): add CHANGELOG.md
    ],
    artifacts=[
        ArtifactInfo(
            type="implementation",
            path="repoq/core/workspace.py",
            lines=200,
            language="Python",
            commit="857cc79",
        ),
        ArtifactInfo(
            type="test",
            path="tests/core/test_workspace.py",
            lines=300,
            language="Python",
            commit="857cc79",
        ),
        ArtifactInfo(
            type="test",
            path="tests/integration/test_gate_workspace.py",
            lines=150,
            language="Python",
            commit="bed0ea5",
        ),
        ArtifactInfo(
            type="documentation",
            path="docs/migration/phase1-workspace.md",
            lines=90,
            language="Markdown",
            commit="f007076",
        ),
        ArtifactInfo(
            type="documentation",
            path="CHANGELOG.md",
            lines=176,
            language="Markdown",
            commit="3e9de12",
        ),
    ],
    requirements=["fr-10", "v7", "theorem-a", "nfr-01"],
    adrs=["adr-008", "adr-010", "adr-013"],
    gates=[
        GateInfo(
            name="soundness", status="passed", evidence="18/18 tests passing (100%)"
        ),
        GateInfo(
            name="confluence", status="passed", evidence="No rule conflicts (data structure only)"
        ),
        GateInfo(
            name="termination", status="passed", evidence="<50ms measured (NFR-01 satisfied)"
        ),
        GateInfo(
            name="reflexive-completeness",
            status="passed",
            evidence="Workspace describes itself via manifest.json",
        ),
        GateInfo(
            name="conservative-extension",
            status="passed",
            evidence="Zero breaking changes (backward compatible)",
        ),
        GateInfo(
            name="performance", status="passed", evidence="<50ms overhead (<5% of analysis time)"
        ),
        GateInfo(
            name="test-coverage", status="passed", evidence="18 tests (15 unit + 3 integration)"
        ),
    ],
)

if __name__ == "__main__":
    # Generate story graph
    repo_dir = Path(__file__).parent.parent
    graph = generate_phase_story(phase1, repo_dir)

    # Save to .repoq/story/
    output_path = repo_dir / ".repoq" / "story" / "phase1.ttl"
    save_story(graph, output_path)

    print(f"✅ Phase 1 story generated: {output_path}")
    print(f"   Triples: {len(graph)}")
    print(f"   Commits: {len(phase1.commits)}")
    print(f"   Artifacts: {len(phase1.artifacts)}")
    print(f"   Gates: {len(phase1.gates)}")
