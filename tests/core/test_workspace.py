"""
Tests for RepoQWorkspace (Phase 5, Phase 1 deliverable).

TDD Approach:
1. Red: Write failing tests
2. Green: Implement minimal code to pass
3. Refactor: Clean up implementation

Requirements:
- FR-10 (Incremental Analysis): Cache directory for SHA-based metrics
- V07 (Reliability): Reproducible workspace structure
- Theorem A (Correctness): Manifest captures ontology checksums
"""

import json
from datetime import datetime

import pytest

# Import will fail initially (TDD Red phase)
# from repoq.core.workspace import RepoQWorkspace, ManifestEntry


class TestRepoQWorkspaceInitialization:
    """Test workspace directory structure creation."""

    def test_initialize_creates_all_directories(self, tmp_path):
        """Test that initialize() creates all required directories."""
        # Arrange
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()

        # Act
        from repoq.core.workspace import RepoQWorkspace

        workspace = RepoQWorkspace(repo_path)
        workspace.initialize()

        # Assert: All directories created (FR-10)
        assert (repo_path / ".repoq").exists()
        assert (repo_path / ".repoq" / "raw").exists()
        assert (repo_path / ".repoq" / "validated").exists()
        assert (repo_path / ".repoq" / "reports").exists()
        assert (repo_path / ".repoq" / "certificates").exists()
        assert (repo_path / ".repoq" / "cache").exists()

    def test_initialize_idempotent(self, tmp_path):
        """Test that initialize() can be called multiple times safely."""
        # Arrange
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        from repoq.core.workspace import RepoQWorkspace

        workspace = RepoQWorkspace(repo_path)

        # Act: Call initialize twice
        workspace.initialize()
        workspace.initialize()  # Should not raise

        # Assert: Directories still exist
        assert (repo_path / ".repoq").exists()

    def test_workspace_paths_accessible(self, tmp_path):
        """Test that workspace paths are accessible as properties."""
        # Arrange
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        from repoq.core.workspace import RepoQWorkspace

        workspace = RepoQWorkspace(repo_path)
        workspace.initialize()

        # Assert: All paths accessible
        assert workspace.root == repo_path / ".repoq"
        assert workspace.raw == repo_path / ".repoq" / "raw"
        assert workspace.validated == repo_path / ".repoq" / "validated"
        assert workspace.reports == repo_path / ".repoq" / "reports"
        assert workspace.certificates == repo_path / ".repoq" / "certificates"
        assert workspace.cache == repo_path / ".repoq" / "cache"

    def test_initialize_creates_gitignore(self, tmp_path):
        """Test that .gitignore is created in .repoq/ to exclude cache."""
        # Arrange
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        from repoq.core.workspace import RepoQWorkspace

        workspace = RepoQWorkspace(repo_path)

        # Act
        workspace.initialize()

        # Assert: .gitignore exists with cache excluded
        gitignore_path = repo_path / ".repoq" / ".gitignore"
        assert gitignore_path.exists()
        content = gitignore_path.read_text()
        assert "cache/" in content  # Cache should be ignored


class TestManifestGeneration:
    """Test manifest.json generation (Theorem A: Correctness)."""

    def test_save_manifest_creates_file(self, tmp_path):
        """Test that save_manifest() creates manifest.json."""
        # Arrange
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        from repoq.core.workspace import RepoQWorkspace

        workspace = RepoQWorkspace(repo_path)
        workspace.initialize()

        # Act
        workspace.save_manifest(
            commit_sha="abc123def456",
            policy_version="1.2.0",
            ontology_checksums={"code.ttl": "sha256:abc123"},
        )

        # Assert: manifest.json exists
        manifest_path = repo_path / ".repoq" / "manifest.json"
        assert manifest_path.exists()

    def test_manifest_contains_required_fields(self, tmp_path):
        """Test that manifest.json contains all required fields (V07 Reliability)."""
        # Arrange
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        from repoq.core.workspace import RepoQWorkspace

        workspace = RepoQWorkspace(repo_path)
        workspace.initialize()

        # Act
        workspace.save_manifest(
            commit_sha="abc123def456",
            policy_version="1.2.0",
            ontology_checksums={
                "code.ttl": "sha256:abc123",
                "c4.ttl": "sha256:def456",
            },
            trs_version="0.3.0-lean4",
        )

        # Assert: All fields present
        manifest_path = repo_path / ".repoq" / "manifest.json"
        data = json.loads(manifest_path.read_text())

        assert data["schema_version"] == "1.0"
        assert data["commit_sha"] == "abc123def456"
        assert data["policy_version"] == "1.2.0"
        assert data["ontology_checksums"]["code.ttl"] == "sha256:abc123"
        assert data["ontology_checksums"]["c4.ttl"] == "sha256:def456"
        assert data["trs_version"] == "0.3.0-lean4"
        assert "analysis_timestamp" in data

    def test_manifest_timestamp_format(self, tmp_path):
        """Test that timestamp is in ISO 8601 format."""
        # Arrange
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        from repoq.core.workspace import RepoQWorkspace

        workspace = RepoQWorkspace(repo_path)
        workspace.initialize()

        # Act
        workspace.save_manifest(
            commit_sha="abc123",
            policy_version="1.0.0",
            ontology_checksums={},
        )

        # Assert: Timestamp is valid ISO 8601
        manifest_path = repo_path / ".repoq" / "manifest.json"
        data = json.loads(manifest_path.read_text())

        # Should parse without error
        timestamp = datetime.fromisoformat(data["analysis_timestamp"])
        assert timestamp.year == 2025  # Current year

    def test_manifest_schema_version(self, tmp_path):
        """Test that manifest includes schema_version for backward compatibility (ADR-016)."""
        # Arrange
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        from repoq.core.workspace import RepoQWorkspace

        workspace = RepoQWorkspace(repo_path)
        workspace.initialize()

        # Act
        workspace.save_manifest(
            commit_sha="test123",
            policy_version="2.0.0",
            ontology_checksums={"test.ttl": "sha256:test"},
        )

        # Assert: schema_version is "1.0"
        manifest_path = repo_path / ".repoq" / "manifest.json"
        data = json.loads(manifest_path.read_text())

        assert data["schema_version"] == "1.0"
        # Verify field order (schema_version should be first for readability)
        keys = list(data.keys())
        assert keys[0] == "schema_version" or keys[0] == "analysis_timestamp"  # JSON sorts keys

    def test_load_manifest_roundtrip(self, tmp_path):
        """Test that save → load roundtrip preserves data (NFR-03 Determinism)."""
        # Arrange
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        from repoq.core.workspace import RepoQWorkspace

        workspace = RepoQWorkspace(repo_path)
        workspace.initialize()

        original_data = {
            "commit_sha": "xyz789",
            "policy_version": "2.0.0",
            "ontology_checksums": {"test.ttl": "sha256:xyz"},
            "trs_version": "0.4.0",
        }

        # Act: Save then load
        workspace.save_manifest(**original_data)
        loaded = workspace.load_manifest()

        # Assert: Data preserved (except timestamp, which is generated)
        assert loaded.commit_sha == original_data["commit_sha"]
        assert loaded.policy_version == original_data["policy_version"]
        assert loaded.ontology_checksums == original_data["ontology_checksums"]
        assert loaded.trs_version == original_data["trs_version"]
        assert loaded.analysis_timestamp is not None

    def test_load_manifest_missing_file(self, tmp_path):
        """Test that load_manifest() raises error if manifest.json missing."""
        # Arrange
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        from repoq.core.workspace import RepoQWorkspace

        workspace = RepoQWorkspace(repo_path)
        workspace.initialize()

        # Act & Assert: Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            workspace.load_manifest()

    def test_load_manifest_invalid_json(self, tmp_path):
        """Test that load_manifest() raises error on invalid JSON."""
        # Arrange
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        from repoq.core.workspace import RepoQWorkspace

        workspace = RepoQWorkspace(repo_path)
        workspace.initialize()

        # Write invalid JSON
        manifest_path = repo_path / ".repoq" / "manifest.json"
        manifest_path.write_text("{ invalid json }")

        # Act & Assert: Should raise JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            workspace.load_manifest()


