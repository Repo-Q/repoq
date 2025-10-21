"""Core modules for RepoQ.

This package contains core functionality:
- model: Data models and structures
- rdf_export: RDF/Turtle export functionality
- repo_loader: Repository loading utilities
- deps: Dependency graph analysis
- jsonld: JSON-LD processing
- stratification_guard: Prevents Russell's paradox in self-referential analysis
- utils: Common utilities
"""

__all__ = [
    "model",
    "rdf_export",
    "repo_loader",
    "deps",
    "jsonld",
    "stratification_guard",
    "utils",
]
