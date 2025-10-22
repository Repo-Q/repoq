"""Tests for Certificate Store (W3C Verifiable Credentials).

TDD RED phase: Write failing tests first.

Tests cover:
- Certificate generation (W3C VC format)
- ECDSA signing (secp256k1)
- Save/load certificates
- Signature verification
- Tamper detection
- Timestamp validation
- Certificate listing
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization

from repoq.core.certificate_store import (
    Certificate,
    CertificateStore,
    InvalidSignatureError,
    TamperedCertificateError,
)
from repoq.quality import QualityMetrics


@pytest.fixture
def temp_cert_dir():
    """Create temporary certificate directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_metrics():
    """Sample QualityMetrics for testing."""
    return QualityMetrics(
        score=85.5,
        complexity=2.3,
        hotspots=5,
        todos=12,
        tests_coverage=0.82,
        grade="B",
        constraints_passed={"coverage": True, "todos": True, "hotspots": True},
    )


@pytest.fixture
def cert_store(temp_cert_dir):
    """CertificateStore instance with temp directory."""
    return CertificateStore(cert_dir=temp_cert_dir)


class TestCertificateGeneration:
    """Test W3C VC certificate generation."""

    def test_generate_certificate_w3c_format(self, cert_store, sample_metrics):
        """Certificate should follow W3C VC format."""
        cert = cert_store.generate_certificate(
            commit_sha="abc123",
            metrics=sample_metrics,
            policy_version="v1.0",
        )

        # W3C VC required fields
        assert cert.context == ["https://www.w3.org/2018/credentials/v1"]
        assert cert.type == ["VerifiableCredential", "QualityGateCertificate"]
        assert cert.issuer == "repoq:quality-gate"
        assert cert.issuance_date is not None

        # Credential subject
        assert cert.credential_subject["id"] == "commit:abc123"
        assert cert.credential_subject["quality_score"] == 85.5
        assert cert.credential_subject["policy_version"] == "v1.0"

    def test_generate_certificate_includes_all_metrics(self, cert_store, sample_metrics):
        """Certificate should include all QualityMetrics fields."""
        cert = cert_store.generate_certificate(
            commit_sha="abc123",
            metrics=sample_metrics,
            policy_version="v1.0",
        )

        subject = cert.credential_subject
        assert subject["quality_score"] == 85.5
        assert subject["complexity"] == 2.3
        assert subject["hotspots"] == 5
        assert subject["todos"] == 12
        assert subject["tests_coverage"] == 0.82
        assert subject["grade"] == "B"
        assert subject["constraints_passed"] == {
            "coverage": True,
            "todos": True,
            "hotspots": True,
        }

    def test_generate_certificate_timestamp_rfc3339(self, cert_store, sample_metrics):
        """Issuance date should be valid RFC3339 timestamp."""
        cert = cert_store.generate_certificate(
            commit_sha="abc123",
            metrics=sample_metrics,
            policy_version="v1.0",
        )

        # Parse timestamp (should not raise)
        timestamp = datetime.fromisoformat(cert.issuance_date.replace("Z", "+00:00"))
        assert timestamp.tzinfo is not None  # Must have timezone

        # Should be recent (within last minute)
        now = datetime.now(timezone.utc)
        delta = (now - timestamp).total_seconds()
        assert delta < 60  # Less than 1 minute old


