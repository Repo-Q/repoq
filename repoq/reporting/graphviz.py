"""Graphviz visualization generation for dependency and coupling graphs.

This module generates DOT files and SVG visualizations for:
- Dependency graphs (modules and external packages)
- Temporal coupling graphs (files changed together)

Requires optional graphviz Python package and Graphviz system installation.
"""
from __future__ import annotations

import logging
import os

from ..core.model import Project

logger = logging.getLogger(__name__)


def export_graphs(project: Project, out_dir: str) -> None:
    """Export dependency and coupling graphs to DOT and SVG files.

    Creates two graph files in the output directory:
    - dependencies.dot/svg: Module dependencies and external packages
    - coupling.dot/svg: Temporal coupling between files

    Args:
        project: Project model with dependencies and coupling data
        out_dir: Output directory for graph files (created if needed)

    Note:
        Gracefully degrades if graphviz is not installed - creates minimal
        DOT files without rendering SVG.

    Example:
        >>> export_graphs(project, "./graphs")
        # Creates: ./graphs/dependencies.dot, ./graphs/coupling.dot
    """
    os.makedirs(out_dir, exist_ok=True)
    _graph_dependencies(project, os.path.join(out_dir, "dependencies.dot"))
    _graph_coupling(project, os.path.join(out_dir, "coupling.dot"))


def _graph_dependencies(project: Project, path: str) -> None:
    """Generate dependency graph DOT file.

    Args:
        project: Project with modules and dependencies
        path: Output DOT file path

    Note:
        Modules are shown as boxes, external packages (pkg:/npm:) as ellipses.
    """
    try:
        from graphviz import Digraph

        g = Digraph("deps", graph_attr={"rankdir": "LR"})
        seen = set()
        for m in project.modules.values():
            g.node(m.id, label=m.name, shape="box")
        for e in project.dependencies:
            for node in (e.source, e.target):
                if node.startswith("pkg:") or node.startswith("npm:"):
                    if node not in seen:
                        g.node(node, label=node, shape="ellipse")
                        seen.add(node)
            g.edge(e.source, e.target, label=str(e.weight))
        g.save(filename=path)
        try:
            g.render(filename=path, format="svg", cleanup=False)
            logger.info(f"Rendered dependency graph to {path}.svg")
        except Exception as e:
            logger.debug(f"Could not render SVG (graphviz not installed?): {e}")
    except ImportError:
        logger.debug("graphviz not installed, creating minimal DOT file")
        with open(path, "w", encoding="utf-8") as f:
            f.write("digraph deps { rankdir=LR; }")
    except Exception as e:
        logger.warning(f"Failed to create dependency graph: {e}")
        with open(path, "w", encoding="utf-8") as f:
            f.write("digraph deps { rankdir=LR; }")


def _graph_coupling(project: Project, path: str) -> None:
    """Generate temporal coupling graph DOT file.

    Args:
        project: Project with coupling edges
        path: Output DOT file path

    Note:
        Undirected graph showing files frequently changed together.
    """
    try:
        from graphviz import Graph

        g = Graph("coupling", graph_attr={"overlap": "scale"})
        for e in project.coupling:
            g.edge(e.a, e.b, label=str(e.weight))
        g.save(filename=path)
        try:
            g.render(filename=path, format="svg", cleanup=False)
            logger.info(f"Rendered coupling graph to {path}.svg")
        except Exception as e:
            logger.debug(f"Could not render SVG (graphviz not installed?): {e}")
    except ImportError:
        logger.debug("graphviz not installed, creating minimal DOT file")
        with open(path, "w", encoding="utf-8") as f:
            f.write("graph coupling {}")
    except Exception as e:
        logger.warning(f"Failed to create coupling graph: {e}")
        with open(path, "w", encoding="utf-8") as f:
            f.write("graph coupling {}")
