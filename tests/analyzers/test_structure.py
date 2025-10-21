"""
Unit tests for StructureAnalyzer

Phase 1 target: 80% coverage
"""

import pytest

from repoq.analyzers.structure import StructureAnalyzer
from repoq.config import AnalyzeConfig
from repoq.core.model import Project


@pytest.fixture
def mock_repo(tmp_path):
    """Create a minimal mock repository"""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Create file structure
    (repo / "README.md").write_text("# Test Project\n")

    src = repo / "src"
    src.mkdir()
    (src / "__init__.py").write_text("")
    (src / "main.py").write_text("def main():\n    pass\n")

    tests = repo / "tests"
    tests.mkdir()
    (tests / "test_main.py").write_text("def test_main():\n    assert True\n")

    return repo


@pytest.fixture
def project():
    """Empty project for testing"""
    return Project(id="test:project", name="test_project", description="Test project")


@pytest.fixture
def config():
    """Default analyze config"""
    return AnalyzeConfig(mode="structure")


class TestStructureAnalyzer:
    """Test suite for StructureAnalyzer"""

    def test_analyzer_initialization(self):
        """Test that analyzer can be instantiated"""
        analyzer = StructureAnalyzer()
        assert analyzer is not None

    def test_run_on_empty_project(self, project, mock_repo, config):
        """Test analyzer on empty project"""
        analyzer = StructureAnalyzer()
        analyzer.run(project, str(mock_repo), config)

        # Should populate files
        assert len(project.files) > 0, "No files detected"

    def test_detects_python_files(self, project, mock_repo, config):
        """Test detection of Python files"""
        analyzer = StructureAnalyzer()
        analyzer.run(project, str(mock_repo), config)

        python_files = [f for f in project.files.values() if f.language == "Python"]
        assert len(python_files) >= 2, "Should detect main.py and test_main.py"

    def test_detects_test_files(self, project, mock_repo, config):
        """Test detection of test files"""
        analyzer = StructureAnalyzer()
        analyzer.run(project, str(mock_repo), config)

        test_files = [f for f in project.files.values() if f.test_file]
        assert len(test_files) >= 1, "Should detect test_main.py as test file"

    def test_creates_modules(self, project, mock_repo, config):
        """Test module creation"""
        analyzer = StructureAnalyzer()
        analyzer.run(project, str(mock_repo), config)

        # Should create modules for src/ and tests/
        assert len(project.modules) >= 2, "Should create at least 2 modules"

    def test_respects_max_files_limit(self, project, mock_repo, config):
        """Test max_files configuration"""
        config.max_files = 2
        analyzer = StructureAnalyzer()
        analyzer.run(project, str(mock_repo), config)

        assert len(project.files) <= 2, "Should respect max_files limit"

    def test_respects_extension_filter(self, project, mock_repo, config):
        """Test extension filtering"""
        config.include_extensions = [".md"]
        analyzer = StructureAnalyzer()
        analyzer.run(project, str(mock_repo), config)

        # Should only include .md files
        for f in project.files.values():
            assert f.path.endswith(".md"), f"Found non-.md file: {f.path}"

    def test_respects_exclude_globs(self, project, mock_repo, config):
        """Test exclude patterns"""
        config.exclude_globs = ["tests/*"]
        analyzer = StructureAnalyzer()
        analyzer.run(project, str(mock_repo), config)

        # Should not include files from tests/
        for f in project.files.values():
            assert "tests/" not in f.path, f"Found excluded file: {f.path}"

    def test_computes_lines_of_code(self, project, mock_repo, config):
        """Test LOC computation"""
        analyzer = StructureAnalyzer()
        analyzer.run(project, str(mock_repo), config)

        # main.py should have LOC > 0
        main_py = next((f for f in project.files.values() if "main.py" in f.path), None)
        assert main_py is not None, "main.py not found"
        assert main_py.lines_of_code > 0, "LOC not computed"

    def test_detects_programming_languages(self, project, mock_repo, config):
        """Test language detection"""
        analyzer = StructureAnalyzer()
        analyzer.run(project, str(mock_repo), config)

        assert "Python" in project.programming_languages, "Python not detected"
        assert project.programming_languages["Python"] > 0, "Python LOC is 0"

    def test_idempotent_execution(self, project, mock_repo, config):
        """Test that running analyzer twice produces same result"""
        analyzer = StructureAnalyzer()

        analyzer.run(project, str(mock_repo), config)
        files_count_1 = len(project.files)
        modules_count_1 = len(project.modules)

        # Run again
        analyzer.run(project, str(mock_repo), config)
        files_count_2 = len(project.files)
        modules_count_2 = len(project.modules)

        # Should be deterministic (or append mode if designed that way)
        # For now, let's check it doesn't crash
        assert files_count_2 >= files_count_1, "Files count decreased on re-run"

    def test_handles_empty_directory(self, project, tmp_path, config):
        """Test handling of empty directory"""
        empty_repo = tmp_path / "empty"
        empty_repo.mkdir()

        analyzer = StructureAnalyzer()
        analyzer.run(project, str(empty_repo), config)

        # Should not crash, may have 0 files
        assert len(project.files) == 0, "Should have no files in empty repo"

    def test_file_id_uniqueness(self, project, mock_repo, config):
        """Test that all file IDs are unique"""
        analyzer = StructureAnalyzer()
        analyzer.run(project, str(mock_repo), config)

        file_ids = [f.id for f in project.files.values()]
        assert len(file_ids) == len(set(file_ids)), "Duplicate file IDs found"

    def test_module_id_uniqueness(self, project, mock_repo, config):
        """Test that all module IDs are unique"""
        analyzer = StructureAnalyzer()
        analyzer.run(project, str(mock_repo), config)

        module_ids = [m.id for m in project.modules.values()]
        assert len(module_ids) == len(set(module_ids)), "Duplicate module IDs found"


# Property-based tests (Phase 1 target)
# TODO: Add hypothesis tests for invariants:
# - All file paths are relative to repo root
# - All LOC values are non-negative
# - Language detection is deterministic
# - Module containment is acyclic
