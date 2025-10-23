"""Tests for PCE (Proof-Carrying Evidence) Witness Generator.

Tests k-repair witness generation for SHACL violations.

Author: RepoQ Team
License: MIT
"""

from __future__ import annotations

import pytest

from repoq.core.shacl_validator import SHACLViolation
from repoq.quality.pce_generator import (
    EFFORT_COEFFICIENTS,
    IMPACT_WEIGHTS,
    FileRepair,
    PCEGenerator,
    WitnessK,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_violations() -> list[SHACLViolation]:
    """Sample SHACL violations for testing."""
    return [
        # File 1: High complexity (2 violations)
        SHACLViolation(
            focus_node="https://example.com/repo/file1.py",
            result_path="repo:cyclomaticComplexity",
            value="25",
            message="File has CC=25 > 15",
            severity="sh:Violation",
            source_shape="ComplexityConstraintShape",
        ),
        SHACLViolation(
            focus_node="https://example.com/repo/file1.py",
            result_path="repo:cyclomaticComplexity",
            value="30",
            message="Function foo has CC=30",
            severity="sh:Warning",
            source_shape="ComplexityConstraintShape",
        ),
        # File 2: Low coverage (1 violation)
        SHACLViolation(
            focus_node="https://example.com/repo/file2.py",
            result_path="repo:testCoverage",
            value="0.5",
            message="Module has coverage 50% < 80%",
            severity="sh:Violation",
            source_shape="TestCoverageConstraintShape",
        ),
        # File 3: Hotspot (1 violation, high impact)
        SHACLViolation(
            focus_node="https://example.com/repo/file3.py",
            result_path="repo:isHotspot",
            value="true",
            message="File is hotspot (churn=50, CC=20)",
            severity="sh:Violation",
            source_shape="HotspotConstraintShape",
        ),
        # File 4: Architecture violation (1 violation)
        SHACLViolation(
            focus_node="https://example.com/repo/file4.py",
            result_path="repo:layer",
            value="Presentation",
            message="Presentation layer depends on Data layer",
            severity="sh:Violation",
            source_shape="LayeringViolationShape",
        ),
    ]


@pytest.fixture
def generator() -> PCEGenerator:
    """PCE generator with default configuration."""
    return PCEGenerator()


# =============================================================================
# TestPCEGeneratorInitialization
# =============================================================================


class TestPCEGeneratorInitialization:
    """Test PCEGenerator initialization and configuration."""

    def test_init_default(self):
        """Test initialization with default coefficients."""
        gen = PCEGenerator()

        assert gen.effort_coefficients == EFFORT_COEFFICIENTS
        assert gen.impact_weights == IMPACT_WEIGHTS

    def test_init_custom_coefficients(self):
        """Test initialization with custom effort coefficients."""
        custom_coeffs = {"Violation": 3.0, "Warning": 1.0}
        gen = PCEGenerator(effort_coefficients=custom_coeffs)

        assert gen.effort_coefficients == custom_coeffs

    def test_init_custom_weights(self):
        """Test initialization with custom impact weights."""
        custom_weights = {"complexity": 2.0, "hotspot": 3.0}
        gen = PCEGenerator(impact_weights=custom_weights)

        assert gen.impact_weights == custom_weights


# =============================================================================
# TestWitnessGeneration
# =============================================================================


class TestWitnessGeneration:
    """Test k-repair witness generation."""

    def test_generate_witness_empty_violations(self, generator):
        """Test witness generation with no violations."""
        witness = generator.generate_witness([], k=0.8)

        assert witness.k == 0.8
        assert witness.repairs == []
        assert witness.violations_total == 0
        assert witness.violations_fixed == 0
        assert witness.effort_hours == 0.0
        assert witness.coverage == 1.0  # 0/0 = 100% (trivial)

    def test_generate_witness_k_80_percent(self, generator, sample_violations):
        """Test witness generation targeting 80% repair."""
        witness = generator.generate_witness(sample_violations, k=0.8)

        # Should fix at least 80% of 5 violations = 4 violations
        assert witness.violations_total == 5
        assert witness.violations_fixed >= 4
        assert witness.coverage >= 0.8
        assert len(witness.repairs) > 0
        assert witness.effort_hours > 0

    def test_generate_witness_k_100_percent(self, generator, sample_violations):
        """Test witness generation targeting 100% repair."""
        witness = generator.generate_witness(sample_violations, k=1.0)

        # Should fix all 5 violations
        assert witness.violations_total == 5
        assert witness.violations_fixed == 5
        assert witness.coverage == 1.0
        assert len(witness.repairs) <= 4  # At most 4 files (file1, file2, file3, file4)

    def test_generate_witness_k_50_percent(self, generator, sample_violations):
        """Test witness generation targeting 50% repair."""
        witness = generator.generate_witness(sample_violations, k=0.5)

        # Should fix at least 50% of 5 violations = 2.5 → 3 violations
        assert witness.violations_total == 5
        assert witness.violations_fixed >= 2
        assert witness.coverage >= 0.4  # At least 2/5 = 40%

    def test_generate_witness_invalid_k(self, generator, sample_violations):
        """Test witness generation with invalid k value."""
        with pytest.raises(ValueError, match="k must be in"):
            generator.generate_witness(sample_violations, k=1.5)

        with pytest.raises(ValueError, match="k must be in"):
            generator.generate_witness(sample_violations, k=-0.1)

    def test_witness_repairs_sorted_by_priority(self, generator, sample_violations):
        """Test that repairs are sorted by priority (impact/effort)."""
        witness = generator.generate_witness(sample_violations, k=1.0)

        # Check that priorities are descending
        priorities = [repair.priority for repair in witness.repairs]
        assert priorities == sorted(priorities, reverse=True)

    def test_witness_greedy_selection(self, generator):
        """Test greedy selection picks highest-priority files first.

        Priority = impact / effort. File with fewer violations but lower effort
        can have higher priority (which is correct for efficiency).
        """
        # Create violations:
        # file1: 5 Violations (effort=10h, impact=7.5, priority=0.75)
        # file2: 1 Warning (effort=0.5h, impact=1.5, priority=3.0) ← HIGHER priority
        violations = [
            SHACLViolation(
                focus_node="file1.py",
                result_path="repo:cc",
                value="20",
                message="High CC",
                severity="sh:Violation",
                source_shape="ComplexityShape",
            )
        ] * 5 + [
            SHACLViolation(
                focus_node="file2.py",
                result_path="repo:cc",
                value="16",
                message="Medium CC",
                severity="sh:Warning",
                source_shape="ComplexityShape",
            )
        ]

        witness = generator.generate_witness(violations, k=0.8)

        # file2 should be first (higher priority: 3.0 vs 0.75)
        assert witness.repairs[0].file_path == "file2.py"
        assert witness.repairs[0].impact_score == 1
        assert witness.repairs[0].priority > witness.repairs[1].priority


# =============================================================================
# TestEffortEstimation
# =============================================================================


class TestEffortEstimation:
    """Test effort estimation for file repairs."""

    def test_estimate_effort_single_violation(self, generator):
        """Test effort estimation for single Violation."""
        violations = [
            SHACLViolation(
                focus_node="file.py",
                result_path="repo:cc",
                value="20",
                message="High CC",
                severity="sh:Violation",
                source_shape="ComplexityShape",
            )
        ]

        effort = generator._estimate_effort(violations)

        # sh:Violation = 2.0 hours (from EFFORT_COEFFICIENTS)
        assert effort == 2.0

    def test_estimate_effort_multiple_violations(self, generator):
        """Test effort estimation for multiple violations."""
        violations = [
            SHACLViolation(
                focus_node="file.py",
                result_path="repo:cc",
                value="20",
                message="High CC",
                severity="sh:Violation",  # 2.0h
                source_shape="ComplexityShape",
            ),
            SHACLViolation(
                focus_node="file.py",
                result_path="repo:coverage",
                value="0.5",
                message="Low coverage",
                severity="sh:Warning",  # 0.5h
                source_shape="CoverageShape",
            ),
        ]

        effort = generator._estimate_effort(violations)

        # 2.0 + 0.5 = 2.5 hours
        assert effort == 2.5

    def test_estimate_effort_unknown_severity(self, generator):
        """Test effort estimation with unknown severity (defaults to 1.0h)."""
        violations = [
            SHACLViolation(
                focus_node="file.py",
                result_path="repo:cc",
                value="20",
                message="High CC",
                severity="sh:CustomSeverity",  # Not in EFFORT_COEFFICIENTS
                source_shape="ComplexityShape",
            )
        ]

        effort = generator._estimate_effort(violations)

        # Unknown severity defaults to 1.0 hour
        assert effort == 1.0


# =============================================================================
# TestImpactCalculation
# =============================================================================


class TestImpactCalculation:
    """Test impact score calculation."""

    def test_calculate_impact_complexity(self, generator):
        """Test impact calculation for complexity violations."""
        violations = [
            SHACLViolation(
                focus_node="file.py",
                result_path="repo:cc",
                value="20",
                message="File has CC=20",  # Contains "complexity"
                severity="sh:Violation",
                source_shape="ComplexityShape",
            )
        ]

        impact = generator._calculate_impact(violations)

        # complexity weight = 1.5 (from IMPACT_WEIGHTS)
        assert impact == 1.5

    def test_calculate_impact_hotspot(self, generator):
        """Test impact calculation for hotspot violations."""
        violations = [
            SHACLViolation(
                focus_node="file.py",
                result_path="repo:hotspot",
                value="true",
                message="File is hotspot",  # Contains "hotspot"
                severity="sh:Violation",
                source_shape="HotspotShape",
            )
        ]

        impact = generator._calculate_impact(violations)

        # hotspot weight = 2.0 (highest impact)
        assert impact == 2.0

    def test_calculate_impact_mixed_types(self, generator):
        """Test impact calculation for mixed violation types."""
        violations = [
            SHACLViolation(
                focus_node="file.py",
                result_path="repo:cc",
                value="20",
                message="Complexity violation",  # 1.5
                severity="sh:Violation",
                source_shape="ComplexityShape",
            ),
            SHACLViolation(
                focus_node="file.py",
                result_path="repo:hotspot",
                value="true",
                message="Hotspot detected",  # 2.0
                severity="sh:Violation",
                source_shape="HotspotShape",
            ),
        ]

        impact = generator._calculate_impact(violations)

        # 1.5 + 2.0 = 3.5
        assert impact == 3.5


# =============================================================================
# TestViolationTypeInference
# =============================================================================


class TestViolationTypeInference:
    """Test violation type inference from messages."""

    def test_infer_type_complexity(self, generator):
        """Test inferring 'complexity' type."""
        violation = SHACLViolation(
            focus_node="file.py",
            result_path="repo:cc",
            value="20",
            message="Cyclomatic Complexity is too high",
            severity="sh:Violation",
            source_shape="ComplexityShape",
        )

        vtype = generator._infer_type(violation)

        assert vtype == "complexity"

    def test_infer_type_coverage(self, generator):
        """Test inferring 'coverage' type."""
        violation = SHACLViolation(
            focus_node="file.py",
            result_path="repo:coverage",
            value="0.5",
            message="Test coverage is below 80%",
            severity="sh:Violation",
            source_shape="CoverageShape",
        )

        vtype = generator._infer_type(violation)

        assert vtype == "coverage"

    def test_infer_type_architecture(self, generator):
        """Test inferring 'architecture' type."""
        violation = SHACLViolation(
            focus_node="file.py",
            result_path="repo:layer",
            value="Presentation",
            message="C4 layer violation detected",
            severity="sh:Violation",
            source_shape="LayerShape",
        )

        vtype = generator._infer_type(violation)

        assert vtype == "architecture"

    def test_infer_type_ddd(self, generator):
        """Test inferring 'ddd' type."""
        violation = SHACLViolation(
            focus_node="file.py",
            result_path="ddd:context",
            value="AnalysisBC",
            message="Bounded context violation",
            severity="sh:Violation",
            source_shape="DDDShape",
        )

        vtype = generator._infer_type(violation)

        assert vtype == "ddd"

    def test_infer_type_unknown(self, generator):
        """Test inferring 'other' for unknown types."""
        violation = SHACLViolation(
            focus_node="file.py",
            result_path="repo:unknown",
            value="x",
            message="Some other violation",
            severity="sh:Violation",
            source_shape="UnknownShape",
        )

        vtype = generator._infer_type(violation)

        assert vtype == "other"


# =============================================================================
# TestFileRepair
# =============================================================================


class TestFileRepair:
    """Test FileRepair dataclass."""

    def test_file_repair_repr(self):
        """Test FileRepair string representation."""
        violations = [
            SHACLViolation(
                focus_node="file.py",
                result_path="repo:cc",
                value="20",
                message="High CC",
                severity="sh:Violation",
                source_shape="ComplexityShape",
            )
        ]

        repair = FileRepair(
            file_path="/home/user/project/src/file.py",
            violations=violations,
            effort_hours=2.5,
            priority=1.8,
            impact_score=3,
        )

        repr_str = repr(repair)

        assert "file.py" in repr_str
        assert "violations=1" in repr_str
        assert "effort=2.5h" in repr_str
        assert "priority=1.80" in repr_str


# =============================================================================
# TestWitnessK
# =============================================================================


class TestWitnessK:
    """Test WitnessK dataclass."""

    def test_witness_coverage_calculation(self):
        """Test automatic coverage calculation."""
        witness = WitnessK(
            k=0.8,
            repairs=[],
            violations_total=10,
            violations_fixed=8,
            effort_hours=5.0,
        )

        assert witness.coverage == 0.8  # 8/10

    def test_witness_coverage_zero_violations(self):
        """Test coverage calculation with zero violations."""
        witness = WitnessK(
            k=0.8,
            repairs=[],
            violations_total=0,
            violations_fixed=0,
            effort_hours=0.0,
        )

        assert witness.coverage == 1.0  # 0/0 = 100% (trivial)

    def test_witness_repr(self):
        """Test WitnessK string representation."""
        witness = WitnessK(
            k=0.8,
            repairs=[FileRepair("file.py", [], 2.0, 1.5, 3)],
            violations_total=10,
            violations_fixed=8,
            effort_hours=5.0,
        )

        repr_str = repr(witness)

        assert "k=80%" in repr_str
        assert "repairs=1 files" in repr_str
        assert "fixed=8/10 (80%)" in repr_str
        assert "effort=5.0h" in repr_str

    def test_witness_summary(self):
        """Test WitnessK human-readable summary."""
        repairs = [
            FileRepair("file1.py", [], 2.0, 3.0, 5),
            FileRepair("file2.py", [], 1.0, 2.0, 2),
            FileRepair("file3.py", [], 0.5, 1.0, 1),
        ]

        witness = WitnessK(
            k=0.8,
            repairs=repairs,
            violations_total=10,
            violations_fixed=8,
            effort_hours=3.5,
        )

        summary = witness.summary()

        assert "k-Repair Witness (k=80%)" in summary
        assert "Total violations: 10" in summary
        assert "Violations fixed: 8 (80%)" in summary
        assert "Files to repair: 3" in summary
        assert "Estimated effort: 3.5 hours" in summary
        assert "file1.py" in summary  # Top repair


# =============================================================================
# TestIntegration
# =============================================================================


class TestIntegration:
    """Integration tests with SHACLValidator."""

    def test_realistic_witness_generation(self, generator):
        """Test witness generation with realistic violation set.

        Priority calculation:
        - auth.py: 3 violations (2*Violation + 1*Warning = 4.5h)
                   impact = 2.0(hotspot) + 1.5(complexity) + 1.0(coverage) = 4.5
                   priority = 4.5 / 4.5 = 1.0
        - utils.py: 1 violation (Warning = 0.5h)
                    impact = 1.0(coverage)
                    priority = 1.0 / 0.5 = 2.0 (HIGHER - better ROI)

        Greedy should pick utils.py FIRST (lower effort for same impact type).
        """
        # Simulate realistic violations from SHACL validator
        violations = [
            # auth.py: 3 violations (complexity + hotspot + coverage)
            SHACLViolation(
                focus_node="https://example.com/repo/auth.py",
                result_path="repo:cyclomaticComplexity",
                value="25",
                message="File has CC=25 > 15",
                severity="sh:Violation",
                source_shape="ComplexityConstraintShape",
            ),
            SHACLViolation(
                focus_node="https://example.com/repo/auth.py",
                result_path="repo:isHotspot",
                value="true",
                message="File is hotspot (churn=50)",
                severity="sh:Violation",
                source_shape="HotspotConstraintShape",
            ),
            SHACLViolation(
                focus_node="https://example.com/repo/auth.py",
                result_path="repo:testCoverage",
                value="0.6",
                message="Coverage 60% < 80%",
                severity="sh:Warning",
                source_shape="CoverageShape",
            ),
            # utils.py: 1 violation (coverage)
            SHACLViolation(
                focus_node="https://example.com/repo/utils.py",
                result_path="repo:testCoverage",
                value="0.5",
                message="Coverage 50% < 80%",
                severity="sh:Warning",
                source_shape="CoverageShape",
            ),
        ]

        witness = generator.generate_witness(violations, k=0.75)

        # Should fix at least 3/4 = 75% of violations
        assert witness.violations_total == 4
        assert witness.violations_fixed >= 3
        assert witness.coverage >= 0.75

        # utils.py should be first (priority = 1.0/0.5 = 2.0 > auth.py's 1.0)
        assert "utils.py" in witness.repairs[0].file_path
        assert len(witness.repairs[0].violations) == 1

        # auth.py should be second (priority = 1.0, but picked to reach 75% coverage)
        assert "auth.py" in witness.repairs[1].file_path
        assert len(witness.repairs[1].violations) == 3
