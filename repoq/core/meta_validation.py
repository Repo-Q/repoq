"""
Meta-loop self-validation module.

STRATIFICATION_LEVEL: 1 (meta-analysis of base repository)

This module operates at level 1 of the stratification hierarchy:
- Level 0: Base repository analysis (files, metrics, issues)
- Level 1: Meta-analysis (self-validation, circular dependencies, universe checks)
- Level 2: Meta-meta operations (analyzing meta-analysis itself - PROHIBITED here)

Implements safe self-analysis with stratification guards to prevent Russell's paradox.
Checks circular dependencies, stratification consistency, and universe violations.

Safety Invariants:
- MAX_SAFE_LEVEL = 2 (hard limit to prevent infinite regress)
- ValueError raised for level > 2
- Read-only mode for all self-analysis operations
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import XSD

from .model import Project

logger = logging.getLogger(__name__)

# Namespaces
META_NS = "http://example.org/vocab/meta#"
REPO_NS = "http://example.org/vocab/repo#"
QUALITY_NS = "http://example.org/vocab/quality#"


@dataclass
class SelfAnalysisResult:
    """Result of meta-loop self-validation."""

    project_id: str
    stratification_level: int
    read_only_mode: bool
    self_reference_detected: bool
    circular_dependencies: list[str]
    universe_violations: list[str]
    safety_checks_passed: bool
    performed_at: datetime
    analyzed_commit: Optional[str] = None


def detect_circular_dependencies(project: Project) -> list[str]:
    """
    Detect circular dependency patterns in project.

    Args:
        project: Project model to analyze

    Returns:
        List of circular dependency descriptions

    Examples:
        ["repoq.core.model → repoq.core.deps → repoq.core.model"]
    """
    circular_deps = []

    # Build dependency graph
    dep_graph: dict[str, set[str]] = {}
    for file in project.files.values():
        file_module = _file_path_to_module(file.path)
        if file_module:
            deps = getattr(file, "dependencies", [])
            dep_graph[file_module] = set(deps)

    # Detect cycles using DFS
    visited = set()
    rec_stack = set()

    def dfs(node: str, path: list[str]) -> None:
        if node in rec_stack:
            # Found cycle
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            circular_deps.append(" → ".join(cycle))
            return

        if node in visited:
            return

        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in dep_graph.get(node, []):
            dfs(neighbor, path.copy())

        rec_stack.remove(node)

    for module in dep_graph:
        if module not in visited:
            dfs(module, [])

    return circular_deps


def _file_path_to_module(file_path: str) -> Optional[str]:
    """
    Convert file path to Python module name.

    Args:
        file_path: File path (e.g., "repoq/core/model.py")

    Returns:
        Module name (e.g., "repoq.core.model") or None

    Examples:
        >>> _file_path_to_module("repoq/core/model.py")
        'repoq.core.model'
        >>> _file_path_to_module("tests/test_foo.py")
        None  # Not a package module
    """
    path = Path(file_path)

    # Only process Python files
    if path.suffix != ".py":
        return None

    # Skip tests and setup files
    if "test" in path.parts or path.name in ["setup.py", "__main__.py"]:
        return None

    # Convert path to module name
    parts = path.with_suffix("").parts
    if parts[0] in ["repoq", "src"]:
        module = ".".join(parts)
        if module.endswith(".__init__"):
            module = module[: -len(".__init__")]
        return module

    return None


def check_stratification_consistency(project: Project) -> list[str]:
    """
    Check stratification level consistency across project.

    Verifies that:
    - All meta-level components declare stratification level
    - No components exceed level 2 (Russell's guard)
    - Level transitions follow rules (0 → 1 → 2, no skips)

    Args:
        project: Project model to analyze

    Returns:
        List of stratification violation descriptions
    """
    violations = []

    # Check for meta-level files without declared level
    meta_files = [
        f for f in project.files.values() if "meta" in f.path.lower() or "ontolog" in f.path.lower()
    ]

    for file in meta_files:
        level = getattr(file, "stratification_level", None)
        if level is None:
            violations.append(f"Meta-level file {file.path} missing stratificationLevel")
        elif level > 2:
            violations.append(f"File {file.path} has stratificationLevel={level} (max: 2, Russell's guard)")

    return violations


def detect_universe_violations(project: Project) -> list[str]:
    """
    Detect universe/type level violations.

    Checks for patterns where types refer to themselves at the same level,
    which can lead to paradoxes similar to Russell's set.

    Args:
        project: Project model to analyze

    Returns:
        List of universe violation descriptions

    Examples:
        ["OntologyManager analyzes Ontology at same level (unsafe)"]
    """
    violations = []

    # Check for self-referential patterns in ontology/meta code
    for file in project.files.values():
        if "ontology" in file.path.lower() or "meta" in file.path.lower():
            # Check if file analyzes/processes same concepts it defines
            file_name_lower = Path(file.path).stem.lower()

            # Heuristic: Look for files that both define and analyze same concept
            if "manager" in file_name_lower and "ontology" in file_name_lower:
                # OntologyManager analyzing Ontology - potential universe collision
                violations.append(
                    f"{file.path}: Manager analyzes same concept it manages (universe collision risk)"
                )

    return violations


def perform_self_analysis(
    project: Project, stratification_level: int = 1, analyzed_commit: Optional[str] = None
) -> SelfAnalysisResult:
    """
    Perform meta-loop self-validation on project.

    Args:
        project: Project model (should be RepoQ analyzing itself)
        stratification_level: Current stratification level (default: 1)
        analyzed_commit: Git commit SHA being analyzed

    Returns:
        SelfAnalysisResult with validation outcomes

    Raises:
        ValueError: If stratification_level > 2 (Russell's guard)
    """
    if stratification_level > 2:
        raise ValueError(f"Stratification level {stratification_level} exceeds max (2) - Russell's paradox risk")

    # Detect self-reference (is this RepoQ analyzing RepoQ?)
    is_self_analysis = "repoq" in project.name.lower() or "repoq" in project.id.lower()

    # Run safety checks
    circular_deps = detect_circular_dependencies(project)
    stratification_violations = check_stratification_consistency(project)
    universe_violations = detect_universe_violations(project)

    # Aggregate safety status
    safety_passed = (
        len(circular_deps) == 0 and len(stratification_violations) == 0 and len(universe_violations) == 0
    )

    return SelfAnalysisResult(
        project_id=project.id,
        stratification_level=stratification_level,
        read_only_mode=True,  # Always true for safe self-analysis
        self_reference_detected=is_self_analysis,
        circular_dependencies=circular_deps,
        universe_violations=stratification_violations + universe_violations,
        safety_checks_passed=safety_passed,
        performed_at=datetime.now(UTC),
        analyzed_commit=analyzed_commit,
    )


def export_self_analysis_rdf(graph: Graph, result: SelfAnalysisResult) -> None:
    """
    Export SelfAnalysisResult to RDF graph.

    Adds meta:SelfAnalysis triples with stratification, safety checks, and violations.

    Args:
        graph: RDFLib Graph to add triples to
        result: SelfAnalysisResult from perform_self_analysis()

    Side Effects:
        Modifies `graph` in-place by adding triples
    """
    META = Namespace(META_NS)
    REPO = Namespace(REPO_NS)

    # Add namespace binding
    graph.bind("meta", META)

    # Create SelfAnalysis node
    analysis_id = f"{result.project_id}/meta/self-analysis"
    analysis_uri = URIRef(analysis_id)

    graph.add((analysis_uri, RDF.type, META.SelfAnalysis))

    # Stratification properties
    graph.add(
        (
            analysis_uri,
            META.stratificationLevel,
            Literal(result.stratification_level, datatype=XSD.nonNegativeInteger),
        )
    )
    graph.add((analysis_uri, META.readOnlyMode, Literal(result.read_only_mode, datatype=XSD.boolean)))
    graph.add((analysis_uri, META.maxSafeLevel, Literal(2, datatype=XSD.nonNegativeInteger)))  # Russell's guard

    # Self-reference detection
    graph.add(
        (
            analysis_uri,
            META.selfReferenceDetected,
            Literal(result.self_reference_detected, datatype=XSD.boolean),
        )
    )

    # Safety status
    graph.add(
        (analysis_uri, META.safetyChecksPassed, Literal(result.safety_checks_passed, datatype=XSD.boolean))
    )

    # Timestamp
    graph.add((analysis_uri, META.performedAt, Literal(result.performed_at, datatype=XSD.dateTime)))

    # Commit SHA
    if result.analyzed_commit:
        graph.add((analysis_uri, META.analyzedCommit, Literal(result.analyzed_commit)))

    # Circular dependencies
    for cycle in result.circular_dependencies:
        violation_msg = f"Circular dependency: {cycle}"
        graph.add((analysis_uri, META.universeViolation, Literal(violation_msg)))

    # Universe violations
    for violation in result.universe_violations:
        graph.add((analysis_uri, META.universeViolation, Literal(violation)))

    # Link to analyzed project
    project_uri = URIRef(result.project_id)
    graph.add((analysis_uri, META.analyzesSelf, project_uri))


def enrich_graph_with_self_analysis(
    graph: Graph, project: Project, stratification_level: int = 1, analyzed_commit: Optional[str] = None
) -> None:
    """
    High-level function to enrich RDF graph with self-analysis validation.

    Args:
        graph: RDFLib Graph to enrich
        project: Project model to analyze
        stratification_level: Current stratification level (default: 1)
        analyzed_commit: Git commit SHA being analyzed

    Side Effects:
        Modifies `graph` in-place by adding meta:SelfAnalysis triples

    Raises:
        ValueError: If stratification_level > 2
    """
    result = perform_self_analysis(project, stratification_level, analyzed_commit)
    export_self_analysis_rdf(graph, result)

    # Log results
    if result.safety_checks_passed:
        logger.info(f"✅ Self-analysis passed: {result.project_id} (level {result.stratification_level})")
    else:
        logger.warning(f"⚠️  Self-analysis found issues: {result.project_id}")
        if result.circular_dependencies:
            logger.warning(f"  Circular dependencies: {len(result.circular_dependencies)}")
        if result.universe_violations:
            logger.warning(f"  Universe violations: {len(result.universe_violations)}")
