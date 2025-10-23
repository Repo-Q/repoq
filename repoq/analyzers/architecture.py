"""Architecture analyzer: detect layers, components, violations, and C4 model.

STRATIFICATION_LEVEL: 1 (analyzes base repository architecture)

This analyzer detects:
- Architectural layers (Presentation, Business, Data, Infrastructure)
- Components (CLI, Core, Analyzers, Reporting)
- Layering violations (e.g., Data → Presentation import)
- Circular dependencies
- Architecture metrics (coupling, cohesion, instability)
- C4 model (System → Container → Component)

Algorithm:
    1. Build dependency graph from imports
    2. Detect layers using file path heuristics
    3. Detect violations (check layering rules)
    4. Calculate metrics (Martin's metrics: I, A, D)
    5. Build C4 model hierarchy

Safety:
- Read-only analysis (no modifications)
- Deterministic (same input → same output)
- Terminating (finite graph traversal)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set

from ..config import AnalyzeConfig
from ..core.model import Project

logger = logging.getLogger(__name__)


@dataclass
class Layer:
    """Architectural layer with dependencies."""

    name: str  # "Presentation", "Business", "Data", "Infrastructure"
    files: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)  # Allowed dependencies

    def __hash__(self) -> int:
        return hash(self.name)


@dataclass
class Component:
    """Architectural component (subsystem)."""

    name: str  # "CLI", "Core", "Analyzers"
    files: List[str] = field(default_factory=list)
    public_api: List[str] = field(default_factory=list)  # Exported symbols
    internal: List[str] = field(default_factory=list)  # Internal-only


@dataclass
class LayeringViolation:
    """Violation of layering rules."""

    file: str
    imported_file: str
    rule: str  # "Data layer must not import from Presentation"
    severity: str  # "high", "medium", "low"


@dataclass
class CircularDependency:
    """Circular dependency between files/components."""

    cycle: List[str]  # [A, B, C, A]
    severity: str


@dataclass
class ArchitectureMetrics:
    """Martin's architecture metrics."""

    cohesion: float  # Average cohesion within components (0-1)
    coupling: float  # Average coupling between components (0-1)
    instability: Dict[str, float]  # I = Ce / (Ce + Ca) per component
    abstractness: Dict[str, float]  # A = Abstract / Total per component
    distance_from_main_sequence: Dict[str, float]  # D = |A + I - 1|


@dataclass
class C4System:
    """C4 model: System level."""

    name: str
    description: str
    type: str = "Software System"


@dataclass
class C4Container:
    """C4 model: Container level."""

    name: str
    technology: str
    components: List[Component] = field(default_factory=list)


@dataclass
class C4Model:
    """C4 model hierarchy."""

    system: C4System
    containers: List[C4Container] = field(default_factory=list)


@dataclass
class ArchitectureModel:
    """Complete architecture analysis result."""

    layers: List[Layer]
    components: List[Component]
    layering_violations: List[LayeringViolation]
    circular_dependencies: List[CircularDependency]
    metrics: ArchitectureMetrics
    c4_model: C4Model


