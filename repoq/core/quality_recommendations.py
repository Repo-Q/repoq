"""
Quality recommendations RDF export module.

Генерирует quality:Recommendation triples на основе ΔQ calculation из refactoring.py.
Включает приоритизацию и linking к затронутым файлам/функциям.
"""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

from rdflib import RDF, Graph, Literal, Namespace, URIRef
from rdflib.namespace import XSD

from ..refactoring import RefactoringTask, generate_refactoring_plan
from .model import Project

# Namespaces
QUALITY_NS = "http://example.org/vocab/quality#"
REPO_NS = "http://example.org/vocab/repo#"


@dataclass
class QualityRecommendation:
    """Represents a single quality recommendation for RDF export."""

    id: str
    title: str
    description: str
    delta_q: Decimal
    priority: str  # critical, high, medium, low
    target_file: Optional[str] = None
    target_function: Optional[str] = None
    estimated_effort_hours: float = 1.0


def convert_refactoring_task_to_recommendation(
    task: RefactoringTask, project_id: str
) -> QualityRecommendation:
    """
    Convert RefactoringTask to QualityRecommendation for RDF export.

    Args:
        task: RefactoringTask from refactoring.py
        project_id: Project URI (e.g., "repo:repoq")

    Returns:
        QualityRecommendation instance
    """
    # Parse estimated effort
    effort_hours = _parse_effort_hours(task.estimated_effort)

    # Generate description from issues and recommendations
    description_parts = ["Issues: " + "; ".join(task.issues[:3])]
    if task.recommendations:
        description_parts.append("Recommendations: " + "; ".join(task.recommendations[:2]))

    description = " | ".join(description_parts)

    return QualityRecommendation(
        id=f"{project_id}/quality/recommendation_{task.id}",
        title=f"Refactor {Path(task.file_path).name}",
        description=description,
        delta_q=Decimal(str(task.delta_q)),
        priority=task.priority,
        target_file=task.file_path,
        estimated_effort_hours=effort_hours,
    )


def _parse_effort_hours(effort_str: str) -> float:
    """
    Parse effort string to hours.

    Args:
        effort_str: e.g., "15 min", "1 hour", "2-4 hours"

    Returns:
        Float hours

    Examples:
        >>> _parse_effort_hours("15 min")
        0.25
        >>> _parse_effort_hours("2-4 hours")
        3.0
    """
    effort_str = effort_str.lower()

    if "min" in effort_str:
        # Extract number before "min"
        import re

        match = re.search(r"(\d+)\s*min", effort_str)
        if match:
            return float(match.group(1)) / 60.0

    elif "hour" in effort_str:
        # Extract number(s) before "hour"
        import re

        # Handle ranges like "2-4 hours"
        range_match = re.search(r"(\d+)-(\d+)\s*hour", effort_str)
        if range_match:
            low = float(range_match.group(1))
            high = float(range_match.group(2))
            return (low + high) / 2.0

        # Handle single number like "1 hour"
        single_match = re.search(r"(\d+)\s*hour", effort_str)
        if single_match:
            return float(single_match.group(1))

    # Default fallback
    return 1.0


