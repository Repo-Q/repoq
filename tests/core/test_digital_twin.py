"""Tests for Digital Twin (repoq/core/digital_twin.py).

Test Coverage:
- DigitalTwin initialization
- Static data loading (story, adr, changelog)
- Ontologies loading
- Complete graph generation
- Snapshot export
"""

from pathlib import Path

import pytest
from rdflib import RDF, Graph, Namespace, URIRef

from repoq.core.digital_twin import DigitalTwin

REPO = Namespace("https://repoq.dev/ontology/repo#")
STORY_OLD = Namespace("https://repoq.io/story#")  # Legacy namespace (phase1.ttl)
STORY_NEW = Namespace("https://repoq.dev/ontology/story#")  # New namespace


class TestDigitalTwinInitialization:
    """Test DigitalTwin initialization and loading."""

    def test_init_with_current_directory(self):
        """Should initialize with current directory if no workspace_root."""
        # Use actual workspace (we're in repoq-pro-final)
        dt = DigitalTwin()

        assert dt.workspace_root.exists()
        assert dt.repoq_dir.exists()
        assert (dt.repoq_dir / "shapes").exists()

    def test_init_with_explicit_path(self):
        """Should initialize with explicit workspace_root."""
        workspace = Path.cwd()
        dt = DigitalTwin(workspace_root=workspace)

        assert dt.workspace_root == workspace
        assert dt.repoq_dir == workspace / ".repoq"

    def test_init_nonexistent_workspace(self):
        """Should raise ValueError if workspace doesn't exist."""
        with pytest.raises(ValueError, match="Workspace root does not exist"):
            DigitalTwin(workspace_root=Path("/nonexistent/path"))

    def test_init_no_repoq_directory(self, tmp_path):
        """Should raise ValueError if .repoq directory missing."""
        with pytest.raises(ValueError, match=".repoq directory not found"):
            DigitalTwin(workspace_root=tmp_path)

    def test_load_static_data(self):
        """Should load static RDF from .repoq/ (story, adr, changelog)."""
        dt = DigitalTwin()

        # Should have loaded static data
        assert len(dt.static_graph) > 0

        # Should have story data (use legacy namespace)
        story_triples = list(dt.static_graph.triples((None, RDF.type, STORY_OLD.Phase)))
        assert len(story_triples) > 0, "Expected story:Phase triples"

    def test_load_ontologies(self):
        """Should load TBox from .repoq/ontologies/."""
        dt = DigitalTwin()

        # Should have loaded ontologies
        assert len(dt.ontologies_graph) > 0

        # Should have repo ontology (we just created it)
        repo_ontology = URIRef("https://repoq.dev/ontology/repo")
        assert (repo_ontology, None, None) in dt.ontologies_graph


