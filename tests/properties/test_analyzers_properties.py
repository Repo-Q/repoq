"""
Property-based tests for analyzers using Hypothesis

Phase 1 target: verify key invariants across all analyzers
"""

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from repoq.analyzers.complexity import ComplexityAnalyzer
from repoq.analyzers.structure import StructureAnalyzer
from repoq.config import AnalyzeConfig
from repoq.core.model import Project


# Strategies for generating test data
@st.composite
def file_tree(draw):
    """Generate random file tree structure"""
    num_files = draw(st.integers(min_value=1, max_value=20))
    extensions = draw(
        st.lists(st.sampled_from([".py", ".js", ".md", ".txt"]), min_size=1, max_size=3)
    )

    files = []
    for _ in range(num_files):
        depth = draw(st.integers(min_value=0, max_value=3))
        path_parts = [
            draw(
                st.text(
                    alphabet=st.characters(whitelist_categories=("Ll",)), min_size=1, max_size=10
                )
            )
            for _ in range(depth)
        ]
        filename = draw(
            st.text(alphabet=st.characters(whitelist_categories=("Ll",)), min_size=1, max_size=10)
        )
        ext = draw(st.sampled_from(extensions))

        path = "/".join(path_parts + [filename + ext]) if path_parts else filename + ext
        files.append(path)

    return files


class TestStructureAnalyzerProperties:
    """Property-based tests for StructureAnalyzer"""

    @settings(max_examples=10)  # Limited for CI performance
    @given(st.integers(min_value=1, max_value=100))
    def test_max_files_honored(self, max_files):
        """Property: analyzer respects max_files limit"""
        # Setup
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)

            # Create many files
            for i in range(50):
                (repo / f"file{i}.py").write_text(f"# file {i}\n")

            project = Project(id="test", name="test")
            config = AnalyzeConfig(mode="structure", max_files=max_files)

            # Run analyzer
            analyzer = StructureAnalyzer()
            analyzer.run(project, str(repo), config)

            # Property: should not exceed limit
            assert (
                len(project.files) <= max_files
            ), f"Analyzer processed {len(project.files)} files, limit was {max_files}"

    @settings(max_examples=10)
    @given(st.lists(st.sampled_from([".py", ".js", ".md"]), min_size=1, max_size=3))
    def test_extension_filter_correct(self, extensions):
        """Property: only specified extensions are included"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)

            # Create files with various extensions
            (repo / "test.py").write_text("# python\n")
            (repo / "test.js").write_text("// js\n")
            (repo / "test.md").write_text("# markdown\n")
            (repo / "test.txt").write_text("text\n")

            project = Project(id="test", name="test")
            config = AnalyzeConfig(mode="structure", include_extensions=extensions)

            analyzer = StructureAnalyzer()
            analyzer.run(project, str(repo), config)

            # Property: all files should have allowed extensions
            for file in project.files.values():
                file_ext = Path(file.path).suffix
                assert (
                    file_ext in extensions
                ), f"File {file.path} has extension {file_ext}, not in {extensions}"

    @settings(max_examples=5)
    @given(st.integers(min_value=0, max_value=10))
    def test_idempotent_analysis(self, seed):
        """Property: running analyzer twice gives same result"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)

            # Create deterministic file structure
            for i in range(seed % 5 + 1):
                (repo / f"file{i}.py").write_text(f"def func{i}():\n    pass\n")

            config = AnalyzeConfig(mode="structure")

            # First run
            project1 = Project(id="test", name="test")
            analyzer1 = StructureAnalyzer()
            analyzer1.run(project1, str(repo), config)

            # Second run
            project2 = Project(id="test", name="test")
            analyzer2 = StructureAnalyzer()
            analyzer2.run(project2, str(repo), config)

            # Property: should produce identical results
            assert len(project1.files) == len(project2.files), "Different file counts"
            assert len(project1.modules) == len(project2.modules), "Different module counts"

            # Check file details match
            for file_id in project1.files:
                assert file_id in project2.files, f"File {file_id} missing in second run"
                f1 = project1.files[file_id]
                f2 = project2.files[file_id]
                assert f1.path == f2.path, "File paths differ"
                assert f1.lines_of_code == f2.lines_of_code, "LOC differs"

    def test_loc_always_non_negative(self):
        """Property: lines of code are always >= 0"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "test.py").write_text("")  # Empty file

            project = Project(id="test", name="test")
            config = AnalyzeConfig(mode="structure")

            analyzer = StructureAnalyzer()
            analyzer.run(project, str(repo), config)

            # Property: all LOC values are non-negative
            for file in project.files.values():
                assert (
                    file.lines_of_code >= 0
                ), f"File {file.path} has negative LOC: {file.lines_of_code}"

    def test_language_consistency(self):
        """Property: same file extension always gives same language"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)

            # Create multiple Python files
            for i in range(5):
                (repo / f"file{i}.py").write_text(f"# file {i}\n")

            project = Project(id="test", name="test")
            config = AnalyzeConfig(mode="structure")

            analyzer = StructureAnalyzer()
            analyzer.run(project, str(repo), config)

            # Property: all .py files should have same language
            python_files = [f for f in project.files.values() if f.path.endswith(".py")]
            languages = set(f.language for f in python_files if f.language)

            assert (
                len(languages) <= 1
            ), f"Inconsistent language detection for .py files: {languages}"


class TestComplexityAnalyzerProperties:
    """Property-based tests for ComplexityAnalyzer"""

    def test_complexity_non_negative(self):
        """Property: complexity metrics are always >= 0"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "test.py").write_text("def simple():\n    return 42\n")

            # First run structure analyzer
            project = Project(id="test", name="test")
            config = AnalyzeConfig(mode="structure")
            StructureAnalyzer().run(project, str(repo), config)

            # Then complexity
            ComplexityAnalyzer().run(project, str(repo), config)

            # Property: all complexity values are non-negative
            for file in project.files.values():
                if file.complexity is not None:
                    assert (
                        file.complexity >= 0
                    ), f"File {file.path} has negative complexity: {file.complexity}"

    def test_maintainability_bounded(self):
        """Property: maintainability index is in valid range"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "test.py").write_text(
                """
def function():
    if True:
        for i in range(10):
            while i > 0:
                i -= 1
    return 42
"""
            )

            project = Project(id="test", name="test")
            config = AnalyzeConfig(mode="structure")
            StructureAnalyzer().run(project, str(repo), config)
            ComplexityAnalyzer().run(project, str(repo), config)

            # Property: maintainability index typically in [0, 100]
            for file in project.files.values():
                if file.maintainability is not None:
                    # Radon can produce values outside this range, but usually bounded
                    assert (
                        -50 <= file.maintainability <= 200
                    ), f"File {file.path} has unusual maintainability: {file.maintainability}"


# TODO Phase 1: Add more property tests
# - Test that module hierarchy is acyclic
# - Test that file paths are always relative
# - Test that commits are chronologically ordered
# - Test that coupling weights are symmetric
# - Test that dependency graph has no self-loops
