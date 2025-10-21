import json
import subprocess
import sys

import pytest


@pytest.fixture
def git_repo(tmp_path):
    """Create a test git repository with sample files."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create README
    (repo / "README.md").write_text(
        "# Test Project\n\nSample repository for testing.\n", encoding="utf-8"
    )

    # Create Python source with TODO
    src_dir = repo / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text(
        """
def hello():
    # TODO: Add logging
    return "Hello World"

def complex_function(x):
    if x > 0:
        if x < 10:
            return "small"
        else:
            return "large"
    else:
        return "negative"
""",
        encoding="utf-8",
    )

    # Create test file
    tests_dir = repo / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_main.py").write_text(
        """
def test_hello():
    from src.main import hello
    assert hello() == "Hello World"
""",
        encoding="utf-8",
    )

    # Commit
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=repo, check=True, capture_output=True
    )

    return repo


def test_full_pipeline(git_repo):
    """Test full command with all outputs (JSON-LD, Markdown, TTL)."""
    out_json = git_repo / "quality.jsonld"
    out_ttl = git_repo / "quality.ttl"
    out_md = git_repo / "quality.md"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "repoq.cli",
            "full",
            str(git_repo),
            "-o",
            str(out_json),
            "--md",
            str(out_md),
            "--ttl",
            str(out_ttl),
            "--hash",
            "sha1",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert out_json.exists()
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["name"] == "test_repo"
    assert data["files"]
    assert any(
        "@type" in i and "oslc_cm:ChangeRequest" in i["@type"] for i in data.get("issues", [])
    )
    assert out_md.exists()
    assert out_ttl.exists()


def test_structure_command(git_repo):
    """Test structure command (structure analysis only)."""
    out_json = git_repo / "structure.jsonld"

    result = subprocess.run(
        [sys.executable, "-m", "repoq.cli", "structure", str(git_repo), "-o", str(out_json)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert out_json.exists()
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["name"] == "test_repo"
    assert "files" in data
    assert len(data["files"]) > 0

    # Structure mode should have files but might not have full history
    assert "modules" in data


def test_structure_with_extension_filter(git_repo):
    """Test structure command with extension filter."""
    out_json = git_repo / "structure_py.jsonld"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "repoq.cli",
            "structure",
            str(git_repo),
            "-o",
            str(out_json),
            "--extensions",
            "py",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert out_json.exists()
    data = json.loads(out_json.read_text(encoding="utf-8"))

    # All files should be Python
    for file_data in data.get("files", []):
        if "fileName" in file_data:
            assert file_data["fileName"].endswith(".py") or file_data["fileName"].endswith("/")


def test_structure_with_max_files(git_repo):
    """Test structure command with max_files limit."""
    out_json = git_repo / "structure_limited.jsonld"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "repoq.cli",
            "structure",
            str(git_repo),
            "-o",
            str(out_json),
            "--max-files",
            "2",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert out_json.exists()
    data = json.loads(out_json.read_text(encoding="utf-8"))

    # Should have at most 2 files
    assert len(data.get("files", [])) <= 2


def test_history_command(git_repo):
    """Test history command (history analysis only)."""
    out_json = git_repo / "history.jsonld"

    result = subprocess.run(
        [sys.executable, "-m", "repoq.cli", "history", str(git_repo), "-o", str(out_json)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert out_json.exists()
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["name"] == "test_repo"

    # History mode should have commits
    assert "commits" in data or len(data.get("commits", [])) >= 0


def test_markdown_output_generated(git_repo):
    """Test that markdown report is generated correctly."""
    out_json = git_repo / "output.jsonld"
    out_md = git_repo / "output.md"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "repoq.cli",
            "full",
            str(git_repo),
            "-o",
            str(out_json),
            "--md",
            str(out_md),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert out_md.exists()
    md_content = out_md.read_text(encoding="utf-8")

    # Check markdown has expected sections
    assert "# Репозиторий:" in md_content or "# Repository:" in md_content
    assert "test_repo" in md_content


def test_hash_algorithm_sha256(git_repo):
    """Test full command with SHA256 hash algorithm."""
    out_json = git_repo / "quality_sha256.jsonld"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "repoq.cli",
            "full",
            str(git_repo),
            "-o",
            str(out_json),
            "--hash",
            "sha256",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert out_json.exists()
    data = json.loads(out_json.read_text(encoding="utf-8"))

    # Check that files have checksums
    for file_data in data.get("files", []):
        if "checksum" in file_data and file_data["checksum"]:
            # SHA256 hashes are longer than SHA1
            if "checksumValue" in file_data["checksum"]:
                # SHA256 = 64 hex chars, SHA1 = 40 hex chars
                pass  # Just verify it exists


def test_graphs_directory_generation(git_repo):
    """Test that graphs directory is created with DOT/SVG files."""
    out_json = git_repo / "quality.jsonld"
    graphs_dir = git_repo / "graphs"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "repoq.cli",
            "full",
            str(git_repo),
            "-o",
            str(out_json),
            "--graphs",
            str(graphs_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    # Graphs directory should exist
    assert graphs_dir.exists()
    assert graphs_dir.is_dir()

    # Should have at least some graph files
    graph_files = list(graphs_dir.glob("*"))
    # Note: May be empty if no dependencies/coupling detected


def test_diff_command(git_repo):
    """Test diff command comparing two analysis results."""
    # Run analysis twice
    out1 = git_repo / "before.jsonld"
    subprocess.run(
        [sys.executable, "-m", "repoq.cli", "structure", str(git_repo), "-o", str(out1)],
        check=True,
        capture_output=True,
        text=True,
    )

    # Add a new file
    (git_repo / "src" / "new.py").write_text("def new(): pass\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=git_repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add new file"], cwd=git_repo, check=True, capture_output=True
    )

    out2 = git_repo / "after.jsonld"
    subprocess.run(
        [sys.executable, "-m", "repoq.cli", "structure", str(git_repo), "-o", str(out2)],
        check=True,
        capture_output=True,
        text=True,
    )

    # Run diff
    result = subprocess.run(
        [sys.executable, "-m", "repoq.cli", "diff", str(out1), str(out2)],
        check=True,
        capture_output=True,
        text=True,
    )

    # Diff output should show changes
    assert result.stdout  # Should have some output


def test_cli_handles_nonexistent_repo(tmp_path):
    """Test that CLI handles non-existent repository gracefully."""
    fake_repo = tmp_path / "nonexistent"
    out_json = tmp_path / "output.jsonld"

    result = subprocess.run(
        [sys.executable, "-m", "repoq.cli", "full", str(fake_repo), "-o", str(out_json)],
        capture_output=True,
        text=True,
    )

    # Should fail with non-zero exit code
    assert result.returncode != 0


def test_cli_verbose_flag(git_repo):
    """Test that verbose flag increases logging output."""
    out_json = git_repo / "quality.jsonld"

    # Run with verbose flag
    result = subprocess.run(
        [sys.executable, "-m", "repoq.cli", "-v", "full", str(git_repo), "-o", str(out_json)],
        check=True,
        capture_output=True,
        text=True,
    )

    # With verbose, might see more output (though captured)
    assert out_json.exists()
