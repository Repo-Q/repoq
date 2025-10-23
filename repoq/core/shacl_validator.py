"""SHACL Validator: Declarative quality validation via SHACL shapes.

This module implements SHACL validation for RDF graphs generated from repository analysis.
Provides actionable feedback by detecting quality violations and architecture issues.

Architecture:
    - SHACLViolation: Dataclass for individual violations
    - ValidationReport: Aggregate report with statistics
    - SHACLValidator: Main validator class using pySHACL

References:
    - FR-01: Detailed Gate Output
    - FR-02: Actionable Feedback
    - V01: Transparency (clear violation messages)
    - V06: Fairness (context-aware rules)
    - ADR-002: RDFLib + pySHACL

Usage:
    >>> validator = SHACLValidator()
    >>> validator.load_shapes("repoq/shapes/quality_constraints.ttl")
    >>> report = validator.validate(data_graph)
    >>> if not report.conforms:
    ...     for violation in report.violations:
    ...         print(f"{violation.focus_node}: {violation.message}")
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pyshacl import validate
from rdflib import Graph, Namespace
from rdflib.namespace import SH

logger = logging.getLogger(__name__)

# Namespaces
REPO = Namespace("https://repoq.dev/ontology/repo#")
CODE = Namespace("http://field33.com/ontologies/CODE/")


@dataclass
class SHACLViolation:
    """SHACL validation violation.

    Attributes:
        focus_node: URI of the node that violated the constraint
        result_path: Property path that was validated
        value: Actual value that caused violation (if applicable)
        message: Human-readable violation message
        severity: sh:Violation, sh:Warning, or sh:Info
        source_shape: URI of the shape that triggered violation
    """

    focus_node: str
    result_path: Optional[str] = None
    value: Optional[str] = None
    message: str = ""
    severity: str = "Violation"
    source_shape: Optional[str] = None

    def __str__(self) -> str:
        """Format violation for display."""
        parts = [f"[{self.severity}]", f"{self.focus_node}"]
        if self.result_path:
            parts.append(f"→ {self.result_path}")
        if self.value:
            parts.append(f"= {self.value}")
        parts.append(f": {self.message}")
        return " ".join(parts)


@dataclass
class ValidationReport:
    """SHACL validation report.

    Attributes:
        conforms: True if no violations detected
        violations: List of all violations
        results_graph: Full SHACL results graph (for debugging)
        text: pySHACL text output
        violation_count: Number of sh:Violation severity
        warning_count: Number of sh:Warning severity
        info_count: Number of sh:Info severity
    """

    conforms: bool
    violations: list[SHACLViolation] = field(default_factory=list)
    results_graph: Optional[Graph] = None
    text: str = ""

    @property
    def violation_count(self) -> int:
        """Count violations with Violation severity."""
        return sum(1 for v in self.violations if v.severity == "Violation")

    @property
    def warning_count(self) -> int:
        """Count violations with Warning severity."""
        return sum(1 for v in self.violations if v.severity == "Warning")

    @property
    def info_count(self) -> int:
        """Count violations with Info severity."""
        return sum(1 for v in self.violations if v.severity == "Info")

    def __str__(self) -> str:
        """Format report summary."""
        if self.conforms:
            return "✅ SHACL Validation Passed (0 violations)"
        return (
            f"❌ SHACL Validation Failed\n"
            f"  Violations: {self.violation_count}\n"
            f"  Warnings:   {self.warning_count}\n"
            f"  Info:       {self.info_count}\n"
            f"  Total:      {len(self.violations)}"
        )


class SHACLValidator:
    """Validates RDF graphs against SHACL shapes.

    Responsibilities:
        - Load quality constraint shapes from .ttl files
        - Validate data graphs using pySHACL
        - Parse SHACL results into structured violations
        - Generate actionable validation reports

    Example:
        >>> validator = SHACLValidator()
        >>> validator.load_shapes_dir(Path("repoq/shapes"))
        >>> report = validator.validate(data_graph)
        >>> print(report)
    """

    def __init__(self):
        """Initialize SHACL validator with empty shapes graph."""
        self.shapes_graph = Graph()
        self.shapes_loaded = 0

    def load_shapes(self, shape_file: Path) -> None:
        """Load SHACL shapes from a file.

        Args:
            shape_file: Path to .ttl file containing SHACL shapes

        Raises:
            FileNotFoundError: If shape file doesn't exist
            ValueError: If shape file is not valid Turtle
        """
        if not shape_file.exists():
            raise FileNotFoundError(f"Shape file not found: {shape_file}")

        try:
            self.shapes_graph.parse(shape_file, format="turtle")
            self.shapes_loaded += 1
            logger.info(f"Loaded SHACL shapes from {shape_file}")
        except Exception as e:
            raise ValueError(f"Failed to parse shape file {shape_file}: {e}")

    def load_shapes_dir(self, shapes_dir: Path) -> None:
        """Load all SHACL shapes from a directory.

        Args:
            shapes_dir: Directory containing .ttl shape files

        Raises:
            ValueError: If directory doesn't exist or contains no .ttl files
        """
        if not shapes_dir.exists():
            raise ValueError(f"Shapes directory not found: {shapes_dir}")

        ttl_files = list(shapes_dir.glob("*.ttl"))
        if not ttl_files:
            raise ValueError(f"No .ttl files found in {shapes_dir}")

        for ttl_file in ttl_files:
            self.load_shapes(ttl_file)

        logger.info(f"Loaded {self.shapes_loaded} shape files from {shapes_dir}")

    def validate(
        self,
        data_graph: Graph,
        inference: str = "rdfs",
        abort_on_first: bool = False,
    ) -> ValidationReport:
        """Validate data graph against loaded SHACL shapes.

        Args:
            data_graph: RDF graph to validate
            inference: Inference engine ("none", "rdfs", "owlrl", "both")
            abort_on_first: Stop validation after first violation

        Returns:
            ValidationReport with parsed violations

        Raises:
            ValueError: If no shapes have been loaded
        """
        if self.shapes_loaded == 0:
            raise ValueError("No SHACL shapes loaded. Call load_shapes() first.")

        # Run pySHACL validation
        conforms, results_graph, results_text = validate(
            data_graph=data_graph,
            shacl_graph=self.shapes_graph,
            inference=inference,
            abort_on_first=abort_on_first,
            meta_shacl=False,  # Don't validate shapes themselves
            debug=False,
        )

        # Parse results
        violations = self._parse_violations(results_graph) if not conforms else []

        logger.info(
            f"SHACL validation complete: conforms={conforms}, " f"violations={len(violations)}"
        )

        return ValidationReport(
            conforms=conforms,
            violations=violations,
            results_graph=results_graph,
            text=results_text,
        )

    def _parse_violations(self, results_graph: Graph) -> list[SHACLViolation]:
        """Parse SHACL results graph into structured violations.

        Args:
            results_graph: RDF graph with SHACL validation results

        Returns:
            List of SHACLViolation objects
        """
        violations = []

        # Query for all validation results
        query = """
            PREFIX sh: <http://www.w3.org/ns/shacl#>
            SELECT ?result ?focusNode ?path ?value ?message ?severity ?sourceShape
            WHERE {
                ?result a sh:ValidationResult .
                ?result sh:focusNode ?focusNode .
                OPTIONAL { ?result sh:resultPath ?path . }
                OPTIONAL { ?result sh:value ?value . }
                OPTIONAL { ?result sh:resultMessage ?message . }
                OPTIONAL { ?result sh:resultSeverity ?severity . }
                OPTIONAL { ?result sh:sourceShape ?sourceShape . }
            }
        """

        for row in results_graph.query(query):
            severity_str = "Violation"  # Default
            if row.severity:
                if row.severity == SH.Warning:
                    severity_str = "Warning"
                elif row.severity == SH.Info:
                    severity_str = "Info"

            violation = SHACLViolation(
                focus_node=str(row.focusNode),
                result_path=str(row.path) if row.path else None,
                value=str(row.value) if row.value else None,
                message=str(row.message) if row.message else "",
                severity=severity_str,
                source_shape=str(row.sourceShape) if row.sourceShape else None,
            )
            violations.append(violation)

        return violations

    def validate_file(
        self,
        data_file: Path,
        inference: str = "rdfs",
    ) -> ValidationReport:
        """Validate RDF file against loaded shapes.

        Args:
            data_file: Path to .ttl data file
            inference: Inference engine

        Returns:
            ValidationReport

        Raises:
            FileNotFoundError: If data file doesn't exist
        """
        if not data_file.exists():
            raise FileNotFoundError(f"Data file not found: {data_file}")

        data_graph = Graph()
        data_graph.parse(data_file, format="turtle")

        logger.info(f"Validating {data_file} ({len(data_graph)} triples)")
        return self.validate(data_graph, inference=inference)
