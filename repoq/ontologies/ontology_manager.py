"""
Ontology Plugin Manager for RepoQ

Manages loading, configuration, and execution of ontology-based analysis plugins.
Provides a framework for extending RepoQ with domain-specific knowledge systems.
"""

import importlib.util
import json
import logging
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path

# Type imports for forward references
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from ..core.model import DependencyEdge, File, Module, Project

logger = logging.getLogger(__name__)

import logging
from dataclasses import dataclass

try:
    import rdflib
    from rdflib import OWL, RDF, RDFS, Graph, Namespace
    from rdflib.plugins.stores.memory import Memory

    HAS_RDFLIB = True
except ImportError:
    HAS_RDFLIB = False
    Graph = None

logger = logging.getLogger(__name__)


class OntologyType(Enum):
    """Types of supported ontologies."""

    CODE = "code"
    ARCHITECTURE = "c4"
    DOMAIN = "ddd"
    PATTERNS = "patterns"
    QUALITY = "quality"
    CUSTOM = "custom"


@dataclass
class OntologyMetadata:
    """Metadata for an ontology plugin."""

    name: str
    type: OntologyType
    version: str
    description: str
    namespace: str
    dependencies: List[str]
    file_path: Path
    enabled: bool = True
    priority: int = 100  # Lower number = higher priority


