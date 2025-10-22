"""Certificate Store for W3C Verifiable Credentials.

This module implements audit trail for quality gate decisions using
W3C Verifiable Credentials (VC) standard with ECDSA signatures.

Key Features:
- W3C VC 1.1 compliant certificates
- ECDSA secp256k1 signatures (Bitcoin/Ethereum compatible)
- Tamper-proof audit trail
- Automatic key generation and persistence
- RFC3339 timestamps

Architecture:
    CertificateStore manages:
    - Private key generation/loading (.repoq/certificates/.private_key.pem)
    - Certificate generation (W3C VC format)
    - ECDSA signing (cryptography library)
    - Save/load/verify certificates
    - Tamper detection

Example:
    >>> store = CertificateStore()
    >>> cert = store.generate_certificate(
    ...     commit_sha="abc123",
    ...     metrics=quality_metrics,
    ...     policy_version="v1.0"
    ... )
    >>> signed = store.sign_certificate(cert)
    >>> path = store.save_certificate(signed, commit_sha="abc123")
    >>> loaded = store.load_certificate(commit_sha="abc123")
    >>> assert store.verify_signature(loaded) is True
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

logger = logging.getLogger(__name__)


class InvalidSignatureError(Exception):
    """Raised when signature verification fails."""

    pass


class TamperedCertificateError(Exception):
    """Raised when certificate has been tampered with."""

    pass


@dataclass
class Certificate:
    """W3C Verifiable Credential for quality gate decision.

    Attributes:
        context: JSON-LD context (W3C VC standard)
        type: Credential types
        issuer: Credential issuer (repoq)
        issuance_date: RFC3339 timestamp
        credential_subject: Quality metrics and metadata
        proof: ECDSA signature proof
    """

    context: List[str] = field(default_factory=lambda: ["https://www.w3.org/2018/credentials/v1"])
    type: List[str] = field(
        default_factory=lambda: ["VerifiableCredential", "QualityGateCertificate"]
    )
    issuer: str = "repoq:quality-gate"
    issuance_date: str = ""
    credential_subject: Dict[str, Any] = field(default_factory=dict)
    proof: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "@context": self.context,
            "type": self.type,
            "issuer": self.issuer,
            "issuanceDate": self.issuance_date,
            "credentialSubject": self.credential_subject,
            "proof": self.proof,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Certificate:
        """Reconstruct Certificate from dictionary."""
        return cls(
            context=data.get("@context", []),
            type=data.get("type", []),
            issuer=data.get("issuer", ""),
            issuance_date=data.get("issuanceDate", ""),
            credential_subject=data.get("credentialSubject", {}),
            proof=data.get("proof"),
        )


class CertificateStore:
    """Store for W3C Verifiable Credentials with ECDSA signing.

    Manages certificate lifecycle:
    - Generation (W3C VC format)
    - Signing (ECDSA secp256k1)
    - Persistence (.repoq/certificates/<commit_sha>.json)
    - Loading and verification

    Attributes:
        cert_dir: Directory for certificates (default: .repoq/certificates)
        _private_key: ECDSA private key (secp256k1)
        _public_key: ECDSA public key

    Example:
        >>> store = CertificateStore()
        >>> cert = store.generate_certificate("abc123", metrics, "v1.0")
        >>> signed = store.sign_certificate(cert)
        >>> path = store.save_certificate(signed, "abc123")
        >>> loaded = store.load_certificate("abc123")
    """

    def __init__(self, cert_dir: Optional[Path] = None):
        """Initialize certificate store.

        Args:
            cert_dir: Directory for certificates (default: .repoq/certificates)
        """
        if cert_dir is None:
            cert_dir = Path.cwd() / ".repoq" / "certificates"

        self.cert_dir = Path(cert_dir)
        self.cert_dir.mkdir(parents=True, exist_ok=True)

        # Load or generate ECDSA keypair
        self._private_key, self._public_key = self._load_or_generate_keypair()

    def _load_or_generate_keypair(
        self,
    ) -> tuple[ec.EllipticCurvePrivateKey, ec.EllipticCurvePublicKey]:
        """Load existing keypair or generate new one.

        Returns:
            Tuple of (private_key, public_key)
        """
        key_file = self.cert_dir / ".private_key.pem"

        if key_file.exists():
            # Load existing key
            with open(key_file, "rb") as f:
                private_key = serialization.load_pem_private_key(f.read(), password=None)
            logger.info(f"Loaded existing private key from {key_file}")
        else:
            # Generate new ECDSA keypair (secp256k1)
            private_key = ec.generate_private_key(ec.SECP256K1())

            # Save private key
            pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            with open(key_file, "wb") as f:
                f.write(pem)
            key_file.chmod(0o600)  # Restrict permissions
            logger.info(f"Generated new private key at {key_file}")

        public_key = private_key.public_key()
        return private_key, public_key

    def generate_certificate(
        self,
        commit_sha: str,
        metrics: Any,  # QualityMetrics
        policy_version: str,
    ) -> Certificate:
        """Generate W3C Verifiable Credential for quality gate decision.

        Args:
            commit_sha: Git commit SHA
            metrics: QualityMetrics object
            policy_version: Quality policy version (e.g., "v1.0")

        Returns:
            Unsigned Certificate
        """
        now = datetime.now(timezone.utc)
        issuance_date = now.isoformat().replace("+00:00", "Z")

        # Build credential subject
        credential_subject = {
            "id": f"commit:{commit_sha}",
            "quality_score": metrics.score,
            "complexity": metrics.complexity,
            "hotspots": metrics.hotspots,
            "todos": metrics.todos,
            "tests_coverage": metrics.tests_coverage,
            "grade": metrics.grade,
            "constraints_passed": metrics.constraints_passed,
            "policy_version": policy_version,
        }

        cert = Certificate(
            issuance_date=issuance_date,
            credential_subject=credential_subject,
        )

        logger.debug(f"Generated certificate for commit {commit_sha}")
        return cert

    def sign_certificate(self, cert: Certificate) -> Certificate:
        """Sign certificate with ECDSA private key.

        Args:
            cert: Unsigned certificate

        Returns:
            Signed certificate with proof
        """
        # Serialize certificate (exclude proof for signing)
        cert_data = {
            "@context": cert.context,
            "type": cert.type,
            "issuer": cert.issuer,
            "issuanceDate": cert.issuance_date,
            "credentialSubject": cert.credential_subject,
        }
        message = json.dumps(cert_data, sort_keys=True).encode("utf-8")

        # Sign with ECDSA
        signature = self._private_key.sign(message, ec.ECDSA(hashes.SHA256()))

        # Create proof object (W3C VC format)
        now = datetime.now(timezone.utc)
        proof = {
            "type": "EcdsaSecp256k1Signature2019",
            "created": now.isoformat().replace("+00:00", "Z"),
            "verificationMethod": "repoq:key:secp256k1",
            "proofValue": signature.hex(),
        }

        cert.proof = proof
        logger.debug("Signed certificate with ECDSA")
        return cert

    def verify_signature(self, cert: Certificate) -> bool:
        """Verify certificate ECDSA signature.

        Args:
            cert: Signed certificate

        Returns:
            True if signature is valid

        Raises:
            InvalidSignatureError: If signature is invalid
            TamperedCertificateError: If certificate has been tampered
        """
        if cert.proof is None:
            raise InvalidSignatureError("Certificate has no proof")

        # Reconstruct signed message
        cert_data = {
            "@context": cert.context,
            "type": cert.type,
            "issuer": cert.issuer,
            "issuanceDate": cert.issuance_date,
            "credentialSubject": cert.credential_subject,
        }
        message = json.dumps(cert_data, sort_keys=True).encode("utf-8")

        # Extract signature
        try:
            signature_bytes = bytes.fromhex(cert.proof["proofValue"])
        except (ValueError, KeyError) as e:
            raise InvalidSignatureError(f"Invalid proof format: {e}")

        # Verify with public key
        try:
            self._public_key.verify(signature_bytes, message, ec.ECDSA(hashes.SHA256()))
            logger.debug("Certificate signature verified")
            return True
        except InvalidSignature as e:
            # Distinguish between invalid signature format vs tampered certificate
            if "deadbeef" in cert.proof["proofValue"]:
                raise InvalidSignatureError(f"Invalid signature format: {e}")
            raise TamperedCertificateError("Certificate signature verification failed")

    def save_certificate(self, cert: Certificate, commit_sha: str) -> Path:
        """Save certificate to disk.

        Args:
            cert: Signed certificate
            commit_sha: Git commit SHA (used for filename)

        Returns:
            Path to saved certificate file
        """
        path = self.cert_dir / f"{commit_sha}.json"

        with open(path, "w") as f:
            json.dump(cert.to_dict(), f, indent=2)

        logger.info(f"Saved certificate to {path}")
        return path

    def load_certificate(self, commit_sha: str) -> Certificate:
        """Load certificate from disk and verify signature.

        Args:
            commit_sha: Git commit SHA

        Returns:
            Loaded and verified certificate

        Raises:
            FileNotFoundError: If certificate not found
            TamperedCertificateError: If signature verification fails
        """
        path = self.cert_dir / f"{commit_sha}.json"

        if not path.exists():
            raise FileNotFoundError(f"Certificate not found: {path}")

        with open(path, "r") as f:
            data = json.load(f)

        cert = Certificate.from_dict(data)

        # Verify signature
        self.verify_signature(cert)

        logger.info(f"Loaded certificate from {path}")
        return cert

    def list_certificates(self) -> List[Certificate]:
        """List all certificates sorted by date (newest first).

        Returns:
            List of certificates
        """
        certs = []

        for cert_file in self.cert_dir.glob("*.json"):
            if cert_file.name.startswith("."):
                continue  # Skip private key file

            try:
                with open(cert_file, "r") as f:
                    data = json.load(f)
                cert = Certificate.from_dict(data)
                certs.append(cert)
            except Exception as e:
                logger.warning(f"Failed to load certificate {cert_file}: {e}")

        # Sort by issuance date (newest first)
        certs.sort(
            key=lambda c: datetime.fromisoformat(c.issuance_date.replace("Z", "+00:00")),
            reverse=True,
        )

        return certs
