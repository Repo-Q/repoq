from __future__ import annotations
from ..core.model import Project

def render_markdown(p: Project) -> str:
    lines = []
    lines.append(f"# {p.name} — RepoQ Report")
    langs = ", ".join(f"{k} ({v} LOC)" for k,v in p.programming_languages.items()) or "-"
    lines.append(f"*Languages:* {langs}")
    lines.append(f"*Modules:* {len(p.modules)}   *Files:* {len(p.files)}   *CI:* {'yes' if p.ci_configured else 'no'}")
    lines.append("")
    lines.append("## Top Hotspots")
    top = sorted(p.files.values(), key=lambda x: (x.hotness or 0), reverse=True)[:20]
    for f in top:
        lines.append(f"- `{f.path}`  hotness={f.hotness}  churn={f.code_churn}  cplx={f.complexity}")
    lines.append("")
    lines.append("## Top Authors")
    topa = sorted(p.contributors.items(), key=lambda kv: kv[1].get('commits',0), reverse=True)[:10]
    for aid, stats in topa:
        lines.append(f"- {aid}: commits={stats.get('commits',0)} +{stats.get('linesAdded',0)} -{stats.get('linesDeleted',0)}")
    return "\n".join(lines) + "\n"
