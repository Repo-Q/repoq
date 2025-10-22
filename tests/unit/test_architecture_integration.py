"""Tests for architecture integration into Q-score.

Verifies that architecture violations affect quality score.
"""

import pytest

from repoq.analyzers.architecture import (
    ArchitectureAnalyzer,
    ArchitectureMetrics,
    ArchitectureModel,
    CircularDependency,
    Component,
    Layer,
    LayeringViolation,
    C4Model,
    C4System,
    generate_architecture_recommendations,
)
from repoq.core.model import File, Project
from repoq.quality import compute_quality_score


def test_clean_architecture_bonus():
    """Test that clean architecture gets +10 bonus."""
    # Create project with no violations
    files = {
        "repoq/cli.py": File(
            id="repo:file:repoq/cli.py",
            path="repoq/cli.py",
            language="python",
            lines_of_code=100,
            complexity=5.0,
        ),
    }
    project = Project(id="test", name="Test", files=files)

    # Create clean architecture model (no violations)
    arch_model = ArchitectureModel(
        layers=[Layer(name="Presentation", files=["repoq/cli.py"], depends_on=[])],
        components=[Component(name="CLI", files=["repoq/cli.py"])],
        layering_violations=[],  # No violations
        circular_dependencies=[],  # No circular deps
        metrics=ArchitectureMetrics(
            cohesion=0.8,
            coupling=0.2,
            instability={"CLI": 0.5},
            abstractness={"CLI": 0.0},
            distance_from_main_sequence={"CLI": 0.5},
        ),
        c4_model=C4Model(system=C4System(name="Test", description="Test", type="System")),
    )

    # Compute Q-score with architecture
    score_with_arch = compute_quality_score(project, arch_model=arch_model)
    score_without_arch = compute_quality_score(project, arch_model=None)

    # Should get +10 bonus for clean architecture
    assert score_with_arch.score > score_without_arch.score
    assert abs(score_with_arch.score - score_without_arch.score - 10.0) < 0.1


def test_layering_violation_penalty():
    """Test that layering violations reduce Q-score."""
    files = {
        "repoq/cli.py": File(
            id="repo:file:repoq/cli.py",
            path="repoq/cli.py",
            language="python",
            lines_of_code=100,
            complexity=5.0,
        ),
    }
    project = Project(id="test", name="Test", files=files)

    # Create architecture model with violations
    arch_model = ArchitectureModel(
        layers=[Layer(name="Presentation", files=["repoq/cli.py"], depends_on=[])],
        components=[Component(name="CLI", files=["repoq/cli.py"])],
        layering_violations=[
            LayeringViolation(
                file="repoq/core/model.py",
                imported_file="repoq/cli.py",
                rule="Data must not import from Presentation",
                severity="high",
            )
        ],
        circular_dependencies=[],
        metrics=ArchitectureMetrics(
            cohesion=0.8,
            coupling=0.2,
            instability={"CLI": 0.5},
            abstractness={"CLI": 0.0},
            distance_from_main_sequence={"CLI": 0.5},
        ),
        c4_model=C4Model(system=C4System(name="Test", description="Test", type="System")),
    )

    # Compute Q-score with architecture violations
    score_with_violations = compute_quality_score(project, arch_model=arch_model)
    score_without_arch = compute_quality_score(project, arch_model=None)

    # Should get -5 penalty for violation
    assert score_with_violations.score < score_without_arch.score
    assert abs(score_without_arch.score - score_with_violations.score - 5.0) < 0.1


def test_circular_dependency_penalty():
    """Test that circular dependencies reduce Q-score."""
    files = {
        "repoq/a.py": File(
            id="repo:file:repoq/a.py",
            path="repoq/a.py",
            language="python",
            lines_of_code=50,
            complexity=5.0,
        ),
    }
    project = Project(id="test", name="Test", files=files)

    # Create architecture model with circular dependency
    arch_model = ArchitectureModel(
        layers=[Layer(name="Infrastructure", files=["repoq/a.py"], depends_on=[])],
        components=[Component(name="Core", files=["repoq/a.py"])],
        layering_violations=[],
        circular_dependencies=[
            CircularDependency(
                cycle=["repoq/a.py", "repoq/b.py", "repoq/a.py"], severity="high"
            )
        ],
        metrics=ArchitectureMetrics(
            cohesion=0.8,
            coupling=0.2,
            instability={"Core": 0.5},
            abstractness={"Core": 0.0},
            distance_from_main_sequence={"Core": 0.5},
        ),
        c4_model=C4Model(system=C4System(name="Test", description="Test", type="System")),
    )

    # Compute Q-score with circular dependency
    score_with_circular = compute_quality_score(project, arch_model=arch_model)
    score_without_arch = compute_quality_score(project, arch_model=None)

    # Should get -5 penalty for circular dependency
    assert score_with_circular.score < score_without_arch.score
    assert abs(score_without_arch.score - score_with_circular.score - 5.0) < 0.1


