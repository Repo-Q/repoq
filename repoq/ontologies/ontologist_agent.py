"""
OntologistAgent: Meta-level ontology management for analyzers.

Responsibilities:
- Validate ontology before analyzer registration
- Detect missing/invalid ontologies
- Generate suggestions (AI-powered) for fixing ontology issues
- Ensure soundness, completeness, consistency across all ontologies

Gates:
1. Ontology exists & parseable
2. All analyzer issue_types have corresponding OWL classes
3. Class hierarchy is acyclic (DAG)
4. Namespace isolation (no collisions)
5. Property domains/ranges consistent
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import networkx as nx
from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef

logger = logging.getLogger(__name__)

# Paths
ONTOLOGIES_DIR = Path(__file__).parent


class GateStatus(Enum):
    """Gate validation status."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"


@dataclass
class GateResult:
    """Result of a single gate validation."""
    gate_name: str
    status: GateStatus
    message: str
    details: Optional[dict] = None
    
    @property
    def passed(self) -> bool:
        return self.status == GateStatus.PASS
    
    @classmethod
    def PASS(cls, gate_name: str, message: str, details: dict = None) -> GateResult:
        return cls(gate_name, GateStatus.PASS, message, details)
    
    @classmethod
    def FAIL(cls, gate_name: str, message: str, details: dict = None) -> GateResult:
        return cls(gate_name, GateStatus.FAIL, message, details)
    
    @classmethod
    def WARNING(cls, gate_name: str, message: str, details: dict = None) -> GateResult:
        return cls(gate_name, GateStatus.WARNING, message, details)


@dataclass
class ValidationReport:
    """Full ontology validation report."""
    analyzer_name: str
    ontology_file: str
    gates: list[GateResult] = field(default_factory=list)
    ai_suggestion: Optional[str] = None
    
    @property
    def passed(self) -> bool:
        """All critical gates passed (warnings OK)."""
        return all(g.passed or g.status == GateStatus.WARNING for g in self.gates)
    
    @property
    def failed_gates(self) -> list[GateResult]:
        return [g for g in self.gates if g.status == GateStatus.FAIL]
    
    def summary(self) -> str:
        """Human-readable summary."""
        if self.passed:
            return f"✅ {self.analyzer_name} ontology validation PASSED ({len(self.gates)} gates checked)"
        
        failed = self.failed_gates
        return (
            f"❌ {self.analyzer_name} ontology validation FAILED\n"
            f"   Failed gates: {', '.join(g.gate_name for g in failed)}\n"
            + "\n".join(f"   - {g.gate_name}: {g.message}" for g in failed)
        )


@dataclass
class AnalyzerMetadata:
    """Metadata describing analyzer's ontology requirements."""
    name: str
    ontology: str  # e.g., "test.ttl"
    rdf_namespace: str  # e.g., "http://example.org/vocab/test#"
    issue_types: list[str]  # e.g., ["UncoveredFunction", "LowCoverage"]
    category: str = "quality"


