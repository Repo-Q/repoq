#!/usr/bin/env python3
"""
Assert Quality Gates for Self-Hosting

This script validates that repoq itself meets quality standards.
Used in CI to enforce minimum quality thresholds.

Phase 0: Warnings only
Phase 1+: Fail on violations
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


class QualityGates:
    """URPKS-based quality gate definitions"""

    # Phase targets (progressive)
    PHASES = {
        "phase0": {
            "coverage": 5,
            "max_high_issues": 999,  # warnings only
            "max_medium_issues": 999,
            "min_files": 1,
            "min_modules": 1,
            "fail_on_violation": False,
        },
        "phase1": {
            "coverage": 80,
            "max_high_issues": 5,
            "max_medium_issues": 20,
            "min_files": 10,
            "min_modules": 3,
            "fail_on_violation": True,
        },
        "phase2": {
            "coverage": 85,
            "max_high_issues": 0,
            "max_medium_issues": 10,
            "min_files": 10,
            "min_modules": 3,
            "shacl_must_pass": True,
            "fail_on_violation": True,
        },
        "phase3": {
            "coverage": 90,
            "max_high_issues": 0,
            "max_medium_issues": 5,
            "max_performance_issues": 0,
            "fail_on_violation": True,
        },
        "ga": {
            "coverage": 95,
            "max_high_issues": 0,
            "max_medium_issues": 0,
            "max_performance_issues": 0,
            "shacl_must_pass": True,
            "fail_on_violation": True,
        },
    }

    def __init__(self, phase: str = "phase0"):
        if phase not in self.PHASES:
            raise ValueError(f"Unknown phase: {phase}. Valid: {list(self.PHASES.keys())}")
        self.phase = phase
        self.gates = self.PHASES[phase]
        self.violations: List[str] = []
        self.warnings: List[str] = []

    def check(self, data: Dict[str, Any], coverage: float = 0.0) -> bool:
        """Run all quality checks"""
        print(f"🔍 Running quality gates for {self.phase.upper()}")
        print("=" * 60)

        self._check_basic_structure(data)
        self._check_issues(data)
        self._check_coverage(coverage)

        # Display results
        self._display_results()

        # Determine pass/fail
        if self.gates["fail_on_violation"] and self.violations:
            print(f"\n❌ FAILED: {len(self.violations)} gate violations")
            return False
        elif self.violations:
            print(f"\n⚠️  WARNING: {len(self.violations)} issues (not blocking in {self.phase})")
            return True
        else:
            print(f"\n✅ PASSED: All gates satisfied for {self.phase}")
            return True

    def _check_basic_structure(self, data: Dict[str, Any]):
        """Check basic project structure"""
        num_files = len(data.get("files", []))
        num_modules = len(data.get("modules", []))
        num_contributors = len(data.get("contributors", []))

        if num_files < self.gates.get("min_files", 0):
            self.violations.append(f"Insufficient files: {num_files} < {self.gates['min_files']}")
        else:
            print(f"✓ Files: {num_files}")

        if num_modules < self.gates.get("min_modules", 0):
            self.violations.append(
                f"Insufficient modules: {num_modules} < {self.gates['min_modules']}"
            )
        else:
            print(f"✓ Modules: {num_modules}")

        if num_contributors == 0:
            self.warnings.append("No contributors detected")
        else:
            print(f"✓ Contributors: {num_contributors}")

    def _check_issues(self, data: Dict[str, Any]):
        """Check issue counts by severity"""
        issues = data.get("issues", [])

        # Count by severity
        high_issues = self._count_by_severity(issues, "Critical")
        medium_issues = self._count_by_severity(issues, "Major")
        low_issues = self._count_by_severity(issues, "Minor")

        print("\nIssues detected:")
        print(f"  High:   {high_issues}")
        print(f"  Medium: {medium_issues}")
        print(f"  Low:    {low_issues}")

        if high_issues > self.gates.get("max_high_issues", 999):
            self.violations.append(
                f"Too many high-severity issues: {high_issues} > {self.gates['max_high_issues']}"
            )

        if medium_issues > self.gates.get("max_medium_issues", 999):
            self.violations.append(
                f"Too many medium-severity issues: {medium_issues} > {self.gates['max_medium_issues']}"
            )

        # List high-severity issues
        if high_issues > 0:
            print("\nHigh-severity issues:")
            for issue in issues:
                if "Critical" in str(issue.get("severity", {}).get("@id", "")):
                    print(f"  - {issue.get('description', 'Unknown')[:80]}")

    def _check_coverage(self, coverage: float):
        """Check test coverage"""
        target = self.gates.get("coverage", 0)

        print(f"\nCoverage: {coverage:.1f}% (target: {target}%)")

        if coverage < target:
            msg = f"Coverage below target: {coverage:.1f}% < {target}%"
            if self.phase in ["phase0"]:
                self.warnings.append(msg)
            else:
                self.violations.append(msg)
        else:
            print("✓ Coverage target met")

    def _count_by_severity(self, issues: List[Dict], severity: str) -> int:
        """Count issues matching severity"""
        return sum(1 for i in issues if severity in str(i.get("severity", {}).get("@id", "")))

    def _display_results(self):
        """Display warnings and violations"""
        if self.warnings:
            print("\n⚠️  Warnings:")
            for w in self.warnings:
                print(f"  - {w}")

        if self.violations:
            print("\n❌ Violations:")
            for v in self.violations:
                print(f"  - {v}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Assert repoq quality gates")
    parser.add_argument("jsonld_file", help="Path to self-analysis JSON-LD file")
    parser.add_argument(
        "--phase",
        default="phase0",
        choices=["phase0", "phase1", "phase2", "phase3", "ga"],
        help="Quality gate phase",
    )
    parser.add_argument(
        "--coverage", type=float, default=0.0, help="Test coverage percentage (e.g., 75.5)"
    )

    args = parser.parse_args()

    # Load JSON-LD
    jsonld_path = Path(args.jsonld_file)
    if not jsonld_path.exists():
        print(f"❌ File not found: {jsonld_path}")
        sys.exit(1)

    with open(jsonld_path) as f:
        data = json.load(f)

    # Run checks
    gates = QualityGates(phase=args.phase)
    passed = gates.check(data, coverage=args.coverage)

    # Exit with appropriate code
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
