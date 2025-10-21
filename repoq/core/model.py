"""Core data models for repository analysis.

This module defines the dataclass models used throughout repoq for representing
repository analysis results, including projects, files, modules, contributors,
issues, and relationships.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


def hash_email(email: str) -> str:
    """Create a truncated SHA256 hash of an email address.

    Used for creating short, anonymized identifiers for contributors
    without exposing full email addresses.

    Args:
        email: Email address to hash. Empty string returns empty string.

    Returns:
        First 16 characters of the SHA256 hash, or empty string if email is empty.

    Example:
        >>> hash_email("user@example.com")
        'a7b8c9d0e1f2g3h4'
    """
    if not email:
        return ""
    return hashlib.sha256(email.encode("utf-8")).hexdigest()[:16]


def foaf_sha1(email: str) -> str:
    """Create FOAF mbox_sha1sum hash for an email address.

    Implements the FOAF (Friend of a Friend) specification for creating
    SHA1 hashes of mailto: URIs. Used for linked data compatibility.

    Args:
        email: Email address to hash. Empty string returns empty string.

    Returns:
        SHA1 hash of "mailto:{email}", or empty string if email is empty.

    Note:
        Uses SHA1 for FOAF spec compatibility (not for security).
        Marked with nosec B324 to indicate this is intentional.

    Reference:
        http://xmlns.com/foaf/spec/#term_mbox_sha1sum

    Example:
        >>> foaf_sha1("user@example.com")
        '3c6e0b8a9c15224a8228b9a98ca1531d316b624b'
    """
    if not email:
        return ""
    return hashlib.sha1(f"mailto:{email}".encode("utf-8")).hexdigest()  # nosec B324


@dataclass
class Issue:
    """Represents a code quality issue, TODO, or defect found in the repository.

    Issues are mapped to OSLC Change Management (CM) ChangeRequests in JSON-LD export,
    enabling integration with project management and issue tracking systems.

    Attributes:
        id: Unique identifier (e.g., "repo:issue:file.py:TodoComment")
        type: Issue type classification (e.g., "repo:TodoComment", "repo:Deprecated")
        file_id: Reference to the file containing the issue (e.g., "repo:file:src/main.py")
        description: Detailed description of the issue
        severity: Severity level - "low", "medium", or "high" (default: "low")
        priority: Priority level - "low", "medium", "high", or None (default: None)
        status: Current status - "Open", "InProgress", "Closed", or None (default: None)
        title: Short title/summary of the issue, or None (default: None)
    """

    id: str
    type: str
    file_id: Optional[str]
    description: str
    severity: str = "low"  # low|medium|high
    priority: Optional[str] = None  # low|medium|high
    status: Optional[str] = None  # Open/Inprogress/Closed
    title: Optional[str] = None


@dataclass
class Person:
    """Represents a contributor to the repository.

    Contributors are mapped to FOAF Persons and PROV-O Agents in JSON-LD export,
    enabling social network analysis and provenance tracking.

    Attributes:
        id: Unique identifier (e.g., "repo:person:a1b2c3d4")
        name: Contributor's display name (e.g., "John Doe")
        email: Email address (default: "")
        email_hash: Truncated SHA256 hash of email for anonymization (default: "")
        foaf_mbox_sha1sum: FOAF-compliant SHA1 hash of mailto: URI (default: "")
        commits: Total number of commits by this contributor (default: 0)
        lines_added: Total lines of code added across all commits (default: 0)
        lines_deleted: Total lines of code deleted across all commits (default: 0)
        owns: List of file IDs owned by this contributor (default: empty list)
        modules_contributed: List of module IDs contributed to (default: empty list)
    """

    id: str
    name: str
    email: str = ""
    email_hash: str = ""
    foaf_mbox_sha1sum: str = ""
    commits: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    owns: List[str] = field(default_factory=list)
    modules_contributed: List[str] = field(default_factory=list)


@dataclass
class File:
    """Represents a source code file in the repository.

    Files are mapped to schema:SoftwareSourceCode, spdx:File, and prov:Entity
    in JSON-LD export, enabling semantic web integration and provenance tracking.

    Attributes:
        id: Unique identifier (e.g., "repo:file:src/main.py")
        path: Relative path from repository root
        language: Detected programming language (e.g., "Python", "JavaScript")
        lines_of_code: Total lines excluding blanks and comments (default: 0)
        complexity: Cyclomatic complexity score (default: None)
        maintainability: Maintainability index 0-100 (default: None)
        commits_count: Number of commits modifying this file (default: 0)
        code_churn: Sum of lines added + deleted over time (default: 0)
        contributors: Dict mapping person_id to contribution metrics (default: {})
        issues: List of issue IDs associated with this file (default: [])
        last_modified: ISO 8601 timestamp of last modification (default: None)
        deprecated: Whether file is marked as deprecated (default: False)
        test_file: Whether file is a test file (default: False)
        module: Module ID containing this file (default: None)
        hotness: Combined metric of churn and complexity (default: None)
        checksum_algo: Checksum algorithm used (e.g., "sha256") (default: None)
        checksum_value: File content checksum value (default: None)
    """

    id: str
    path: str
    language: Optional[str] = None
    lines_of_code: int = 0
    complexity: Optional[float] = None
    maintainability: Optional[float] = None
    commits_count: int = 0
    code_churn: int = 0
    contributors: Dict[str, Dict[str, int]] = field(default_factory=dict)  # person_id -> metrics
    issues: List[str] = field(default_factory=list)
    last_modified: Optional[str] = None
    deprecated: bool = False
    test_file: bool = False
    module: Optional[str] = None
    hotness: Optional[float] = None
    checksum_algo: Optional[str] = None
    checksum_value: Optional[str] = None


@dataclass
class Module:
    """Represents a logical module or package in the repository.

    Modules group related files and can contain sub-modules, forming a tree structure.

    Attributes:
        id: Unique identifier (e.g., "repo:module:src/utils")
        name: Module name (e.g., "utils")
        path: Relative path from repository root
        contains_files: List of file IDs in this module (default: [])
        contains_modules: List of sub-module IDs (default: [])
        total_loc: Sum of lines of code in all contained files (default: 0)
        total_commits: Sum of commits affecting this module (default: 0)
        num_authors: Number of unique contributors to this module (default: 0)
        owner: Person ID of primary owner (default: None)
        hotspot_score: Combined metric of activity and complexity (default: None)
        main_language: Predominant programming language (default: None)
    """

    id: str
    name: str
    path: str
    contains_files: List[str] = field(default_factory=list)
    contains_modules: List[str] = field(default_factory=list)
    total_loc: int = 0
    total_commits: int = 0
    num_authors: int = 0
    owner: Optional[str] = None
    hotspot_score: Optional[float] = None
    main_language: Optional[str] = None


@dataclass
class DependencyEdge:
    """Represents a dependency relationship between modules or files.

    Attributes:
        source: ID of dependent module/file
        target: ID of dependency module/file
        weight: Dependency strength (default: 1)
        type: Dependency category: "import", "runtime", or "build" (default: "import")
        version_constraint: Version constraint/range in normalized form (optional)
        original_constraint: Original version constraint before normalization (optional)
    """

    source: str  # module/file id
    target: str
    weight: int = 1
    type: str = "import"  # import|runtime|build
    version_constraint: Optional[str] = None  # Normalized SemVer range
    original_constraint: Optional[str] = None  # Original constraint from manifest


@dataclass
class CouplingEdge:
    """Represents temporal coupling between files (files changed together).

    Attributes:
        a: ID of first file
        b: ID of second file
        weight: Number of commits where both files changed together (default: 1)
    """

    a: str  # file id
    b: str  # file id
    weight: int = 1


@dataclass
class Commit:
    """Represents a Git commit mapped to PROV-O Activity.

    Attributes:
        id: Unique commit identifier (e.g., "repo:commit:a1b2c3d4")
        message: Commit message text
        author_id: Person ID of commit author (default: None)
        ended_at: ISO 8601 timestamp of commit (default: None)
    """

    id: str
    message: str
    author_id: Optional[str]
    ended_at: Optional[str]


@dataclass
class VersionResource:
    """Represents a versioned resource mapped to OSLC Configuration Management.

    Attributes:
        id: Unique version resource identifier
        version_id: Version string (e.g., "v1.2.3", commit SHA)
        branch: Git branch name (default: None)
        committer: Person ID of committer (default: None)
        committed: ISO 8601 timestamp of commit (default: None)
    """

    id: str
    version_id: str
    branch: Optional[str]
    committer: Optional[str]
    committed: Optional[str]


@dataclass
class TestCase:
    """Represents a test case mapped to OSLC QM TestCase.

    Attributes:
        id: Unique test case identifier
        name: Test case name/title
        classname: Test class or suite name (default: None)
    """

    id: str
    name: str
    classname: Optional[str] = None


@dataclass
class TestResult:
    """Represents a test execution result mapped to OSLC QM TestResult.

    Attributes:
        id: Unique test result identifier
        testcase: TestCase ID this result belongs to
        status: Execution status: "passed", "failed", "skipped", or "error"
        time: Execution time in seconds (default: None)
        message: Error message or additional details (default: None)
    """

    id: str
    testcase: str
    status: str  # passed|failed|skipped|error
    time: Optional[float] = None
    message: Optional[str] = None


@dataclass
class Project:
    """Main repository analysis model aggregating all metrics and entities.

    The Project class is the root entity mapped to multiple semantic web types:
    repo:Project, schema:SoftwareSourceCode, codemeta:SoftwareSourceCode,
    prov:Entity, and okn_sd:Software in JSON-LD export.

    Attributes:
        id: Unique project identifier (URL or path)
        name: Project name (e.g., "repoq")
        description: Project description (default: None)
        repository_url: Git repository URL (default: None)
        license: SPDX license identifier (e.g., "MIT") (default: None)
        programming_languages: Dict mapping language to LOC count (default: {})
        last_commit_date: ISO 8601 timestamp of most recent commit (default: None)
        ci_configured: List of detected CI/CD systems (e.g., ["GitHub Actions"]) (default: [])
        modules: Dict of Module objects keyed by module ID (default: {})
        files: Dict of File objects keyed by file ID (default: {})
        contributors: Dict of Person objects keyed by person ID (default: {})
        issues: Dict of Issue objects keyed by issue ID (default: {})
        dependencies: List of DependencyEdge objects (default: [])
        coupling: List of CouplingEdge objects (default: [])
        commits: List of Commit objects (default: [])
        versions: List of VersionResource objects (default: [])
        tests_cases: Dict of TestCase objects keyed by test ID (default: {})
        tests_results: List of TestResult objects (default: [])
    """

    id: str
    name: str
    description: Optional[str] = None
    repository_url: Optional[str] = None
    license: Optional[str] = None
    programming_languages: Dict[str, int] = field(default_factory=dict)  # language -> LOC
    last_commit_date: Optional[str] = None
    ci_configured: List[str] = field(default_factory=list)
    modules: Dict[str, Module] = field(default_factory=dict)
    files: Dict[str, File] = field(default_factory=dict)
    contributors: Dict[str, Person] = field(default_factory=dict)
    issues: Dict[str, Issue] = field(default_factory=dict)
    dependencies: List[DependencyEdge] = field(default_factory=list)
    coupling: List[CouplingEdge] = field(default_factory=list)
    commits: List[Commit] = field(default_factory=list)
    versions: List[VersionResource] = field(default_factory=list)
    tests_cases: Dict[str, TestCase] = field(default_factory=dict)
    tests_results: List[TestResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert Project to plain dictionary for JSON serialization.

        Returns:
            Dictionary with all Project attributes, recursively converting
            nested dataclasses to dicts using dataclasses.asdict().
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "repository_url": self.repository_url,
            "license": self.license,
            "programming_languages": self.programming_languages,
            "last_commit_date": self.last_commit_date,
            "ci_configured": self.ci_configured,
            "modules": {k: asdict(v) for k, v in self.modules.items()},
            "files": {k: asdict(v) for k, v in self.files.items()},
            "contributors": {k: asdict(v) for k, v in self.contributors.items()},
            "issues": {k: asdict(v) for k, v in self.issues.items()},
            "dependencies": [asdict(e) for e in self.dependencies],
            "coupling": [asdict(e) for e in self.coupling],
            "commits": [asdict(c) for c in self.commits],
            "versions": [asdict(v) for v in self.versions],
            "tests_cases": {k: asdict(v) for k, v in self.tests_cases.items()},
            "tests_results": [asdict(r) for r in self.tests_results],
        }
