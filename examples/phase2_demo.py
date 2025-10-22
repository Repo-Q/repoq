#!/usr/bin/env python3
"""
Example script demonstrating RepoQ Phase 2 features.

Shows all 6 RDF enrichment layers in action:
1. Meta-ontology enrichment
2. Test coverage → RDF
3. TRS rules extraction
4. Quality recommendations with ΔQ
5. Self-validation (meta-loop closure)
6. Base analysis

Usage:
    python examples/phase2_demo.py
"""

from pathlib import Path

from repoq.core.model import File, Project
from repoq.core.rdf_export import export_ttl, validate_shapes


def create_demo_project():
    """Create a demo project for testing."""
    project = Project(
        id="repo:repoq-demo",
        name="RepoQ Phase 2 Demo",
        repository_url="https://github.com/Repo-Q/repoq",
        programming_languages={"Python": 1.0},
    )

    # Add some sample files
    file1 = File(
        id="repo:repoq-demo/repoq/core/meta_validation.py",
        path="repoq/core/meta_validation.py",
        complexity=12.0,
        lines_of_code=330,
    )
    file1.stratification_level = 1

    file2 = File(
        id="repo:repoq-demo/repoq/core/rdf_export.py",
        path="repoq/core/rdf_export.py",
        complexity=15.0,
        lines_of_code=460,
    )

    project.files["repoq/core/meta_validation.py"] = file1
    project.files["repoq/core/rdf_export.py"] = file2

    return project


def demo_rdf_export():
    """Demonstrate RDF export with all enrichment layers."""
    print("=" * 70)
    print("RepoQ Phase 2 Demo: Semantic RDF Export")
    print("=" * 70)

    # Create demo project
    print("\n1. Creating demo project...")
    project = create_demo_project()
    print(f"   ✓ Created: {project.name}")
    print(f"   ✓ Files: {len(project.files)}")

    # Export with all enrichment layers
    print("\n2. Exporting RDF/Turtle with 6 enrichment layers...")
    project_path = Path(__file__).parent.parent
    output_path = project_path / "examples" / "repoq_phase2_demo.ttl"

    export_ttl(
        project,
        str(output_path),
        enrich_meta=True,  # Layer 1: Meta-ontology
        enrich_test_coverage=True,  # Layer 2: Test coverage
        enrich_trs_rules=True,  # Layer 3: TRS rules
        enrich_quality_recommendations=True,  # Layer 4: ΔQ recommendations
        enrich_self_analysis=True,  # Layer 5: Self-validation
        top_k_recommendations=5,
        min_delta_q=10.0,
        stratification_level=1,
        analyzed_commit="HEAD",
    )

    print(f"   ✓ Exported to: {output_path}")

    # Validate against SHACL shapes
    print("\n3. Validating against SHACL shapes...")
    shapes_dir = project_path / "repoq" / "shapes"

    result = validate_shapes(
        project,
        str(shapes_dir),
        enrich_meta=True,
        enrich_test_coverage=True,
        enrich_trs_rules=True,
        enrich_quality_recommendations=True,
        enrich_self_analysis=True,
    )

    if result["conforms"]:
        print("   ✓ SHACL validation: PASSED")
    else:
        print("   ✗ SHACL validation: FAILED")
        print(f"   Violations: {len(result.get('violations', []))}")
        for i, violation in enumerate(result.get("violations", [])[:3], 1):
            print(f"     {i}. {violation.get('message', 'Unknown violation')}")

    # Show RDF file stats
    print("\n4. RDF file statistics...")
    if output_path.exists():
        content = output_path.read_text()
        lines = content.split("\n")
        print(f"   ✓ Lines: {len(lines)}")
        print(f"   ✓ Size: {output_path.stat().st_size / 1024:.1f} KB")

        # Count triple types
        meta_count = content.count("meta:")
        test_count = content.count("test:")
        trs_count = content.count("trs:")
        quality_count = content.count("quality:")
        repo_count = content.count("repo:")

        print("\n   Triple counts by namespace:")
        print(f"     - meta:     {meta_count}")
        print(f"     - test:     {test_count}")
        print(f"     - trs:      {trs_count}")
        print(f"     - quality:  {quality_count}")
        print(f"     - repo:     {repo_count}")

    print("\n" + "=" * 70)
    print("Demo complete! Check examples/repoq_phase2_demo.ttl")
    print("=" * 70)


