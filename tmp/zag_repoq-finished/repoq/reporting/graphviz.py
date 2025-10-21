from __future__ import annotations
import os
from graphviz import Graph
from ..core.model import Project

def export_graphs(p: Project, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    g = Graph("coupling", format="svg")
    nodes = set()
    for e in p.coupling:
        nodes.add(e.a); nodes.add(e.b)
    for n in nodes: g.node(n, label=n.split(":")[-1])
    for e in p.coupling: g.edge(e.a, e.b, label=str(int(e.weight)))
    g.render(filename=os.path.join(out_dir, "coupling"), cleanup=True)