class TestECDSASigning:
    """Test ECDSA signature generation and verification."""

    def test_sign_certificate_creates_proof(self, cert_store, sample_metrics):
        """Signing should add proof object to certificate."""
        cert = cert_store.generate_certificate(
            commit_sha="abc123",
            metrics=sample_metrics,
            policy_version="v1.0",
        )

        signed_cert = cert_store.sign_certificate(cert)

        assert signed_cert.proof is not None
        assert signed_cert.proof["type"] == "EcdsaSecp256k1Signature2019"
        assert signed_cert.proof["created"] is not None
        assert signed_cert.proof["verificationMethod"] is not None
        assert signed_cert.proof["proofValue"] is not None

    def test_sign_certificate_proof_value_is_hex(self, cert_store, sample_metrics):
        """Proof value should be hex-encoded ECDSA signature."""
        cert = cert_store.generate_certificate(
            commit_sha="abc123",
            metrics=sample_metrics,
            policy_version="v1.0",
        )

        signed_cert = cert_store.sign_certificate(cert)
        proof_value = signed_cert.proof["proofValue"]

        # Should be hex string (even length, valid hex chars)
        assert len(proof_value) % 2 == 0
        assert all(c in "0123456789abcdef" for c in proof_value.lower())
        assert len(proof_value) >= 128  # ECDSA signature ~64 bytes = 128 hex chars

    def test_verify_signature_valid_cert(self, cert_store, sample_metrics):
        """Verify should return True for valid signature."""
        cert = cert_store.generate_certificate(
            commit_sha="abc123",
            metrics=sample_metrics,
            policy_version="v1.0",
        )
        signed_cert = cert_store.sign_certificate(cert)

        assert cert_store.verify_signature(signed_cert) is True

    def test_verify_signature_tampered_cert_fails(self, cert_store, sample_metrics):
        """Verify should detect tampered certificate."""
        cert = cert_store.generate_certificate(
            commit_sha="abc123",
            metrics=sample_metrics,
            policy_version="v1.0",
        )
        signed_cert = cert_store.sign_certificate(cert)

        # Tamper with score
        signed_cert.credential_subject["quality_score"] = 99.9

        with pytest.raises(TamperedCertificateError):
            cert_store.verify_signature(signed_cert)

    def test_verify_signature_invalid_signature_fails(self, cert_store, sample_metrics):
        """Verify should reject invalid signature."""
        cert = cert_store.generate_certificate(
            commit_sha="abc123",
            metrics=sample_metrics,
            policy_version="v1.0",
        )
        signed_cert = cert_store.sign_certificate(cert)

        # Corrupt signature
        signed_cert.proof["proofValue"] = "deadbeef" * 16

        with pytest.raises(InvalidSignatureError):
            cert_store.verify_signature(signed_cert)


class TestCertificatePersistence:
    """Test save/load certificates to disk."""

    def test_save_certificate_creates_file(self, cert_store, sample_metrics):
        """Save should create JSON-LD file in .repoq/certificates/."""
        cert = cert_store.generate_certificate(
            commit_sha="abc123",
            metrics=sample_metrics,
            policy_version="v1.0",
        )
        signed_cert = cert_store.sign_certificate(cert)

        path = cert_store.save_certificate(signed_cert, commit_sha="abc123")

        assert path.exists()
        assert path.name == "abc123.json"
        # Parent could be temp dir or 'certificates'
        assert "abc123.json" in str(path)

    def test_save_certificate_valid_json_ld(self, cert_store, sample_metrics):
        """Saved file should be valid JSON-LD."""
        cert = cert_store.generate_certificate(
            commit_sha="abc123",
            metrics=sample_metrics,
            policy_version="v1.0",
        )
        signed_cert = cert_store.sign_certificate(cert)
        path = cert_store.save_certificate(signed_cert, commit_sha="abc123")

        with open(path, "r") as f:
            data = json.load(f)

        # Valid JSON-LD structure
        assert "@context" in data
        assert "type" in data
        assert "credentialSubject" in data
        assert "proof" in data

    def test_load_certificate_returns_cert(self, cert_store, sample_metrics):
        """Load should return Certificate object."""
        cert = cert_store.generate_certificate(
            commit_sha="abc123",
            metrics=sample_metrics,
            policy_version="v1.0",
        )
        signed_cert = cert_store.sign_certificate(cert)
        cert_store.save_certificate(signed_cert, commit_sha="abc123")

        loaded_cert = cert_store.load_certificate(commit_sha="abc123")

        assert loaded_cert.credential_subject["id"] == "commit:abc123"
        assert loaded_cert.credential_subject["quality_score"] == 85.5
        assert loaded_cert.proof is not None

    def test_load_certificate_missing_raises(self, cert_store):
        """Load should raise FileNotFoundError for missing cert."""
        with pytest.raises(FileNotFoundError):
            cert_store.load_certificate(commit_sha="nonexistent")

    def test_load_certificate_verifies_signature(self, cert_store, sample_metrics):
        """Load should automatically verify signature."""
        cert = cert_store.generate_certificate(
            commit_sha="abc123",
            metrics=sample_metrics,
            policy_version="v1.0",
        )
        signed_cert = cert_store.sign_certificate(cert)
        path = cert_store.save_certificate(signed_cert, commit_sha="abc123")

        # Tamper with file on disk
        with open(path, "r") as f:
            data = json.load(f)
        data["credentialSubject"]["quality_score"] = 99.9
        with open(path, "w") as f:
            json.dump(data, f)

        # Load should detect tampering
        with pytest.raises(TamperedCertificateError):
            cert_store.load_certificate(commit_sha="abc123")


