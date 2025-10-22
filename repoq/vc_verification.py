"""W3C Verifiable Credentials verification module.

This module provides verification for W3C Verifiable Credentials (VC)
with ECDSA signatures, supporting the QualityAssessmentCredential type.

Verification steps:
    1. Load VC from JSON file
    2. Extract proof and signature
    3. Verify ECDSA signature using public key
    4. Validate VC structure (required fields)
    5. Check expiration (if present)

Example VC structure:
    {
      "@context": ["https://www.w3.org/2018/credentials/v1"],
      "type": ["VerifiableCredential", "QualityAssessmentCredential"],
      "issuer": "did:repoq:v1",
      "issuanceDate": "2025-10-21T10:30:00Z",
      "credentialSubject": {...},
      "proof": {
        "type": "EcdsaSecp256k1Signature2019",
        "created": "2025-10-21T10:30:00Z",
        "proofPurpose": "assertionMethod",
        "verificationMethod": "did:repoq:v1#key-1",
        "jws": "eyJhbGc...signature..."
      }
    }
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec


@dataclass
class VerificationResult:
    """Result of VC verification.

    Attributes:
        valid: True if signature and structure are valid
        issuer: DID of credential issuer
        subject: Credential subject data
        issued_at: Issuance timestamp
        expires_at: Expiration timestamp (if present)
        errors: List of validation errors (if any)
    """

    valid: bool
    issuer: str | None = None
    subject: Dict[str, Any] | None = None
    issued_at: str | None = None
    expires_at: str | None = None
    errors: list[str] | None = None


def verify_vc(vc_path: Path, public_key_path: Path | None = None) -> VerificationResult:
    """Verify W3C Verifiable Credential.

    Args:
        vc_path: Path to VC JSON file
        public_key_path: Path to public key PEM file (optional, uses issuer DID if None)

    Returns:
        VerificationResult with validation status and details

    Example:
        >>> result = verify_vc(Path("quality_cert.json"), Path("public_key.pem"))
        >>> if result.valid:
        ...     print(f"✅ VC valid, issued by {result.issuer}")
        ... else:
        ...     print(f"❌ VC invalid: {result.errors}")
    """
    errors = []

    # 1. Load VC from file
    try:
        with open(vc_path, encoding="utf-8") as f:
            vc = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return VerificationResult(
            valid=False,
            errors=[f"Failed to load VC: {e}"],
        )

    # 2. Validate VC structure
    validation_errors = _validate_vc_structure(vc)
    if validation_errors:
        return VerificationResult(
            valid=False,
            errors=validation_errors,
        )

    # 3. Extract metadata
    issuer = vc.get("issuer")
    subject = vc.get("credentialSubject")
    issued_at = vc.get("issuanceDate")
    expires_at = vc.get("expirationDate")

    # 4. Check expiration
    if expires_at:
        try:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if datetime.now(expiry.tzinfo) > expiry:
                errors.append(f"VC expired on {expires_at}")
        except ValueError:
            errors.append(f"Invalid expiration date: {expires_at}")

    # 5. Verify signature
    proof = vc.get("proof", {})
    jws = proof.get("jws")

    if not jws:
        errors.append("Missing signature (proof.jws)")
        return VerificationResult(
            valid=False,
            issuer=issuer,
            subject=subject,
            issued_at=issued_at,
            expires_at=expires_at,
            errors=errors,
        )

    # 6. Load public key
    if public_key_path and public_key_path.exists():
        try:
            with open(public_key_path, "rb") as f:
                public_key = serialization.load_pem_public_key(f.read())
        except Exception as e:
            errors.append(f"Failed to load public key: {e}")
            return VerificationResult(
                valid=False,
                issuer=issuer,
                subject=subject,
                issued_at=issued_at,
                expires_at=expires_at,
                errors=errors,
            )
    else:
        # Use default key (for demo purposes - in production, resolve DID)
        errors.append("Public key not provided (use --public-key)")
        return VerificationResult(
            valid=False,
            issuer=issuer,
            subject=subject,
            issued_at=issued_at,
            expires_at=expires_at,
            errors=errors,
        )

    # 7. Verify ECDSA signature
    try:
        # JWS format: base64url(header).base64url(payload).base64url(signature)
        parts = jws.split(".")
        if len(parts) != 3:
            errors.append(f"Invalid JWS format (expected 3 parts, got {len(parts)})")
            return VerificationResult(
                valid=False,
                issuer=issuer,
                subject=subject,
                issued_at=issued_at,
                expires_at=expires_at,
                errors=errors,
            )

        header_b64, payload_b64, signature_b64 = parts

        # Decode signature
        signature = _base64url_decode(signature_b64)

        # Message to verify: header.payload
        message = f"{header_b64}.{payload_b64}".encode("utf-8")

        # Verify with public key
        if isinstance(public_key, ec.EllipticCurvePublicKey):
            public_key.verify(
                signature,
                message,
                ec.ECDSA(hashes.SHA256()),
            )
        else:
            errors.append("Public key is not ECDSA")
            return VerificationResult(
                valid=False,
                issuer=issuer,
                subject=subject,
                issued_at=issued_at,
                expires_at=expires_at,
                errors=errors,
            )

        # Signature valid!
        return VerificationResult(
            valid=len(errors) == 0,
            issuer=issuer,
            subject=subject,
            issued_at=issued_at,
            expires_at=expires_at,
            errors=errors if errors else None,
        )

    except InvalidSignature:
        errors.append("Signature verification failed (invalid signature)")
        return VerificationResult(
            valid=False,
            issuer=issuer,
            subject=subject,
            issued_at=issued_at,
            expires_at=expires_at,
            errors=errors,
        )
    except Exception as e:
        errors.append(f"Signature verification error: {e}")
        return VerificationResult(
            valid=False,
            issuer=issuer,
            subject=subject,
            issued_at=issued_at,
            expires_at=expires_at,
            errors=errors,
        )


def _validate_vc_structure(vc: Dict[str, Any]) -> list[str]:
    """Validate W3C VC structure.

    Args:
        vc: Verifiable Credential dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Required fields
    if "@context" not in vc:
        errors.append("Missing @context")
    elif "https://www.w3.org/2018/credentials/v1" not in vc["@context"]:
        errors.append("Missing W3C credentials context")

    if "type" not in vc:
        errors.append("Missing type")
    elif "VerifiableCredential" not in vc["type"]:
        errors.append("Missing VerifiableCredential type")

    if "issuer" not in vc:
        errors.append("Missing issuer")

    if "issuanceDate" not in vc:
        errors.append("Missing issuanceDate")

    if "credentialSubject" not in vc:
        errors.append("Missing credentialSubject")

    if "proof" not in vc:
        errors.append("Missing proof")
    else:
        proof = vc["proof"]
        if "type" not in proof:
            errors.append("Missing proof.type")
        if "jws" not in proof:
            errors.append("Missing proof.jws (signature)")

    return errors