def test_multiple_violations_cumulative():
    """Test that multiple violations have cumulative penalties."""
    files = {
        "repoq/cli.py": File(
            id="repo:file:repoq/cli.py",
            path="repoq/cli.py",
            language="python",
            lines_of_code=100,
            complexity=5.0,
        ),
    }
    project = Project(id="test", name="Test", files=files)

    # Create architecture model with 2 layering violations + 1 circular
    arch_model = ArchitectureModel(
        layers=[Layer(name="Presentation", files=["repoq/cli.py"], depends_on=[])],
        components=[Component(name="CLI", files=["repoq/cli.py"])],
        layering_violations=[
            LayeringViolation(
                file="repoq/core/model.py",
                imported_file="repoq/cli.py",
                rule="Data → Presentation",
                severity="high",
            ),
            LayeringViolation(
                file="repoq/core/utils.py",
                imported_file="repoq/cli.py",
                rule="Infrastructure → Presentation",
                severity="medium",
            ),
        ],
        circular_dependencies=[
            CircularDependency(cycle=["repoq/a.py", "repoq/b.py", "repoq/a.py"], severity="high")
        ],
        metrics=ArchitectureMetrics(
            cohesion=0.8,
            coupling=0.2,
            instability={"CLI": 0.5},
            abstractness={"CLI": 0.0},
            distance_from_main_sequence={"CLI": 0.5},
        ),
        c4_model=C4Model(system=C4System(name="Test", description="Test", type="System")),
    )

    # Compute Q-score with multiple violations
    score_with_violations = compute_quality_score(project, arch_model=arch_model)
    score_without_arch = compute_quality_score(project, arch_model=None)

    # Should get -15 total penalty (2×5 for violations + 1×5 for circular)
    penalty = score_without_arch.score - score_with_violations.score
    assert penalty >= 10.0  # At least -10 (could be capped)
    assert penalty <= 25.0  # Max -15 violations + max -10 circular


def test_generate_architecture_recommendations_layering():
    """Test generating recommendations for layering violations."""
    arch_model = ArchitectureModel(
        layers=[],
        components=[],
        layering_violations=[
            LayeringViolation(
                file="repoq/core/model.py",
                imported_file="repoq/cli.py",
                rule="Data must not import from Presentation",
                severity="high",
            )
        ],
        circular_dependencies=[],
        metrics=ArchitectureMetrics(
            cohesion=0.8,
            coupling=0.2,
            instability={},
            abstractness={},
            distance_from_main_sequence={},
        ),
        c4_model=C4Model(system=C4System(name="Test", description="Test", type="System")),
    )

    recommendations = generate_architecture_recommendations(arch_model, "repo:test")

    # Should have 1 recommendation for layering violation
    assert len(recommendations) >= 1

    rec = recommendations[0]
    assert "layering violation" in rec["title"].lower()
    assert rec["priority"] in ["high", "medium"]
    assert rec["delta_q"] > 0
    assert rec["category"] == "architecture"
    assert rec["violation_type"] == "layering_violation"


def test_generate_architecture_recommendations_circular():
    """Test generating recommendations for circular dependencies."""
    arch_model = ArchitectureModel(
        layers=[],
        components=[],
        layering_violations=[],
        circular_dependencies=[
            CircularDependency(
                cycle=["repoq/a.py", "repoq/b.py", "repoq/c.py", "repoq/a.py"], severity="high"
            )
        ],
        metrics=ArchitectureMetrics(
            cohesion=0.8,
            coupling=0.2,
            instability={},
            abstractness={},
            distance_from_main_sequence={},
        ),
        c4_model=C4Model(system=C4System(name="Test", description="Test", type="System")),
    )

    recommendations = generate_architecture_recommendations(arch_model, "repo:test")

    # Should have 1 recommendation for circular dependency
    assert len(recommendations) >= 1

    rec = recommendations[0]
    assert "circular dependency" in rec["title"].lower()
    assert rec["priority"] in ["high", "medium"]
    assert rec["delta_q"] > 0
    assert rec["category"] == "architecture"
    assert rec["violation_type"] == "circular_dependency"


def test_generate_architecture_recommendations_high_coupling():
    """Test generating recommendations for high coupling."""
    arch_model = ArchitectureModel(
        layers=[],
        components=[],
        layering_violations=[],
        circular_dependencies=[],
        metrics=ArchitectureMetrics(
            cohesion=0.8,
            coupling=0.2,
            instability={"Analyzers": 0.9},  # High instability > 0.8
            abstractness={"Analyzers": 0.0},
            distance_from_main_sequence={"Analyzers": 0.9},
        ),
        c4_model=C4Model(system=C4System(name="Test", description="Test", type="System")),
    )

    recommendations = generate_architecture_recommendations(arch_model, "repo:test")

    # Should have 1 recommendation for high coupling
    assert len(recommendations) >= 1

    rec = recommendations[0]
    assert "coupling" in rec["title"].lower() or "instability" in rec["description"].lower()
    assert rec["priority"] == "medium"
    assert rec["delta_q"] > 0
    assert rec["category"] == "architecture"
    assert rec["violation_type"] == "high_coupling"
