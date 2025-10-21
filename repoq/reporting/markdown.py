"""Markdown report generation module.

This module generates human-readable Markdown reports from Project analysis
results, including:
- Repository metadata and statistics
- Programming language distribution
- Top contributors by commit count
- Hotspot files with risk scores
- Code quality issues (TODO/FIXME/Deprecated)
- Test execution results

Uses Jinja2 templating for flexible report customization.
"""

from __future__ import annotations

import logging

from jinja2 import Template

from ..core.model import Project

logger = logging.getLogger(__name__)

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
    """Generate Markdown report from Project analysis results.

    Creates a formatted Markdown document with sections for:
    - Repository overview (name, URL, license, CI)
    - Language statistics (LOC per language)
    - Top 10 contributors by commit count
    - Top 15 hotspot files with risk metrics
    - Code quality markers (TODO/FIXME/Deprecated)
    - Test results (up to 20 most recent)

    Args:
        project: Project model with analysis results

    Returns:
        Formatted Markdown string ready for file output

    Example:
        >>> project = Project(id="repo:test", name="Test Project")
        >>> md = render_markdown(project)
        >>> print(md[:50])
        '\\n# Репозиторий: **Test Project**\\n...'
    """
    try:
        return TEMPLATE.render(p=project)
    except Exception as e:
        logger.error(f"Failed to render Markdown template: {e}")
        raise
