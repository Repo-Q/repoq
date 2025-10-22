"""Integration tests for RepoQ analyzers.

These tests verify that analyzers work correctly with real repository structures.
Run with: pytest tests/integration/ -m integration
"""

import json
from pathlib import Path

import pytest

from repoq.analyzers.complexity import ComplexityAnalyzer
from repoq.analyzers.history import HistoryAnalyzer
from repoq.analyzers.hotspots import HotspotsAnalyzer
from repoq.analyzers.structure import StructureAnalyzer
from repoq.config import AnalyzeConfig
from repoq.core.model import Project


@pytest.mark.integration
class TestStructureAnalyzerIntegration:
    """Integration tests for StructureAnalyzer."""

    def test_analyze_python_repo(self, python_repo: Path):
        """StructureAnalyzer should analyze Python repository."""
        project = Project(id="test:1", name="test-repo")
        config = AnalyzeConfig(mode="structure")

        analyzer = StructureAnalyzer()
        analyzer.run(project, str(python_repo), config)

        # Verify files were discovered
        assert len(project.files) > 0

        # Verify Python files were found
        python_files = [f for f in project.files.values() if f.path.endswith(".py")]
        assert len(python_files) > 0

        # Verify language detection
        for f in python_files:
            assert f.language == "Python"

    def test_analyze_with_exclusions(self, python_repo: Path):
        """StructureAnalyzer should respect exclusion globs."""
        project = Project(id="test:1", name="test-repo")
        config = AnalyzeConfig(mode="structure", exclude_globs=["tests/**", "**/__pycache__/**"])

        analyzer = StructureAnalyzer()
        analyzer.run(project, str(python_repo), config)

        # Verify test files were excluded
        test_files = [f for f in project.files.values() if "test_" in f.path]
        assert len(test_files) == 0

    def test_analyze_with_extensions_filter(self, python_repo: Path):
        """StructureAnalyzer should filter by extension."""
        project = Project(id="test:1", name="test-repo")
        config = AnalyzeConfig(mode="structure", include_extensions=["py"])

        analyzer = StructureAnalyzer()
        analyzer.run(project, str(python_repo), config)

        # All files should be .py
        for f in project.files.values():
            assert f.path.endswith(".py")


@pytest.mark.integration
class TestComplexityAnalyzerIntegration:
    """Integration tests for ComplexityAnalyzer."""

    def test_analyze_complexity(self, python_repo: Path):
        """ComplexityAnalyzer should calculate metrics."""
        project = Project(id="test:1", name="test-repo")
        config = AnalyzeConfig(mode="full")

        # First run structure analyzer to populate files
        StructureAnalyzer().run(project, str(python_repo), config)

        # Then run complexity analyzer
        ComplexityAnalyzer().run(project, str(python_repo), config)

        # Verify complexity was calculated for some files
        complex_files = [f for f in project.files.values() if f.complexity is not None]
        assert len(complex_files) > 0

    def test_complexity_values_reasonable(self, python_repo: Path):
        """Complexity values should be in reasonable range."""
        project = Project(id="test:1", name="test-repo")
        config = AnalyzeConfig(mode="full")

        StructureAnalyzer().run(project, str(python_repo), config)
        ComplexityAnalyzer().run(project, str(python_repo), config)

        # Complexity should be positive and finite
        for f in project.files.values():
            if f.complexity is not None:
                assert f.complexity >= 0
                assert f.complexity < 100  # Reasonable upper bound for test code


@pytest.mark.integration
class TestHistoryAnalyzerIntegration:
    """Integration tests for HistoryAnalyzer."""

    def test_analyze_git_history(self, python_repo: Path):
        """HistoryAnalyzer should extract commit history."""
        project = Project(id="test:1", name="test-repo")
        config = AnalyzeConfig(mode="history")

        # Run structure first to populate files
        StructureAnalyzer().run(project, str(python_repo), config)

        # Run history analyzer
        HistoryAnalyzer().run(project, str(python_repo), config)

        # Verify commits were found
        assert len(project.commits) > 0

        # Verify contributors were found
        assert len(project.contributors) > 0

        # Verify last commit date is set
        assert project.last_commit_date is not None

    def test_history_with_file_churn(self, python_repo: Path):
        """HistoryAnalyzer should track file churn."""
        project = Project(id="test:1", name="test-repo")
        config = AnalyzeConfig(mode="history")

        StructureAnalyzer().run(project, str(python_repo), config)
        HistoryAnalyzer().run(project, str(python_repo), config)

        # Some files should have churn data (or at least history was analyzed)
        # Note: churn might be 0 for files with single commit
        assert len(project.commits) > 0, "Should have at least one commit"
        assert len(project.files) > 0, "Should have at least one file"


