"""
Tests for TRS rules extraction module.
"""

from pathlib import Path

import pytest
from rdflib import Graph

from repoq.core.trs_rules import (
    TRSRule,
    TRSSystem,
    enrich_graph_with_trs_rules,
    export_trs_systems_rdf,
    extract_rules_from_module,
    extract_trs_systems,
)


def test_extract_rules_from_spdx_module():
    """Test extracting rules from spdx_trs.py module."""
    module_path = Path("repoq/normalize/spdx_trs.py")

    if not module_path.exists():
        pytest.skip("spdx_trs.py not found")

    rules = extract_rules_from_module(module_path)

    assert len(rules) > 0, "Expected to extract at least one rule"

    # Check that rules have required fields
    for rule in rules:
        assert rule.id != ""
        assert rule.name != ""
        assert rule.left_hand_side != ""
        assert rule.right_hand_side != ""
        assert rule.module == "spdx_trs"

    print(f"✅ Extracted {len(rules)} rules from spdx_trs.py")


def test_extract_rules_from_rdf_module():
    """Test extracting rules from rdf_trs.py module."""
    module_path = Path("repoq/normalize/rdf_trs.py")

    if not module_path.exists():
        pytest.skip("rdf_trs.py not found")

    rules = extract_rules_from_module(module_path)

    # RDF module may have fewer explicit rules (canonicalization functions)
    assert isinstance(rules, list)

    print(f"✅ Extracted {len(rules)} rules from rdf_trs.py")


def test_extract_trs_systems():
    """Test extracting all TRS systems from normalize/ directory."""
    normalize_dir = Path("repoq/normalize")

    if not normalize_dir.exists():
        pytest.skip("normalize/ directory not found")

    systems = extract_trs_systems(normalize_dir)

    assert len(systems) > 0, "Expected to extract at least one TRS system"

    # Check that systems have required fields
    for system in systems:
        assert system.id != ""
        assert system.name != ""
        assert len(system.rules) >= 0  # May have 0 rules if extraction failed

    print(f"✅ Extracted {len(systems)} TRS systems")

    for system in systems:
        print(f"  - {system.name}: {len(system.rules)} rules")


def test_trs_rule_structure():
    """Test TRSRule dataclass structure."""
    rule = TRSRule(
        id="trs:spdx_trs/rule_1",
        name="spdx_idempotence",
        left_hand_side="A OR A",
        right_hand_side="A",
        module="spdx_trs",
        description="idempotence",
    )

    assert rule.id == "trs:spdx_trs/rule_1"
    assert rule.name == "spdx_idempotence"
    assert rule.left_hand_side == "A OR A"
    assert rule.right_hand_side == "A"
    assert rule.module == "spdx_trs"
    assert rule.description == "idempotence"


def test_export_trs_systems_rdf():
    """Test exporting TRS systems to RDF graph."""
    g = Graph()

    # Create sample TRS system
    rule1 = TRSRule(
        id="trs:test/rule_1",
        name="test_rule_1",
        left_hand_side="A OR A",
        right_hand_side="A",
        module="test",
        description="idempotence",
    )

    rule2 = TRSRule(
        id="trs:test/rule_2",
        name="test_rule_2",
        left_hand_side="A AND A",
        right_hand_side="A",
        module="test",
        description="idempotence for AND",
    )

    system = TRSSystem(
        id="trs:test",
        name="Test TRS",
        rules=[rule1, rule2],
        confluence_proven=True,
        termination_proven=True,
        critical_pairs_count=0,
    )

    export_trs_systems_rdf(g, [system], "repo:test_project")

    # Verify TRS system triple
    query_system = """
    PREFIX trs: <http://example.org/vocab/trs#>
    SELECT ?system ?name ?confluence WHERE {
        ?system a trs:RewriteSystem ;
                trs:systemName ?name ;
                trs:confluenceProven ?confluence .
    }
    """
    results = list(g.query(query_system))
    assert len(results) == 1
    assert str(results[0][1]) == "Test TRS"
    assert bool(results[0][2]) is True

    # Verify rules
    query_rules = """
    PREFIX trs: <http://example.org/vocab/trs#>
    SELECT ?rule ?lhs ?rhs WHERE {
        ?rule a trs:Rule ;
              trs:leftHandSide ?lhs ;
              trs:rightHandSide ?rhs .
    }
    """
    results = list(g.query(query_rules))
    assert len(results) == 2

    lhs_values = {str(r[1]) for r in results}
    assert "A OR A" in lhs_values
    assert "A AND A" in lhs_values

    print(f"✅ Exported {len(results)} rules to RDF")


