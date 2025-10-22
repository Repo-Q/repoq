"""End-to-end tests for RepoQ CLI.

These tests simulate real user workflows from command line to output files.
Run with: pytest tests/e2e/ -m e2e
"""

import json
import subprocess
from pathlib import Path

import pytest


@pytest.mark.e2e
class TestCLIAnalyzeE2E:
    """E2E tests for 'repoq analyze' command."""

    def test_analyze_local_repo(self, python_repo: Path, temp_dir: Path):
        """End-to-end: analyze local repository."""
        output_jsonld = temp_dir / "output.jsonld"
        output_md = temp_dir / "output.md"

        # Run CLI command
        result = subprocess.run(
            [
                "uv",
                "run",
                "repoq",
                "analyze",
                str(python_repo),
                "--output",
                str(output_jsonld),
                "--md",
                str(output_md),
                "--extensions",
                "py",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Verify command succeeded
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Verify output files were created
        assert output_jsonld.exists(), "JSON-LD output not created"
        assert output_md.exists(), "Markdown output not created"

        # Verify JSON-LD structure (@type is a list)
        data = json.loads(output_jsonld.read_text())
        assert "repo:Project" in data["@type"]
        # Check for files key (not prefixed in our export)
        assert "files" in data or "repoq:hasFile" in data

        # Verify Markdown content
        md_content = output_md.read_text()
        assert "Репозиторий" in md_content or "Repository" in md_content
        assert len(md_content) > 100

    def test_analyze_with_exclusions(self, python_repo: Path, temp_dir: Path):
        """E2E: analyze with exclusion patterns."""
        output = temp_dir / "filtered.jsonld"

        result = subprocess.run(
            [
                "uv",
                "run",
                "repoq",
                "analyze",
                str(python_repo),
                "--output",
                str(output),
                "--exclude",
                "tests/**,**/__pycache__/**",
                "--extensions",
                "py",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert output.exists()

        # Verify test files were excluded
        data = json.loads(output.read_text())
        files = data.get("repoq:hasFile", [])
        test_files = [f for f in files if "test_" in f.get("repoq:path", "")]
        assert len(test_files) == 0

    def test_analyze_current_directory(self, python_repo: Path, temp_dir: Path):
        """E2E: analyze using '.' (current directory)."""
        output = temp_dir / "current.jsonld"

        # Change to repo directory
        result = subprocess.run(
            [
                "uv",
                "run",
                "repoq",
                "analyze",
                ".",
                "--output",
                str(output),
                "--extensions",
                "py",
            ],
            capture_output=True,
            text=True,
            cwd=str(python_repo),
            timeout=30,
        )

        assert result.returncode == 0
        assert output.exists()


@pytest.mark.e2e
class TestCLIStructureE2E:
    """E2E tests for 'repoq structure' command."""

    def test_structure_analysis(self, python_repo: Path, temp_dir: Path):
        """E2E: structure-only analysis."""
        output = temp_dir / "structure.jsonld"

        result = subprocess.run(
            [
                "uv",
                "run",
                "repoq",
                "structure",
                str(python_repo),
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert output.exists()

        data = json.loads(output.read_text())
        assert "repo:Project" in data["@type"]


@pytest.mark.e2e
class TestCLIHistoryE2E:
    """E2E tests for 'repoq history' command."""

    def test_history_analysis(self, python_repo: Path, temp_dir: Path):
        """E2E: history-only analysis."""
        output = temp_dir / "history.jsonld"

        result = subprocess.run(
            [
                "uv",
                "run",
                "repoq",
                "history",
                str(python_repo),
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert output.exists()

        data = json.loads(output.read_text())
        # History analysis should include commit information
        # Check for commits or contributors (keys without prefix in our export)
        assert (
            "prov:wasAssociatedWith" in data
            or "repoq:hasContributor" in data
            or "repoq:hasCommit" in data
            or "commits" in data
            or "contributors" in data
            or data.get("repoq:totalCommits", 0) > 0
        )


@pytest.mark.e2e
class TestCLIFullWorkflow:
    """E2E tests for complete workflows."""

    def test_full_analysis_workflow(self, python_repo: Path, temp_dir: Path):
        """E2E: Full analysis with all output formats."""
        jsonld_output = temp_dir / "full.jsonld"
        md_output = temp_dir / "full.md"
        ttl_output = temp_dir / "full.ttl"

        result = subprocess.run(
            [
                "uv",
                "run",
                "repoq",
                "full",
                str(python_repo),
                "--output",
                str(jsonld_output),
                "--md",
                str(md_output),
                "--ttl",
                str(ttl_output),
                "--extensions",
                "py",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0, f"Full analysis failed: {result.stderr}"

        # Verify all outputs
        assert jsonld_output.exists()
        assert md_output.exists()
        assert ttl_output.exists()

        # Verify JSON-LD (@type is a list)
        jsonld_data = json.loads(jsonld_output.read_text())
        assert "repo:Project" in jsonld_data["@type"]
        assert "files" in jsonld_data or "repoq:hasFile" in jsonld_data

        # Verify Markdown
        md_content = md_output.read_text()
        assert len(md_content) > 100

        # Verify Turtle
        ttl_content = ttl_output.read_text()
        assert len(ttl_content) > 100
        assert "@prefix" in ttl_content or "PREFIX" in ttl_content

    def test_analysis_with_quality_gate(self, python_repo: Path, temp_dir: Path):
        """E2E: Analysis with quality gate threshold."""
        output = temp_dir / "gated.jsonld"

        # This should pass (test code is simple)
        result = subprocess.run(
            [
                "uv",
                "run",
                "repoq",
                "analyze",
                str(python_repo),
                "--output",
                str(output),
                "--fail-on-issues",
                "high",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should succeed or fail based on code quality
        assert result.returncode in [0, 2]  # 0=pass, 2=quality gate failed

    def test_baseline_comparison_workflow(self, python_repo: Path, temp_dir: Path):
        """E2E: Baseline comparison workflow."""
        baseline = temp_dir / "baseline.jsonld"
        current = temp_dir / "current.jsonld"

        # Create baseline
        result1 = subprocess.run(
            [
                "uv",
                "run",
                "repoq",
                "analyze",
                str(python_repo),
                "--output",
                str(baseline),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result1.returncode == 0

        # Modify repository (add file)
        new_file = python_repo / "newfile.py"
        new_file.write_text('def new_func():\n    """New function."""\n    return 42\n')

        import os

        os.system(f"cd {python_repo} && git add . && git commit -q -m 'Add new file'")

        # Create current analysis
        result2 = subprocess.run(
            [
                "uv",
                "run",
                "repoq",
                "analyze",
                str(python_repo),
                "--output",
                str(current),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result2.returncode == 0

        # Compare with diff command
        result3 = subprocess.run(
            [
                "uv",
                "run",
                "repoq",
                "diff",
                str(baseline),
                str(current),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        assert result3.returncode == 0


@pytest.mark.e2e
class TestCLIErrorHandling:
    """E2E tests for CLI error handling."""

    def test_invalid_repository_path(self, temp_dir: Path):
        """E2E: Handle invalid repository path gracefully."""
        nonexistent = temp_dir / "nonexistent"
        output = temp_dir / "output.jsonld"

        result = subprocess.run(
            [
                "uv",
                "run",
                "repoq",
                "analyze",
                str(nonexistent),
                "--output",
                str(output),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should fail gracefully
        assert result.returncode != 0

    def test_missing_required_argument(self):
        """E2E: Handle missing required arguments."""
        result = subprocess.run(
            ["uv", "run", "repoq", "diff"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should show error
        assert result.returncode != 0
        assert "Error" in result.stdout or "error" in result.stderr.lower()


@pytest.mark.e2e
@pytest.mark.slow
def test_self_analysis_e2e(temp_dir: Path):
    """E2E: RepoQ should analyze itself successfully."""
    repo_root = Path(__file__).parent.parent.parent
    output = temp_dir / "self_analysis.jsonld"

    result = subprocess.run(
        [
            "uv",
            "run",
            "repoq",
            "analyze",
            str(repo_root),
            "--output",
            str(output),
            "--exclude",
            "site/**,tmp/**,.venv/**,*.jsonld,*.md",
            "--extensions",
            "py",
            "--max-files",
            "200",
        ],
        capture_output=True,
        text=True,
        timeout=120,  # Self-analysis takes longer
    )

    # Should complete successfully
    assert result.returncode == 0, f"Self-analysis failed: {result.stderr}"
    assert output.exists()

    # Verify output (@type is a list)
    data = json.loads(output.read_text())
    assert "repo:Project" in data["@type"]

    # Should have found significant number of files
    files = data.get("repoq:hasFile", [])
    assert len(files) > 10