class TestOntologyChecksums:
    """Test ontology checksum calculation (Theorem A: Correctness)."""

    def test_compute_ontology_checksums(self, tmp_path):
        """Test that compute_ontology_checksums() calculates SHA256."""
        # Arrange
        ontologies_dir = tmp_path / "ontologies"
        ontologies_dir.mkdir()

        # Create test ontology files
        (ontologies_dir / "code.ttl").write_text("@prefix code: <...> .")
        (ontologies_dir / "c4.ttl").write_text("@prefix c4: <...> .")

        # Act
        from repoq.core.workspace import compute_ontology_checksums

        checksums = compute_ontology_checksums(ontologies_dir)

        # Assert: Checksums calculated for both files
        assert "code.ttl" in checksums
        assert "c4.ttl" in checksums
        assert checksums["code.ttl"].startswith("sha256:")
        assert checksums["c4.ttl"].startswith("sha256:")

    def test_ontology_checksums_deterministic(self, tmp_path):
        """Test that same file → same checksum (NFR-03 Determinism)."""
        # Arrange
        ontologies_dir = tmp_path / "ontologies"
        ontologies_dir.mkdir()
        (ontologies_dir / "test.ttl").write_text("Test content")

        # Act: Compute twice
        from repoq.core.workspace import compute_ontology_checksums

        checksums1 = compute_ontology_checksums(ontologies_dir)
        checksums2 = compute_ontology_checksums(ontologies_dir)

        # Assert: Same checksums
        assert checksums1 == checksums2

    def test_ontology_checksums_empty_dir(self, tmp_path):
        """Test that empty ontologies directory returns empty dict."""
        # Arrange
        ontologies_dir = tmp_path / "ontologies"
        ontologies_dir.mkdir()

        # Act
        from repoq.core.workspace import compute_ontology_checksums

        checksums = compute_ontology_checksums(ontologies_dir)

        # Assert: Empty dict
        assert checksums == {}


class TestWorkspaceIntegration:
    """Integration tests for workspace with real scenarios."""

    def test_concurrent_workspace_access(self, tmp_path):
        """Test that multiple workspace instances can access same repo safely."""
        # Arrange
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        from repoq.core.workspace import RepoQWorkspace

        workspace1 = RepoQWorkspace(repo_path)
        workspace2 = RepoQWorkspace(repo_path)

        # Act: Both initialize
        workspace1.initialize()
        workspace2.initialize()  # Should not conflict

        # Assert: Both can save/load manifests
        workspace1.save_manifest(
            commit_sha="aaa",
            policy_version="1.0",
            ontology_checksums={},
        )

        loaded = workspace2.load_manifest()
        assert loaded.commit_sha == "aaa"

    def test_workspace_preserves_existing_files(self, tmp_path):
        """Test that initialize() doesn't delete existing files in .repoq/."""
        # Arrange
        repo_path = tmp_path / "test_repo"
        repo_path.mkdir()
        from repoq.core.workspace import RepoQWorkspace

        workspace = RepoQWorkspace(repo_path)
        workspace.initialize()

        # Create test file
        test_file = repo_path / ".repoq" / "raw" / "test.ttl"
        test_file.write_text("Test data")

        # Act: Re-initialize
        workspace.initialize()

        # Assert: File still exists
        assert test_file.exists()
        assert test_file.read_text() == "Test data"
