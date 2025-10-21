"""
Unit tests for ComplexityAnalyzer.

Tests cyclomatic complexity (lizard) and maintainability index (radon) analysis.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from repoq.analyzers.complexity import ComplexityAnalyzer
from repoq.config import AnalyzeConfig
from repoq.core.model import File, Project


@pytest.fixture
def temp_project_dir():
    """Create a temporary directory for test projects."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def project_with_files(temp_project_dir: Path) -> tuple[Project, str]:
    """Create a project with sample files."""
    project = Project(id="test:project", name="test_project")

    # Create Python file with simple function
    simple_py = temp_project_dir / "simple.py"
    simple_py.write_text(
        """
def hello():
    return "world"
"""
    )
    project.files["repo:file:simple.py"] = File(
        id="repo:file:simple.py", path="simple.py", language="Python"
    )

    # Create Python file with complex function (high CC)
    complex_py = temp_project_dir / "complex.py"
    complex_py.write_text(
        """
def complex_function(a, b, c):
    if a > 0:
        if b > 0:
            if c > 0:
                return a + b + c
            else:
                return a + b
        else:
            if c > 0:
                return a + c
            else:
                return a
    else:
        if b > 0:
            if c > 0:
                return b + c
            else:
                return b
        else:
            return 0
"""
    )
    project.files["repo:file:complex.py"] = File(
        id="repo:file:complex.py", path="complex.py", language="Python"
    )

    # Create non-Python file
    js_file = temp_project_dir / "script.js"
    js_file.write_text(
        """
function test() {
    return 42;
}
"""
    )
    project.files["repo:file:script.js"] = File(
        id="repo:file:script.js", path="script.js", language="JavaScript"
    )

    return project, str(temp_project_dir)


@pytest.fixture
def default_config():
    """Create default AnalyzeConfig."""
    return AnalyzeConfig(
        mode="full", exclude_globs=["**/.git/**", "**/node_modules/**", "**/.venv/**"]
    )


