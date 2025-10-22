"""Digital Twin: Dynamic RDF generation from repository state.

Implements ADR-015 (Digital Twin Architecture - Hybrid Approach):
- Static ABox: .repoq/ (story, adr, changelog) [manual]
- Dynamic ABox: generated on-demand (git, files, tests) [this module]
- TBox: .repoq/ontologies/ (ontologies)

Architecture:
    DigitalTwin loads static RDF and generates dynamic RDF:
    - get_commits_rdf(): Git history → RDF (repo:Commit)
    - get_files_rdf(): File tree → RDF (repo:File)
    - get_tests_rdf(): Test suite → RDF (test:Test)
    - get_complete_graph(): Static + Dynamic merged
    - export_snapshot(): Save merged graph to TTL

Usage:
    >>> dt = DigitalTwin(workspace_root=Path("/path/to/repo"))
    >>> commits_graph = dt.get_commits_rdf(limit=10)
    >>> files_graph = dt.get_files_rdf(extensions=[".py"])
    >>> complete = dt.get_complete_graph()
    >>> complete.query("SELECT ?commit WHERE { ?commit a repo:Commit }")
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import git
from rdflib import RDF, Graph, Literal, Namespace, URIRef
from rdflib.namespace import XSD

logger = logging.getLogger(__name__)

# Namespaces
REPO = Namespace("https://repoq.dev/ontology/repo#")
STORY = Namespace("https://repoq.dev/ontology/story#")
ADR = Namespace("https://repoq.dev/ontology/adr#")
CHANGELOG = Namespace("https://repoq.dev/ontology/changelog#")


class DigitalTwin:
    """Digital Twin: unified RDF view of repository.

    Responsibilities:
    - Load static RDF from .repoq/
    - Generate dynamic RDF from git/fs/tests
    - Merge into complete graph
    - Export snapshots

    Attributes:
        workspace_root: Path to repository root
        static_graph: RDF from .repoq/ (story, adr, changelog)
        ontologies_graph: TBox (ontologies)
    """

    def __init__(self, workspace_root: Optional[Path] = None):
        """Initialize Digital Twin.

        Args:
            workspace_root: Path to repository root (default: current directory)
        """
        self.workspace_root = workspace_root or Path.cwd()
        if not self.workspace_root.exists():
            raise ValueError(f"Workspace root does not exist: {self.workspace_root}")

        self.repoq_dir = self.workspace_root / ".repoq"
        if not self.repoq_dir.exists():
            raise ValueError(f".repoq directory not found: {self.repoq_dir}")

        # Graphs
        self.static_graph = Graph()
        self.ontologies_graph = Graph()

        # Load static data
        self._load_static_data()
        self._load_ontologies()

        logger.info(
            f"DigitalTwin initialized: {len(self.static_graph)} static triples, "
            f"{len(self.ontologies_graph)} ontology triples"
        )

    def _load_static_data(self) -> None:
        """Load static RDF from .repoq/ (story, adr, changelog)."""
        static_dirs = ["story", "adr", "changelog"]

        for dir_name in static_dirs:
            dir_path = self.repoq_dir / dir_name
            if not dir_path.exists():
                logger.warning(f"Static directory not found: {dir_path}")
                continue

            # Load all .ttl files in directory
            for ttl_file in dir_path.rglob("*.ttl"):
                try:
                    self.static_graph.parse(ttl_file, format="turtle")
                    logger.debug(f"Loaded static data: {ttl_file}")
                except Exception as e:
                    logger.error(f"Failed to parse {ttl_file}: {e}")

        logger.info(f"Loaded {len(self.static_graph)} static triples")

    def _load_ontologies(self) -> None:
        """Load TBox from .repoq/ontologies/."""
        ontologies_dir = self.repoq_dir / "ontologies"
        if not ontologies_dir.exists():
            logger.warning(f"Ontologies directory not found: {ontologies_dir}")
            return

        # Load all .ttl files (ontologies)
        for ttl_file in ontologies_dir.glob("*.ttl"):
            try:
                self.ontologies_graph.parse(ttl_file, format="turtle")
                logger.debug(f"Loaded ontology: {ttl_file}")
            except Exception as e:
                logger.error(f"Failed to parse {ttl_file}: {e}")

        logger.info(f"Loaded {len(self.ontologies_graph)} ontology triples")

    def get_commits_rdf(
        self, branch: str = "HEAD", limit: Optional[int] = None, since: Optional[datetime] = None
    ) -> Graph:
        """Generate RDF from Git commit history.

        Args:
            branch: Branch name or "HEAD" for current branch
            limit: Max number of commits to fetch (None = all)
            since: Only commits after this date

        Returns:
            Graph with repo:Commit, repo:Author, repo:FileChange triples

        Raises:
            ValueError: If not a git repository
        """
        graph = Graph()
        graph.bind("repo", REPO)

        try:
            repo = git.Repo(self.workspace_root)
        except git.InvalidGitRepositoryError:
            raise ValueError(f"Not a git repository: {self.workspace_root}")

        # Get commits
        commits_iter = repo.iter_commits(branch, max_count=limit)

        for commit in commits_iter:
            # Filter by date if specified
            if since and datetime.fromtimestamp(commit.committed_date) < since:
                continue

            # Commit URI
            commit_uri = URIRef(f"https://repoq.dev/resource/commit/{commit.hexsha}")

            # Commit type
            graph.add((commit_uri, RDF.type, REPO.Commit))

            # SHA
            graph.add((commit_uri, REPO.sha, Literal(commit.hexsha)))
            graph.add((commit_uri, REPO.shortSha, Literal(commit.hexsha[:7])))

            # Message
            message_lines = commit.message.strip().split("\n", 1)
            subject = message_lines[0]
            body = message_lines[1].strip() if len(message_lines) > 1 else ""

            graph.add((commit_uri, REPO.message, Literal(commit.message.strip())))
            graph.add((commit_uri, REPO.subject, Literal(subject)))
            if body:
                graph.add((commit_uri, REPO.body, Literal(body)))

            # Dates
            authored_date = datetime.fromtimestamp(commit.authored_date)
            committed_date = datetime.fromtimestamp(commit.committed_date)
            graph.add(
                (commit_uri, REPO.authoredDate, Literal(authored_date, datatype=XSD.dateTime))
            )
            graph.add(
                (commit_uri, REPO.committedDate, Literal(committed_date, datatype=XSD.dateTime))
            )

            # Author
            author_uri = URIRef(f"https://repoq.dev/resource/author/{commit.author.email}")
            graph.add((author_uri, RDF.type, REPO.Author))
            graph.add((author_uri, REPO.authorName, Literal(commit.author.name)))
            graph.add((author_uri, REPO.authorEmail, Literal(commit.author.email)))
            graph.add((commit_uri, REPO.author, author_uri))

            # Committer (if different from author)
            if commit.committer.email != commit.author.email:
                committer_uri = URIRef(
                    f"https://repoq.dev/resource/author/{commit.committer.email}"
                )
                graph.add((committer_uri, RDF.type, REPO.Author))
                graph.add((committer_uri, REPO.authorName, Literal(commit.committer.name)))
                graph.add((committer_uri, REPO.authorEmail, Literal(commit.committer.email)))
                graph.add((commit_uri, REPO.committer, committer_uri))

            # Parents
            for parent in commit.parents:
                parent_uri = URIRef(f"https://repoq.dev/resource/commit/{parent.hexsha}")
                graph.add((commit_uri, REPO.parent, parent_uri))

            # File changes
            if commit.parents:
                parent = commit.parents[0]
                diffs = parent.diff(commit, create_patch=False)

                for diff in diffs:
                    change_uri = URIRef(
                        f"https://repoq.dev/resource/change/{commit.hexsha[:7]}_{diff.a_path or diff.b_path}"
                    )

                    # Determine change type
                    if diff.new_file:
                        graph.add((change_uri, RDF.type, REPO.Addition))
                    elif diff.deleted_file:
                        graph.add((change_uri, RDF.type, REPO.Deletion))
                    elif diff.renamed_file:
                        graph.add((change_uri, RDF.type, REPO.Rename))
                    else:
                        graph.add((change_uri, RDF.type, REPO.Modification))

                    # Link to commit
                    graph.add((commit_uri, REPO.hasChange, change_uri))

                    # File path
                    file_path = diff.b_path or diff.a_path
                    file_uri = URIRef(f"https://repoq.dev/resource/file/{file_path}")
                    graph.add((change_uri, REPO.changesFile, file_uri))

                    # Stats (if available)
                    if hasattr(diff, "diff") and diff.diff:
                        # Count lines (rough approximation)
                        diff_text = (
                            diff.diff.decode("utf-8", errors="ignore")
                            if isinstance(diff.diff, bytes)
                            else str(diff.diff)
                        )
                        added = diff_text.count("\n+")
                        removed = diff_text.count("\n-")
                        if added > 0:
                            graph.add(
                                (change_uri, REPO.linesAdded, Literal(added, datatype=XSD.integer))
                            )
                        if removed > 0:
                            graph.add(
                                (
                                    change_uri,
                                    REPO.linesRemoved,
                                    Literal(removed, datatype=XSD.integer),
                                )
                            )

        logger.info(f"Generated {len(graph)} triples from Git commits")
        return graph

    def get_files_rdf(
        self, extensions: Optional[list[str]] = None, exclude_patterns: Optional[list[str]] = None
    ) -> Graph:
        """Generate RDF from file tree.

        Args:
            extensions: Include only these extensions (e.g., [".py", ".ttl"])
            exclude_patterns: Exclude paths matching these patterns (e.g., ["__pycache__"])

        Returns:
            Graph with repo:File triples (path, size, LOC)
        """
        graph = Graph()
        graph.bind("repo", REPO)

        # Default exclusions
        if exclude_patterns is None:
            exclude_patterns = [
                "__pycache__",
                ".git",
                ".venv",
                "venv",
                ".pytest_cache",
                ".mypy_cache",
                ".ruff_cache",
                "node_modules",
                ".tox",
                "*.egg-info",
                "build",
                "dist",
            ]

        def should_exclude(path: Path) -> bool:
            """Check if path matches exclusion patterns."""
            for pattern in exclude_patterns:
                if pattern.startswith("*"):
                    # Extension pattern (e.g., "*.egg-info")
                    if path.name.endswith(pattern[1:]):
                        return True
                else:
                    # Name pattern (e.g., "__pycache__")
                    if pattern in path.parts:
                        return True
            return False

        # Iterate files
        for file_path in self.workspace_root.rglob("*"):
            # Skip directories
            if not file_path.is_file():
                continue

            # Skip excluded paths
            if should_exclude(file_path):
                continue

            # Filter by extension if specified
            if extensions and file_path.suffix not in extensions:
                continue

            # File URI
            relative_path = file_path.relative_to(self.workspace_root)
            file_uri = URIRef(f"https://repoq.dev/resource/file/{relative_path}")

            # Determine file type
            if file_path.suffix == ".py":
                graph.add((file_uri, RDF.type, REPO.PythonFile))
            elif file_path.suffix == ".ttl":
                graph.add((file_uri, RDF.type, REPO.TTLFile))
            elif file_path.suffix == ".md":
                graph.add((file_uri, RDF.type, REPO.MarkdownFile))
            else:
                graph.add((file_uri, RDF.type, REPO.File))

            # Path properties
            graph.add((file_uri, REPO.filePath, Literal(str(relative_path))))
            graph.add((file_uri, REPO.fileName, Literal(file_path.name)))
            graph.add((file_uri, REPO.fileExtension, Literal(file_path.suffix)))

            # Size
            try:
                size = file_path.stat().st_size
                graph.add((file_uri, REPO.fileSize, Literal(size, datatype=XSD.integer)))
            except Exception as e:
                logger.warning(f"Could not get size for {file_path}: {e}")

            # Lines of code (for text files)
            if file_path.suffix in [
                ".py",
                ".ttl",
                ".md",
                ".txt",
                ".yaml",
                ".yml",
                ".json",
                ".toml",
            ]:
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = len(f.readlines())
                    graph.add((file_uri, REPO.linesOfCode, Literal(lines, datatype=XSD.integer)))
                except Exception as e:
                    logger.warning(f"Could not count lines for {file_path}: {e}")

        logger.info(f"Generated {len(graph)} triples from file tree")
        return graph

    def get_tests_rdf(self) -> Graph:
        """Generate RDF from test suite (pytest collection).

        Returns:
            Graph with test:Test, test:TestSuite triples
        """
        # TODO: Implement with pytest collection
        graph = Graph()
        return graph

    def get_complete_graph(self, include_ontologies: bool = False) -> Graph:
        """Merge static + dynamic RDF into complete graph.

        Args:
            include_ontologies: Include TBox (ontologies) in result

        Returns:
            Complete graph with all triples
        """
        complete = Graph()

        # Add static data
        complete += self.static_graph

        # Add dynamic data
        complete += self.get_commits_rdf()
        complete += self.get_files_rdf()
        complete += self.get_tests_rdf()

        # Optionally add ontologies
        if include_ontologies:
            complete += self.ontologies_graph

        logger.info(f"Complete graph: {len(complete)} triples")
        return complete

    def export_snapshot(
        self, output_path: Path, include_ontologies: bool = False, format: str = "turtle"
    ) -> None:
        """Export complete graph to file.

        Args:
            output_path: Path to save file
            include_ontologies: Include TBox in export
            format: RDF serialization format (turtle, xml, json-ld)
        """
        graph = self.get_complete_graph(include_ontologies=include_ontologies)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        graph.serialize(destination=output_path, format=format)

        logger.info(f"Exported {len(graph)} triples to {output_path} ({format})")
