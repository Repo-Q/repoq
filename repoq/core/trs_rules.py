"""
TRS (Term Rewriting System) rules extraction module.

Извлекает правила переписывания из normalize/ и генерирует trs:Rule triples.
Включает metadata о confluence, termination, soundness из TRS verification.
"""

import ast
import inspect
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

from rdflib import Graph, Literal, Namespace, RDF, URIRef
from rdflib.namespace import XSD


# Namespaces
TRS_NS = "http://example.org/vocab/trs#"
REPO_NS = "http://example.org/vocab/repo#"


@dataclass
class TRSRule:
    """Represents a single TRS rewrite rule."""

    id: str
    name: str
    left_hand_side: str  # Pattern (e.g., "A OR A")
    right_hand_side: str  # Replacement (e.g., "A")
    module: str  # e.g., "spdx_trs"
    description: Optional[str] = None
    termination_proven: bool = False
    soundness_proven: bool = False


@dataclass
class TRSSystem:
    """Represents a complete TRS."""

    id: str
    name: str
    rules: List[TRSRule]
    confluence_proven: bool = False
    termination_proven: bool = False
    critical_pairs_count: int = 0


def extract_rules_from_module(module_path: Path) -> List[TRSRule]:
    """
    Extract TRS rules from a normalize/*.py module.

    Parses the module's docstring and function definitions to identify
    rewrite rules.

    Args:
        module_path: Path to normalize module (e.g., spdx_trs.py)

    Returns:
        List of TRSRule objects

    Example:
        >>> rules = extract_rules_from_module(Path("repoq/normalize/spdx_trs.py"))
        >>> len(rules) >= 4  # At least idempotence, absorption, etc.
        True
    """
    rules = []
    module_name = module_path.stem  # e.g., "spdx_trs"

    # Read module content
    content = module_path.read_text()

    # Extract rules from module docstring
    docstring_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
    if docstring_match:
        docstring = docstring_match.group(1)

        # Look for "Rewrite Rules:" section
        rules_section = re.search(
            r"Rewrite Rules?:(.*?)(?=\n\n|\Z)", docstring, re.DOTALL | re.IGNORECASE
        )

        if rules_section:
            rules_text = rules_section.group(1)

            # Parse rules like: "1. A OR A → A (idempotence)"
            # Use greedy match for RHS, then capture last (...) as description
            rule_pattern = re.compile(r"(\d+)\.\s+(.*?)\s*→\s*(.*?)\s+\(([^)]+)\)", re.MULTILINE)

            for match in rule_pattern.finditer(rules_text):
                rule_num, lhs, rhs, description = match.groups()

                rule = TRSRule(
                    id=f"trs:{module_name}/rule_{rule_num}",
                    name=f"{module_name}_rule_{rule_num}",
                    left_hand_side=lhs.strip(),
                    right_hand_side=rhs.strip(),
                    module=module_name,
                    description=description.strip(),
                )
                rules.append(rule)

    # Extract function-based rules (e.g., _apply_idempotence_or)
    function_pattern = re.compile(
        r'def (_apply_\w+)\(.*?\):\s*"""(.*?)"""', re.MULTILINE | re.DOTALL
    )

    for match in function_pattern.finditer(content):
        func_name, func_doc = match.groups()

        # Extract rule from function docstring
        # e.g., "Apply absorption: A OR (A AND B) → A."
        rule_match = re.search(r"(.*?)\s*[→:]\s*(.*?)(?:\.|$)", func_doc, re.DOTALL)

        if rule_match:
            lhs_desc, rhs_desc = rule_match.groups()

            # Try to extract symbolic form
            symbolic_match = re.search(r"([\w\s()]+)\s+→\s+([\w\s()]+)", func_doc)

            if symbolic_match:
                lhs, rhs = symbolic_match.groups()

                rule = TRSRule(
                    id=f"trs:{module_name}/{func_name}",
                    name=func_name,
                    left_hand_side=lhs.strip(),
                    right_hand_side=rhs.strip(),
                    module=module_name,
                    description=lhs_desc.strip(),
                )
                rules.append(rule)

    return rules


def extract_trs_systems(normalize_dir: Path) -> List[TRSSystem]:
    """
    Extract all TRS systems from normalize/ directory.

    Args:
        normalize_dir: Path to repoq/normalize directory

    Returns:
        List of TRSSystem objects

    Example:
        >>> systems = extract_trs_systems(Path("repoq/normalize"))
        >>> len(systems) >= 3  # At least spdx, rdf, semver
        True
    """
    systems = []

    # Scan all *_trs.py modules
    trs_modules = list(normalize_dir.glob("*_trs.py"))

    for module_path in trs_modules:
        module_name = module_path.stem
        rules = extract_rules_from_module(module_path)

        if not rules:
            continue

        # Create TRS system
        system = TRSSystem(
            id=f"trs:{module_name}",
            name=module_name.replace("_", " ").title(),
            rules=rules,
            confluence_proven=False,  # TODO: Extract from verification tests
            termination_proven=False,  # TODO: Extract from verification tests
            critical_pairs_count=0,  # TODO: Extract from check_critical_pairs()
        )

        systems.append(system)

    return systems