class OntologistAgent:
    """
    Static ontology validator with optional AI-powered suggestions.
    
    Validates that:
    1. Ontology file exists and parses successfully
    2. All analyzer issue types have corresponding OWL classes
    3. Class hierarchy is acyclic
    4. Namespace is isolated (no conflicts)
    5. Property domains/ranges are consistent
    """
    
    def __init__(self, ontologies_dir: Path = ONTOLOGIES_DIR):
        self.ontologies_dir = ontologies_dir
        self._loaded_ontologies: dict[str, Graph] = {}
    
    def validate_for_analyzer(
        self,
        metadata: AnalyzerMetadata,
        mode: str = "strict"
    ) -> ValidationReport:
        """
        Validate ontology for analyzer.
        
        Args:
            metadata: Analyzer metadata (name, ontology, issue_types, etc.)
            mode: "strict" (fail-fast) or "ai_assist" (generate suggestions)
        
        Returns:
            ValidationReport with all gate results
        """
        report = ValidationReport(
            analyzer_name=metadata.name,
            ontology_file=metadata.ontology
        )
        
        # Gate 1: Existence & Parseability
        gate1 = self.check_ontology_exists(metadata)
        report.gates.append(gate1)
        if not gate1.passed:
            return report  # Fail-fast
        
        # Load ontology for subsequent gates
        ontology = self._load_ontology(metadata.ontology)
        
        # Gate 2: Issue Types Coverage
        gate2 = self.check_issue_types_defined(metadata, ontology)
        report.gates.append(gate2)
        
        # Gate 3: Acyclicity
        gate3 = self.check_no_cycles(ontology)
        report.gates.append(gate3)
        
        # Gate 4: Namespace Isolation
        gate4 = self.check_namespace_isolation(metadata, ontology)
        report.gates.append(gate4)
        
        # Gate 5: Property Consistency
        gate5 = self.check_property_consistency(ontology)
        report.gates.append(gate5)
        
        # AI assistance if requested and validation failed
        if mode == "ai_assist" and not report.passed:
            report.ai_suggestion = self._generate_ontology_suggestion(metadata, report)
        
        return report
    
    # =========================================================================
    # GATES
    # =========================================================================
    
    def check_ontology_exists(self, metadata: AnalyzerMetadata) -> GateResult:
        """Gate 1: Ontology file exists and is parseable."""
        ontology_path = self.ontologies_dir / metadata.ontology
        
        if not ontology_path.exists():
            return GateResult.FAIL(
                "ontology_exists",
                f"Ontology file not found: {metadata.ontology}",
                {"path": str(ontology_path)}
            )
        
        try:
            g = Graph()
            g.parse(ontology_path, format='turtle')
            return GateResult.PASS(
                "ontology_exists",
                f"Ontology loaded successfully ({len(g)} triples)",
                {"path": str(ontology_path), "triples": len(g)}
            )
        except Exception as e:
            return GateResult.FAIL(
                "ontology_exists",
                f"Failed to parse ontology: {e}",
                {"path": str(ontology_path), "error": str(e)}
            )
    
    def check_issue_types_defined(
        self,
        metadata: AnalyzerMetadata,
        ontology: Graph
    ) -> GateResult:
        """Gate 2: All issue_types have corresponding OWL classes."""
        namespace = Namespace(metadata.rdf_namespace)
        missing = []
        
        for issue_type in metadata.issue_types:
            cls_uri = namespace[issue_type]
            
            # Check if class exists in ontology
            is_class = (cls_uri, RDF.type, OWL.Class) in ontology
            is_subclass = len(list(ontology.triples((cls_uri, RDFS.subClassOf, None)))) > 0
            
            if not (is_class or is_subclass):
                missing.append(issue_type)
        
        if missing:
            return GateResult.FAIL(
                "issue_types_defined",
                f"Missing OWL classes for issue types: {missing}",
                {"missing": missing, "namespace": metadata.rdf_namespace}
            )
        
        return GateResult.PASS(
            "issue_types_defined",
            f"All {len(metadata.issue_types)} issue types defined as OWL classes",
            {"issue_types": metadata.issue_types}
        )
    
    def check_no_cycles(self, ontology: Graph) -> GateResult:
        """Gate 3: Class hierarchy is acyclic (DAG)."""
        graph = nx.DiGraph()
        
        # Build inheritance graph
        for s, p, o in ontology.triples((None, RDFS.subClassOf, None)):
            if isinstance(o, URIRef):
                graph.add_edge(str(s), str(o))
        
        if graph.number_of_nodes() == 0:
            return GateResult.PASS(
                "no_cycles",
                "No class hierarchy (no rdfs:subClassOf relationships)",
                {"nodes": 0, "edges": 0}
            )
        
        try:
            cycles = list(nx.simple_cycles(graph))
            if cycles:
                return GateResult.FAIL(
                    "no_cycles",
                    f"Circular inheritance detected: {len(cycles)} cycle(s)",
                    {"cycles": cycles[:3]}  # Show first 3
                )
            
            return GateResult.PASS(
                "no_cycles",
                f"Class hierarchy is acyclic (DAG with {graph.number_of_nodes()} nodes)",
                {"nodes": graph.number_of_nodes(), "edges": graph.number_of_edges()}
            )
        except Exception as e:
            return GateResult.WARNING(
                "no_cycles",
                f"Could not check for cycles: {e}",
                {"error": str(e)}
            )
    
    def check_namespace_isolation(
        self,
        metadata: AnalyzerMetadata,
        ontology: Graph
    ) -> GateResult:
        """Gate 4: All classes/properties use declared namespace."""
        namespace = Namespace(metadata.rdf_namespace)
        violations = []
        
        # Check classes
        for cls in ontology.subjects(RDF.type, OWL.Class):
            if isinstance(cls, URIRef) and not str(cls).startswith(str(namespace)):
                # Allow standard prefixes (owl, rdfs, rdf)
                if not any(str(cls).startswith(p) for p in [
                    "http://www.w3.org/2002/07/owl#",
                    "http://www.w3.org/2000/01/rdf-schema#",
                    "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
                ]):
                    violations.append(("class", str(cls)))
        
        # Check properties
        for prop in ontology.subjects(RDF.type, OWL.ObjectProperty):
            if isinstance(prop, URIRef) and not str(prop).startswith(str(namespace)):
                violations.append(("property", str(prop)))
        
        for prop in ontology.subjects(RDF.type, OWL.DatatypeProperty):
            if isinstance(prop, URIRef) and not str(prop).startswith(str(namespace)):
                violations.append(("property", str(prop)))
        
        if violations:
            return GateResult.FAIL(
                "namespace_isolation",
                f"{len(violations)} entities outside declared namespace",
                {"violations": violations[:5], "namespace": metadata.rdf_namespace}
            )
        
        return GateResult.PASS(
            "namespace_isolation",
            f"All entities use declared namespace: {metadata.rdf_namespace}",
            {"namespace": metadata.rdf_namespace}
        )
    
    def check_property_consistency(self, ontology: Graph) -> GateResult:
        """Gate 5: Properties have valid domains and ranges."""
        issues = []
        
        # Check ObjectProperty domains/ranges
        for prop in ontology.subjects(RDF.type, OWL.ObjectProperty):
            domains = list(ontology.objects(prop, RDFS.domain))
            ranges = list(ontology.objects(prop, RDFS.range))
            
            # Domains should exist as classes
            for domain in domains:
                if isinstance(domain, URIRef):
                    if (domain, RDF.type, OWL.Class) not in ontology:
                        issues.append(f"Property {prop} has undefined domain: {domain}")
            
            # Ranges should exist as classes
            for rng in ranges:
                if isinstance(rng, URIRef):
                    if (rng, RDF.type, OWL.Class) not in ontology:
                        issues.append(f"Property {prop} has undefined range: {rng}")
        
        if issues:
            return GateResult.WARNING(
                "property_consistency",
                f"{len(issues)} property domain/range issue(s)",
                {"issues": issues[:5]}
            )
        
        return GateResult.PASS(
            "property_consistency",
            "All property domains and ranges are defined",
            {}
        )
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _load_ontology(self, ontology_file: str) -> Graph:
        """Load and cache ontology."""
        if ontology_file in self._loaded_ontologies:
            return self._loaded_ontologies[ontology_file]
        
        g = Graph()
        ontology_path = self.ontologies_dir / ontology_file
        g.parse(ontology_path, format='turtle')
        self._loaded_ontologies[ontology_file] = g
        return g
    
    def _generate_ontology_suggestion(
        self,
        metadata: AnalyzerMetadata,
        report: ValidationReport
    ) -> str:
        """Generate AI-powered suggestion for fixing ontology issues."""
        # For now, return static suggestion
        # TODO: Integrate with BAML GenerateOntologyFragment
        
        failed = report.failed_gates
        if not failed:
            return None
        
        suggestion = "# Suggested fixes:\n\n"
        
        for gate in failed:
            if gate.gate_name == "issue_types_defined":
                missing = gate.details.get("missing", [])
                namespace_prefix = metadata.rdf_namespace.split('#')[0].split('/')[-1]
                
                suggestion += f"# Missing classes for {metadata.name}:\n"
                for issue_type in missing:
                    suggestion += f"""
{namespace_prefix}:{issue_type} a owl:Class ;
    rdfs:subClassOf quality:Issue ;
    rdfs:label "{issue_type.replace('_', ' ')}" ;
    rdfs:comment "Issue type for {metadata.name}" .
"""
        
        return suggestion


# =============================================================================
# CLI for manual validation
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python ontologist_agent.py <ontology_file.ttl>")
        sys.exit(1)
    
    ontology_file = sys.argv[1]
    
    # Example: validate test.ttl
    metadata = AnalyzerMetadata(
        name="CoverageAnalyzer",
        ontology=ontology_file,
        rdf_namespace="http://example.org/vocab/test#",
        issue_types=["UncoveredFunction", "LowCoverage"],
        category="testing"
    )
    
    agent = OntologistAgent()
    report = agent.validate_for_analyzer(metadata, mode="ai_assist")
    
    print(report.summary())
    
    if report.ai_suggestion:
        print("\n" + "="*80)
        print("AI SUGGESTION:")
        print("="*80)
        print(report.ai_suggestion)
    
    sys.exit(0 if report.passed else 1)
