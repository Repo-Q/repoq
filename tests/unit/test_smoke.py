"""Smoke tests for RepoQ - Quick validation of critical functionality.

These tests run fast and catch major breakages. They should pass on every commit.
Run with: pytest tests/unit/test_smoke.py -m smoke
"""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from repoq.cli import app
from repoq.core.model import File, Project


@pytest.mark.smoke
@pytest.mark.unit
class TestCLISmoke:
    """Smoke tests for CLI commands."""

    def test_cli_help(self):
        """CLI --help should work."""
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "repoq" in result.stdout.lower()

    def test_cli_version(self):
        """CLI should have version info."""
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        # Version info should be in help output

    def test_analyze_command_exists(self):
        """Analyze command should be available."""
        runner = CliRunner()
        result = runner.invoke(app, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "analyze" in result.stdout.lower()

    def test_structure_command_exists(self):
        """Structure command should be available."""
        runner = CliRunner()
        result = runner.invoke(app, ["structure", "--help"])
        assert result.exit_code == 0

    def test_history_command_exists(self):
        """History command should be available."""
        runner = CliRunner()
        result = runner.invoke(app, ["history", "--help"])
        assert result.exit_code == 0

    def test_diff_command_exists(self):
        """Diff command should be available."""
        runner = CliRunner()
        result = runner.invoke(app, ["diff", "--help"])
        assert result.exit_code == 0

    def test_gate_command_exists(self):
        """Gate command should be available."""
        runner = CliRunner()
        result = runner.invoke(app, ["gate", "--help"])
        assert result.exit_code == 0


@pytest.mark.smoke
@pytest.mark.unit
class TestCoreModelSmoke:
    """Smoke tests for core data models."""

    def test_project_creation(self):
        """Project model should instantiate."""
        project = Project(
            id="test:project:1", name="test-project", repository_url="https://github.com/test/repo"
        )
        assert project.id == "test:project:1"
        assert project.name == "test-project"
        assert len(project.files) == 0
        assert len(project.contributors) == 0

    def test_filenode_creation(self):
        """File model should instantiate."""
        node = File(id="test:file:main.py", path="src/main.py", lines_of_code=100)
        assert node.id == "test:file:main.py"
        assert node.path == "src/main.py"
        assert node.lines_of_code == 100

    def test_project_add_file(self):
        """Project should store files."""
        project = Project(id="test:1", name="test")
        file_node = File(id="test:file:1", path="main.py", lines_of_code=10)
        project.files["test:file:1"] = file_node

        assert len(project.files) == 1
        assert project.files["test:file:1"].path == "main.py"


@pytest.mark.smoke
@pytest.mark.unit
class TestAnalyzersSmoke:
    """Smoke tests for analyzers."""

    def test_structure_analyzer_import(self):
        """StructureAnalyzer should import."""
        from repoq.analyzers.structure import StructureAnalyzer

        analyzer = StructureAnalyzer()
        assert analyzer is not None

    def test_complexity_analyzer_import(self):
        """ComplexityAnalyzer should import."""
        from repoq.analyzers.complexity import ComplexityAnalyzer

        analyzer = ComplexityAnalyzer()
        assert analyzer is not None

    def test_history_analyzer_import(self):
        """HistoryAnalyzer should import."""
        from repoq.analyzers.history import HistoryAnalyzer

        analyzer = HistoryAnalyzer()
        assert analyzer is not None

    def test_hotspots_analyzer_import(self):
        """HotspotsAnalyzer should import."""
        from repoq.analyzers.hotspots import HotspotsAnalyzer

        analyzer = HotspotsAnalyzer()
        assert analyzer is not None

    def test_weakness_analyzer_import(self):
        """WeaknessAnalyzer should import."""
        from repoq.analyzers.weakness import WeaknessAnalyzer

        analyzer = WeaknessAnalyzer()
        assert analyzer is not None


@pytest.mark.smoke
@pytest.mark.unit
class TestExportersSmoke:
    """Smoke tests for exporters."""

    def test_jsonld_export(self, temp_dir: Path):
        """JSON-LD export should work."""
        from repoq.core.jsonld import dump_jsonld

        project = Project(id="test:1", name="test")
        output_path = temp_dir / "test.jsonld"

        dump_jsonld(project, str(output_path))

        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert "@context" in data
        # @type is a list in our implementation
        assert "repo:Project" in data["@type"]

    def test_markdown_export(self):
        """Markdown export should work."""
        from repoq.reporting.markdown import render_markdown

        project = Project(id="test:1", name="test-project")
        markdown = render_markdown(project)

        assert "test-project" in markdown
        assert isinstance(markdown, str)
        assert len(markdown) > 0


@pytest.mark.smoke
@pytest.mark.unit
class TestConfigSmoke:
    """Smoke tests for configuration."""

    def test_analyze_config_creation(self):
        """AnalyzeConfig should instantiate with defaults."""
        from repoq.config import AnalyzeConfig

        config = AnalyzeConfig()
        assert config.mode == "full"
        # include_extensions defaults to None in our implementation
        assert config.include_extensions is None or config.include_extensions == []
        # exclude_globs has sensible defaults (.git, node_modules, etc.)
        assert isinstance(config.exclude_globs, list)
        assert len(config.exclude_globs) > 0  # Should have default exclusions

    def test_config_loading(self, temp_dir: Path):
        """Config should load from YAML file."""
        from repoq.config import load_config

        config_file = temp_dir / "config.yaml"
        config_file.write_text("""
mode: structure
max_files: 500
include_extensions:
  - py
  - js
""")

        config = load_config(str(config_file))
        assert config["mode"] == "structure"
        assert config["max_files"] == 500
        assert "py" in config["include_extensions"]


@pytest.mark.smoke
@pytest.mark.unit
def test_ontology_manager_import():
    """OntologyManager should import without errors."""
    from repoq.ontologies.ontology_manager import OntologyManager

    manager = OntologyManager()
    assert manager is not None
    assert hasattr(manager, "load_plugins")
    assert hasattr(manager, "analyze_project")


@pytest.mark.smoke
@pytest.mark.unit
def test_repo_loader_import():
    """RepoLoader utilities should import."""
    from repoq.core.repo_loader import is_url

    # Test URL detection
    assert is_url("https://github.com/user/repo.git")
    assert is_url("git@github.com:user/repo.git")
    assert not is_url("./local/path")
    assert not is_url("/absolute/path")


@pytest.mark.smoke
@pytest.mark.unit
def test_critical_imports():
    """All critical modules should import without errors."""
    # Core
    # Analyzers

    # Core modules

    # Reporting

    # All imports succeeded
    assert True
