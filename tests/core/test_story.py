"""Tests for story generation (Phase 1 POC)."""

import subprocess
from datetime import datetime
from pathlib import Path

import pytest
from rdflib import RDF, Literal, Namespace

from repoq.core.story import (
    ArtifactInfo,
    GateInfo,
    PhaseInfo,
    extract_requirements,
    generate_phase_story,
    get_git_commit_info,
    save_story,
)

STORY = Namespace("https://repoq.io/story#")
VDAD = Namespace("https://repoq.io/vdad#")


class TestRequirementExtraction:
    """Tests for extract_requirements()."""

    def test_extract_fr_requirements(self):
        """Test extraction of FR-XX requirements."""
        text = "Implements FR-10 and FR-23"
        result = extract_requirements(text)
        assert "fr-10" in result
        assert "fr-23" in result

    def test_extract_v_requirements(self):
        """Test extraction of V-XX requirements."""
        text = "Satisfies V07 and V7"
        result = extract_requirements(text)
        assert "v7" in result  # V07 normalized to v7

    def test_extract_nfr_requirements(self):
        """Test extraction of NFR-XX requirements."""
        text = "Addresses NFR-01 and NFR01"
        result = extract_requirements(text)
        assert "nfr-01" in result

    def test_extract_theorem_requirements(self):
        """Test extraction of Theorem X requirements."""
        text = "Proves Theorem A and Theorem B"
        result = extract_requirements(text)
        assert "theorem-a" in result
        assert "theorem-b" in result

    def test_extract_adr_requirements(self):
        """Test extraction of ADR-XXX requirements."""
        text = "Implements ADR-013 and ADR-8"
        result = extract_requirements(text)
        assert "adr-013" in result
        assert "adr-008" in result  # ADR-8 normalized to adr-008

    def test_extract_mixed_requirements(self):
        """Test extraction of multiple requirement types."""
        text = """
        feat(workspace): implement RepoQWorkspace
        
        Traceability:
        - FR-10: Reproducible analysis
        - V07: Observability
        - Theorem A: Reproducibility
        - NFR-01: Performance
        - ADR-013: Incremental migration
        """
        result = extract_requirements(text)
        assert "fr-10" in result
        assert "v7" in result
        assert "theorem-a" in result
        assert "nfr-01" in result
        assert "adr-013" in result

    def test_extract_no_requirements(self):
        """Test extraction when no requirements present."""
        text = "Just a normal commit message"
        result = extract_requirements(text)
        assert len(result) == 0

    def test_deduplication(self):
        """Test that duplicate requirements are deduplicated."""
        text = "FR-10 and FR-10 and FR-10"
        result = extract_requirements(text)
        assert result.count("fr-10") == 1


