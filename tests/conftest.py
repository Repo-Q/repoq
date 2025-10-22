"""Pytest configuration and shared fixtures for RepoQ tests.

This module provides:
- Shared fixtures for test repositories
- Test data factories
- Configuration helpers
- Cleanup utilities
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator

import pytest


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Path to test data directory."""
    return Path(__file__).parent / "fixtures" / "data"


@pytest.fixture(scope="session")
def sample_repos_dir() -> Path:
    """Path to sample repositories for testing."""
    return Path(__file__).parent / "fixtures" / "repos"


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test output.

    Yields:
        Path to temporary directory (cleaned up after test)
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="repoq_test_"))
    try:
        yield tmpdir
    finally:
        if tmpdir.exists():
            shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def git_repo(temp_dir: Path) -> Path:
    """Create a minimal git repository for testing.

    Returns:
        Path to git repository root
    """
    repo_dir = temp_dir / "test_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Initialize git repo
    os.system(f"cd {repo_dir} && git init -q")
    os.system(f"cd {repo_dir} && git config user.email 'test@example.com'")
    os.system(f"cd {repo_dir} && git config user.name 'Test User'")

    # Create sample files
    (repo_dir / "README.md").write_text("# Test Repository\n")
    (repo_dir / "main.py").write_text(
        'def hello():\n    """Say hello."""\n    print("Hello, World!")\n'
    )

    # Initial commit
    os.system(f"cd {repo_dir} && git add . && git commit -q -m 'Initial commit'")

    return repo_dir


@pytest.fixture
def python_repo(git_repo: Path) -> Path:
    """Create a Python repository with realistic structure.

    Returns:
        Path to Python project root
    """
    # Create package structure
    pkg_dir = git_repo / "mypackage"
    pkg_dir.mkdir(exist_ok=True)

    (pkg_dir / "__init__.py").write_text('"""My Package."""\n__version__ = "1.0.0"\n')

    (pkg_dir / "core.py").write_text("""
\"\"\"Core module.\"\"\"

class DataProcessor:
    \"\"\"Process data with various methods.\"\"\"

    def __init__(self, name: str):
        self.name = name

    def process(self, data: list) -> dict:
        \"\"\"Process input data.\"\"\"
        if not data:
            raise ValueError("Data cannot be empty")
        return {"name": self.name, "count": len(data)}

    def validate(self, item: any) -> bool:
        \"\"\"Validate item.\"\"\"
        return item is not None
""")

    (pkg_dir / "utils.py").write_text("""
\"\"\"Utility functions.\"\"\"

def calculate_sum(numbers: list[int]) -> int:
    \"\"\"Calculate sum of numbers.\"\"\"
    return sum(numbers)

def format_output(data: dict) -> str:
    \"\"\"Format data as string.\"\"\"
    return str(data)
""")

    # Create tests
    tests_dir = git_repo / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("")

    (tests_dir / "test_core.py").write_text("""
import pytest
from mypackage.core import DataProcessor

def test_processor_creation():
    p = DataProcessor("test")
    assert p.name == "test"

def test_process_data():
    p = DataProcessor("test")
    result = p.process([1, 2, 3])
    assert result["count"] == 3
""")

    # Commit changes
    os.system(f"cd {git_repo} && git add . && git commit -q -m 'Add package structure'")

    return git_repo


@pytest.fixture
def config_dict() -> Dict[str, Any]:
    """Sample configuration dictionary."""
    return {
        "mode": "full",
        "include_extensions": ["py", "js"],
        "exclude_globs": ["tests/**", ".*"],
        "max_files": 1000,
        "thresholds": {
            "complexity": 15,
            "maintainability": 20,
        },
    }


@pytest.fixture
def mock_project_data() -> Dict[str, Any]:
    """Mock project data for ontology testing."""
    return {
        "id": "test:project:1",
        "name": "test-project",
        "files": [
            {"path": "src/main.py", "name": "main.py", "lines": 100, "language": "Python"},
            {"path": "src/utils.py", "name": "utils.py", "lines": 50, "language": "Python"},
            {
                "path": "tests/test_main.py",
                "name": "test_main.py",
                "lines": 80,
                "language": "Python",
            },
        ],
        "analyzers": {
            "structure": {
                "files": [
                    {
                        "path": "src/main.py",
                        "name": "main.py",
                        "lines": 100,
                        "classes": [
                            {
                                "name": "MainClass",
                                "complexity": 5,
                                "lines": 50,
                                "methods": [
                                    {"name": "process", "complexity": 3, "visibility": "public"}
                                ],
                            }
                        ],
                    }
                ]
            }
        },
    }


@pytest.fixture(autouse=True)
def cleanup_artifacts(temp_dir: Path):
    """Automatically cleanup test artifacts after each test."""
    yield
    # Cleanup common artifact patterns
    for pattern in ["*.jsonld", "*.md", "*.ttl", ".repoq"]:
        for item in temp_dir.glob(pattern):
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item, ignore_errors=True)


# Markers for test organization
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line(
        "markers", "integration: Integration tests (slower, external dependencies)"
    )
    config.addinivalue_line("markers", "e2e: End-to-end tests (full workflow)")
    config.addinivalue_line("markers", "smoke: Smoke tests (critical functionality)")
    config.addinivalue_line("markers", "slow: Slow tests (skip in quick runs)")