class TestDigitalTwinDynamicGeneration:
    """Test dynamic RDF generation (commits, files, tests)."""

    def test_get_commits_rdf_returns_graph(self):
        """Should return Graph with commits."""
        dt = DigitalTwin()
        graph = dt.get_commits_rdf(limit=5)

        assert isinstance(graph, Graph)
        assert len(graph) > 0  # Should have commits

    def test_get_commits_rdf_has_commit_triples(self):
        """Should include repo:Commit triples."""
        dt = DigitalTwin()
        graph = dt.get_commits_rdf(limit=5)

        # Should have Commit instances
        commits = list(graph.subjects(RDF.type, REPO.Commit))
        assert len(commits) > 0
        assert len(commits) <= 5  # Respects limit

    def test_get_commits_rdf_has_required_properties(self):
        """Should include sha, message, dates for each commit."""
        dt = DigitalTwin()
        graph = dt.get_commits_rdf(limit=1)

        commits = list(graph.subjects(RDF.type, REPO.Commit))
        assert len(commits) == 1

        commit = commits[0]

        # Must have sha
        sha = list(graph.objects(commit, REPO.sha))
        assert len(sha) == 1
        assert len(str(sha[0])) == 40  # Full SHA

        # Must have message
        messages = list(graph.objects(commit, REPO.message))
        assert len(messages) == 1

        # Must have dates
        authored = list(graph.objects(commit, REPO.authoredDate))
        assert len(authored) == 1

    def test_get_commits_rdf_has_author(self):
        """Should include repo:Author for each commit."""
        dt = DigitalTwin()
        graph = dt.get_commits_rdf(limit=1)

        commits = list(graph.subjects(RDF.type, REPO.Commit))
        commit = commits[0]

        # Must have author
        authors = list(graph.objects(commit, REPO.author))
        assert len(authors) == 1

        author = authors[0]

        # Author must have name and email
        names = list(graph.objects(author, REPO.authorName))
        emails = list(graph.objects(author, REPO.authorEmail))
        assert len(names) == 1
        assert len(emails) == 1

    def test_get_commits_rdf_respects_limit(self):
        """Should respect limit parameter."""
        dt = DigitalTwin()

        graph_3 = dt.get_commits_rdf(limit=3)
        commits_3 = list(graph_3.subjects(RDF.type, REPO.Commit))
        assert len(commits_3) == 3

        graph_10 = dt.get_commits_rdf(limit=10)
        commits_10 = list(graph_10.subjects(RDF.type, REPO.Commit))
        assert len(commits_10) <= 10  # May have fewer if repo is small

    def test_get_files_rdf_empty(self):
        """Should return empty graph (not implemented yet)."""
        dt = DigitalTwin()
        graph = dt.get_files_rdf()

        assert isinstance(graph, Graph)
        assert len(graph) > 0  # Now implemented

    def test_get_files_rdf_has_file_triples(self):
        """Should include repo:File triples."""
        dt = DigitalTwin()
        graph = dt.get_files_rdf(extensions=[".py"])

        # Should have File instances
        files = list(graph.subjects(RDF.type, REPO.PythonFile))
        assert len(files) > 0

    def test_get_files_rdf_has_required_properties(self):
        """Should include filePath, fileName, fileSize for each file."""
        dt = DigitalTwin()
        graph = dt.get_files_rdf(extensions=[".py"], exclude_patterns=["tests"])

        files = list(graph.subjects(RDF.type, REPO.PythonFile))
        assert len(files) > 0

        file_uri = files[0]

        # Must have filePath
        paths = list(graph.objects(file_uri, REPO.filePath))
        assert len(paths) == 1

        # Must have fileName
        names = list(graph.objects(file_uri, REPO.fileName))
        assert len(names) == 1

        # Must have fileSize
        sizes = list(graph.objects(file_uri, REPO.fileSize))
        assert len(sizes) == 1
        assert int(sizes[0]) > 0

    def test_get_files_rdf_filters_by_extension(self):
        """Should filter by extensions parameter."""
        dt = DigitalTwin()

        # Only .py files
        graph_py = dt.get_files_rdf(extensions=[".py"])
        py_files = list(graph_py.subjects(RDF.type, REPO.PythonFile))
        assert len(py_files) > 0

        # No .ttl files should be PythonFile
        for file_uri in py_files:
            paths = list(graph_py.objects(file_uri, REPO.filePath))
            assert str(paths[0]).endswith(".py")

    def test_get_files_rdf_excludes_patterns(self):
        """Should exclude paths matching patterns."""
        dt = DigitalTwin()

        # Exclude tests directory (and .venv by default)
        graph = dt.get_files_rdf(
            extensions=[".py"], exclude_patterns=["tests", "__pycache__", ".venv"]
        )

        # Should not have test files or .venv files
        for file_uri in graph.subjects(RDF.type, REPO.PythonFile):
            paths = list(graph.objects(file_uri, REPO.filePath))
            path_str = str(paths[0])
            assert "tests" not in path_str, f"Found test file: {path_str}"
            assert ".venv" not in path_str, f"Found .venv file: {path_str}"

    def test_get_tests_rdf_returns_graph(self):
        """Should return Graph with tests."""
        dt = DigitalTwin()
        graph = dt.get_tests_rdf()

        assert isinstance(graph, Graph)
        # Should have tests (our own tests!)
        assert len(graph) > 0

    def test_get_tests_rdf_has_test_suite(self):
        """Should include repo:TestSuite."""
        dt = DigitalTwin()
        graph = dt.get_tests_rdf()

        # Should have TestSuite
        suites = list(graph.subjects(RDF.type, REPO.TestSuite))
        assert len(suites) == 1, "Expected exactly one TestSuite"

    def test_get_tests_rdf_has_test_triples(self):
        """Should include repo:Test triples."""
        dt = DigitalTwin()
        graph = dt.get_tests_rdf()

        # Should have Test instances
        tests = list(graph.subjects(RDF.type, REPO.TestFunction)) + list(
            graph.subjects(RDF.type, REPO.TestClass)
        )
        assert len(tests) > 0, "Expected test triples"

    def test_get_tests_rdf_has_test_properties(self):
        """Should include testName, testNodeId for each test."""
        dt = DigitalTwin()
        graph = dt.get_tests_rdf()

        tests = list(graph.subjects(RDF.type, REPO.TestFunction))
        if tests:
            test = tests[0]

            # Must have testName
            names = list(graph.objects(test, REPO.testName))
            assert len(names) == 1

            # Must have testNodeId
            node_ids = list(graph.objects(test, REPO.testNodeId))
            assert len(node_ids) == 1
            assert "::" in str(node_ids[0])  # Pytest format

    def test_get_tests_rdf_counts_tests(self):
        """TestSuite should have test counts."""
        dt = DigitalTwin()
        graph = dt.get_tests_rdf()

        suites = list(graph.subjects(RDF.type, REPO.TestSuite))
        suite = suites[0]

        # Must have testCount
        counts = list(graph.objects(suite, REPO.testCount))
        assert len(counts) == 1
        assert int(counts[0]) > 0

    def test_get_tests_rdf_empty(self):
        """Should return non-empty graph (now implemented)."""
        dt = DigitalTwin()
        graph = dt.get_tests_rdf()

        assert isinstance(graph, Graph)
        assert len(graph) > 0  # Now implemented