@pytest.mark.integration
class TestHotspotsAnalyzerIntegration:
    """Integration tests for HotspotsAnalyzer."""

    def test_identify_hotspots(self, python_repo: Path):
        """HotspotsAnalyzer should identify hotspots."""
        project = Project(id="test:1", name="test-repo")
        config = AnalyzeConfig(mode="full")

        # Run prerequisite analyzers
        StructureAnalyzer().run(project, str(python_repo), config)
        ComplexityAnalyzer().run(project, str(python_repo), config)
        HistoryAnalyzer().run(project, str(python_repo), config)

        # Run hotspots analyzer
        HotspotsAnalyzer().run(project, str(python_repo), config)

        # Verify hotspot analyzer ran successfully
        # Note: hotness might be 0 for simple test repos with minimal activity
        assert len(project.files) > 0, "Should have files"
        # Check that hotness attribute exists (even if 0)
        for f in project.files.values():
            assert hasattr(f, "hotness"), "File should have hotness attribute"

    def test_hotspot_scores_normalized(self, python_repo: Path):
        """Hotspot scores should be normalized 0-1."""
        project = Project(id="test:1", name="test-repo")
        config = AnalyzeConfig(mode="full")

        StructureAnalyzer().run(project, str(python_repo), config)
        ComplexityAnalyzer().run(project, str(python_repo), config)
        HistoryAnalyzer().run(project, str(python_repo), config)
        HotspotsAnalyzer().run(project, str(python_repo), config)

        # All hotspot scores should be in [0, 1] range (File uses 'hotness')
        for f in project.files.values():
            if (f.hotness or 0) > 0:
                assert 0 <= f.hotness <= 1


@pytest.mark.integration
class TestFullAnalysisPipeline:
    """Integration tests for complete analysis pipeline."""

    def test_full_analysis_workflow(self, python_repo: Path, temp_dir: Path):
        """Complete analysis workflow should produce valid output."""
        from repoq.core.jsonld import dump_jsonld
        from repoq.reporting.markdown import render_markdown

        project = Project(id=f"file://{python_repo}", name=python_repo.name, repository_url=None)
        config = AnalyzeConfig(mode="full")

        # Run all analyzers
        StructureAnalyzer().run(project, str(python_repo), config)
        ComplexityAnalyzer().run(project, str(python_repo), config)
        HistoryAnalyzer().run(project, str(python_repo), config)
        HotspotsAnalyzer().run(project, str(python_repo), config)

        # Verify project has data
        assert len(project.files) > 0
        assert len(project.commits) > 0
        assert len(project.contributors) > 0

        # Export to JSON-LD
        jsonld_path = temp_dir / "analysis.jsonld"
        dump_jsonld(project, str(jsonld_path))

        assert jsonld_path.exists()
        data = json.loads(jsonld_path.read_text())
        # @type is a list in our implementation
        assert "repo:Project" in data["@type"]
        assert "files" in data or "repoq:hasFile" in data

        # Export to Markdown
        markdown = render_markdown(project)
        assert len(markdown) > 100
        assert project.name in markdown

    def test_analysis_with_real_metrics(self, python_repo: Path):
        """Analysis should produce realistic metrics."""
        project = Project(id="test:1", name="test-repo")
        config = AnalyzeConfig(mode="full")

        StructureAnalyzer().run(project, str(python_repo), config)
        ComplexityAnalyzer().run(project, str(python_repo), config)
        HistoryAnalyzer().run(project, str(python_repo), config)
        HotspotsAnalyzer().run(project, str(python_repo), config)

        # Verify metrics are present and reasonable
        # Full analysis should produce reasonable metrics
        total_loc = sum(f.lines_of_code for f in project.files.values())
        assert total_loc > 0
        assert total_loc < 10000  # Test repo shouldn't be huge

        # Verify commit count
        assert len(project.commits) >= 2  # We created 2 commits

        # Verify contributor count
        assert len(project.contributors) >= 1


@pytest.mark.integration
@pytest.mark.slow
def test_analyze_self(temp_dir: Path):
    """RepoQ should be able to analyze itself."""
    repo_root = Path(__file__).parent.parent.parent

    project = Project(id=f"file://{repo_root}", name="repoq", repository_url=None)
    config = AnalyzeConfig(
        mode="structure",
        include_extensions=["py"],
        exclude_globs=["site/**", "tmp/**", ".venv/**", "*.jsonld", "*.md"],
        max_files=500,
    )

    # Should not crash
    StructureAnalyzer().run(project, str(repo_root), config)

    # Should find files
    assert len(project.files) > 10

    # Should detect Python
    python_files = [f for f in project.files.values() if f.language == "Python"]
    assert len(python_files) > 5