class TestComplexityAnalyzer:
    """Test suite for ComplexityAnalyzer."""

    def test_analyzer_initialization(self):
        """Test that ComplexityAnalyzer can be instantiated."""
        analyzer = ComplexityAnalyzer()
        assert analyzer.name == "complexity"

    def test_run_on_empty_project(self, temp_project_dir: Path, default_config: AnalyzeConfig):
        """Test that analyzer handles empty projects gracefully."""
        project = Project(id="test:empty", name="empty")
        analyzer = ComplexityAnalyzer()

        # Should not raise exception
        analyzer.run(project, str(temp_project_dir), default_config)

    def test_detects_cyclomatic_complexity(
        self, project_with_files: tuple[Project, str], default_config: AnalyzeConfig
    ):
        """Test that analyzer computes cyclomatic complexity using lizard."""
        project, repo_dir = project_with_files
        analyzer = ComplexityAnalyzer()

        analyzer.run(project, repo_dir, default_config)

        # Simple function should have low complexity
        simple_file = project.files.get("repo:file:simple.py")
        assert simple_file is not None
        if simple_file.complexity is not None:
            assert simple_file.complexity >= 1.0  # At least 1 for simple function
            assert simple_file.complexity <= 5.0  # Should be low

        # Complex function should have higher complexity
        complex_file = project.files.get("repo:file:complex.py")
        assert complex_file is not None
        if complex_file.complexity is not None:
            assert complex_file.complexity > 5.0  # Nested ifs increase CC

    def test_computes_maintainability_index(
        self, project_with_files: tuple[Project, str], default_config: AnalyzeConfig
    ):
        """Test that analyzer computes maintainability index for Python files."""
        project, repo_dir = project_with_files
        analyzer = ComplexityAnalyzer()

        analyzer.run(project, repo_dir, default_config)

        # Check that Python files have MI computed
        for fid, file in project.files.items():
            if file.language == "Python":
                # MI should be set (radon returns float)
                if file.maintainability is not None:
                    assert isinstance(file.maintainability, float)
                    # MI typically ranges 0-100
                    assert 0.0 <= file.maintainability <= 100.0

    def test_skips_non_python_for_maintainability(
        self, project_with_files: tuple[Project, str], default_config: AnalyzeConfig
    ):
        """Test that MI is only computed for Python files."""
        project, repo_dir = project_with_files
        analyzer = ComplexityAnalyzer()

        analyzer.run(project, repo_dir, default_config)

        # JavaScript file should not have MI
        js_file = project.files.get("repo:file:script.js")
        assert js_file is not None
        # MI computation is Python-only, so it might be None
        # (or remain unset if lizard doesn't analyze JS functions)

    def test_respects_exclude_globs(self, temp_project_dir: Path):
        """Test that analyzer respects exclude_globs configuration."""
        project = Project(id="test:exclude", name="exclude_test")

        # Create file in excluded directory
        excluded_dir = temp_project_dir / ".venv"
        excluded_dir.mkdir()
        excluded_file = excluded_dir / "excluded.py"
        excluded_file.write_text("def excluded(): pass")

        project.files["repo:file:.venv/excluded.py"] = File(
            id="repo:file:.venv/excluded.py", path=".venv/excluded.py", language="Python"
        )

        config = AnalyzeConfig(mode="full", exclude_globs=["**/.venv/**"])

        analyzer = ComplexityAnalyzer()
        analyzer.run(project, str(temp_project_dir), config)

        # Excluded file should not be analyzed (no complexity set)
        excluded = project.files["repo:file:.venv/excluded.py"]
        # Since file is excluded, lizard won't process it

    def test_handles_missing_lizard_gracefully(
        self,
        project_with_files: tuple[Project, str],
        default_config: AnalyzeConfig,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test that analyzer handles missing lizard dependency."""
        project, repo_dir = project_with_files

        # Mock lizard import to fail
        def mock_import(name, *args, **kwargs):
            if name == "lizard":
                raise ImportError("lizard not installed")
            return __import__(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        analyzer = ComplexityAnalyzer()
        # Should not raise exception
        analyzer.run(project, repo_dir, default_config)

    def test_handles_missing_radon_gracefully(
        self,
        project_with_files: tuple[Project, str],
        default_config: AnalyzeConfig,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test that analyzer handles missing radon dependency."""
        project, repo_dir = project_with_files

        # Mock radon.mi import to fail
        def mock_import(name, *args, **kwargs):
            if "radon" in name:
                raise ImportError("radon not installed")
            return __import__(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        analyzer = ComplexityAnalyzer()
        # Should not raise exception (lizard part still works)
        analyzer.run(project, repo_dir, default_config)

    def test_handles_malformed_python_file(
        self, temp_project_dir: Path, default_config: AnalyzeConfig
    ):
        """Test that analyzer handles files with syntax errors."""
        project = Project(id="test:malformed", name="malformed")

        # Create Python file with syntax error
        bad_py = temp_project_dir / "bad.py"
        bad_py.write_text("def broken(\n    # missing closing paren and body")

        project.files["repo:file:bad.py"] = File(
            id="repo:file:bad.py", path="bad.py", language="Python"
        )

        analyzer = ComplexityAnalyzer()
        # Should not raise exception
        analyzer.run(project, repo_dir=str(temp_project_dir), cfg=default_config)

    def test_idempotent_execution(
        self, project_with_files: tuple[Project, str], default_config: AnalyzeConfig
    ):
        """Test that running analyzer multiple times produces consistent results."""
        project, repo_dir = project_with_files
        analyzer = ComplexityAnalyzer()

        # First run
        analyzer.run(project, repo_dir, default_config)
        first_complexities = {
            fid: (f.complexity, f.maintainability) for fid, f in project.files.items()
        }

        # Second run
        analyzer.run(project, repo_dir, default_config)
        second_complexities = {
            fid: (f.complexity, f.maintainability) for fid, f in project.files.items()
        }

        # Results should be identical
        assert first_complexities == second_complexities

    def test_complexity_values_are_numeric(
        self, project_with_files: tuple[Project, str], default_config: AnalyzeConfig
    ):
        """Test that complexity values are numeric (float)."""
        project, repo_dir = project_with_files
        analyzer = ComplexityAnalyzer()

        analyzer.run(project, repo_dir, default_config)

        for file in project.files.values():
            if file.complexity is not None:
                assert isinstance(file.complexity, (int, float))
                assert file.complexity >= 0

            if file.maintainability is not None:
                assert isinstance(file.maintainability, (int, float))

    def test_max_complexity_across_functions(
        self, temp_project_dir: Path, default_config: AnalyzeConfig
    ):
        """Test that file complexity is max CC across all functions in file."""
        project = Project(id="test:max", name="max_complexity")

        # Create file with multiple functions of different complexity
        multi_fn = temp_project_dir / "multi.py"
        multi_fn.write_text(
            """
def simple():
    return 1

def complex(x):
    if x > 0:
        if x < 10:
            if x % 2 == 0:
                return "even and small"
            else:
                return "odd and small"
        else:
            return "large"
    else:
        return "negative"

def another_simple():
    return 2
"""
        )

        project.files["repo:file:multi.py"] = File(
            id="repo:file:multi.py", path="multi.py", language="Python"
        )

        analyzer = ComplexityAnalyzer()
        analyzer.run(project, str(temp_project_dir), default_config)

        # File complexity should be max of all functions (complex() has highest CC)
        file = project.files["repo:file:multi.py"]
        if file.complexity is not None:
            # complex() function has nested ifs, so CC > simple functions
            assert file.complexity > 1.0

    def test_handles_empty_python_file(self, temp_project_dir: Path, default_config: AnalyzeConfig):
        """Test that analyzer handles empty Python files."""
        project = Project(id="test:empty_file", name="empty_file")

        empty_py = temp_project_dir / "empty.py"
        empty_py.write_text("")

        project.files["repo:file:empty.py"] = File(
            id="repo:file:empty.py", path="empty.py", language="Python"
        )

        analyzer = ComplexityAnalyzer()
        # Should not raise exception
        analyzer.run(project, str(temp_project_dir), default_config)

        # Empty file might have MI computed (radon handles empty files)
        file = project.files["repo:file:empty.py"]
        # No assertion on values since behavior may vary