class TestDigitalTwinCompleteGraph:
    """Test complete graph generation and export."""

    def test_get_complete_graph_without_ontologies(self):
        """Should merge static + dynamic (no ontologies)."""
        dt = DigitalTwin()
        complete = dt.get_complete_graph(include_ontologies=False)

        # Should have static data
        assert len(complete) >= len(dt.static_graph)

        # Should NOT have ontologies
        repo_ontology = URIRef("https://repoq.dev/ontology/repo")
        assert (repo_ontology, None, None) not in complete

    def test_get_complete_graph_with_ontologies(self):
        """Should merge static + dynamic + ontologies."""
        dt = DigitalTwin()
        complete = dt.get_complete_graph(include_ontologies=True)

        # Should have static + ontologies
        expected = len(dt.static_graph) + len(dt.ontologies_graph)
        assert len(complete) >= expected

        # Should have ontologies
        repo_ontology = URIRef("https://repoq.dev/ontology/repo")
        assert (repo_ontology, None, None) in complete

    def test_get_complete_graph_has_commits(self):
        """Complete graph should include commits."""
        dt = DigitalTwin()
        complete = dt.get_complete_graph()

        commits = list(complete.subjects(RDF.type, REPO.Commit))
        assert len(commits) > 0, "Expected commits in complete graph"

    def test_get_complete_graph_has_files(self):
        """Complete graph should include files."""
        dt = DigitalTwin()
        complete = dt.get_complete_graph()

        files = list(complete.subjects(RDF.type, REPO.File)) + list(
            complete.subjects(RDF.type, REPO.PythonFile)
        )
        assert len(files) > 0, "Expected files in complete graph"

    def test_sparql_query_recent_commits(self):
        """Should support SPARQL queries for recent commits."""
        dt = DigitalTwin()
        complete = dt.get_complete_graph()

        # Query: Get 5 most recent commits with authors
        query = """
        PREFIX repo: <https://repoq.dev/ontology/repo#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?commit ?sha ?subject ?author ?date
        WHERE {
            ?commit rdf:type repo:Commit ;
                    repo:sha ?sha ;
                    repo:subject ?subject ;
                    repo:author ?authorURI ;
                    repo:committedDate ?date .
            ?authorURI repo:authorName ?author .
        }
        ORDER BY DESC(?date)
        LIMIT 5
        """

        results = list(complete.query(query))
        assert len(results) > 0, "Expected SPARQL results"
        assert len(results) <= 5

        # Verify result structure
        for row in results:
            assert row.commit is not None
            assert row.sha is not None
            assert row.subject is not None
            assert row.author is not None
            assert row.date is not None

    def test_sparql_query_python_files(self):
        """Should support SPARQL queries for Python files."""
        dt = DigitalTwin()
        complete = dt.get_complete_graph()

        # Query: Get Python files with LOC > 100
        query = """
        PREFIX repo: <https://repoq.dev/ontology/repo#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

        SELECT ?file ?path ?loc
        WHERE {
            ?file rdf:type repo:PythonFile ;
                  repo:filePath ?path ;
                  repo:linesOfCode ?loc .
            FILTER (?loc > 100)
        }
        ORDER BY DESC(?loc)
        LIMIT 10
        """

        results = list(complete.query(query))
        # May have 0 results if no files > 100 LOC, but query should not error
        assert isinstance(results, list)

        for row in results:
            assert int(row.loc) > 100

    def test_export_snapshot(self, tmp_path):
        """Should export complete graph to TTL file."""
        dt = DigitalTwin()
        output = tmp_path / "snapshot.ttl"

        dt.export_snapshot(output, include_ontologies=True, format="turtle")

        # File should exist
        assert output.exists()

        # Should be parseable
        g = Graph()
        g.parse(output, format="turtle")
        assert len(g) > 0

    def test_export_snapshot_creates_directories(self, tmp_path):
        """Should create parent directories if missing."""
        dt = DigitalTwin()
        output = tmp_path / "nested" / "dir" / "snapshot.ttl"

        dt.export_snapshot(output, include_ontologies=False)

        assert output.exists()
        assert output.parent.exists()