def demo_self_analysis():
    """Demonstrate meta-loop self-validation."""
    print("\n" + "=" * 70)
    print("Meta-Loop Self-Validation Demo")
    print("=" * 70)

    from repoq.core.meta_validation import perform_self_analysis

    # Create demo project
    project = create_demo_project()

    # Perform self-analysis
    print("\n1. Running self-analysis (stratification level 1)...")
    result = perform_self_analysis(project, stratification_level=1, analyzed_commit="HEAD")

    print("\n   Results:")
    print(f"   - Self-reference detected: {result.self_reference_detected}")
    print(f"   - Stratification level: {result.stratification_level}")
    print(f"   - Read-only mode: {result.read_only_mode}")
    print(f"   - Safety checks passed: {result.safety_checks_passed}")
    print(f"   - Circular dependencies: {len(result.circular_dependencies)}")
    print(f"   - Universe violations: {len(result.universe_violations)}")

    if result.circular_dependencies:
        print("\n   ⚠️  Circular dependencies detected:")
        for i, cycle in enumerate(result.circular_dependencies[:3], 1):
            print(f"      {i}. {cycle}")

    if result.universe_violations:
        print("\n   ⚠️  Universe violations detected:")
        for i, violation in enumerate(result.universe_violations[:3], 1):
            print(f"      {i}. {violation}")

    if result.safety_checks_passed:
        print("\n   ✅ All safety checks passed! Meta-loop is safe.")
    else:
        print("\n   ⚠️  Safety checks failed. Review violations above.")

    print("\n" + "=" * 70)


def demo_sparql_queries():
    """Demonstrate SPARQL queries on RDF data."""
    print("\n" + "=" * 70)
    print("SPARQL Query Examples")
    print("=" * 70)

    print("""
Example SPARQL queries you can run on the exported RDF data:

1. Top recommendations by ΔQ:

   SELECT ?rec ?file ?deltaQ ?priority
   WHERE {
     ?rec a quality:Recommendation ;
          quality:deltaQ ?deltaQ ;
          quality:priority ?priority ;
          quality:targetsFile ?file .
   }
   ORDER BY DESC(?deltaQ)
   LIMIT 5

2. Test coverage by file:

   SELECT ?file ?coverage
   WHERE {
     ?file a repo:File ;
           test:coveragePercentage ?coverage .
   }
   ORDER BY ASC(?coverage)
   LIMIT 10

3. TRS rules by system:

   SELECT ?system ?rule ?lhs ?rhs
   WHERE {
     ?system a trs:RewriteSystem .
     ?rule a trs:Rule ;
           trs:inSystem ?system ;
           trs:leftHandSide ?lhs ;
           trs:rightHandSide ?rhs .
   }

4. Self-analysis safety status:

   SELECT ?analysis ?level ?safety ?violation
   WHERE {
     ?analysis a meta:SelfAnalysis ;
               meta:stratificationLevel ?level ;
               meta:safetyChecksPassed ?safety .
     OPTIONAL { ?analysis meta:universeViolation ?violation . }
   }

5. Files with high complexity:

   SELECT ?file ?complexity
   WHERE {
     ?file a repo:File ;
           repo:complexity ?complexity .
     FILTER (?complexity > 15)
   }
   ORDER BY DESC(?complexity)
""")

    print("=" * 70)


if __name__ == "__main__":
    try:
        demo_rdf_export()
        demo_self_analysis()
        demo_sparql_queries()

        print("\n✅ All demos completed successfully!")
        print("\nNext steps:")
        print("  1. Explore examples/repoq_phase2_demo.ttl")
        print("  2. Run SPARQL queries using rdflib or Apache Jena")
        print("  3. Visualize RDF graph with GraphViz or WebVOWL")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