class ArchitectureAnalyzer:
    """Analyze project architecture and detect violations.

    Example:
        >>> from repoq.core.model import Project
        >>> analyzer = ArchitectureAnalyzer()
        >>> model = analyzer.analyze(project)
        >>> print(f"Layers: {len(model.layers)}")
        >>> print(f"Violations: {len(model.layering_violations)}")
    """

    # Layering rules: layer → allowed dependencies
    LAYERING_RULES = {
        "Presentation": ["Business", "Infrastructure"],
        "Business": ["Data", "Infrastructure"],
        "Data": ["Infrastructure"],
        "Infrastructure": [],
    }

    def run(self, project: Project, repo_dir: str, cfg: AnalyzeConfig) -> None:
        """Run architecture analysis (BaseAnalyzer interface).

        Analyzes architecture and attaches ArchitectureModel to project.architecture_model.

        Args:
            project: Project model to populate
            repo_dir: Repository directory path
            cfg: Analysis configuration
        """
        logger.info("Running architecture analysis...")
        arch_model = self.analyze(project)

        # Attach to project for downstream use (e.g., Q-score calculation)
        # TODO: Add architecture_model field to Project dataclass
        # For now, store in project.__dict__ as workaround
        project.__dict__["architecture_model"] = arch_model

        logger.info(
            f"Architecture analysis complete: {len(arch_model.layers)} layers, "
            f"{len(arch_model.layering_violations)} violations, "
            f"{len(arch_model.circular_dependencies)} circular deps"
        )

    def analyze(self, project: Project) -> ArchitectureModel:
        """Analyze project architecture.

        Args:
            project: Project model with files and dependencies

        Returns:
            ArchitectureModel with layers, violations, metrics, C4 model
        """
        # 1. Build dependency graph
        dep_graph = self._build_dependency_graph(project)

        # 2. Detect layers
        layers = self._detect_layers(project, dep_graph)

        # 3. Detect components
        components = self._detect_components(project)

        # 4. Detect violations
        layering_violations = self._detect_layering_violations(layers, dep_graph)
        circular_dependencies = self._detect_circular_dependencies(dep_graph)

        # 5. Calculate metrics
        metrics = self._calculate_metrics(dep_graph, components)

        # 6. Build C4 model
        c4_model = self._build_c4_model(project, components)

        return ArchitectureModel(
            layers=layers,
            components=components,
            layering_violations=layering_violations,
            circular_dependencies=circular_dependencies,
            metrics=metrics,
            c4_model=c4_model,
        )

    def _build_dependency_graph(self, project: Project) -> Dict[str, Set[str]]:
        """Build dependency graph from DependencyEdge objects.

        Returns:
            Dict mapping file path → set of imported file paths
        """
        graph: Dict[str, Set[str]] = {file_path: set() for file_path in project.files.keys()}

        # Extract file paths from dependency edges
        for edge in project.dependencies:
            # edge.source and edge.target are IDs like "repo:file:repoq/cli.py"
            # Extract the path part
            source_path = self._extract_path_from_id(edge.source)
            target_path = self._extract_path_from_id(edge.target)

            if source_path and target_path:
                if source_path not in graph:
                    graph[source_path] = set()
                graph[source_path].add(target_path)

        return graph

    def _extract_path_from_id(self, file_id: str) -> str | None:
        """Extract file path from ID like 'repo:file:repoq/cli.py'.

        Args:
            file_id: File ID (e.g., "repo:file:repoq/cli.py")

        Returns:
            File path (e.g., "repoq/cli.py") or None if format is invalid
        """
        if ":" in file_id:
            parts = file_id.split(":", 2)
            if len(parts) >= 3:
                return parts[2]  # "repoq/cli.py"
        return None

    def _detect_layers(self, project: Project, dep_graph: Dict[str, Set[str]]) -> List[Layer]:
        """Detect architectural layers using file path heuristics.

        Heuristic:
        - repoq/cli.py, repoq/reporting/ → Presentation
        - repoq/analyzers/, repoq/refactoring.py → Business
        - repoq/core/model.py, repoq/core/deps.py → Data
        - repoq/core/utils.py, repoq/normalize/ → Infrastructure

        Returns:
            List of Layer objects with file assignments
        """
        layer_files = {
            "Presentation": [],
            "Business": [],
            "Data": [],
            "Infrastructure": [],
        }

        for file_path in project.files.keys():
            if "cli" in file_path or "reporting" in file_path:
                layer_files["Presentation"].append(file_path)
            elif "analyzers" in file_path or "refactoring" in file_path:
                layer_files["Business"].append(file_path)
            elif "core/model" in file_path or "core/deps" in file_path:
                layer_files["Data"].append(file_path)
            else:
                layer_files["Infrastructure"].append(file_path)

        return [
            Layer(
                name=name,
                files=files,
                depends_on=self.LAYERING_RULES[name],
            )
            for name, files in layer_files.items()
            if files  # Only non-empty layers
        ]

    def _get_layer(self, file_path: str, layers: List[Layer]) -> str | None:
        """Get layer name for a file."""
        for layer in layers:
            if file_path in layer.files:
                return layer.name
        return None

    def _detect_layering_violations(
        self, layers: List[Layer], dep_graph: Dict[str, Set[str]]
    ) -> List[LayeringViolation]:
        """Detect layering violations (e.g., Data → Presentation).

        Returns:
            List of LayeringViolation objects
        """
        violations = []

        for file, deps in dep_graph.items():
            file_layer = self._get_layer(file, layers)
            if not file_layer:
                continue

            allowed_layers = self.LAYERING_RULES.get(file_layer, [])

            for dep in deps:
                dep_layer = self._get_layer(dep, layers)
                if not dep_layer:
                    continue

                # Check if dependency is allowed
                if dep_layer not in allowed_layers and dep_layer != file_layer:
                    violations.append(
                        LayeringViolation(
                            file=file,
                            imported_file=dep,
                            rule=f"{file_layer} must not import from {dep_layer}",
                            severity="high" if dep_layer == "Presentation" else "medium",
                        )
                    )

        return violations

    def _detect_circular_dependencies(
        self, dep_graph: Dict[str, Set[str]]
    ) -> List[CircularDependency]:
        """Detect circular dependencies using DFS.

        Returns:
            List of CircularDependency objects
        """
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in dep_graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(
                        CircularDependency(
                            cycle=cycle,
                            severity="high" if len(cycle) <= 3 else "medium",
                        )
                    )

            path.pop()
            rec_stack.remove(node)

        for node in dep_graph:
            if node not in visited:
                dfs(node)

        return cycles

    def _detect_components(self, project: Project) -> List[Component]:
        """Detect components by grouping files by directory.

        Returns:
            List of Component objects
        """
        component_files: Dict[str, List[str]] = {}

        for file_path in project.files.keys():
            # Extract component name from path (first directory)
            parts = Path(file_path).parts
            if len(parts) >= 2:
                component_name = parts[1]  # repoq/analyzers → "analyzers"
            else:
                component_name = "Core"

            if component_name not in component_files:
                component_files[component_name] = []
            component_files[component_name].append(file_path)

        return [
            Component(
                name=name.capitalize(),
                files=files,
                public_api=[],  # TODO: Extract from __init__.py
                internal=files,  # All files are internal by default
            )
            for name, files in component_files.items()
        ]

    def _calculate_metrics(
        self, dep_graph: Dict[str, Set[str]], components: List[Component]
    ) -> ArchitectureMetrics:
        """Calculate Martin's architecture metrics.

        Metrics:
        - Cohesion: average within-component dependencies / total
        - Coupling: average between-component dependencies / total
        - Instability (I): Ce / (Ce + Ca) per component
        - Abstractness (A): Abstract classes / Total classes
        - Distance from Main Sequence (D): |A + I - 1|

        Returns:
            ArchitectureMetrics object
        """
        # Calculate cohesion (average within-component dependencies)
        within_component_deps = 0
        total_deps = sum(len(deps) for deps in dep_graph.values())

        for component in components:
            component_files = set(component.files)
            for file in component.files:
                for dep in dep_graph.get(file, []):
                    if dep in component_files:
                        within_component_deps += 1

        cohesion = within_component_deps / total_deps if total_deps > 0 else 0.0

        # Calculate coupling (between-component dependencies)
        between_component_deps = total_deps - within_component_deps
        coupling = between_component_deps / total_deps if total_deps > 0 else 0.0

        # Calculate instability per component (I = Ce / (Ce + Ca))
        instability = {}
        for component in components:
            ce = 0  # Efferent coupling (outgoing dependencies)
            ca = 0  # Afferent coupling (incoming dependencies)

            component_files = set(component.files)

            for file in component.files:
                for dep in dep_graph.get(file, []):
                    if dep not in component_files:
                        ce += 1

            for file, deps in dep_graph.items():
                if file not in component_files:
                    for dep in deps:
                        if dep in component_files:
                            ca += 1

            instability[component.name] = ce / (ce + ca) if (ce + ca) > 0 else 0.0

        # Abstractness and distance (placeholder - requires class analysis)
        abstractness = {comp.name: 0.0 for comp in components}
        distance = {
            comp.name: abs(abstractness[comp.name] + instability[comp.name] - 1.0)
            for comp in components
        }

        return ArchitectureMetrics(
            cohesion=cohesion,
            coupling=coupling,
            instability=instability,
            abstractness=abstractness,
            distance_from_main_sequence=distance,
        )

    def _build_c4_model(self, project: Project, components: List[Component]) -> C4Model:
        """Build C4 model hierarchy.

        Returns:
            C4Model with System → Container → Component hierarchy
        """
        # Group components into containers
        containers = {
            "CLI": C4Container(name="CLI", technology="Python Click"),
            "Core": C4Container(name="Core", technology="Python Library"),
            "Analyzers": C4Container(name="Analyzers", technology="Plugin Architecture"),
            "Reporting": C4Container(name="Reporting", technology="Visualization"),
        }

        for component in components:
            if component.name == "Cli":
                containers["CLI"].components.append(component)
            elif component.name == "Core":
                containers["Core"].components.append(component)
            elif component.name == "Analyzers":
                containers["Analyzers"].components.append(component)
            elif component.name == "Reporting":
                containers["Reporting"].components.append(component)
            else:
                # Default to Core
                containers["Core"].components.append(component)

        return C4Model(
            system=C4System(
                name="RepoQ",
                description="Repository Quality Analysis Tool with Semantic RDF Export",
                type="Software System",
            ),
            containers=[c for c in containers.values() if c.components],
        )


