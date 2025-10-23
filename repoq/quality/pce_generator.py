"""PCE (Proof-Carrying Evidence) Witness Generator.

This module implements k-repair witness generation for SHACL validation violations.
A witness is a constructive proof that shows HOW to repair violations (Theorem D).

Key Concepts:
    - Witness: Minimal repair plan to fix k% of violations
    - k-repair: Optimize for impact (violations fixed per file)
    - Effort estimation: Hours required based on violation severity

References:
    - FR-02: Actionable Feedback
    - V08: Actionability (clear next steps)
    - Theorem D: Constructiveness (∀v ∈ Violations. ∃w ∈ Witness. repair(w) → ¬v)

Example:
    >>> from repoq.core.shacl_validator import SHACLValidator
    >>> validator = SHACLValidator()
    >>> validator.load_shapes_dir(Path("shapes/"))
    >>> report = validator.validate(graph)
    >>>
    >>> generator = PCEGenerator()
    >>> witness = generator.generate_witness(report.violations, k=0.8)
    >>> print(f"Fix {len(witness.repairs)} files → {witness.violations_fixed} violations")
    >>> print(f"Estimated effort: {witness.effort_hours:.1f}h")

Author: RepoQ Team
License: MIT
Version: 2.0.0-beta.4
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from repoq.core.shacl_validator import SHACLViolation

# Effort coefficients (hours per violation type)
EFFORT_COEFFICIENTS = {
    "Violation": 2.0,  # sh:Violation: 2 hours average
    "Warning": 0.5,  # sh:Warning: 30 minutes
    "Info": 0.1,  # sh:Info: 6 minutes
}

# Impact weights (for prioritization)
IMPACT_WEIGHTS = {
    "complexity": 1.5,  # Complexity violations have high ripple effect
    "coverage": 1.0,  # Coverage is important but localized
    "hotspot": 2.0,  # Hotspots indicate systemic issues
    "architecture": 1.8,  # Architecture violations affect multiple modules
    "ddd": 1.6,  # DDD violations impact domain model
}


@dataclass
class FileRepair:
    """Repair plan for a single file.

    Attributes:
        file_path: Absolute path to file requiring repair
        violations: List of SHACL violations in this file
        effort_hours: Estimated hours to fix all violations
        priority: Higher = more important (based on impact)
        impact_score: Number of violations fixed by repairing this file
    """

    file_path: str
    violations: list[SHACLViolation]
    effort_hours: float
    priority: float
    impact_score: int = field(default=0)

    def __repr__(self) -> str:
        return (
            f"FileRepair(file={Path(self.file_path).name}, "
            f"violations={len(self.violations)}, "
            f"effort={self.effort_hours:.1f}h, "
            f"priority={self.priority:.2f})"
        )


@dataclass
class WitnessK:
    """k-repair witness (constructive proof of repairability).

    A witness demonstrates that fixing a minimal set of files will
    resolve k% of violations. This is a constructive proof (Theorem D).

    Attributes:
        k: Target repair percentage (0.0-1.0)
        repairs: Prioritized list of file repairs
        violations_total: Total number of violations
        violations_fixed: Number of violations fixed by this witness
        effort_hours: Total estimated effort (sum of all repairs)
        coverage: Actual repair percentage (violations_fixed / violations_total)
    """

    k: float
    repairs: list[FileRepair]
    violations_total: int
    violations_fixed: int
    effort_hours: float
    coverage: float = field(init=False)

    def __post_init__(self) -> None:
        """Calculate coverage after initialization."""
        self.coverage = (
            self.violations_fixed / self.violations_total if self.violations_total > 0 else 1.0
        )

    def __repr__(self) -> str:
        return (
            f"WitnessK(k={self.k:.0%}, "
            f"repairs={len(self.repairs)} files, "
            f"fixed={self.violations_fixed}/{self.violations_total} ({self.coverage:.0%}), "
            f"effort={self.effort_hours:.1f}h)"
        )

    def summary(self) -> str:
        """Human-readable summary of witness.

        Returns:
            Multiline string with repair plan summary
        """
        lines = [
            f"k-Repair Witness (k={self.k:.0%}):",
            f"  Total violations: {self.violations_total}",
            f"  Violations fixed: {self.violations_fixed} ({self.coverage:.0%})",
            f"  Files to repair: {len(self.repairs)}",
            f"  Estimated effort: {self.effort_hours:.1f} hours",
            "",
            "Top 5 repairs (by priority):",
        ]

        for i, repair in enumerate(self.repairs[:5], 1):
            file_name = Path(repair.file_path).name
            lines.append(
                f"  {i}. {file_name}: "
                f"{len(repair.violations)} violations, "
                f"{repair.effort_hours:.1f}h "
                f"(priority={repair.priority:.2f})"
            )

        if len(self.repairs) > 5:
            lines.append(f"  ... and {len(self.repairs) - 5} more files")

        return "\n".join(lines)


class PCEGenerator:
    """Proof-Carrying Evidence generator for SHACL violations.

    Generates k-repair witnesses that provide constructive proofs of
    how to repair violations. Uses greedy algorithm optimized for
    impact (violations fixed per unit effort).

    References:
        - Theorem D (Constructiveness)
        - FR-02 (Actionable Feedback)
        - V08 (Actionability)
    """

    def __init__(
        self,
        effort_coefficients: dict[str, float] | None = None,
        impact_weights: dict[str, float] | None = None,
    ) -> None:
        """Initialize PCE generator.

        Args:
            effort_coefficients: Custom effort hours per severity level
            impact_weights: Custom impact weights per violation type
        """
        self.effort_coefficients = effort_coefficients or EFFORT_COEFFICIENTS
        self.impact_weights = impact_weights or IMPACT_WEIGHTS

    def generate_witness(
        self,
        violations: list[SHACLViolation],
        k: float = 0.8,
    ) -> WitnessK:
        """Generate k-repair witness for violations.

        Algorithm:
            1. Group violations by file (focus_node)
            2. Calculate effort & impact for each file
            3. Sort by priority (impact / effort)
            4. Greedily select files until k% violations fixed

        Args:
            violations: List of SHACL violations from validator
            k: Target repair percentage (default 0.8 = 80%)

        Returns:
            WitnessK with prioritized repair plan

        Raises:
            ValueError: If k not in [0.0, 1.0]
        """
        if not 0.0 <= k <= 1.0:
            raise ValueError(f"k must be in [0.0, 1.0], got {k}")

        if not violations:
            # No violations = trivial witness
            return WitnessK(
                k=k,
                repairs=[],
                violations_total=0,
                violations_fixed=0,
                effort_hours=0.0,
            )

        # Step 1: Group violations by file
        violations_by_file = self._group_by_file(violations)

        # Step 2: Create file repairs with effort & impact
        file_repairs = []
        for file_path, file_violations in violations_by_file.items():
            effort = self._estimate_effort(file_violations)
            impact = self._calculate_impact(file_violations)
            priority = impact / effort if effort > 0 else 0.0

            file_repairs.append(
                FileRepair(
                    file_path=file_path,
                    violations=file_violations,
                    effort_hours=effort,
                    priority=priority,
                    impact_score=len(file_violations),
                )
            )

        # Step 3: Sort by priority (descending)
        file_repairs.sort(key=lambda r: r.priority, reverse=True)

        # Step 4: Greedily select files until k% violations fixed
        target_violations = int(k * len(violations))
        selected_repairs = []
        violations_fixed = 0
        total_effort = 0.0

        for repair in file_repairs:
            if violations_fixed >= target_violations:
                break

            selected_repairs.append(repair)
            violations_fixed += len(repair.violations)
            total_effort += repair.effort_hours

        return WitnessK(
            k=k,
            repairs=selected_repairs,
            violations_total=len(violations),
            violations_fixed=violations_fixed,
            effort_hours=total_effort,
        )

    def _group_by_file(
        self,
        violations: list[SHACLViolation],
    ) -> dict[str, list[SHACLViolation]]:
        """Group violations by file (focus_node).

        Args:
            violations: List of SHACL violations

        Returns:
            Dictionary mapping file paths to violations
        """
        grouped: dict[str, list[SHACLViolation]] = {}

        for violation in violations:
            file_path = violation.focus_node
            if file_path not in grouped:
                grouped[file_path] = []
            grouped[file_path].append(violation)

        return grouped

    def _estimate_effort(self, violations: list[SHACLViolation]) -> float:
        """Estimate effort (hours) to fix violations in a file.

        Uses severity-based coefficients from EFFORT_COEFFICIENTS.

        Args:
            violations: List of violations in the same file

        Returns:
            Estimated hours required
        """
        total_effort = 0.0

        for violation in violations:
            # Extract severity from violation (e.g., "sh:Violation" -> "Violation")
            severity = (
                violation.severity.split(":")[-1]
                if ":" in violation.severity
                else violation.severity
            )

            coefficient = self.effort_coefficients.get(severity, 1.0)
            total_effort += coefficient

        return total_effort

    def _calculate_impact(self, violations: list[SHACLViolation]) -> float:
        """Calculate impact score for violations.

        Impact = weighted sum of violations by type.
        Higher impact = more important to fix.

        Args:
            violations: List of violations in the same file

        Returns:
            Impact score (higher = more important)
        """
        total_impact = 0.0

        for violation in violations:
            # Infer violation type from message or source shape
            violation_type = self._infer_type(violation)
            weight = self.impact_weights.get(violation_type, 1.0)

            total_impact += weight

        return total_impact

    def _infer_type(self, violation: SHACLViolation) -> str:
        """Infer violation type from message/source shape.

        Args:
            violation: SHACL violation

        Returns:
            Type string (e.g., "complexity", "coverage", "hotspot")
        """
        message_lower = violation.message.lower()

        if "complexity" in message_lower or "cc" in message_lower:
            return "complexity"
        elif "coverage" in message_lower:
            return "coverage"
        elif "hotspot" in message_lower or "churn" in message_lower:
            return "hotspot"
        elif "layer" in message_lower or "c4" in message_lower:
            return "architecture"
        elif "bounded context" in message_lower or "ddd" in message_lower:
            return "ddd"
        else:
            return "other"
