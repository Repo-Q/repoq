#!/usr/bin/env python3
"""
TRS Verification Runner

Executes comprehensive TRS property verification for all RepoQ normalization systems.
Can be run standalone or as part of CI pipeline.
"""

import sys
import json
import argparse
import time
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from rules.trs_properties import verify_all_trs_systems
from rules.trs_verifiers import create_all_verifiers
from rules.self_application_rules import run_safe_self_analysis, SAFE_CONFIGS


def run_trs_verification(verification_level: str = "standard") -> Dict[str, Any]:
    """Run TRS verification with specified level."""
    print(f"Running TRS verification at level: {verification_level}")
    
    # Create all verifiers
    verifiers = create_all_verifiers()
    
    # Run verification
    start_time = time.time()
    results = verify_all_trs_systems(verifiers)
    verification_time = time.time() - start_time
    
    # Add metadata
    results["_metadata"] = {
        "verification_level": verification_level,
        "total_time_seconds": verification_time,
        "timestamp": time.time(),
        "runner_version": "1.0.0"
    }
    
    return results


def run_self_application(config_name: str = "standard") -> Dict[str, Any]:
    """Run safe self-application analysis."""
    print(f"Running self-application with config: {config_name}")
    
    if config_name not in SAFE_CONFIGS:
        raise ValueError(f"Unknown config: {config_name}. Available: {list(SAFE_CONFIGS.keys())}")
    
    config = SAFE_CONFIGS[config_name].copy()
    
    try:
        results = run_safe_self_analysis(config)
        print("✅ Self-application completed successfully")
        return results
    except Exception as e:
        print(f"❌ Self-application failed: {e}")
        return {"error": str(e), "success": False}


def print_verification_summary(results: Dict[str, Any]) -> None:
    """Print human-readable verification summary."""
    print("\n" + "="*60)
    print("TRS VERIFICATION SUMMARY")
    print("="*60)
    
    summary = results.get("_summary", {})
    metadata = results.get("_metadata", {})
    
    print(f"Total Systems: {summary.get('total_systems', 0)}")
    print(f"Verification Time: {metadata.get('total_time_seconds', 0):.2f}s")
    print(f"Overall Status: {'✅ PASS' if summary.get('all_passed', False) else '❌ FAIL'}")
    print()
    
    # System-by-system results
    for system_name, system_results in results.items():
        if system_name.startswith("_"):
            continue
            
        print(f"📋 {system_name.upper()} TRS:")
        
        properties = ["idempotence", "determinism", "confluence", "termination", "soundness"]
        for prop in properties:
            if prop in system_results:
                prop_result = system_results[prop]
                status = "✅" if prop_result.get("passed", False) else "❌"
                time_ms = prop_result.get("time_ms", 0)
                print(f"  {status} {prop.capitalize():<12} ({time_ms:.1f}ms)")
        
        # Show violations if any
        details = system_results.get("verification_details", {})
        violations = []
        
        for violation_type in ["idempotence_violations", "determinism_violations", "termination_violations"]:
            if violation_type in details and details[violation_type]:
                violations.extend(details[violation_type])
        
        if violations:
            print(f"  ⚠️  {len(violations)} violations detected")
        
        print()


def print_self_application_summary(results: Dict[str, Any]) -> None:
    """Print self-application analysis summary."""
    print("\n" + "="*60)
    print("SELF-APPLICATION SUMMARY")
    print("="*60)
    
    if "error" in results:
        print(f"❌ Failed: {results['error']}")
        return
    
    # Safety report
    safety_report = results.get("safety_report", {})
    print(f"Safety Status: {safety_report.get('safety_status', 'unknown')}")
    print(f"Analysis Duration: {safety_report.get('analysis_duration', 0):.2f}s")
    print(f"Safety Violations: {safety_report.get('violation_count', 0)}")
    
    # Normalization stats
    norm_stats = results.get("normalization_stats", {})
    if norm_stats:
        total = norm_stats.get("total_normalized", 0)
        errors = norm_stats.get("errors", 0)
        success_rate = (total - errors) / max(total, 1) * 100
        
        print(f"Items Normalized: {total}")
        print(f"Normalization Errors: {errors}")
        print(f"Success Rate: {success_rate:.1f}%")
    
    # Analyzer results
    analyzers = results.get("analyzers", {})
    if analyzers:
        print("\nAnalyzer Results:")
        for analyzer_name, analyzer_data in analyzers.items():
            if isinstance(analyzer_data, dict):
                if "files" in analyzer_data:
                    file_count = len(analyzer_data["files"])
                    print(f"  📊 {analyzer_name}: {file_count} files analyzed")
                elif "violations" in analyzer_data:
                    violation_count = len(analyzer_data["violations"])
                    print(f"  🔍 {analyzer_name}: {violation_count} issues found")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="RepoQ TRS Verification Runner")
    parser.add_argument(
        "--mode", 
        choices=["verify", "self-apply", "both"],
        default="both",
        help="Verification mode (default: both)"
    )
    parser.add_argument(
        "--level",
        choices=["basic", "standard", "advanced"],
        default="standard", 
        help="Verification level (default: standard)"
    )
    parser.add_argument(
        "--config",
        choices=list(SAFE_CONFIGS.keys()),
        default="standard",
        help="Self-application config (default: standard)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for results (JSON format)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output except errors"
    )
    
    args = parser.parse_args()
    
    all_results = {}
    exit_code = 0
    
    try:
        # TRS Verification
        if args.mode in ["verify", "both"]:
            verification_results = run_trs_verification(args.level)
            all_results["verification"] = verification_results
            
            if not args.quiet:
                print_verification_summary(verification_results)
            
            # Check if verification passed
            if not verification_results.get("_summary", {}).get("all_passed", False):
                exit_code = 1
        
        # Self-Application
        if args.mode in ["self-apply", "both"]:
            self_app_results = run_self_application(args.config)
            all_results["self_application"] = self_app_results
            
            if not args.quiet:
                print_self_application_summary(self_app_results)
            
            # Check if self-application passed
            if "error" in self_app_results:
                exit_code = 1
        
        # Save results
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(all_results, f, indent=2, default=str)
            
            if not args.quiet:
                print(f"\n📁 Results saved to: {output_path}")
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        exit_code = 1
    
    if not args.quiet:
        status = "✅ SUCCESS" if exit_code == 0 else "❌ FAILURE"
        print(f"\n{status} - Exit code: {exit_code}")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()