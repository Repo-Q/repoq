"""Ontology management for RepoQ.

STRATIFICATION_LEVEL: 1 (meta-level ontology operations)

This package operates at level 1:
- Level 0: Base repository code (files, modules, dependencies)
- Level 1: Ontology definitions and SHACL validation
- Level 2: Meta-ontology operations (analyzing ontologies themselves)

This package contains ontology-related functionality:
- ontology_manager: Central ontology manager with SHACL validation
"""

__all__ = [
    "ontology_manager",
]