def export_architecture_rdf(graph, arch_model: ArchitectureModel, project_id: str) -> None:
    """Export architecture model to RDF graph.

    Adds triples for:
    - arch:Layer (with layerName, belongsToLayer)
    - arch:Component (with componentName, componentFiles)
    - arch:LayeringViolation (with violatingFile, violationRule, severity)
    - arch:CircularDependency (with cycle, severity)
    - c4:System, c4:Container, c4:Component (C4 model hierarchy)
    - swarch:Adaptability, swarch:Reliability, swarch:PerformanceEfficiency (Field33 metrics)

    Args:
        graph: RDFLib Graph to add triples to
        arch_model: ArchitectureModel from analyzer
        project_id: Project URI (e.g., "repo:repoq")

    Side Effects:
        Modifies `graph` in-place by adding architecture triples
    """
    from rdflib import RDF, Literal, Namespace, URIRef
    from rdflib.namespace import XSD

    ARCH = Namespace("http://example.org/vocab/arch#")
    C4 = Namespace("http://repoq.io/ontology/c4#")

    # Bind namespaces
    graph.bind("arch", ARCH)
    graph.bind("c4", C4)

    # 1. Export layers
    for layer in arch_model.layers:
        layer_uri = URIRef(f"{project_id}/arch/layer/{layer.name}")
        graph.add((layer_uri, RDF.type, ARCH.Layer))
        graph.add((layer_uri, ARCH.layerName, Literal(layer.name)))

        for file in layer.files:
            file_uri = URIRef(f"{project_id}/{file}")
            graph.add((file_uri, ARCH.belongsToLayer, layer_uri))

        # Dependencies
        for dep_layer in layer.depends_on:
            dep_uri = URIRef(f"{project_id}/arch/layer/{dep_layer}")
            graph.add((layer_uri, ARCH.allowedDependency, dep_uri))

    # 2. Export components
    for component in arch_model.components:
        comp_uri = URIRef(f"{project_id}/arch/component/{component.name}")
        graph.add((comp_uri, RDF.type, ARCH.Component))
        graph.add((comp_uri, ARCH.componentName, Literal(component.name)))

        for file in component.files:
            file_uri = URIRef(f"{project_id}/{file}")
            graph.add((file_uri, ARCH.belongsToComponent, comp_uri))

    # 3. Export layering violations
    for i, violation in enumerate(arch_model.layering_violations):
        viol_uri = URIRef(f"{project_id}/arch/violation/layering_{i}")
        graph.add((viol_uri, RDF.type, ARCH.LayeringViolation))
        graph.add((viol_uri, ARCH.violatingFile, Literal(violation.file)))
        graph.add((viol_uri, ARCH.importedFile, Literal(violation.imported_file)))
        graph.add((viol_uri, ARCH.violationRule, Literal(violation.rule)))
        graph.add((viol_uri, ARCH.severity, Literal(violation.severity)))

    # 4. Export circular dependencies
    for i, circular in enumerate(arch_model.circular_dependencies):
        circ_uri = URIRef(f"{project_id}/arch/violation/circular_{i}")
        graph.add((circ_uri, RDF.type, ARCH.CircularDependency))
        graph.add((circ_uri, ARCH.cycle, Literal(str(circular.cycle))))
        graph.add((circ_uri, ARCH.severity, Literal(circular.severity)))

    # 5. Export metrics
    metrics = arch_model.metrics
    metrics_uri = URIRef(f"{project_id}/arch/metrics")
    graph.add((metrics_uri, RDF.type, ARCH.Metrics))
    graph.add((metrics_uri, ARCH.cohesion, Literal(metrics.cohesion, datatype=XSD.decimal)))
    graph.add((metrics_uri, ARCH.coupling, Literal(metrics.coupling, datatype=XSD.decimal)))

    # Instability per component
    for comp_name, instability in metrics.instability.items():
        comp_uri = URIRef(f"{project_id}/arch/component/{comp_name}")
        graph.add((comp_uri, ARCH.instability, Literal(instability, datatype=XSD.decimal)))

    # 6. Export C4 model
    system = arch_model.c4_model.system
    system_uri = URIRef(f"{project_id}/c4/system")
    graph.add((system_uri, RDF.type, C4.System))
    graph.add((system_uri, C4.systemName, Literal(system.name)))
    graph.add((system_uri, C4.systemDescription, Literal(system.description)))

    for container in arch_model.c4_model.containers:
        container_uri = URIRef(f"{project_id}/c4/container/{container.name}")
        graph.add((container_uri, RDF.type, C4.Container))
        graph.add((container_uri, C4.belongsToSystem, system_uri))
        graph.add((container_uri, C4.containerName, Literal(container.name)))
        graph.add((container_uri, C4.technology, Literal(container.technology)))

        for component in container.components:
            comp_uri = URIRef(f"{project_id}/arch/component/{component.name}")
            graph.add((comp_uri, C4.belongsToContainer, container_uri))

    # 7. Export Field33 architecture metrics
    export_field33_metrics(graph, arch_model.metrics, project_id)


