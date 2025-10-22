"""E2E tests for refactor-plan command."""

from pathlib import Path

from typer.testing import CliRunner

from repoq.cli import app

runner = CliRunner()


def test_refactor_plan_help():
    """Test refactor-plan command help output."""
    result = runner.invoke(app, ["refactor-plan", "--help"])
    assert result.exit_code == 0
    assert "Generate actionable refactoring plan" in result.output
    assert "PCE (Proof of Correct Execution)" in result.output
    assert "--top-k" in result.output
    assert "--format" in result.output


def test_refactor_plan_missing_file():
    """Test refactor-plan with missing analysis file."""
    result = runner.invoke(app, ["refactor-plan", "nonexistent.jsonld"])
    assert result.exit_code == 2
    assert "not found" in result.output


def test_refactor_plan_with_baseline(tmp_path):
    """Test refactor-plan with baseline data (if exists)."""
    baseline = Path("baseline-quality.jsonld")

    if baseline.exists():
        # Test markdown format
        result = runner.invoke(app, ["refactor-plan", str(baseline), "--top-k", "3"])
        assert result.exit_code == 0
        assert (
            "Generating refactoring plan" in result.output
            or "No refactoring needed" in result.output
        )

        # Test JSON format
        output_json = tmp_path / "tasks.json"
        result = runner.invoke(
            app, ["refactor-plan", str(baseline), "--format", "json", "-o", str(output_json)]
        )
        assert result.exit_code == 0
        if output_json.exists():
            import json

            data = json.loads(output_json.read_text())
            assert "tasks" in data
            assert "baseline_q" in data
            assert "projected_q" in data