class OntologyPlugin(ABC):
    """Abstract base class for ontology plugins."""

    def __init__(self, metadata: OntologyMetadata):
        self.metadata = metadata
        self.graph: Optional[Any] = None  # rdflib.Graph when available
        self._loaded = False
        self._concepts: Dict[str, Any] = {}
        self._inference_rules: List[Dict[str, Any]] = []

    @abstractmethod
    def detect_applicability(self, project_data: Dict[str, Any]) -> float:
        """
        Determine if this ontology is applicable to the project.
        Returns confidence score 0.0-1.0.
        """
        pass

    def check_applicability(self, project_data: Dict[str, Any]) -> float:
        """
        Alias for detect_applicability for backward compatibility.
        Returns confidence score 0.0-1.0.
        """
        return self.detect_applicability(project_data)

    @abstractmethod
    def extract_concepts(self, project_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract ontology concepts from project data."""
        pass

    @abstractmethod
    def validate_constraints(self, concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate extracted concepts against ontology constraints."""
        pass

    def load_ontology(self) -> bool:
        """Load the ontology definition."""
        if self._loaded:
            return True

        try:
            if not HAS_RDFLIB:
                logger.warning("rdflib not available, ontology features disabled")
                return False

            self.graph = Graph()

            # Load JSON-LD ontology file
            with open(self.metadata.file_path, "r", encoding="utf-8") as f:
                ontology_data = json.load(f)

            # Parse JSON-LD into RDF graph
            self.graph.parse(data=json.dumps(ontology_data), format="json-ld")

            self._loaded = True
            logger.info(f"Loaded ontology: {self.metadata.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load ontology {self.metadata.name}: {e}")
            return False

    def get_concept_hierarchy(self) -> Dict[str, List[str]]:
        """Get class hierarchy from ontology."""
        if not self._loaded or not self.graph:
            return {}

        hierarchy = {}
        for subj, pred, obj in self.graph.triples((None, RDFS.subClassOf, None)):
            parent = str(obj)
            child = str(subj)
            if parent not in hierarchy:
                hierarchy[parent] = []
            hierarchy[parent].append(child)

        return hierarchy

    def get_properties(self, concept_uri: str) -> List[str]:
        """Get properties applicable to a concept."""
        if not self._loaded or not self.graph:
            return []

        properties = []
        concept = rdflib.URIRef(concept_uri)

        # Find properties with this concept as domain
        for subj, pred, obj in self.graph.triples((None, RDFS.domain, concept)):
            properties.append(str(subj))

        return properties

    def infer_relationships(self, concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply inference rules to derive new relationships."""
        if not self._loaded:
            return []

        inferred = []

        # Apply simple RDFS inference
        for rule in self._inference_rules:
            try:
                inferred.extend(self._apply_inference_rule(rule, concepts))
            except Exception as e:
                logger.warning(f"Inference rule failed: {e}")

        return inferred

    def _apply_inference_rule(
        self, rule: Dict[str, Any], concepts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply a single inference rule."""
        # Simplified inference - real implementation would use proper reasoner
        return []


class CodeOntologyPlugin(OntologyPlugin):
    """Plugin for basic code structure ontology."""

    def detect_applicability(self, project_data: Dict[str, Any]) -> float:
        """Always applicable for code projects."""
        files = project_data.get("files", [])
        code_files = []
        for f in files:
            # Handle both dict and string formats
            path = f if isinstance(f, str) else f.get("path", "")
            if any(path.endswith(ext) for ext in [".py", ".js", ".java", ".cpp", ".cs"]):
                code_files.append(path)
        return min(1.0, len(code_files) / 10)  # Max at 10+ code files

    def extract_concepts(self, project_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract code concepts like classes, methods, functions."""
        concepts = []

        structure_data = project_data.get("analyzers", {}).get("structure", {})
        files = structure_data.get("files", [])

        for file_info in files:
            # Module concept
            concepts.append(
                {
                    "@type": "code:Module",
                    "@id": f"code:module:{file_info.get('path', 'unknown')}",
                    "code:hasName": file_info.get("name", ""),
                    "code:hasPath": file_info.get("path", ""),
                    "code:hasLineCount": file_info.get("lines", 0),
                    "code:hasLanguage": file_info.get("language", "unknown"),
                }
            )

            # Class concepts
            classes = file_info.get("classes", [])
            for class_info in classes:
                concepts.append(
                    {
                        "@type": "code:Class",
                        "@id": f"code:class:{class_info.get('name', 'unknown')}",
                        "code:hasName": class_info.get("name", ""),
                        "code:hasComplexity": class_info.get("complexity", 0),
                        "code:hasLineCount": class_info.get("lines", 0),
                    }
                )

                # Method concepts
                methods = class_info.get("methods", [])
                for method_info in methods:
                    concepts.append(
                        {
                            "@type": "code:Method",
                            "@id": f"code:method:{method_info.get('name', 'unknown')}",
                            "code:hasName": method_info.get("name", ""),
                            "code:hasComplexity": method_info.get("complexity", 0),
                            "code:hasVisibility": method_info.get("visibility", "public"),
                        }
                    )

        return concepts

    def validate_constraints(self, concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate code concepts against constraints."""
        violations = []

        for concept in concepts:
            concept_type = concept.get("@type", "")

            # High complexity violation
            if "code:hasComplexity" in concept:
                complexity = concept["code:hasComplexity"]
                if complexity > 15:
                    violations.append(
                        {
                            "type": "high_complexity",
                            "concept": concept.get("@id", ""),
                            "message": f"Complexity {complexity} exceeds threshold of 15",
                            "severity": "warning" if complexity <= 20 else "error",
                        }
                    )

            # Large module violation
            if concept_type == "code:Module" and "code:hasLineCount" in concept:
                lines = concept["code:hasLineCount"]
                if lines > 1000:
                    violations.append(
                        {
                            "type": "large_module",
                            "concept": concept.get("@id", ""),
                            "message": f"Module has {lines} lines, consider splitting",
                            "severity": "warning",
                        }
                    )

        return violations


class C4ModelPlugin(OntologyPlugin):
    """Plugin for C4 architectural model."""

    def detect_applicability(self, project_data: Dict[str, Any]) -> float:
        """Applicable if architectural patterns detected."""
        # Look for microservices, APIs, containers, etc.
        structure = project_data.get("analyzers", {}).get("structure", {})

        # Check for architectural indicators
        indicators = 0
        files = structure.get("files", [])

        for file_info in files:
            path = file_info.get("path", "").lower()
            if any(pattern in path for pattern in ["api", "service", "controller", "component"]):
                indicators += 1

        return min(1.0, indicators / 5)  # Max at 5+ architectural files

    def extract_concepts(self, project_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract C4 architectural concepts."""
        concepts = []

        # System level concept
        concepts.append(
            {
                "@type": "c4:SoftwareSystem",
                "@id": "c4:system:main",
                "c4:hasName": project_data.get("project_name", "Unknown System"),
                "c4:hasDescription": "Main software system",
                "c4:isInternal": True,
            }
        )

        # Container level concepts (detect from directory structure)
        structure = project_data.get("analyzers", {}).get("structure", {})
        directories = set()

        for file_info in structure.get("files", []):
            path_parts = Path(file_info.get("path", "")).parts
            if len(path_parts) > 1:
                directories.add(path_parts[0])

        for directory in directories:
            concepts.append(
                {
                    "@type": "c4:Container",
                    "@id": f"c4:container:{directory}",
                    "c4:hasName": directory,
                    "c4:hasDescription": f"Container for {directory} functionality",
                    "c4:hasTechnology": "Python",  # Simplified
                }
            )

        # Component level concepts (from classes/modules)
        files = structure.get("files", [])
        for file_info in files:
            if file_info.get("classes"):
                concepts.append(
                    {
                        "@type": "c4:Component",
                        "@id": f"c4:component:{file_info.get('name', 'unknown')}",
                        "c4:hasName": file_info.get("name", ""),
                        "c4:hasResponsibility": f"Implements {file_info.get('name', '')} functionality",
                        "c4:mappedToCode": f"code:module:{file_info.get('path', '')}",
                    }
                )

        return concepts

    def validate_constraints(self, concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate C4 architectural constraints."""
        violations = []

        # Check for too many dependencies
        containers = [c for c in concepts if c.get("@type") == "c4:Container"]
        if len(containers) > 10:
            violations.append(
                {
                    "type": "too_many_containers",
                    "message": f"System has {len(containers)} containers, consider consolidation",
                    "severity": "warning",
                }
            )

        return violations


class DDDOntologyPlugin(OntologyPlugin):
    """Plugin for Domain-Driven Design concepts."""

    def detect_applicability(self, project_data: Dict[str, Any]) -> float:
        """Applicable if DDD patterns detected."""
        structure = project_data.get("analyzers", {}).get("structure", {})

        # Look for DDD indicators
        ddd_indicators = ["entity", "aggregate", "repository", "service", "domain", "valueobject"]
        score = 0

        for file_info in structure.get("files", []):
            path = file_info.get("path", "").lower()
            name = file_info.get("name", "").lower()

            for indicator in ddd_indicators:
                if indicator in path or indicator in name:
                    score += 1
                    break

        return min(1.0, score / 3)  # Max at 3+ DDD indicators

    def extract_concepts(self, project_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract DDD concepts."""
        concepts = []

        # Detect bounded contexts from directory structure
        structure = project_data.get("analyzers", {}).get("structure", {})
        contexts = set()

        for file_info in structure.get("files", []):
            path_parts = Path(file_info.get("path", "")).parts
            if len(path_parts) > 2 and path_parts[0] == "src":
                contexts.add(path_parts[1])

        for context in contexts:
            concepts.append(
                {
                    "@type": "ddd:BoundedContext",
                    "@id": f"ddd:context:{context}",
                    "ddd:hasName": context,
                    "ddd:hasDescription": f"Bounded context for {context} domain",
                    "ddd:contextType": "ddd:Core",  # Simplified
                }
            )

        # Detect entities, services, etc. from class names
        for file_info in structure.get("files", []):
            classes = file_info.get("classes", [])

            for class_info in classes:
                class_name = class_info.get("name", "").lower()

                if "entity" in class_name:
                    concepts.append(
                        {
                            "@type": "ddd:Entity",
                            "@id": f"ddd:entity:{class_info.get('name', '')}",
                            "ddd:hasName": class_info.get("name", ""),
                            "ddd:implementedBy": f"code:class:{class_info.get('name', '')}",
                        }
                    )
                elif "service" in class_name:
                    concepts.append(
                        {
                            "@type": "ddd:DomainService",
                            "@id": f"ddd:service:{class_info.get('name', '')}",
                            "ddd:hasName": class_info.get("name", ""),
                            "ddd:implementedBy": f"code:class:{class_info.get('name', '')}",
                        }
                    )
                elif "repository" in class_name:
                    concepts.append(
                        {
                            "@type": "ddd:Repository",
                            "@id": f"ddd:repository:{class_info.get('name', '')}",
                            "ddd:hasName": class_info.get("name", ""),
                            "ddd:implementedBy": f"code:class:{class_info.get('name', '')}",
                        }
                    )

        return concepts

    def validate_constraints(self, concepts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate DDD constraints."""
        violations = []

        # Check for anemic domain model
        entities = [c for c in concepts if c.get("@type") == "ddd:Entity"]
        services = [c for c in concepts if c.get("@type") == "ddd:DomainService"]

        if len(services) > len(entities) * 2:
            violations.append(
                {
                    "type": "anemic_domain_model",
                    "message": f"Too many services ({len(services)}) vs entities ({len(entities)}), possible anemic domain model",
                    "severity": "warning",
                }
            )

        return violations


class OntologyManager:
    """Manages ontology plugins and provides unified interface."""

    def __init__(self, plugin_directory: Optional[Path] = None):
        self.plugin_directory = plugin_directory or Path(__file__).parent / "plugins"
        self.plugins: Dict[str, OntologyPlugin] = {}
        self.active_plugins: set = set()  # Set of active plugin names
        self._loaded = False

    def load_plugins(self) -> None:
        """Load all available ontology plugins."""
        if self._loaded:
            return

        # Load built-in plugins
        self._register_builtin_plugins()

        # Load custom plugins from directory
        self._load_custom_plugins()

        self._loaded = True
        logger.info(f"Loaded {len(self.plugins)} ontology plugins")

    def _register_builtin_plugins(self) -> None:
        """Register built-in ontology plugins."""
        plugins = [
            (CodeOntologyPlugin, "code_ontology.jsonld", OntologyType.CODE),
            (C4ModelPlugin, "c4_model.jsonld", OntologyType.ARCHITECTURE),
            (DDDOntologyPlugin, "ddd_ontology.jsonld", OntologyType.DOMAIN),
        ]

        for plugin_class, filename, ontology_type in plugins:
            file_path = self.plugin_directory / filename
            if file_path.exists():
                metadata = OntologyMetadata(
                    name=plugin_class.__name__,
                    type=ontology_type,
                    version="1.0.0",
                    description=plugin_class.__doc__ or "",
                    namespace=f"http://ontology.repoq.dev/{ontology_type.value}#",
                    dependencies=[],
                    file_path=file_path,
                )

                plugin = plugin_class(metadata)
                self.plugins[metadata.name] = plugin

    def _load_custom_plugins(self) -> None:
        """Load custom ontology plugins from directory."""
        if not self.plugin_directory.exists():
            return

        for plugin_file in self.plugin_directory.glob("*.py"):
            try:
                self._load_custom_plugin(plugin_file)
            except Exception as e:
                logger.warning(f"Failed to load custom plugin {plugin_file}: {e}")

    def _load_custom_plugin(self, plugin_file: Path) -> None:
        """Load a single custom plugin file."""
        spec = importlib.util.spec_from_file_location("custom_plugin", plugin_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Look for OntologyPlugin subclasses
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, OntologyPlugin)
                    and attr != OntologyPlugin
                ):
                    # Create plugin instance
                    # This would need metadata configuration
                    pass

    def analyze_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze project data using all applicable ontologies.

        Args:
            project_data: Dictionary containing project information

        Returns:
            Dictionary with analysis results from all ontologies
        """
        analysis_results = {
            "concepts": [],
            "relationships": [],
            "violations": [],
            "plugin_results": {},
            "summary": {},
        }

        # Load ontologies on first use
        if not self.plugins:
            self.load_plugins()

        # Apply each plugin to project data
        concept_map = {}
        for plugin_name, plugin in self.plugins.items():
            if not plugin.metadata.enabled:
                continue

            try:
                # Check if plugin is applicable
                applicability = plugin.check_applicability(project_data)
                if applicability < 0.1:  # Skip if not applicable
                    continue

                self.active_plugins.add(plugin_name)
                plugin.applicability_score = applicability

                # Extract concepts
                concepts = plugin.extract_concepts(project_data)
                concept_map[plugin_name] = concepts
                analysis_results["concepts"].extend(concepts)

                # Validate concepts
                violations = plugin.validate_constraints(concepts)
                analysis_results["violations"].extend(violations)

                # Store plugin-specific results
                analysis_results["plugin_results"][plugin_name] = {
                    "applicability": applicability,
                    "concepts": concepts,
                    "violations": violations,
                }

                logger.info(
                    f"Applied {plugin_name}: {len(concepts)} concepts, {len(violations)} violations"
                )

            except Exception as e:
                logger.error(f"Plugin {plugin_name} failed: {e}")
                continue

        # Generate cross-ontology relationships
        if len(concept_map) > 1:
            relationships = self._generate_cross_ontology_relationships(concept_map)
            analysis_results["relationships"] = relationships

        # Generate summary
        analysis_results["summary"] = {
            "total_concepts": len(analysis_results["concepts"]),
            "total_violations": len(analysis_results["violations"]),
            "active_plugins": list(self.active_plugins),
            "ontology_coverage": len(self.active_plugins) / len(self.plugins)
            if self.plugins
            else 0,
        }

        return analysis_results

    def analyze_project_structure(self, project: "Project") -> Dict[str, Any]:
        """
        Analyze project structure using loaded ontologies.

        Args:
            project: Project object to analyze

        Returns:
            Dictionary with ontological analysis results
        """
        # Convert Project object to dictionary for analysis
        project_data = self._project_to_dict(project)

        # Use standard project analysis
        return self.analyze_project(project_data)

    def _project_to_dict(self, project: "Project") -> Dict[str, Any]:
        """Convert Project object to dictionary for ontology analysis."""
        # Handle case where files/modules are dicts (keyed by ID) vs lists
        files = project.files if isinstance(project.files, list) else list(project.files.values())
        modules = (
            project.modules if isinstance(project.modules, list) else list(project.modules.values())
        )

        return {
            "name": project.name,
            "description": project.description,
            "programming_languages": getattr(project, "programming_languages", {}),
            "files": [self._file_to_dict(f) for f in files],
            "modules": [self._module_to_dict(m) for m in modules],
            "dependencies": [self._dependency_to_dict(d) for d in project.dependencies],
            "license": project.license,
            "ci_configured": getattr(project, "ci_configured", []),
        }

    def _file_to_dict(self, file: "File") -> Dict[str, Any]:
        """Convert File object to dictionary."""
        return {
            "path": file.path,
            "size": file.lines_of_code,  # Use lines_of_code as size
            "language": file.language,
            "checksum": file.checksum_value,
            "type": "file",
            "complexity": file.complexity,
            "maintainability": file.maintainability,
        }

    def _module_to_dict(self, module: "Module") -> Dict[str, Any]:
        """Convert Module object to dictionary."""
        return {
            "name": module.name,
            "path": module.path,
            "language": getattr(module, "language", "unknown"),  # Module might not have language
            "type": "module",
            "contains_files": getattr(module, "contains_files", []),
            "contains_modules": getattr(module, "contains_modules", []),
        }

    def _dependency_to_dict(self, dependency: "DependencyEdge") -> Dict[str, Any]:
        """Convert DependencyEdge object to dictionary."""
        return {
            "source": dependency.source,
            "target": dependency.target,
            "type": dependency.type,
            "relationship": "dependency",
        }
        """Analyze project using applicable ontologies."""
        if not self._loaded:
            self.load_plugins()

        # Determine applicable plugins
        self.active_plugins = set()  # Use set for O(1) lookup and .add() method
        for plugin in self.plugins.values():
            if plugin.metadata.enabled:
                score = plugin.detect_applicability(project_data)
                if score > 0.1:  # Minimum threshold
                    plugin.applicability_score = score
                    self.active_plugins.add(plugin.metadata.name)

        # Sort by applicability score and priority
        self.active_plugins.sort(key=lambda p: (-p.applicability_score, p.metadata.priority))

        # Load ontologies for active plugins
        for plugin in self.active_plugins:
            plugin.load_ontology()

        # Extract concepts from each applicable ontology
        all_concepts = []
        all_violations = []

        for plugin in self.active_plugins:
            try:
                concepts = plugin.extract_concepts(project_data)
                violations = plugin.validate_constraints(concepts)

                # Add ontology metadata to concepts
                for concept in concepts:
                    concept["_ontology"] = plugin.metadata.name
                    concept["_ontology_type"] = plugin.metadata.type.value

                all_concepts.extend(concepts)
                all_violations.extend(violations)

                logger.info(
                    f"Plugin {plugin.metadata.name}: {len(concepts)} concepts, {len(violations)} violations"
                )

            except Exception as e:
                logger.error(f"Plugin {plugin.metadata.name} failed: {e}")

        # Apply cross-ontology inference
        inferred_relationships = self._apply_cross_ontology_inference(all_concepts)

        return {
            "concepts": all_concepts,
            "violations": all_violations,
            "inferred_relationships": inferred_relationships,
            "active_ontologies": [p.metadata.name for p in self.active_plugins],
            "ontology_coverage": {
                p.metadata.type.value: p.applicability_score for p in self.active_plugins
            },
        }

    def _apply_cross_ontology_inference(
        self, concepts: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply inference rules across different ontologies."""
        relationships = []

        # Map concepts by type for cross-reference
        concept_map = {}
        for concept in concepts:
            concept_type = concept.get("@type", "")
            if concept_type not in concept_map:
                concept_map[concept_type] = []
            concept_map[concept_type].append(concept)

        # Apply cross-ontology mapping rules
        relationships.extend(self._map_code_to_c4(concept_map))
        relationships.extend(self._map_ddd_to_c4(concept_map))
        relationships.extend(self._map_code_to_ddd(concept_map))

        return relationships

    def _map_code_to_c4(self, concept_map: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Map code concepts to C4 architectural elements."""
        relationships = []

        code_classes = concept_map.get("code:Class", [])
        c4_components = concept_map.get("c4:Component", [])

        # Simple mapping: classes to components based on name similarity
        for code_class in code_classes:
            class_name = code_class.get("code:hasName", "").lower()

            for component in c4_components:
                component_name = component.get("c4:hasName", "").lower()

                if class_name in component_name or component_name in class_name:
                    relationships.append(
                        {
                            "@type": "cross-ontology:implements",
                            "source": component.get("@id"),
                            "target": code_class.get("@id"),
                            "confidence": 0.8,
                            "type": "code_to_c4_mapping",
                        }
                    )

        return relationships

    def _map_ddd_to_c4(self, concept_map: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Map DDD concepts to C4 architectural elements."""
        relationships = []

        bounded_contexts = concept_map.get("ddd:BoundedContext", [])
        c4_containers = concept_map.get("c4:Container", [])

        # Map bounded contexts to containers
        for context in bounded_contexts:
            context_name = context.get("ddd:hasName", "").lower()

            for container in c4_containers:
                container_name = container.get("c4:hasName", "").lower()

                if context_name == container_name:
                    relationships.append(
                        {
                            "@type": "cross-ontology:maps_to",
                            "source": context.get("@id"),
                            "target": container.get("@id"),
                            "confidence": 0.9,
                            "type": "ddd_to_c4_mapping",
                        }
                    )

        return relationships

    def _map_code_to_ddd(
        self, concept_map: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Map code concepts to DDD concepts."""
        relationships = []

        # This is handled in the DDD plugin's 'implementedBy' property
        # Additional cross-reference logic could be added here

        return relationships

    def get_ontology_summary(self) -> Dict[str, Any]:
        """Get summary of loaded ontologies."""
        return {
            "total_plugins": len(self.plugins),
            "active_plugins": len(self.active_plugins),
            "ontology_types": list(set(p.metadata.type.value for p in self.plugins.values())),
            "plugins": {
                name: {
                    "type": plugin.metadata.type.value,
                    "enabled": plugin.metadata.enabled,
                    "loaded": plugin._loaded,
                    "applicability": getattr(plugin, "applicability_score", 0.0),
                }
                for name, plugin in self.plugins.items()
            },
        }


# Global ontology manager instance
ontology_manager = OntologyManager()


def analyze_with_ontologies(project_data: Dict[str, Any]) -> Dict[str, Any]:
    """Main function to analyze project with ontology support."""
    return ontology_manager.analyze_project(project_data)


def get_supported_ontologies() -> List[str]:
    """Get list of supported ontology types."""
    return [ot.value for ot in OntologyType]