def export_field33_metrics(graph, metrics: ArchitectureMetrics, project_id: str) -> None:
    """Export Field33 software_architecture_metric ontology triples.

    Maps ArchitectureMetrics to Field33 ontology classes:
    - Adaptability (cohesion): ability to adapt to changes
    - Reliability (1 - instability_avg): ability to perform intended function
    - PerformanceEfficiency (1 - coupling): efficient use of resources

    Follows AWS Well-Architected Framework pillars:
    - https://wa.aws.amazon.com/wellarchitected/2020-07-02T19-33-23/

    Args:
        graph: RDFLib Graph to add triples to
        metrics: ArchitectureMetrics from analyzer
        project_id: Project URI (e.g., "repo:repoq")

    Side Effects:
        Adds Field33 metric triples to graph
    """
    from datetime import datetime, timezone

    from rdflib import RDF, Literal, Namespace, URIRef
    from rdflib.namespace import XSD

    # Field33 namespaces
    SWARCH = Namespace("http://field33.com/ontologies/@fld33_domain/software_architecture_metric/")
    METHODOLOGY = Namespace("http://field33.com/ontologies/@fld33/methodology/")

    graph.bind("swarch", SWARCH)
    graph.bind("methodology", METHODOLOGY)

    # 1. Adaptability (based on cohesion)
    # High cohesion = high adaptability (changes are localized)
    adaptability_uri = URIRef(f"{project_id}/arch/metric/adaptability")
    graph.add((adaptability_uri, RDF.type, SWARCH.Adaptability))
    graph.add(
        (adaptability_uri, METHODOLOGY.value, Literal(metrics.cohesion, datatype=XSD.decimal))
    )
    graph.add((adaptability_uri, METHODOLOGY.unit, Literal("score")))
    graph.add(
        (
            adaptability_uri,
            METHODOLOGY.timestamp,
            Literal(
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                datatype=XSD.dateTime,
            ),
        )
    )
    graph.add(
        (
            adaptability_uri,
            METHODOLOGY.description,
            Literal(
                "Architecture adaptability (cohesion): "
                "ability to adapt functionality to behavioral and structural changes"
            ),
        )
    )

    # 2. Reliability (based on inverse instability)
    # Low instability = high reliability (stable interfaces)
    if metrics.instability:
        instability_avg = sum(metrics.instability.values()) / len(metrics.instability)
        reliability_score = 1.0 - instability_avg
    else:
        reliability_score = 1.0

    reliability_uri = URIRef(f"{project_id}/arch/metric/reliability")
    graph.add((reliability_uri, RDF.type, SWARCH.Reliability))
    graph.add(
        (reliability_uri, METHODOLOGY.value, Literal(reliability_score, datatype=XSD.decimal))
    )
    graph.add((reliability_uri, METHODOLOGY.unit, Literal("score")))
    graph.add(
        (
            reliability_uri,
            METHODOLOGY.timestamp,
            Literal(
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                datatype=XSD.dateTime,
            ),
        )
    )
    graph.add(
        (
            reliability_uri,
            METHODOLOGY.description,
            Literal(
                "Architecture reliability (inverse instability): "
                "ability to perform intended function correctly and consistently"
            ),
        )
    )

    # 3. PerformanceEfficiency (based on inverse coupling)
    # Low coupling = high performance efficiency (less overhead)
    performance_score = 1.0 - metrics.coupling

    performance_uri = URIRef(f"{project_id}/arch/metric/performance_efficiency")
    graph.add((performance_uri, RDF.type, SWARCH.PerformanceEfficiency))
    graph.add(
        (performance_uri, METHODOLOGY.value, Literal(performance_score, datatype=XSD.decimal))
    )
    graph.add((performance_uri, METHODOLOGY.unit, Literal("score")))
    graph.add(
        (
            performance_uri,
            METHODOLOGY.timestamp,
            Literal(
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                datatype=XSD.dateTime,
            ),
        )
    )
    graph.add(
        (
            performance_uri,
            METHODOLOGY.description,
            Literal(
                "Architecture performance efficiency (inverse coupling): "
                "efficient use of computing resources"
            ),
        )
    )

    # 4. Link metrics to architecture model
    arch_uri = URIRef(f"{project_id}/arch/model")
    graph.add((arch_uri, RDF.type, SWARCH["Architecture"]))  # Custom class
    graph.add((arch_uri, SWARCH.hasMetric, adaptability_uri))
    graph.add((arch_uri, SWARCH.hasMetric, reliability_uri))
    graph.add((arch_uri, SWARCH.hasMetric, performance_uri))


