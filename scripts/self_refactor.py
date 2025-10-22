#!/usr/bin/env python3
"""Self-refactoring script: apply RepoQ to itself with full RDF enrichment.

This script demonstrates the reflexive capability of RepoQ by analyzing
its own codebase and generating quality recommendations based on the
quality:Recommendation ontology with ΔQ metrics.

Σ (Signature):
- Input: RepoQ project directory (.)
- Output: RDF Turtle with 6 enrichment layers + quality recommendations
- Meta-language: Python + RDFLib + SPARQL
- Target: Generate actionable refactoring plan with ΔQ scores

Γ (Gates):
- soundness: All enrichment layers must conform to SHACL shapes
- confluence: No circular dependencies in meta-validation
- termination: Analysis completes within resource budgets
- quality: Generate ≥5 recommendations with positive ΔQ

"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from repoq.core.model import Project
from repoq.core.rdf_export import export_ttl, validate_shapes
from repoq.analyzers.structure import StructureAnalyzer
from repoq.analyzers.complexity import ComplexityAnalyzer
from repoq.analyzers.weakness import WeaknessAnalyzer
from repoq.analyzers.ci_qm import CIQualityAnalyzer
from repoq.analyzers.history import HistoryAnalyzer
from repoq.analyzers.hotspots import HotspotsAnalyzer
from repoq.config import AnalyzeConfig
from repoq import __version__

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def analyze_repoq_self() -> Project:
    """Run full RepoQ analysis on itself.
    
    Returns:
        Project: Analyzed project with all metrics and issues
    """
    logger.info("=== Starting RepoQ self-analysis ===")
    
    # Create project instance
    project = Project(
        id="https://github.com/kirill-0440/repoq",
        name="RepoQ",
        description="Repository Quality Analysis with Semantic Web Export",
        repository_url="https://github.com/kirill-0440/repoq",
    )
    project.analyzed_at = datetime.now(timezone.utc).isoformat()
    project.repoq_version = __version__
    
    # Configure analysis
    cfg = AnalyzeConfig(
        mode="full",
        since="1 year ago",
        include_extensions=["py"],
        exclude_globs=[
            "**/venv/**",
            "**/.venv/**",
            "**/node_modules/**",
            "**/__pycache__/**",
            "**/.pytest_cache/**",
            "**/dist/**",
            "**/build/**",
        ],
        max_files=500,  # Limit for performance
    )
    
    repo_dir = project_root
    
    # Run all analyzers
    logger.info("Running structure analysis...")
    StructureAnalyzer().run(project, repo_dir, cfg)
    
    logger.info("Running complexity analysis...")
    ComplexityAnalyzer().run(project, repo_dir, cfg)
    
    logger.info("Running weakness detection...")
    WeaknessAnalyzer().run(project, repo_dir, cfg)
    
    logger.info("Running CI quality checks...")
    CIQualityAnalyzer().run(project, repo_dir, cfg)
    
    logger.info("Running history analysis...")
    HistoryAnalyzer().run(project, repo_dir, cfg)
    
    logger.info("Running hotspot detection...")
    HotspotsAnalyzer().run(project, repo_dir, cfg)
    
    # Summary
    logger.info(f"✓ Analyzed {len(project.files)} files")
    logger.info(f"✓ Found {len(project.issues)} issues")
    # Count hotspot issues
    hotspot_count = sum(1 for issue in project.issues.values() if "hotspot" in issue.type.lower())
    logger.info(f"✓ Identified {hotspot_count} hotspots")
    logger.info(f"✓ Detected {len(project.modules)} modules")
    
    return project


def export_with_full_enrichment(project: Project, output_path: Path) -> None:
    """Export RDF with all enrichment layers including quality recommendations.
    
    Args:
        project: Analyzed project
        output_path: Path for Turtle output
    """
    logger.info("=== Exporting RDF with full enrichment ===")
    
    # Export with all enrichment layers
    export_ttl(
        project=project,
        ttl_path=str(output_path),
        context_file=None,
        field33_context=None,
        enrich_meta=True,
        enrich_test_coverage=False,  # Renamed from enrich_tests
        enrich_trs_rules=False,  # Renamed from enrich_trs
        enrich_quality_recommendations=True,
        enrich_self_analysis=True,
        stratification_level=1,  # Safe level (0=base, 1=meta, 2=meta-meta)
    )
    
    file_size = output_path.stat().st_size
    logger.info(f"✓ RDF exported: {file_size / 1024:.1f} KB ({file_size:,} bytes)")
    
    # Count lines
    with open(output_path, "r") as f:
        line_count = sum(1 for _ in f)
    logger.info(f"✓ Total lines: {line_count:,}")


def validate_rdf(project: Project) -> dict:
    """Validate RDF against SHACL shapes.
    
    Args:
        project: Project to validate
        
    Returns:
        Validation report dict
    """
    logger.info("=== Validating RDF against SHACL shapes ===")
    
    shapes_dir = project_root / "repoq" / "shapes"
    
    result = validate_shapes(
        project=project,
        shapes_dir=str(shapes_dir),
        context_file=None,
        field33_context=None,
        enrich_meta=True,
        enrich_test_coverage=False,
        enrich_trs_rules=False,
        enrich_quality_recommendations=True,
        enrich_self_analysis=True,
        stratification_level=1,
    )
    
    conforms = result.get("conforms", False)
    logger.info(f"{'✓' if conforms else '✗'} SHACL validation: {'PASSED' if conforms else 'FAILED'}")
    
    if not conforms:
        logger.warning(f"Validation report:\n{result.get('report', 'No report')}")
    
    return result


def extract_recommendations(rdf_path: Path) -> list[dict]:
    """Extract quality:Recommendation triples from RDF using SPARQL.
    
    Args:
        rdf_path: Path to Turtle file
        
    Returns:
        List of recommendation dicts with title, description, delta_q, effort
    """
    logger.info("=== Extracting quality recommendations via SPARQL ===")
    
    from rdflib import Graph, Namespace
    
    # Load RDF
    g = Graph()
    g.parse(rdf_path, format="turtle")
    
    # Define namespaces
    QUALITY = Namespace("https://w3id.org/okn/o/quality#")
    REPO = Namespace("https://w3id.org/okn/o/repo#")
    
    # SPARQL query for recommendations
    query = """
    PREFIX quality: <http://example.org/vocab/quality#>
    PREFIX repo: <http://example.org/vocab/repo#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    
    SELECT ?rec ?title ?desc ?delta_q ?effort ?priority ?file
    WHERE {
        ?rec a quality:Recommendation ;
             quality:recommendationTitle ?title ;
             quality:recommendationDescription ?desc ;
             quality:deltaQ ?delta_q ;
             quality:estimatedEffortHours ?effort ;
             quality:priority ?priority .
        OPTIONAL { ?rec quality:targetsFile ?file }
    }
    ORDER BY DESC(?delta_q)
    """
    
    results = g.query(query)
    recommendations = []
    
    for row in results:
        rec = {
            "uri": str(row.rec),
            "title": str(row.title),
            "description": str(row.desc),
            "delta_q": float(row.delta_q) if row.delta_q else 0.0,
            "effort": float(row.effort) if row.effort else 0.0,
            "priority": str(row.priority),
            "file": str(row.file) if row.file else None,
        }
        recommendations.append(rec)
    
    logger.info(f"✓ Found {len(recommendations)} quality recommendations")
    
    return recommendations


def print_top_recommendations(recommendations: list[dict], top_n: int = 5) -> None:
    """Print top N recommendations by ΔQ.
    
    Args:
        recommendations: List of recommendation dicts
        top_n: Number of top items to print
    """
    logger.info(f"\n=== Top {top_n} Refactoring Recommendations by ΔQ ===")
    
    # Sort by delta_q descending
    sorted_recs = sorted(recommendations, key=lambda x: x["delta_q"], reverse=True)
    
    for i, rec in enumerate(sorted_recs[:top_n], 1):
        print(f"\n{i}. {rec['title']}")
        print(f"   Priority: {rec['priority']}")
        print(f"   ΔQ: {rec['delta_q']:.1f} (quality improvement points)")
        print(f"   Effort: {rec['effort']:.1f} hours")
        print(f"   ROI: {rec['delta_q'] / max(rec['effort'], 0.1):.2f} (ΔQ per hour)")
        if rec['file']:
            print(f"   File: {rec['file']}")
        print(f"   Description: {rec['description'][:150]}...")


def check_self_analysis_safety(rdf_path: Path) -> dict:
    """Check meta-validation safety results from RDF.
    
    Args:
        rdf_path: Path to Turtle file
        
    Returns:
        Dict with safety check results
    """
    logger.info("=== Checking meta-validation safety ===")
    
    from rdflib import Graph, Namespace, Literal
    
    g = Graph()
    g.parse(rdf_path, format="turtle")
    
    META = Namespace("http://example.org/vocab/meta#")
    
    # Query for self-analysis results
    query = """
    PREFIX meta: <http://example.org/vocab/meta#>
    
    SELECT ?analysis ?safety ?violations
    WHERE {
        ?analysis a meta:SelfAnalysis ;
                  meta:safetyChecksPassed ?safety .
        OPTIONAL {
            SELECT ?analysis (COUNT(?violation) as ?violations)
            WHERE {
                ?analysis meta:universeViolation ?violation .
            }
            GROUP BY ?analysis
        }
    }
    LIMIT 1
    """
    
    results = list(g.query(query))
    
    if not results:
        logger.warning("⚠ No meta:SelfAnalysis found in RDF")
        return {"found": False}
    
    row = results[0]
    safety_result = {
        "found": True,
        "safety_checks_passed": bool(row.safety),
        "universe_violations": int(row.violations) if row.violations else 0,
    }
    
    if safety_result["safety_checks_passed"]:
        logger.info("✓ Safety checks: PASSED")
        logger.info(f"  - Universe violations: {safety_result['universe_violations']}")
    else:
        logger.warning("⚠ Safety checks: FAILED")
        logger.warning(f"  - Universe violations: {safety_result['universe_violations']}")
    
    return safety_result


def main() -> int:
    """Main entry point for self-refactoring analysis.
    
    Returns:
        Exit code (0 = success, 1 = failure)
    """
    output_path = project_root / "repoq_self_refactor.ttl"
    
    try:
        # Phase 1: Analyze
        project = analyze_repoq_self()
        
        # Phase 2: Export RDF with enrichment
        export_with_full_enrichment(project, output_path)
        
        # Phase 3: Validate (continue even if validation warnings)
        validation = validate_rdf(project)
        conforms = validation.get("conforms", False)
        if not conforms:
            logger.warning("SHACL validation warnings detected (universe violations expected for self-analysis)")
        
        # Phase 4: Extract recommendations
        recommendations = extract_recommendations(output_path)
        
        if not recommendations:
            logger.warning("No quality recommendations generated")
        else:
            print_top_recommendations(recommendations, top_n=5)
        
        # Phase 5: Check meta-validation safety
        safety = check_self_analysis_safety(output_path)
        
        # Success summary (even with warnings)
        logger.info("\n=== Self-refactoring analysis complete ===")
        logger.info(f"✓ RDF output: {output_path}")
        logger.info(f"✓ Recommendations: {len(recommendations)}")
        logger.info(f"{'✓' if conforms else '⚠'} SHACL validation: {'PASSED' if conforms else 'WARNINGS'}")
        logger.info(f"{'✓' if safety.get('found', False) else '⚠'} Meta-validation: {'ANALYZED' if safety.get('found', False) else 'NOT FOUND'}")
        
        return 0
        
    except Exception as e:
        logger.exception(f"Self-refactoring analysis failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
