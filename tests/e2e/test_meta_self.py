"""E2E tests for `repoq meta-self` command.

Smoke tests for self-analysis functionality.
"""

from __future__ import annotations

from typer.testing import CliRunner

from repoq.cli import app

runner = CliRunner()


def test_meta_self_help():
    """Test meta-self command shows help."""
    result = runner.invoke(app, ["meta-self", "--help"])

    assert result.exit_code == 0
    assert "meta" in result.stdout.lower() or "self" in result.stdout.lower()


def test_meta_self_basic_structure():
    """Test meta-self command exists and has proper structure."""
    # Just test that command is registered properly
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "meta-self" in result.stdout or "meta_self" in result.stdout