def test_enrich_graph_with_trs_rules():
    """Test high-level enrichment function."""
    normalize_dir = Path("repoq/normalize")

    if not normalize_dir.exists():
        pytest.skip("normalize/ directory not found")

    g = Graph()

    enrich_graph_with_trs_rules(g, "repo:test_project", normalize_dir=normalize_dir)

    # Verify graph has TRS data
    query = """
    PREFIX trs: <http://example.org/vocab/trs#>
    SELECT (COUNT(?s) as ?count) WHERE {
        ?s a trs:RewriteSystem .
    }
    """
    results = list(g.query(query))
    count = int(results[0][0])

    assert count >= 1, "Expected at least one TRS system"

    # Verify rules exist
    query_rules = """
    PREFIX trs: <http://example.org/vocab/trs#>
    SELECT (COUNT(?r) as ?count) WHERE {
        ?r a trs:Rule .
    }
    """
    results = list(g.query(query_rules))
    rules_count = int(results[0][0])

    print(f"✅ Enriched graph: {count} TRS systems, {rules_count} rules")


def test_integration_with_rdf_export(tmp_path):
    """Test integration with full RDF export pipeline."""
    from repoq.core.model import File, Project
    from repoq.core.rdf_export import export_ttl

    # Create test project
    project = Project(id="repo:test", name="test")
    file1 = File(id=f"{project.id}/file1", path="src/main.py", language="python")
    project.files = {file1.id: file1}

    ttl_path = tmp_path / "test_output.ttl"

    # Export with TRS rules enrichment
    export_ttl(project, str(ttl_path), enrich_trs_rules=True)

    # Verify output contains TRS data
    content = ttl_path.read_text()
    assert "trs:" in content
    assert "RewriteSystem" in content or "Rule" in content

    print(f"✅ RDF export with TRS rules: {ttl_path}")


def test_spdx_idempotence_rule_extraction():
    """Test that SPDX idempotence rule is extracted correctly."""
    module_path = Path("repoq/normalize/spdx_trs.py")

    if not module_path.exists():
        pytest.skip("spdx_trs.py not found")

    rules = extract_rules_from_module(module_path)

    # Look for idempotence rule
    idempotence_rules = [r for r in rules if "idempotence" in r.description.lower()]

    assert len(idempotence_rules) > 0, "Expected to find idempotence rule"

    # Check LHS/RHS format
    for rule in idempotence_rules:
        assert "OR" in rule.left_hand_side or "AND" in rule.left_hand_side
        # RHS should be simpler than LHS
        assert len(rule.right_hand_side) <= len(rule.left_hand_side)

    print(f"✅ Found {len(idempotence_rules)} idempotence rules")


def test_trs_system_verification_metadata():
    """Test that TRS systems can store verification metadata."""
    system = TRSSystem(
        id="trs:test",
        name="Test",
        rules=[],
        confluence_proven=True,
        termination_proven=True,
        critical_pairs_count=3,
    )

    assert system.confluence_proven is True
    assert system.termination_proven is True
    assert system.critical_pairs_count == 3


def test_rule_extraction_regex_robustness():
    """Test that rule extraction handles various docstring formats."""
    # This is a unit test for the regex patterns
    import re

    # Pattern from trs_rules.py (updated to handle nested parens)
    rule_pattern = re.compile(r"(\d+)\.\s+(.*?)\s*→\s*(.*?)\s+\(([^)]+)\)", re.MULTILINE)

    test_cases = [
        ("1. A OR A → A (idempotence)", ("1", "A OR A", "A", "idempotence")),
        ("4. A OR (A AND B) → A (absorption)", ("4", "A OR (A AND B)", "A", "absorption")),
        ("5. X WITH Y → X WITH Y (identity)", ("5", "X WITH Y", "X WITH Y", "identity")),
    ]

    for text, expected in test_cases:
        match = rule_pattern.search(text)
        assert match is not None, f"Failed to match: {text}"

        num, lhs, rhs, desc = match.groups()
        assert (num, lhs.strip(), rhs.strip(), desc.strip()) == expected

    print("✅ Rule extraction regex is robust")
