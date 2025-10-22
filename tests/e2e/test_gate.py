"""E2E tests for `repoq gate` command.

Smoke tests for quality gate functionality.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest
from typer.testing import CliRunner

from repoq.cli import app


runner = CliRunner()


def test_gate_help():
    """Test gate command shows help."""
    result = runner.invoke(app, ["gate", "--help"])
    
    assert result.exit_code == 0
    assert "gate" in result.stdout.lower() or "quality" in result.stdout.lower()


def test_gate_with_mock_implementation():
    """Test gate command with mocked implementation."""
    # Simply test that command is registered and has correct signature
    result = runner.invoke(app, ["--help"])
    
    assert result.exit_code == 0
    assert "gate" in result.stdout


