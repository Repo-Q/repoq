"""
SHACL Validation Module for RepoQ Digital Twin
==============================================

Validates RDF data in .repoq/ against SHACL shapes.

Gate Conditions:
- All mandatory constraints must pass (sh:Violation)
- Warnings logged but don't fail validation (sh:Warning)
- Info messages logged for improvements (sh:Info)

Author: URPKS Agent
Date: 2025-10-22
Version: 1.0.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from rdflib import Graph, Namespace
from rdflib import Literal as RDFLiteral
from rdflib.namespace import RDF, SH, XSD

logger = logging.getLogger(__name__)

# Namespaces
REPOQ = Namespace("https://repoq.dev/ontology/")
STORY = Namespace("https://repoq.dev/ontology/story#")
ADR = Namespace("https://repoq.dev/ontology/adr#")
CHANGELOG = Namespace("https://repoq.dev/ontology/changelog#")
CERT = Namespace("https://repoq.dev/certificate#")


@dataclass
class ValidationResult:
    """Result of SHACL validation."""

    conforms: bool
    """Whether data conforms to all SHACL shapes."""

    violations: list[ValidationIssue]
    """Critical violations (must fix)."""

    warnings: list[ValidationIssue]
    """Warnings (should fix)."""

    info: list[ValidationIssue]
    """Informational messages (nice to have)."""

    shapes_graph: Graph
    """SHACL shapes used for validation."""

    data_graph: Graph
    """Data graph that was validated."""

    report_graph: Graph | None
    """Full SHACL validation report graph."""

    timestamp: datetime
    """When validation was performed."""

    @property
    def passed(self) -> bool:
        """Whether validation passed (no violations)."""
        return self.conforms and len(self.violations) == 0

    @property
    def total_issues(self) -> int:
        """Total number of issues (violations + warnings + info)."""
        return len(self.violations) + len(self.warnings) + len(self.info)

    def summary(self) -> str:
        """Human-readable summary."""
        status = "✅ PASSED" if self.passed else "❌ FAILED"
        lines = [
            f"Validation Result: {status}",
            f"Timestamp: {self.timestamp.isoformat()}",
            f"Conforms: {self.conforms}",
            f"Violations: {len(self.violations)}",
            f"Warnings: {len(self.warnings)}",
            f"Info: {len(self.info)}",
        ]
        return "\n".join(lines)


@dataclass
class ValidationIssue:
    """Single validation issue (violation/warning/info)."""

    severity: Literal["Violation", "Warning", "Info"]
    """Issue severity level."""

    focus_node: str | None
    """RDF node that failed validation."""

    message: str
    """Human-readable error message."""

    source_shape: str | None
    """SHACL shape that triggered this issue."""

    result_path: str | None
    """Property path that failed."""

    value: str | None
    """Value that caused the issue."""

    def __str__(self) -> str:
        """Format issue for display."""
        parts = [f"[{self.severity}]"]
        if self.focus_node:
            parts.append(f"Node: {self.focus_node}")
        if self.result_path:
            parts.append(f"Path: {self.result_path}")
        parts.append(f"Message: {self.message}")
        if self.value:
            parts.append(f"Value: {self.value}")
        return " | ".join(parts)


class SHACLValidator:
    """SHACL validator for RepoQ digital twin."""

    def __init__(self, workspace_root: Path):
        """Initialize validator.

        Args:
            workspace_root: Root directory of RepoQ workspace (contains .repoq/)
        """
        self.workspace_root = workspace_root
        self.repoq_dir = workspace_root / ".repoq"
        self.shapes_dir = self.repoq_dir / "shapes"
        self.data_dir = self.repoq_dir / "data"
        self.certificates_dir = self.repoq_dir / "certificates"

        # Ensure directories exist
        self.certificates_dir.mkdir(parents=True, exist_ok=True)

    def load_shapes(self, shape_files: list[Path] | None = None) -> Graph:
        """Load SHACL shapes from files.

        Args:
            shape_files: Specific shape files to load. If None, loads all *.ttl from shapes/

        Returns:
            Combined graph of all shapes
        """
        shapes = Graph()

        if shape_files is None:
            # Load all shapes
            shape_files = list(self.shapes_dir.glob("*.ttl"))

        for shape_file in shape_files:
            logger.info(f"Loading shape: {shape_file.name}")
            shapes.parse(shape_file, format="turtle")

        logger.info(f"Loaded {len(shapes)} triples from {len(shape_files)} shape files")
        return shapes

    def load_data(
        self,
        data_files: list[Path] | None = None,
        include_ontologies: bool = True,
    ) -> Graph:
        """Load data graphs to validate.

        Args:
            data_files: Specific data files to load. If None, loads all from data directories.
            include_ontologies: Whether to include ontology definitions (TBox)

        Returns:
            Combined data graph
        """
        data = Graph()

        # Load ontologies (TBox) if requested
        if include_ontologies:
            ontologies_dir = self.repoq_dir / "ontologies"
            if ontologies_dir.exists():
                for onto_file in ontologies_dir.glob("*.ttl"):
                    logger.info(f"Loading ontology: {onto_file.name}")
                    data.parse(onto_file, format="turtle")

        # Load data (ABox)
        if data_files is None:
            # Load all data from subdirectories
            data_dirs = [
                self.repoq_dir / "story",
                self.repoq_dir / "adr",
                self.repoq_dir / "changelog",
            ]
            data_files = []
            for data_dir in data_dirs:
                if data_dir.exists():
                    data_files.extend(data_dir.glob("*.ttl"))

        for data_file in data_files:
            logger.info(f"Loading data: {data_file}")
            data.parse(data_file, format="turtle")

        logger.info(f"Loaded {len(data)} triples from {len(data_files)} data files")
        return data

    def validate(
        self,
        data_graph: Graph | None = None,
        shapes_graph: Graph | None = None,
    ) -> ValidationResult:
        """Validate data against SHACL shapes.

        Args:
            data_graph: Data to validate. If None, loads from workspace.
            shapes_graph: SHACL shapes. If None, loads from shapes/.

        Returns:
            ValidationResult with detailed information
        """
        # Import pyshacl here to avoid requiring it at module level
        try:
            import pyshacl
        except ImportError as e:
            raise ImportError(
                "pyshacl is required for validation. Install with: pip install pyshacl"
            ) from e

        # Load graphs if not provided
        if data_graph is None:
            data_graph = self.load_data()
        if shapes_graph is None:
            shapes_graph = self.load_shapes()

        logger.info("Running SHACL validation...")
        logger.info(f"Data graph: {len(data_graph)} triples")
        logger.info(f"Shapes graph: {len(shapes_graph)} triples")

        # Run pyshacl validation
        conforms, report_graph, report_text = pyshacl.validate(
            data_graph=data_graph,
            shacl_graph=shapes_graph,
            inference="rdfs",  # Use RDFS inference
            abort_on_first=False,  # Check all shapes
            allow_warnings=True,  # Collect warnings separately
            meta_shacl=False,  # Don't validate shapes themselves
        )

        logger.info(f"Validation result: {'CONFORMS' if conforms else 'DOES NOT CONFORM'}")

        # Parse validation report
        violations, warnings, info = self._parse_report(report_graph)

        logger.info(
            f"Issues: {len(violations)} violations, {len(warnings)} warnings, {len(info)} info"
        )

        return ValidationResult(
            conforms=conforms,
            violations=violations,
            warnings=warnings,
            info=info,
            shapes_graph=shapes_graph,
            data_graph=data_graph,
            report_graph=report_graph,
            timestamp=datetime.now(),
        )

    def _parse_report(
        self, report_graph: Graph
    ) -> tuple[list[ValidationIssue], list[ValidationIssue], list[ValidationIssue]]:
        """Parse SHACL validation report into structured issues.

        Args:
            report_graph: RDF graph containing validation report

        Returns:
            Tuple of (violations, warnings, info)
        """
        violations = []
        warnings = []
        info = []

        # Query validation results
        for result in report_graph.subjects(RDF.type, SH.ValidationResult):
            # Extract severity
            severity_node = report_graph.value(result, SH.resultSeverity)
            if severity_node == SH.Violation:
                severity = "Violation"
                target_list = violations
            elif severity_node == SH.Warning:
                severity = "Warning"
                target_list = warnings
            elif severity_node == SH.Info:
                severity = "Info"
                target_list = info
            else:
                severity = "Violation"  # Default to violation if unknown
                target_list = violations

            # Extract details
            focus_node = report_graph.value(result, SH.focusNode)
            message = report_graph.value(result, SH.resultMessage)
            source_shape = report_graph.value(result, SH.sourceShape)
            result_path = report_graph.value(result, SH.resultPath)
            value = report_graph.value(result, SH.value)

            issue = ValidationIssue(
                severity=severity,
                focus_node=str(focus_node) if focus_node else None,
                message=str(message) if message else "No message provided",
                source_shape=str(source_shape) if source_shape else None,
                result_path=str(result_path) if result_path else None,
                value=str(value) if value else None,
            )

            target_list.append(issue)

        return violations, warnings, info

    def generate_certificate(self, result: ValidationResult) -> Path:
        """Generate validation certificate after successful validation.

        Args:
            result: Validation result (must have passed=True)

        Returns:
            Path to generated certificate

        Raises:
            ValueError: If validation did not pass
        """
        if not result.passed:
            raise ValueError("Cannot generate certificate for failed validation")

        # Create certificate graph
        cert_graph = Graph()
        cert_graph.bind("cert", CERT)
        cert_graph.bind("sh", SH)

        # Certificate URI
        timestamp_str = result.timestamp.strftime("%Y%m%d%H%M%S")
        cert_uri = CERT[f"validation-{timestamp_str}"]

        # Add certificate triples
        cert_graph.add((cert_uri, RDF.type, CERT.ValidationCertificate))
        cert_graph.add(
            (
                cert_uri,
                CERT.timestamp,
                RDFLiteral(result.timestamp.isoformat(), datatype=XSD.dateTime),
            )
        )
        cert_graph.add((cert_uri, CERT.conforms, RDFLiteral(result.conforms, datatype=XSD.boolean)))
        cert_graph.add(
            (cert_uri, CERT.violations, RDFLiteral(len(result.violations), datatype=XSD.integer))
        )
        cert_graph.add(
            (cert_uri, CERT.warnings, RDFLiteral(len(result.warnings), datatype=XSD.integer))
        )
        cert_graph.add((cert_uri, CERT.info, RDFLiteral(len(result.info), datatype=XSD.integer)))
        cert_graph.add(
            (cert_uri, CERT.dataTriples, RDFLiteral(len(result.data_graph), datatype=XSD.integer))
        )
        cert_graph.add(
            (
                cert_uri,
                CERT.shapesTriples,
                RDFLiteral(len(result.shapes_graph), datatype=XSD.integer),
            )
        )

        # Save certificate
        cert_file = self.certificates_dir / f"validation-{timestamp_str}.ttl"
        cert_graph.serialize(destination=cert_file, format="turtle")

        logger.info(f"Generated certificate: {cert_file}")
        return cert_file

    def validate_and_certify(
        self,
        data_graph: Graph | None = None,
        shapes_graph: Graph | None = None,
    ) -> tuple[ValidationResult, Path | None]:
        """Validate and generate certificate if successful.

        Args:
            data_graph: Data to validate
            shapes_graph: SHACL shapes

        Returns:
            Tuple of (result, certificate_path). Certificate is None if validation failed.
        """
        result = self.validate(data_graph, shapes_graph)

        if result.passed:
            cert_path = self.generate_certificate(result)
            return result, cert_path
        else:
            return result, None