def _base64url_decode(data: str) -> bytes:
    """Decode base64url string to bytes.

    Args:
        data: Base64url encoded string

    Returns:
        Decoded bytes
    """
    # Add padding if needed
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding

    # Replace URL-safe characters
    data = data.replace("-", "+").replace("_", "/")

    return base64.b64decode(data)


def format_verification_report(result: VerificationResult) -> str:
    """Format verification result as human-readable report.

    Args:
        result: VerificationResult from verify_vc

    Returns:
        Multi-line formatted report
    """
    lines = []

    lines.append("=" * 60)
    if result.valid:
        lines.append("[bold green]✅ Verifiable Credential: VALID[/bold green]")
    else:
        lines.append("[bold red]❌ Verifiable Credential: INVALID[/bold red]")
    lines.append("=" * 60)
    lines.append("")

    if result.issuer:
        lines.append("[bold]📋 Credential Details[/bold]")
        lines.append("")
        lines.append(f"  Issuer: {result.issuer}")

        if result.issued_at:
            lines.append(f"  Issued: {result.issued_at}")

        if result.expires_at:
            lines.append(f"  Expires: {result.expires_at}")

        lines.append("")

    if result.subject:
        lines.append("[bold]📊 Subject Data[/bold]")
        lines.append("")
        for key, value in result.subject.items():
            if key.startswith("@"):
                continue
            lines.append(f"  {key}: {value}")
        lines.append("")

    if result.errors:
        lines.append("[bold red]❌ Validation Errors[/bold red]")
        lines.append("")
        for i, error in enumerate(result.errors, 1):
            lines.append(f"  {i}. {error}")
        lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)
