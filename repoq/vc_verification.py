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


def _load_vc_from_file(vc_path: Path) -> tuple[Dict[str, Any] | None, list[str]]:
    """Load VC JSON from file.

    Returns:
        Tuple of (vc_dict, errors). vc_dict is None if loading failed.
    """
    try:
        with open(vc_path, encoding="utf-8") as f:
            return json.load(f), []
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return None, [f"Failed to load VC: {e}"]


def _check_vc_expiration(expires_at: str | None) -> list[str]:
    """Check if VC has expired.

    Args:
        expires_at: ISO8601 expiration date string (or None)

    Returns:
        List of errors (empty if not expired)
    """
    if not expires_at:
        return []

    try:
        expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if datetime.now(expiry.tzinfo) > expiry:
            return [f"VC expired on {expires_at}"]
        return []
    except ValueError:
        return [f"Invalid expiration date: {expires_at}"]


def _load_public_key(public_key_path: Path | None) -> tuple[Any | None, list[str]]:
    """Load public key from PEM file.

    Returns:
        Tuple of (public_key, errors). public_key is None if loading failed.
    """
    if not public_key_path or not public_key_path.exists():
        return None, ["Public key not provided (use --public-key)"]

    try:
        with open(public_key_path, "rb") as f:
            return serialization.load_pem_public_key(f.read()), []
    except Exception as e:
        return None, [f"Failed to load public key: {e}"]


def _parse_jws_signature(jws: str) -> tuple[bytes | None, str | None, list[str]]:
    """Parse JWS compact serialization format.

    Args:
        jws: JWS string (base64url(header).base64url(payload).base64url(signature))

    Returns:
        Tuple of (signature_bytes, message_to_verify, errors)
    """
    parts = jws.split(".")
    if len(parts) != 3:
        return None, None, [f"Invalid JWS format (expected 3 parts, got {len(parts)})"]

    header_b64, payload_b64, signature_b64 = parts
    try:
        signature = _base64url_decode(signature_b64)
        message = f"{header_b64}.{payload_b64}"
        return signature, message, []
    except Exception as e:
        return None, None, [f"Failed to decode JWS: {e}"]


def _verify_ecdsa_signature(
    public_key: Any, signature: bytes, message: str
) -> list[str]:
    """Verify ECDSA signature.

    Args:
        public_key: Loaded public key
        signature: Raw signature bytes
        message: Message that was signed

    Returns:
        List of errors (empty if valid)
    """
    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        return ["Public key is not ECDSA"]

    try:
        public_key.verify(
            signature,
            message.encode("utf-8"),
            ec.ECDSA(hashes.SHA256()),
        )
        return []
    except InvalidSignature:
        return ["Signature verification failed (invalid signature)"]
    except Exception as e:
        return [f"Signature verification error: {e}"]


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
    errors: list[str] = []

    # 1. Load VC from file
    vc, load_errors = _load_vc_from_file(vc_path)
    if load_errors:
        return VerificationResult(valid=False, errors=load_errors)

    # 2. Validate VC structure
    validation_errors = _validate_vc_structure(vc)
    if validation_errors:
        return VerificationResult(valid=False, errors=validation_errors)

    # 3. Extract metadata
    issuer = vc.get("issuer")
    subject = vc.get("credentialSubject")
    issued_at = vc.get("issuanceDate")
    expires_at = vc.get("expirationDate")

    # 4. Check expiration
    errors.extend(_check_vc_expiration(expires_at))

    # 5. Check signature presence
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
    public_key, key_errors = _load_public_key(public_key_path)
    if key_errors:
        errors.extend(key_errors)
        return VerificationResult(
            valid=False,
            issuer=issuer,
            subject=subject,
            issued_at=issued_at,
            expires_at=expires_at,
            errors=errors,
        )

    # 7. Parse JWS and verify ECDSA signature
    signature, message, jws_errors = _parse_jws_signature(jws)
    if jws_errors:
        errors.extend(jws_errors)
        return VerificationResult(
            valid=False,
            issuer=issuer,
            subject=subject,
            issued_at=issued_at,
            expires_at=expires_at,
            errors=errors,
        )

    # 8. Verify signature
    sig_errors = _verify_ecdsa_signature(public_key, signature, message)
    errors.extend(sig_errors)

    return VerificationResult(
        valid=len(errors) == 0,
        issuer=issuer,
        subject=subject,
        issued_at=issued_at,
        expires_at=expires_at,
        errors=errors if errors else None,
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
