from __future__ import annotations

from jinja2 import Template

from ..core.model import Project

TEMPLATE = Template(
    """
# Репозиторий: **{{ p.name }}**

**URL**: {{ p.repository_url or '-' }}  
**Лицензия**: {{ p.license or '-' }}  
**Дата последнего коммита**: {{ p.last_commit_date or '-' }}  
**CI**: {{ p.ci_configured|join(', ') if p.ci_configured else '-' }}

## Языки (LOC)
{% for lang, loc in p.programming_languages.items() -%}
- {{ lang }}: {{ loc }}
{% endfor %}

## Топ авторов (по коммитам)
{% set top_authors = (p.contributors.values()|list|sort(attribute='commits', reverse=True)) -%}
{% for person in top_authors -%}
{% if loop.index <= 10 -%}
- {{ person.name }} — {{ person.commits }} коммитов
{% endif -%}
{% endfor %}

## Hotspots
{% set hotspots = (p.files.values()|list|sort(attribute='hotness', reverse=True)) -%}
{% for f in hotspots -%}
{% if loop.index <= 15 and f.hotness and f.hotness > 0 -%}
- {{ f.path }} — score={{ '%.3f'|format(f.hotness or 0) }}, LOC={{ f.lines_of_code }}, churn={{ f.code_churn }}, cplx={{ f.complexity or '-' }}
{% endif -%}
{% endfor %}

## TODO/FIXME/Deprecated
{% for issue in p.issues.values() -%}
{% if 'TodoComment' in issue.type or 'Deprecated' in issue.type -%}
- {{ issue.file_id }} — {{ issue.description }}
{% endif -%}
{% else %}
Нет найденных пометок.
{% endfor %}

## Тесты (JUnit → OSLC QM)
{% set test_results = (p.tests_results|list) -%}
Всего результатов: {{ test_results|length }}
{% for tr in test_results -%}
{% if loop.index <= 20 -%}
- {{ tr.testcase }} — {{ tr.status }} ({{ tr.time or '-' }}s)
{% endif -%}
{% endfor %}
"""
)


def render_markdown(project: Project) -> str:
    return TEMPLATE.render(p=project)