class TestCertificateListing:
    """Test certificate listing and querying."""

    def test_list_certificates_empty(self, cert_store):
        """List should return empty list for new store."""
        certs = cert_store.list_certificates()
        assert certs == []

    def test_list_certificates_returns_all(self, cert_store, sample_metrics):
        """List should return all saved certificates."""
        # Save 3 certificates
        for sha in ["abc123", "def456", "ghi789"]:
            cert = cert_store.generate_certificate(
                commit_sha=sha,
                metrics=sample_metrics,
                policy_version="v1.0",
            )
            signed_cert = cert_store.sign_certificate(cert)
            cert_store.save_certificate(signed_cert, commit_sha=sha)

        certs = cert_store.list_certificates()
        assert len(certs) == 3
        shas = {cert.credential_subject["id"].split(":")[1] for cert in certs}
        assert shas == {"abc123", "def456", "ghi789"}

    def test_list_certificates_sorted_by_date(self, cert_store, sample_metrics):
        """List should return certificates sorted by date (newest first)."""
        import time

        shas = ["old", "middle", "new"]
        for sha in shas:
            cert = cert_store.generate_certificate(
                commit_sha=sha,
                metrics=sample_metrics,
                policy_version="v1.0",
            )
            signed_cert = cert_store.sign_certificate(cert)
            cert_store.save_certificate(signed_cert, commit_sha=sha)
            time.sleep(0.1)  # Ensure different timestamps

        certs = cert_store.list_certificates()
        commit_shas = [cert.credential_subject["id"].split(":")[1] for cert in certs]
        assert commit_shas == ["new", "middle", "old"]


class TestCertificateDataclass:
    """Test Certificate dataclass."""

    def test_certificate_to_dict(self, cert_store, sample_metrics):
        """Certificate should convert to dict for JSON serialization."""
        cert = cert_store.generate_certificate(
            commit_sha="abc123",
            metrics=sample_metrics,
            policy_version="v1.0",
        )

        cert_dict = cert.to_dict()

        assert isinstance(cert_dict, dict)
        assert cert_dict["@context"] == ["https://www.w3.org/2018/credentials/v1"]
        assert cert_dict["credentialSubject"]["id"] == "commit:abc123"

    def test_certificate_from_dict(self):
        """Certificate should reconstruct from dict."""
        data = {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["VerifiableCredential", "QualityGateCertificate"],
            "issuer": "repoq:quality-gate",
            "issuanceDate": "2025-10-22T10:00:00Z",
            "credentialSubject": {
                "id": "commit:abc123",
                "quality_score": 85.5,
                "policy_version": "v1.0",
            },
            "proof": {
                "type": "EcdsaSecp256k1Signature2019",
                "created": "2025-10-22T10:00:00Z",
                "verificationMethod": "repoq:key:secp256k1",
                "proofValue": "deadbeef",
            },
        }

        cert = Certificate.from_dict(data)

        assert cert.context == ["https://www.w3.org/2018/credentials/v1"]
        assert cert.credential_subject["id"] == "commit:abc123"
        assert cert.proof["proofValue"] == "deadbeef"


class TestCertificateStoreKeyManagement:
    """Test private key generation and persistence."""

    def test_new_store_generates_keypair(self, temp_cert_dir):
        """New CertificateStore should generate ECDSA keypair."""
        store = CertificateStore(cert_dir=temp_cert_dir)

        assert store._private_key is not None
        assert store._public_key is not None

    def test_store_persists_private_key(self, temp_cert_dir):
        """Private key should be saved to disk."""
        CertificateStore(cert_dir=temp_cert_dir)

        key_file = temp_cert_dir / ".private_key.pem"
        assert key_file.exists()

    def test_store_loads_existing_key(self, temp_cert_dir):
        """Store should load existing private key on second init."""
        store1 = CertificateStore(cert_dir=temp_cert_dir)
        pub_key_1 = store1._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        # Create new store instance (should load same key)
        store2 = CertificateStore(cert_dir=temp_cert_dir)
        pub_key_2 = store2._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        assert pub_key_1 == pub_key_2