def generate_architecture_recommendations(
    arch_model: ArchitectureModel, project_id: str
) -> List[Dict[str, Any]]:
    """Generate refactoring recommendations based on architecture violations.

    Creates recommendations for:
    - Layering violations (move imports to correct layer)
    - Circular dependencies (break cycles with dependency injection)
    - High coupling (introduce interfaces, extract components)

    Args:
        arch_model: ArchitectureModel from analyzer
        project_id: Project identifier

    Returns:
        List of recommendation dicts compatible with QualityRecommendation
    """
    recommendations = []
    rec_id = 1

    # 1. Recommendations for layering violations
    for violation in arch_model.layering_violations:
        delta_q = 15.0 if violation.severity == "high" else 8.0

        recommendations.append(
            {
                "id": f"{project_id}/quality/arch_rec_{rec_id}",
                "title": f"Fix layering violation in {violation.file}",
                "description": (
                    f"File {violation.file} imports {violation.imported_file}. "
                    f"Violation: {violation.rule}. "
                    "Move import to allowed layer or introduce facade pattern."
                ),
                "delta_q": delta_q,
                "priority": "high" if violation.severity == "high" else "medium",
                "target_file": violation.file,
                "estimated_effort_hours": 2.0,
                "category": "architecture",
                "violation_type": "layering_violation",
            }
        )
        rec_id += 1

    # 2. Recommendations for circular dependencies
    for circular in arch_model.circular_dependencies:
        delta_q = 12.0 if circular.severity == "high" else 6.0

        cycle_str = " → ".join(circular.cycle)
        recommendations.append(
            {
                "id": f"{project_id}/quality/arch_rec_{rec_id}",
                "title": f"Break circular dependency: {cycle_str}",
                "description": (
                    f"Circular dependency detected: {cycle_str}. "
                    "Consider: (1) Dependency injection, (2) Extract interface, "
                    "(3) Introduce events/observer pattern."
                ),
                "delta_q": delta_q,
                "priority": "high" if circular.severity == "high" else "medium",
                "target_file": circular.cycle[0] if circular.cycle else None,
                "estimated_effort_hours": 3.0,
                "category": "architecture",
                "violation_type": "circular_dependency",
            }
        )
        rec_id += 1

    # 3. Recommendations for high coupling
    for comp_name, instability in arch_model.metrics.instability.items():
        if instability > 0.8:  # High instability = many outgoing dependencies
            delta_q = 10.0

            recommendations.append(
                {
                    "id": f"{project_id}/quality/arch_rec_{rec_id}",
                    "title": f"Reduce coupling in {comp_name} component",
                    "description": (
                        f"Component {comp_name} has high instability (I={instability:.2f}). "
                        "Consider: (1) Extract stable interfaces, (2) Apply dependency inversion, "
                        "(3) Split into smaller components."
                    ),
                    "delta_q": delta_q,
                    "priority": "medium",
                    "target_file": None,
                    "estimated_effort_hours": 4.0,
                    "category": "architecture",
                    "violation_type": "high_coupling",
                }
            )
            rec_id += 1

    return recommendations