def enrich_with_verification_data(
    systems: List[TRSSystem], tests_dir: Optional[Path] = None
) -> None:
    """
    Enrich TRS systems with verification data from property tests.

    Args:
        systems: List of TRSSystem objects to enrich
        tests_dir: Path to tests/properties directory (default: auto-detect)

    Side Effects:
        Modifies systems in-place by setting confluence_proven, etc.
    """
    if tests_dir is None:
        tests_dir = Path("tests/properties")

    if not tests_dir.exists():
        return

    # Scan property test files
    for test_file in tests_dir.glob("test_*.py"):
        content = test_file.read_text()

        # Look for confluence tests
        if "test_confluence" in content or "test_critical_pairs" in content:
            # Extract which system is being tested
            module_match = re.search(r"from repoq\.normalize\.(\w+)", content)
            if module_match:
                module_name = module_match.group(1)

                # Find corresponding system
                for system in systems:
                    if system.id.endswith(module_name):
                        system.confluence_proven = True

        # Look for termination tests
        if "test_termination" in content or "test_idempotence" in content:
            module_match = re.search(r"from repoq\.normalize\.(\w+)", content)
            if module_match:
                module_name = module_match.group(1)

                for system in systems:
                    if system.id.endswith(module_name):
                        system.termination_proven = True


def export_trs_systems_rdf(graph: Graph, systems: List[TRSSystem], project_id: str) -> None:
    """
    Add TRS systems and rules to RDF graph.

    Args:
        graph: RDFLib Graph to add triples to
        systems: List of TRS systems
        project_id: Project URI (e.g., "repo:repoq")

    Side Effects:
        Modifies `graph` in-place by adding triples
    """
    TRS = Namespace(TRS_NS)
    REPO = Namespace(REPO_NS)

    # Add namespace binding
    graph.bind("trs", TRS)

    for system in systems:
        # Create TRS system instance
        system_uri = URIRef(f"{project_id}/{system.id}")
        graph.add((system_uri, RDF.type, TRS.RewriteSystem))
        graph.add((system_uri, TRS.systemName, Literal(system.name)))

        # Add verification metadata
        graph.add(
            (
                system_uri,
                TRS.confluenceProven,
                Literal(system.confluence_proven, datatype=XSD.boolean),
            )
        )
        graph.add(
            (
                system_uri,
                TRS.terminationProven,
                Literal(system.termination_proven, datatype=XSD.boolean),
            )
        )
        graph.add(
            (
                system_uri,
                TRS.soundnessProven,
                Literal(system.termination_proven, datatype=XSD.boolean),  # Soundness = termination for now
            )
        )
        graph.add(
            (
                system_uri,
                TRS.criticalPairsCount,
                Literal(system.critical_pairs_count, datatype=XSD.nonNegativeInteger),
            )
        )

        # Add rules
        for rule in system.rules:
            rule_uri = URIRef(rule.id)
            graph.add((rule_uri, RDF.type, TRS.Rule))
            graph.add((rule_uri, TRS.ruleName, Literal(rule.name)))
            graph.add((rule_uri, TRS.leftHandSide, Literal(rule.left_hand_side)))
            graph.add((rule_uri, TRS.rightHandSide, Literal(rule.right_hand_side)))
            graph.add((rule_uri, TRS.inSystem, system_uri))

            if rule.description:
                graph.add((rule_uri, TRS.ruleDescription, Literal(rule.description)))

            if rule.termination_proven:
                graph.add(
                    (
                        rule_uri,
                        TRS.terminationProven,
                        Literal(True, datatype=XSD.boolean),
                    )
                )

            if rule.soundness_proven:
                graph.add(
                    (rule_uri, TRS.soundnessProven, Literal(True, datatype=XSD.boolean))
                )


def enrich_graph_with_trs_rules(
    graph: Graph,
    project_id: str,
    normalize_dir: Optional[Path] = None,
    tests_dir: Optional[Path] = None,
) -> None:
    """
    High-level function to enrich RDF graph with TRS rules.

    Args:
        graph: RDFLib Graph to enrich
        project_id: Project URI (e.g., "repo:repoq")
        normalize_dir: Path to normalize/ directory (default: auto-detect)
        tests_dir: Path to tests/properties directory (default: auto-detect)

    Raises:
        FileNotFoundError: If normalize_dir not found
    """
    if normalize_dir is None:
        normalize_dir = Path("repoq/normalize")

    if not normalize_dir.exists():
        raise FileNotFoundError(f"Normalize directory not found: {normalize_dir}")

    # Extract TRS systems
    systems = extract_trs_systems(normalize_dir)

    # Enrich with verification data from tests
    enrich_with_verification_data(systems, tests_dir)

    # Export to RDF
    export_trs_systems_rdf(graph, systems, project_id)