class TestGitCommitInfo:
    """Tests for get_git_commit_info()."""

    def test_get_commit_info_real_commit(self, tmp_path):
        """Test getting info for a real git commit."""
        # Create test repo
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "test.txt").write_text("hello")

        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Add second commit (to test diff-tree properly)
        (repo_path / "test2.txt").write_text("world")
        subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Second commit"],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

        # Get commit SHA
        sha_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        commit_sha = sha_result.stdout.strip()

        # Test get_git_commit_info
        info = get_git_commit_info(commit_sha, repo_path)

        assert info["sha"] == commit_sha
        assert "Test User" in info["author"]
        assert "test@test.com" in info["author"]
        assert info["subject"] == "Second commit"
        assert "test2.txt" in info["files"]

    def test_get_commit_info_invalid_sha(self, tmp_path):
        """Test getting info for invalid commit SHA."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)

        with pytest.raises(subprocess.CalledProcessError):
            get_git_commit_info("invalid123", repo_path)


class TestPhaseStoryGeneration:
    """Tests for generate_phase_story()."""

    def test_generate_minimal_phase_story(self, tmp_path):
        """Test generating story for minimal phase."""
        # Create test repo
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)

        phase = PhaseInfo(
            name="phase1",
            label="Phase 1: Test",
            status="completed",
            start_date=None,
            end_date=None,
            author="Test User",
            commits=[],
            artifacts=[],
            requirements=["fr-10"],
            adrs=["adr-013"],
            gates=[],
        )

        graph = generate_phase_story(phase, repo_path)

        # Check phase node exists
        phase_uri = STORY["phases/phase1"]
        assert (phase_uri, RDF.type, STORY.Phase) in graph

        # Check requirements
        assert (phase_uri, VDAD.satisfies, VDAD["fr-10"]) in graph

        # Check ADRs
        assert (phase_uri, VDAD.implements, VDAD["adr-013"]) in graph

    def test_generate_phase_story_with_artifacts(self, tmp_path):
        """Test generating story with artifacts."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)

        phase = PhaseInfo(
            name="phase1",
            label="Phase 1: Test",
            status="completed",
            start_date=datetime(2025, 1, 15, 8, 0, 0),
            end_date=datetime(2025, 1, 15, 12, 30, 0),
            author="Test User",
            commits=[],
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
            ],
            requirements=[],
            adrs=[],
            gates=[],
        )

        graph = generate_phase_story(phase, repo_path)

        # Check artifacts
        workspace_uri = STORY["artifacts/repoq-core-workspace.py"]
        assert (workspace_uri, RDF.type, STORY.Implementation) in graph
        assert (workspace_uri, STORY.path, Literal("repoq/core/workspace.py")) in graph
        assert (workspace_uri, STORY.lines, Literal(200)) in graph

        test_uri = STORY["artifacts/tests-core-test_workspace.py"]
        assert (test_uri, RDF.type, STORY.TestSuite) in graph

    def test_generate_phase_story_with_gates(self, tmp_path):
        """Test generating story with quality gates."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)

        phase = PhaseInfo(
            name="phase1",
            label="Phase 1: Test",
            status="completed",
            start_date=None,
            end_date=None,
            author="Test User",
            commits=[],
            artifacts=[],
            requirements=[],
            adrs=[],
            gates=[
                GateInfo(name="soundness", status="passed", evidence="18/18 tests passing"),
                GateInfo(name="performance", status="passed", evidence="<50ms overhead"),
            ],
        )

        graph = generate_phase_story(phase, repo_path)

        # Check gates
        gate_soundness = STORY["gates/phase1-soundness"]
        assert (gate_soundness, RDF.type, STORY.Gate) in graph
        assert (gate_soundness, STORY.gateName, Literal("soundness")) in graph
        assert (gate_soundness, STORY.gateStatus, Literal("passed")) in graph

    def test_generate_phase_story_with_duration(self, tmp_path):
        """Test duration calculation."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)

        phase = PhaseInfo(
            name="phase1",
            label="Phase 1: Test",
            status="completed",
            start_date=datetime(2025, 1, 15, 8, 0, 0),
            end_date=datetime(2025, 1, 15, 12, 30, 0),  # 4h 30m
            author="Test User",
            commits=[],
            artifacts=[],
            requirements=[],
            adrs=[],
            gates=[],
        )

        graph = generate_phase_story(phase, repo_path)

        # Check duration
        phase_uri = STORY["phases/phase1"]
        duration_triple = list(graph.triples((phase_uri, STORY.duration, None)))
        assert len(duration_triple) == 1
        assert "PT4H30M" in str(duration_triple[0][2])


class TestStorySaving:
    """Tests for save_story()."""

    def test_save_story_creates_file(self, tmp_path):
        """Test that save_story creates TTL file."""
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)

        phase = PhaseInfo(
            name="phase1",
            label="Phase 1: Test",
            status="completed",
            start_date=None,
            end_date=None,
            author="Test User",
            commits=[],
            artifacts=[],
            requirements=["fr-10"],
            adrs=[],
            gates=[],
        )

        graph = generate_phase_story(phase, repo_path)

        output_path = tmp_path / ".repoq" / "story" / "phase1.ttl"
        save_story(graph, output_path)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

        # Check content is valid Turtle
        content = output_path.read_text()
        assert "@prefix story:" in content
        assert "story:Phase" in content

    def test_save_story_creates_directories(self, tmp_path):
        """Test that save_story creates parent directories."""
        output_path = tmp_path / "deep" / "nested" / "path" / "story.ttl"

        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)

        phase = PhaseInfo(
            name="phase1",
            label="Phase 1: Test",
            status="completed",
            start_date=None,
            end_date=None,
            author="Test User",
            commits=[],
            artifacts=[],
            requirements=[],
            adrs=[],
            gates=[],
        )

        graph = generate_phase_story(phase, repo_path)
        save_story(graph, output_path)

        assert output_path.exists()
        assert output_path.parent.exists()