def export_recommendations_rdf(
    graph: Graph, recommendations: List[QualityRecommendation], project_id: str
) -> None:
    """
    Add quality recommendations to RDF graph.

    Args:
        graph: RDFLib Graph to add triples to
        recommendations: List of QualityRecommendation objects
        project_id: Project URI (e.g., "repo:repoq")

    Side Effects:
        Modifies `graph` in-place by adding triples
    """
    QUALITY = Namespace(QUALITY_NS)

    # Add namespace binding
    graph.bind("quality", QUALITY)

    for rec in recommendations:
        rec_uri = URIRef(rec.id)
        graph.add((rec_uri, RDF.type, QUALITY.Recommendation))
        graph.add((rec_uri, QUALITY.recommendationTitle, Literal(rec.title)))
        graph.add((rec_uri, QUALITY.recommendationDescription, Literal(rec.description)))

        # ΔQ (the key metric)
        graph.add((rec_uri, QUALITY.deltaQ, Literal(rec.delta_q, datatype=XSD.decimal)))

        # Priority
        graph.add((rec_uri, QUALITY.priority, Literal(rec.priority)))

        # Estimated effort
        graph.add(
            (
                rec_uri,
                QUALITY.estimatedEffortHours,
                Literal(rec.estimated_effort_hours, datatype=XSD.decimal),
            )
        )

        # Link to target file
        if rec.target_file:
            file_uri = URIRef(f"{project_id}/{rec.target_file}")
            graph.add((rec_uri, QUALITY.targetsFile, file_uri))

        # Link to target function (if available)
        if rec.target_function:
            function_uri = URIRef(f"{project_id}/{rec.target_file}/fn/{rec.target_function}")
            graph.add((rec_uri, QUALITY.targetsFunction, function_uri))


def generate_recommendations_from_project(
    project: Project, top_k: int = 10, min_delta_q: float = 3.0
) -> List[QualityRecommendation]:
    """
    Generate quality recommendations from project analysis.

    Args:
        project: Project model with analysis data
        top_k: Number of top recommendations to generate
        min_delta_q: Minimum ΔQ threshold

    Returns:
        List of QualityRecommendation objects, sorted by ΔQ descending

    Raises:
        ValueError: If project has no files or insufficient data
    """
    if not project.files:
        return []

    # Convert project to JSON-LD for refactoring.py
    import json
    from tempfile import NamedTemporaryFile

    from .jsonld import to_jsonld

    with NamedTemporaryFile(mode="w", suffix=".jsonld", delete=False) as tmp:
        jsonld_data = to_jsonld(project)
        json.dump(jsonld_data, tmp)
        tmp_path = tmp.name

    try:
        # Generate refactoring plan using existing algorithm
        plan = generate_refactoring_plan(tmp_path, top_k=top_k, min_delta_q=min_delta_q)

        # Convert tasks to recommendations
        recommendations = [
            convert_refactoring_task_to_recommendation(task, project.id) for task in plan.tasks
        ]

        # Sort by ΔQ descending
        recommendations.sort(key=lambda r: float(r.delta_q), reverse=True)

        return recommendations
    finally:
        # Cleanup temp file
        import os

        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _project_to_refactoring_input(project: Project) -> dict:
    """
    Convert Project model to dict format expected by refactoring.py.

    Args:
        project: Project model

    Returns:
        Dict with files array in JSON-LD-like structure
    """
    files_list = []

    for file in project.files.values():
        file_dict = {
            "@id": file.id,
            "@type": ["repo:File"],
            "path": file.path,
            "complexity": file.complexity or 0.0,
            "lines_of_code": file.lines_of_code or 0,
            "churn": getattr(file, "churn", 0),
            "last_modified": getattr(file, "last_modified", None),
        }

        # Add issues if available
        if hasattr(file, "issues"):
            file_dict["issues"] = file.issues

        files_list.append(file_dict)

    return {
        "@id": project.id,
        "@type": ["repo:Project"],
        "name": project.name,
        "files": files_list,
    }


def enrich_graph_with_quality_recommendations(
    graph: Graph,
    project: Project,
    top_k: int = 10,
    min_delta_q: float = 3.0,
) -> None:
    """
    High-level function to enrich RDF graph with quality recommendations.

    Args:
        graph: RDFLib Graph to enrich
        project: Project model with analysis data
        top_k: Number of top recommendations to generate (default: 10)
        min_delta_q: Minimum ΔQ threshold (default: 3.0)

    Side Effects:
        Modifies `graph` in-place by adding quality:Recommendation triples
    """
    # Generate recommendations
    recommendations = generate_recommendations_from_project(project, top_k, min_delta_q)

    # Export to RDF
    export_recommendations_rdf(graph, recommendations, project.id)
