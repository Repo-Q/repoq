from __future__ import annotations

import os

from ..core.model import Project


def export_graphs(project: Project, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    _graph_dependencies(project, os.path.join(out_dir, "dependencies.dot"))
    _graph_coupling(project, os.path.join(out_dir, "coupling.dot"))


def _graph_dependencies(project: Project, path: str) -> None:
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
        except Exception:
            pass
    except Exception:
        with open(path, "w", encoding="utf-8") as f:
            f.write("digraph deps { rankdir=LR; }")


def _graph_coupling(project: Project, path: str) -> None:
    try:
        from graphviz import Graph

        g = Graph("coupling", graph_attr={"overlap": "scale"})
        for e in project.coupling:
            g.edge(e.a, e.b, label=str(e.weight))
        g.save(filename=path)
        try:
            g.render(filename=path, format="svg", cleanup=False)
        except Exception:
            pass
    except Exception:
        with open(path, "w", encoding="utf-8") as f:
            f.write("graph coupling {}")
