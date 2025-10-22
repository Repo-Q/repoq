"""
RepoQ Workspace Manager (Phase 5, Phase 1 deliverable).

Manages .repoq/ directory structure for reproducible analysis.

Addresses:
- FR-10 (Incremental Analysis): Cache directory for SHA-based metrics
- V07 (Reliability): Reproducible workspace structure
- Theorem A (Correctness): Manifest captures ontology checksums
- NFR-03 (Determinism): Same input → same checksums

References:
- Phase 5 Migration Roadmap: docs/vdad/phase5-migration-roadmap.md (Phase 1)
- ADR-008 (SHA-Based Incremental Caching)
- ADR-010 (W3C Verifiable Credentials storage)
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


@dataclass
class ManifestEntry:
    """Manifest entry for reproducible analysis (V07 Reliability).

    Attributes:
        commit_sha: Git commit SHA analyzed
        policy_version: Quality policy version (e.g., "1.2.0")
        ontology_checksums: SHA256 checksums of ontology files (Theorem A)
        trs_version: Any2Math TRS version (Phase 3)
        analysis_timestamp: ISO 8601 timestamp
    """

    commit_sha: str
    policy_version: str
    ontology_checksums: Dict[str, str]
    trs_version: Optional[str] = None
    analysis_timestamp: Optional[str] = None


class RepoQWorkspace:
    """Manages .repoq/ workspace structure.

    Directory structure:
        .repoq/
        ├── raw/           # ABox-raw facts (TTL)
        ├── validated/     # Post-SHACL validated facts
        ├── reports/       # Markdown/HTML reports
        ├── certificates/  # W3C Verifiable Credentials (ADR-010)
        ├── cache/         # SHA-keyed metrics cache (ADR-008)
        ├── manifest.json  # Analysis manifest (V07 Reliability)
        └── .gitignore     # Ignore cache/

    Usage:
        >>> workspace = RepoQWorkspace(repo_path)
        >>> workspace.initialize()
        >>> workspace.save_manifest(
        ...     commit_sha="abc123",
        ...     policy_version="1.0.0",
        ...     ontology_checksums=compute_ontology_checksums(ontologies_dir)
        ... )
    """

    def __init__(self, repo_path: Path):
        """Initialize workspace manager.

        Args:
            repo_path: Path to repository root
        """
        self.repo_path = Path(repo_path)
        self.root = self.repo_path / ".repoq"
        self.raw = self.root / "raw"
        self.validated = self.root / "validated"
        self.reports = self.root / "reports"
        self.certificates = self.root / "certificates"
        self.cache = self.root / "cache"

    def initialize(self) -> None:
        """Create all workspace directories (idempotent).

        Creates:
        - .repoq/ directory structure
        - .gitignore to exclude cache/

        Requirements:
        - FR-10 (Incremental Analysis): Cache directory
        - V07 (Reliability): Reproducible structure
        """
        # Create all directories (exist_ok=True for idempotency)
        self.root.mkdir(exist_ok=True)
        self.raw.mkdir(exist_ok=True)
        self.validated.mkdir(exist_ok=True)
        self.reports.mkdir(exist_ok=True)
        self.certificates.mkdir(exist_ok=True)
        self.cache.mkdir(exist_ok=True)

        # Create .gitignore to exclude cache/ (local-only data)
        gitignore_path = self.root / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text(
                "# RepoQ workspace .gitignore\n"
                "# Cache is local-only (not committed to VCS)\n"
                "cache/\n"
            )

    def save_manifest(
        self,
        commit_sha: str,
        policy_version: str,
        ontology_checksums: Dict[str, str],
        trs_version: Optional[str] = None,
    ) -> None:
        """Save analysis manifest to .repoq/manifest.json.

        Args:
            commit_sha: Git commit SHA analyzed
            policy_version: Quality policy version (e.g., "1.2.0")
            ontology_checksums: SHA256 checksums of ontology files
            trs_version: Any2Math TRS version (optional, Phase 3)

        Generates:
            .repoq/manifest.json with ISO 8601 timestamp

        Requirements:
        - V07 (Reliability): Reproducible analysis tracking
        - Theorem A (Correctness): Ontology checksums validated
        - NFR-03 (Determinism): Checksums ensure reproducibility
        """
        # Generate timestamp (ISO 8601 with UTC)
        timestamp = datetime.now(timezone.utc).isoformat()

        # Create manifest entry
        manifest = ManifestEntry(
            commit_sha=commit_sha,
            policy_version=policy_version,
            ontology_checksums=ontology_checksums,
            trs_version=trs_version,
            analysis_timestamp=timestamp,
        )

        # Write to JSON (pretty-printed for readability)
        manifest_path = self.root / "manifest.json"
        manifest_path.write_text(json.dumps(asdict(manifest), indent=2, sort_keys=True))

    def load_manifest(self) -> ManifestEntry:
        """Load analysis manifest from .repoq/manifest.json.

        Returns:
            ManifestEntry with analysis metadata

        Raises:
            FileNotFoundError: If manifest.json doesn't exist
            JSONDecodeError: If manifest.json is invalid

        Requirements:
        - V07 (Reliability): Reproducibility verification
        """
        manifest_path = self.root / "manifest.json"

        if not manifest_path.exists():
            raise FileNotFoundError(
                f"Manifest not found: {manifest_path}\n"
                "Run analysis with gate to generate manifest."
            )

        # Parse JSON
        data = json.loads(manifest_path.read_text())

        # Convert to ManifestEntry
        return ManifestEntry(**data)


def compute_ontology_checksums(ontologies_dir: Path) -> Dict[str, str]:
    """Compute SHA256 checksums for all ontology files (Theorem A).

    Args:
        ontologies_dir: Directory containing ontology .ttl files

    Returns:
        Dict mapping filename → "sha256:..." checksum

    Requirements:
    - Theorem A (Correctness): Ontology integrity validation
    - NFR-03 (Determinism): Same file → same checksum

    Example:
        >>> checksums = compute_ontology_checksums(Path("repoq/ontologies"))
        >>> checksums
        {
            "code.ttl": "sha256:abc123...",
            "c4.ttl": "sha256:def456...",
            "ddd.ttl": "sha256:789xyz..."
        }
    """
    checksums = {}

    ontologies_dir = Path(ontologies_dir)
    if not ontologies_dir.exists():
        return checksums

    # Process all .ttl files
    for ttl_file in sorted(ontologies_dir.glob("*.ttl")):
        # Compute SHA256 checksum
        sha256 = hashlib.sha256()
        sha256.update(ttl_file.read_bytes())
        checksum = f"sha256:{sha256.hexdigest()}"

        # Store with filename (not full path for portability)
        checksums[ttl_file.name] = checksum

    return checksums
