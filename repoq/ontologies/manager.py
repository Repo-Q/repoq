"""OntologyManager: RDF triple management with SPARQL queries and pattern detection.

TDD Cycle 1 - GREEN + REFACTOR Phase.

Design:
- Backend abstraction: RDFLib (default), Oxigraph (future per ADR-002)
- Namespaces: code, c4, ddd (bound on init)
- SPARQL: SELECT queries with dict result binding
- Patterns: MVC, LayeredArchitecture detection via pre-defined queries
- Persistence: Turtle/JSON-LD serialization

Soundness gates:
- RDFLib ensures deterministic triple addition (set semantics)
- SPARQL queries terminate (no recursion, finite graph)
- Pattern detection is read-only (no side effects)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rdflib import Graph, Literal, Namespace, URIRef

if TYPE_CHECKING:
    from repoq.core.stratification_guard import StratificationGuard

# Namespace URIs (constants per DRY principle)
NAMESPACE_CODE = "http://repoq.io/ontology/code#"
NAMESPACE_C4 = "http://repoq.io/ontology/c4#"
NAMESPACE_DDD = "http://repoq.io/ontology/ddd#"


class OntologyManager:
    """Manages RDF triples with SPARQL query support and pattern detection.

    Backend abstraction allows switching between RDFLib (default) and Oxigraph (future).

    Features:
    - Add/query RDF triples
    - Execute SPARQL SELECT queries with dict results
    - Detect architectural patterns (MVC, Layered Architecture)
    - Save/load ontologies in Turtle/JSON-LD formats

    Attributes:
        backend_name: Backend type ("rdflib" or "oxigraph").
        _impl: Backend implementation (RDFLibBackend or OxigraphBackend).

    Example:
        >>> manager = OntologyManager()
        >>> manager.add_triple(
        ...     URIRef("http://example.org/Module1"),
        ...     URIRef("http://repoq.io/ontology/code#complexity"),
        ...     Literal(15)
        ... )
        >>> manager.query("SELECT ?s ?p ?o WHERE { ?s ?p ?o }")
        [{'s': ..., 'p': ..., 'o': ...}]
    """

    def __init__(self, backend: str = "rdflib") -> None:
        """Initialize ontology manager with specified backend.

        Args:
            backend: Backend type ("rdflib" or "oxigraph"). Default: "rdflib".

        Raises:
            ValueError: If backend is not "rdflib" or "oxigraph".
            ImportError: If Oxigraph backend requested but not installed.
        """
        self.backend_name = backend
        if backend == "rdflib":
            self._impl = RDFLibBackend()
        elif backend == "oxigraph":
            # Future: Oxigraph implementation (ADR-002)
            try:
                self._impl = OxigraphBackend()
            except ImportError as exc:
                raise ImportError(
                    "Oxigraph backend not available. Install with: pip install repoq[oxigraph]"
                ) from exc
        else:
            raise ValueError(f"Unknown backend: {backend}")

    def add_triple(self, subject: URIRef, predicate: URIRef, obj: URIRef | Literal) -> None:
        """Add a single RDF triple.

        Args:
            subject: Subject URI (resource being described).
            predicate: Predicate URI (property/relationship).
            obj: Object (URI or Literal value).

        Example:
            >>> manager.add_triple(
            ...     URIRef("http://example.org/Module1"),
            ...     URIRef("http://repoq.io/ontology/code#complexity"),
            ...     Literal(15)
            ... )
        """
        return self._impl.add_triple(subject, predicate, obj)

    def query(self, sparql: str) -> list[dict[str, Any]]:
        """Execute SPARQL SELECT query and return results as list of dicts.

        Args:
            sparql: SPARQL SELECT query string.

        Returns:
            List of result bindings (each binding is a dict).

        Example:
            >>> results = manager.query('''
            ...     PREFIX code: <http://repoq.io/ontology/code#>
            ...     SELECT ?module ?complexity
            ...     WHERE { ?module code:complexity ?complexity }
            ... ''')
            >>> results[0]['complexity']
            15
        """
        return self._impl.query(sparql)

    def detect_pattern(self, pattern_name: str) -> list[dict[str, Any]]:
        """Detect architectural patterns in the code ontology.

        Supported patterns (from Phase 4 architecture):
        - "mvc": Model-View-Controller pattern
        - "layered": Layered Architecture (Presentation → Business → Data)
        - Future: "microservices", "plugin", "hexagonal"

        Args:
            pattern_name: Pattern identifier (lowercase).

        Returns:
            List of pattern instances (each instance is a dict of bindings).

        Raises:
            ValueError: If pattern_name is not recognized.

        Example:
            >>> instances = manager.detect_pattern("mvc")
            >>> instances[0]['controller']
            rdflib.term.URIRef('http://example.org/UserController')
        """
        return self._impl.detect_pattern(pattern_name)

    def save(self, file_path: str, format: str = "turtle") -> None:
        """Save ontology to file.

        Args:
            file_path: Output file path.
            format: RDF serialization format ("turtle", "json-ld", "xml", etc.).

        Example:
            >>> manager.save("output.ttl", format="turtle")
        """
        return self._impl.save(file_path, format)

    def load(self, file_path: str, format: str = "turtle") -> None:
        """Load ontology from file.

        Args:
            file_path: Input file path.
            format: RDF serialization format ("turtle", "json-ld", "xml", etc.).

        Example:
            >>> manager.load("input.ttl", format="turtle")
        """
        return self._impl.load(file_path, format)

    def count(self) -> int:
        """Return number of triples in ontology.

        Returns:
            Number of RDF triples.

        Example:
            >>> manager.count()
            42
        """
        return self._impl.count()

    def add_triple_with_guard(
        self,
        guard: StratificationGuard,
        subject: URIRef,
        predicate: URIRef,
        obj: URIRef | Literal,
        from_level: int,
        to_level: int,
    ) -> None:
        """Add triple with stratification guard validation.

        Integration method for Phase 5.3: Validates level transition
        before adding triple to ontology.

        Args:
            guard: StratificationGuard instance for validation.
            subject: Subject URI.
            predicate: Predicate URI.
            obj: Object (URI or Literal).
            from_level: Source stratification level.
            to_level: Target stratification level.

        Raises:
            ValueError: If transition is unsafe (downward or same-level).

        Example:
            >>> from repoq.core.stratification_guard import StratificationGuard
            >>> guard = StratificationGuard()
            >>> manager.add_triple_with_guard(
            ...     guard,
            ...     URIRef("http://example.org/Module1"),
            ...     URIRef("http://example.org/vocab/meta#level"),
            ...     Literal(1),
            ...     from_level=0,
            ...     to_level=1
            ... )
        """
        # Check transition safety
        result = guard.check_transition(from_level, to_level)
        if not result.is_safe:
            raise ValueError(f"Unsafe transition: {result.reason}")

        # Add triple if safe
        self.add_triple(subject, predicate, obj)


class RDFLibBackend:
    """RDFLib backend implementation (default, pure Python).

    Pros: Pure Python, mature (10+ years), W3C compliant, easy install/debug.
    Cons: Slower for large graphs (>10K triples), in-memory only.
    Use case: Default for repos <10K files, CI/CD, development.

    Attributes:
        graph: RDFLib Graph instance (in-memory triple store).
    """

    def __init__(self) -> None:
        """Initialize RDFLib backend with common namespaces."""
        self.graph = Graph()

        # Bind common namespaces (use module-level constants)
        CODE = Namespace(NAMESPACE_CODE)
        C4 = Namespace(NAMESPACE_C4)
        DDD = Namespace(NAMESPACE_DDD)

        self.graph.bind("code", CODE)
        self.graph.bind("c4", C4)
        self.graph.bind("ddd", DDD)

    def add_triple(self, subject: URIRef, predicate: URIRef, obj: URIRef | Literal) -> None:
        """Add triple to RDFLib graph.

        Args:
            subject: Subject URI.
            predicate: Predicate URI.
            obj: Object (URI or Literal).
        """
        self.graph.add((subject, predicate, obj))

    def query(self, sparql: str) -> list[dict[str, Any]]:
        """Execute SPARQL SELECT query.

        Args:
            sparql: SPARQL SELECT query string.

        Returns:
            List of result bindings (rdflib.query.ResultRow converted to dict).
        """
        results = []
        for row in self.graph.query(sparql):
            # Convert rdflib.query.ResultRow to dict
            result_dict = {}
            for key in row.labels:
                result_dict[key] = row[key]
            results.append(result_dict)
        return results

    def detect_pattern(self, pattern_name: str) -> list[dict[str, Any]]:
        """Detect architectural patterns using pre-defined SPARQL queries.

        Args:
            pattern_name: Pattern identifier ("mvc" or "layered").

        Returns:
            List of pattern instances.

        Raises:
            ValueError: If pattern_name is not recognized.
        """

        if pattern_name == "mvc":
            # MVC Pattern: Controller calls Model, renders View
            query = """
            PREFIX code: <http://repoq.io/ontology/code#>
            SELECT ?controller ?model ?view
            WHERE {
                ?controller rdf:type code:Class .
                ?controller code:name ?controller_name .
                FILTER(CONTAINS(?controller_name, "Controller"))

                ?controller code:calls ?model .
                ?model rdf:type code:Class .
                ?model code:name ?model_name .
                FILTER(CONTAINS(?model_name, "Model"))

                ?controller code:renders ?view .
                ?view rdf:type code:Template .
            }
            """
            return self.query(query)

        if pattern_name == "layered":
            # Layered Architecture: Presentation → Business → Data
            query = """
            PREFIX code: <http://repoq.io/ontology/code#>
            SELECT ?presentation ?business ?data
            WHERE {
                ?presentation rdf:type code:Module .
                ?presentation code:layer "presentation" .
                ?presentation code:depends_on ?business .

                ?business rdf:type code:Module .
                ?business code:layer "business" .
                ?business code:depends_on ?data .

                ?data rdf:type code:Module .
                ?data code:layer "data" .
            }
            """
            return self.query(query)

        raise ValueError(f"Unknown pattern: {pattern_name}")

    def save(self, file_path: str, format: str = "turtle") -> None:
        """Save graph to file (Turtle, JSON-LD, etc.).

        Args:
            file_path: Output file path.
            format: RDF serialization format.
        """
        self.graph.serialize(destination=file_path, format=format)

    def load(self, file_path: str, format: str = "turtle") -> None:
        """Load graph from file.

        Args:
            file_path: Input file path.
            format: RDF serialization format.
        """
        self.graph.parse(source=file_path, format=format)

    def count(self) -> int:
        """Return number of triples in graph.

        Returns:
            Number of RDF triples.
        """
        return len(self.graph)


class OxigraphBackend:
    """Oxigraph backend (optional, future per ADR-002).

    Pros: 10-100x faster (Rust), persistent on-disk, SPARQL 1.1 compliant.
    Cons: Requires C++ toolchain, less mature, larger footprint.
    Use case: Large repos (>10K files), production.

    Note: Not yet implemented. Tracked in GitHub issue.
    """

    def __init__(self) -> None:
        """Raise NotImplementedError with tracking information."""
        raise NotImplementedError(
            "Oxigraph backend not yet implemented. "
            "Tracked in: https://github.com/kirill-0440/repoq/issues/TODO"
        )
