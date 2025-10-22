"""E2E tests for `repoq verify` command.

Smoke tests for W3C VC verification functionality.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from repoq.cli import app


runner = CliRunner()


@pytest.fixture
def valid_vc_file(tmp_path: Path) -> Path:
    """Create minimal valid W3C VC structure."""
    vc = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", "QualityAssessmentCredential"],
        "issuer": "did:repoq:v1",
        "issuanceDate": "2025-01-01T00:00:00Z",
        "credentialSubject": {
            "@id": "https://github.com/user/repo",
            "qualityScore": 85.0,
        },
        "proof": {
            "type": "EcdsaSecp256k1Signature2019",
            "created": "2025-01-01T00:00:00Z",
            "proofPurpose": "assertionMethod",
            "verificationMethod": "did:repoq:v1#key-1",
            "jws": "eyJhbGciOiJFUzI1NksifQ.eyJzdWJqZWN0Ijp7ImlkIjoicmVwbyJ9fQ.VALID_SIG",
        },
    }
    
    vc_file = tmp_path / "valid_vc.json"
    with open(vc_file, "w") as f:
        json.dump(vc, f, indent=2)
    
    return vc_file


@pytest.fixture
def malformed_vc_file(tmp_path: Path) -> Path:
    """Create malformed VC missing required fields."""
    vc = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        # Missing "type", "issuanceDate", "proof"
        "issuer": "did:repoq:v1",
        "credentialSubject": {"qualityScore": 85.0},
    }
    
    vc_file = tmp_path / "malformed_vc.json"
    with open(vc_file, "w") as f:
        json.dump(vc, f, indent=2)
    
    return vc_file


def test_verify_help():
    """Test verify command shows help."""
    result = runner.invoke(app, ["verify", "--help"])
    
    assert result.exit_code == 0
    assert "verify" in result.stdout.lower() or "credential" in result.stdout.lower()


def test_verify_malformed_vc(malformed_vc_file: Path):
    """Test verify command with malformed VC."""
    result = runner.invoke(app, ["verify", str(malformed_vc_file)])
    
    # Should fail due to structure validation
    assert result.exit_code in [1, 2]


def test_verify_file_not_found():
    """Test verify command with non-existent file."""
    result = runner.invoke(app, ["verify", "/nonexistent/vc.json"])
    
    assert result.exit_code == 2
    assert "not found" in result.stdout.lower() or "❌" in result.stdout


