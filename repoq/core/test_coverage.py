"""
Test coverage to RDF export module.

Парсит pytest coverage reports (coverage.json) и генерирует test:TestCase triples.
Включает связи между тестами и тестируемыми концептами (test:testedConcept).
"""

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import XSD


# Namespaces
TEST_NS = "http://example.org/vocab/test#"
REPO_NS = "http://example.org/vocab/repo#"


@dataclass
class TestCase:
    """Represents a single test case."""

    id: str
    name: str
    file_path: str
    test_class: Optional[str] = None
    tested_concept: Optional[str] = None  # e.g., "ComplexityAnalyzer", "SelfAnalysis"
    status: str = "unknown"  # unknown, passed, failed, skipped


@dataclass
class TestCoverage:
    """Represents overall test coverage."""

    coverage_percentage: Decimal
    covered_lines: int
    total_lines: int
    files_covered: int
    total_files: int


def parse_coverage_json(coverage_path: str | Path) -> TestCoverage:
    """
    Parse coverage.json from pytest-cov.

    Args:
        coverage_path: Path to coverage.json file

    Returns:
        TestCoverage with aggregated metrics

    Raises:
        FileNotFoundError: If coverage.json doesn't exist
        json.JSONDecodeError: If coverage.json is malformed
    """
    coverage_path = Path(coverage_path)
    if not coverage_path.exists():
        raise FileNotFoundError(f"Coverage report not found: {coverage_path}")

    with coverage_path.open("r") as f:
        data = json.load(f)

    # Extract totals
    totals = data.get("totals", {})
    files = data.get("files", {})

    return TestCoverage(
        coverage_percentage=Decimal(str(totals.get("percent_covered", 0.0))),
        covered_lines=totals.get("covered_lines", 0),
        total_lines=totals.get("num_statements", 0),
        files_covered=sum(1 for f in files.values() if f["summary"]["percent_covered"] > 0),
        total_files=len(files),
    )


def parse_pytest_collection(collect_output: str) -> List[TestCase]:
    """
    Parse pytest --collect-only output to extract test cases.

    Args:
        collect_output: Output from `pytest --collect-only -q`

    Returns:
        List of TestCase objects

    Example:
        >>> output = "tests/test_foo.py::TestClass::test_method"
        >>> tests = parse_pytest_collection(output)
        >>> len(tests)
        1
    """
    tests = []
    pattern = re.compile(r"^(tests/[^:]+)::([\w:]+)$")

    for line in collect_output.strip().split("\n"):
        line = line.strip()
        if not line or "::" not in line:
            continue

        match = pattern.match(line)
        if not match:
            continue

        file_path, test_path = match.groups()
        parts = test_path.split("::")

        if len(parts) == 1:
            # Function test
            test_name = parts[0]
            test_class = None
        else:
            # Class method test
            test_class = parts[0]
            test_name = parts[1]

        # Extract tested concept from test name or class
        # Naming convention: TestFooAnalyzer → FooAnalyzer
        #                    test_bar_baz → bar
        tested_concept = _extract_tested_concept(test_class or test_name)

        test_id = f"test:{file_path}/{test_class or ''}/{test_name}"

        tests.append(
            TestCase(
                id=test_id,
                name=test_name,
                file_path=file_path,
                test_class=test_class,
                tested_concept=tested_concept,
            )
        )

    return tests


def _extract_tested_concept(name: str) -> Optional[str]:
    """
    Extract tested concept from test name.

    Args:
        name: Test name or class name

    Returns:
        Concept name or None if not extractable

    Examples:
        >>> _extract_tested_concept("TestComplexityAnalyzer")
        'ComplexityAnalyzer'
        >>> _extract_tested_concept("test_shacl_validation")
        'shacl_validation'
    """
    # Pattern 1: TestFooBar → FooBar
    if name.startswith("Test") and len(name) > 4:
        return name[4:]

    # Pattern 2: test_foo_bar → foo_bar
    if name.startswith("test_"):
        return name[5:]

    return None


def export_test_coverage_rdf(
    graph: Graph,
    coverage: TestCoverage,
    tests: List[TestCase],
    project_id: str,
) -> None:
    """
    Add test coverage triples to RDF graph.

    Args:
        graph: RDFLib Graph to add triples to
        coverage: Test coverage metrics
        tests: List of test cases
        project_id: Project URI (e.g., "repo:repoq")

    Side Effects:
        Modifies `graph` in-place by adding triples
    """
    TEST = Namespace(TEST_NS)
    REPO = Namespace(REPO_NS)

    # Add namespace binding
    graph.bind("test", TEST)

    # 1. Export overall coverage
    coverage_uri = URIRef(f"{project_id}/test/coverage")
    graph.add((coverage_uri, RDF.type, TEST.Coverage))
    graph.add(
        (
            coverage_uri,
            TEST.coveragePercentage,
            Literal(coverage.coverage_percentage, datatype=XSD.decimal),
        )
    )
    graph.add(
        (coverage_uri, TEST.coveredLines, Literal(coverage.covered_lines, datatype=XSD.integer))
    )
    graph.add(
        (coverage_uri, TEST.totalLines, Literal(coverage.total_lines, datatype=XSD.integer))
    )

    # 2. Export test cases
    for test in tests:
        test_uri = URIRef(test.id)
        graph.add((test_uri, RDF.type, TEST.TestCase))
        graph.add((test_uri, TEST.testName, Literal(test.name)))
        graph.add((test_uri, TEST.testFilePath, Literal(test.file_path)))

        if test.test_class:
            graph.add((test_uri, TEST.testClass, Literal(test.test_class)))

        if test.tested_concept:
            # Link to tested concept (generic string for now)
            graph.add((test_uri, TEST.testedConcept, Literal(test.tested_concept)))

        graph.add((test_uri, TEST.testStatus, Literal(test.status)))


def enrich_graph_with_test_coverage(
    graph: Graph,
    project_id: str,
    coverage_path: str | Path = "coverage.json",
    pytest_collect_output: Optional[str] = None,
) -> None:
    """
    High-level function to enrich RDF graph with test coverage data.

    Args:
        graph: RDFLib Graph to enrich
        project_id: Project URI (e.g., "repo:repoq")
        coverage_path: Path to coverage.json (default: "coverage.json")
        pytest_collect_output: Output from pytest --collect-only
                               If None, will run pytest automatically

    Raises:
        FileNotFoundError: If coverage.json not found
        RuntimeError: If pytest collection fails
    """
    # Parse coverage
    coverage = parse_coverage_json(coverage_path)

    # Parse test collection
    if pytest_collect_output is None:
        import subprocess

        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode not in [0, 5]:  # 5 = no tests collected
            raise RuntimeError(f"pytest collection failed: {result.stderr}")
        pytest_collect_output = result.stdout

    tests = parse_pytest_collection(pytest_collect_output)

    # Export to RDF
    export_test_coverage_rdf(graph, coverage, tests, project_id)
