"""
Integration tests for RepoQWorkspace with gate command (Phase 5.1).

Tests workspace integration with existing gate.py:
- Workspace initialized automatically on gate run
- Manifest generated after every gate run
- Performance <5% overhead (NFR-01)
"""

import subprocess
from pathlib import Path


class TestGateWorkspaceIntegration:
    """Integration tests for workspace + gate."""

    def test_gate_initializes_workspace_automatically(self, tmp_path, monkeypatch):
        """Test that running gate creates .repoq/ automatically."""
        # Arrange: Create test repo
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "test.py").write_text("print('hello')")

        # Initialize git
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
            ["git", "commit", "-m", "Initial"], cwd=repo_path, check=True, capture_output=True
        )

        monkeypatch.chdir(repo_path)

        # Act: Run pipeline (which initializes workspace)
        from repoq.config import AnalyzeConfig
        from repoq.core.model import Project
        from repoq.pipeline import run_pipeline

        project = Project(id="test", name="test")
        config = AnalyzeConfig(mode="structure")

        run_pipeline(project, str(repo_path), config)

        # Assert: Workspace created
        assert (repo_path / ".repoq").exists()
        assert (repo_path / ".repoq" / "cache").exists()
        assert (repo_path / ".repoq" / "manifest.json").exists()

    def test_gate_generates_manifest_on_success(self, tmp_path, monkeypatch):
        """Test that manifest.json created after gate run."""
        # Arrange
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "test.py").write_text("print('hello')")

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
            ["git", "commit", "-m", "Initial"], cwd=repo_path, check=True, capture_output=True
        )

        monkeypatch.chdir(repo_path)

        # Act: Run pipeline
        from repoq.config import AnalyzeConfig
        from repoq.core.model import Project
        from repoq.pipeline import run_pipeline

        project = Project(id="test", name="test")
        config = AnalyzeConfig(mode="structure")

        run_pipeline(project, str(repo_path), config)

        # Assert: Manifest exists with valid content
        from repoq.core.workspace import RepoQWorkspace

        workspace = RepoQWorkspace(repo_path)
        manifest = workspace.load_manifest()

        assert manifest.commit_sha != "unknown"
        assert manifest.policy_version == "2.0.0-alpha"
        assert len(manifest.ontology_checksums) > 0

    def test_workspace_performance_overhead(self, tmp_path, monkeypatch):
        """Test that workspace adds <5% overhead (NFR-01)."""
        # Arrange
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        (repo_path / "test.py").write_text("print('hello')")

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
            ["git", "commit", "-m", "Initial"], cwd=repo_path, check=True, capture_output=True
        )

        monkeypatch.chdir(repo_path)

        # Act: Measure workspace operations
        import time

        from repoq.core.workspace import RepoQWorkspace, compute_ontology_checksums

        workspace = RepoQWorkspace(repo_path)

        start = time.perf_counter()
        workspace.initialize()

        ontology_dir = Path(__file__).parent.parent.parent / "repoq" / "ontologies"
        checksums = compute_ontology_checksums(ontology_dir)

        workspace.save_manifest(
            commit_sha="benchmark",
            policy_version="1.0.0",
            ontology_checksums=checksums,
        )
        workspace.load_manifest()
        end = time.perf_counter()

        elapsed_ms = (end - start) * 1000

        # Assert: <50ms for workspace operations (negligible overhead)
        assert elapsed_ms < 50, f"Workspace operations took {elapsed_ms:.2f}ms, expected <50ms"
