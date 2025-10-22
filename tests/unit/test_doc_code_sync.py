"""Tests for DocCodeSyncAnalyzer."""

import tempfile
from pathlib import Path

import pytest

from repoq.analyzers.doc_code_sync import DocCodeSyncAnalyzer
from repoq.config import AnalyzeConfig
from repoq.core.model import File, Project


@pytest.fixture
def test_project():
    """Create test project with sample Python files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # File 1: Function with missing docstring
        file1 = repo_path / "module1.py"
        file1.write_text("""
def calculate(x, y):
    return x + y
""")

        # File 2: Function with docstring but signature mismatch
        file2 = repo_path / "module2.py"
        file2.write_text('''
def process(data, config):
    """Process data with configuration.

    Args:
        data: Input data
        options: Configuration options (WRONG NAME!)

    Returns:
        Processed result
    """
    return data
''')

        # File 3: Function with TODO in docstring
        file3 = repo_path / "module3.py"
        file3.write_text('''
def transform(value):
    """Transform value.

    TODO: Implement proper validation
    """
    return value
''')

        # File 4: Class without docstring
        file4 = repo_path / "module4.py"
        file4.write_text("""
class DataProcessor:
    def __init__(self):
        self.data = []

    def process(self):
        return self.data
""")

        # Create Project model
        project = Project(id="repo:test", name="test")
        project.files = {
            "repo:test:file:module1.py": File(
                id="repo:test:file:module1.py",
                path="module1.py",
                language="Python",
                lines_of_code=3,
            ),
            "repo:test:file:module2.py": File(
                id="repo:test:file:module2.py",
                path="module2.py",
                language="Python",
                lines_of_code=12,
            ),
            "repo:test:file:module3.py": File(
                id="repo:test:file:module3.py",
                path="module3.py",
                language="Python",
                lines_of_code=8,
            ),
            "repo:test:file:module4.py": File(
                id="repo:test:file:module4.py",
                path="module4.py",
                language="Python",
                lines_of_code=7,
            ),
        }

        yield project, repo_path


def test_missing_docstring_detection(test_project):
    """Test detection of missing docstrings."""
    project, repo_path = test_project

    analyzer = DocCodeSyncAnalyzer()
    issues = analyzer._analyze_python_file(project.id, "module1.py", repo_path / "module1.py")

    # Should detect missing docstring for calculate()
    assert len(issues) >= 1
    missing_doc_issues = [i for i in issues if i.type == "repo:MissingDocstring"]
    assert len(missing_doc_issues) == 1
    assert "calculate" in missing_doc_issues[0].description


def test_signature_mismatch_detection(test_project):
    """Test detection of docstring signature mismatches."""
    project, repo_path = test_project

    # This test requires docstring_parser
    try:
        import docstring_parser  # noqa: F401

        analyzer = DocCodeSyncAnalyzer()
        issues = analyzer._analyze_python_file(project.id, "module2.py", repo_path / "module2.py")

        # Should detect mismatch: 'config' vs 'options'
        mismatch_issues = [i for i in issues if i.type == "repo:DocstringSignatureMismatch"]
        assert len(mismatch_issues) == 1
        assert (
            "config" in mismatch_issues[0].description
            or "options" in mismatch_issues[0].description
        )

    except ImportError:
        pytest.skip("docstring_parser not available")


def test_todo_in_docstring_detection(test_project):
    """Test detection of TODO markers in docstrings."""
    project, repo_path = test_project

    analyzer = DocCodeSyncAnalyzer()
    issues = analyzer._analyze_python_file(project.id, "module3.py", repo_path / "module3.py")

    # Should detect TODO in docstring
    todo_issues = [i for i in issues if i.type == "repo:OutdatedDocstring"]
    assert len(todo_issues) == 1
    assert "TODO" in todo_issues[0].description or "todo" in todo_issues[0].description


def test_class_missing_docstring(test_project):
    """Test detection of missing class docstrings."""
    project, repo_path = test_project

    analyzer = DocCodeSyncAnalyzer()
    issues = analyzer._analyze_python_file(project.id, "module4.py", repo_path / "module4.py")

    # Should detect missing docstring for DataProcessor class
    missing_doc_issues = [i for i in issues if i.type == "repo:MissingDocstring"]
    assert len(missing_doc_issues) >= 1
    class_issues = [i for i in missing_doc_issues if "class" in i.title.lower()]
    assert len(class_issues) == 1


def test_full_analysis_run(test_project):
    """Test full analyzer run with issue generation."""
    project, repo_path = test_project

    cfg = AnalyzeConfig(mode="full")
    analyzer = DocCodeSyncAnalyzer()
    analyzer.run(project, str(repo_path), cfg)

    # Should generate multiple issues
    assert len(project.issues) >= 4  # At least 1 per problematic file

    # Check issue types
    issue_types = {issue.type for issue in project.issues.values()}
    assert "repo:MissingDocstring" in issue_types


def test_readme_example_validation():
    """Test README.md code example validation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)

        # Create README with outdated import
        readme = repo_path / "README.md"
        readme.write_text("""
# Test Project

## Example

```python
from test_project.nonexistent_module import something

something.do_work()
```
""")

        # Create project (without the imported module)
        project = Project(id="repo:test_project", name="test_project")

        analyzer = DocCodeSyncAnalyzer()
        issues = analyzer._check_readme_examples(project.id, readme, project)

        # Should detect outdated import
        assert len(issues) >= 1
        outdated_issues = [i for i in issues if i.type == "repo:OutdatedREADMEExample"]
        assert len(outdated_issues) == 1
        assert "nonexistent_module" in outdated_issues[0].description


def test_skips_private_functions(test_project):
    """Test that analyzer skips private functions."""
    project, repo_path = test_project

    # Create file with private function
    private_file = repo_path / "module5.py"
    private_file.write_text("""
def _private_helper(x):
    return x * 2

def public_function(x):
    return _private_helper(x)
""")

    project.files["repo:test:file:module5.py"] = File(
        id="repo:test:file:module5.py",
        path="module5.py",
        language="Python",
        lines_of_code=6,
    )

    analyzer = DocCodeSyncAnalyzer()
    issues = analyzer._analyze_python_file(project.id, "module5.py", private_file)

    # Should only flag public_function, not _private_helper
    missing_doc_issues = [i for i in issues if i.type == "repo:MissingDocstring"]
    assert len(missing_doc_issues) == 1  # Only public_function
    assert "public_function" in missing_doc_issues[0].description
    assert "_private_helper" not in missing_doc_issues[0].description
