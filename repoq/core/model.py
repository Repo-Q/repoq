from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional


def hash_email(email: str) -> str:
    if not email:
        return ""
    return hashlib.sha256(email.encode("utf-8")).hexdigest()[:16]


def foaf_sha1(email: str) -> str:
    if not email:
        return ""
    return hashlib.sha1(f"mailto:{email}".encode("utf-8")).hexdigest()  # nosec B324


@dataclass
class Issue:
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
    source: str  # module/file id
    target: str
    weight: int = 1
    type: str = "import"  # import|runtime|build


@dataclass
class CouplingEdge:
    a: str  # file id
    b: str  # file id
    weight: int = 1


@dataclass
class Commit:
    id: str
    message: str
    author_id: Optional[str]
    ended_at: Optional[str]


@dataclass
class VersionResource:
    id: str
    version_id: str
    branch: Optional[str]
    committer: Optional[str]
    committed: Optional[str]


@dataclass
class TestCase:
    id: str
    name: str
    classname: Optional[str] = None


@dataclass
class TestResult:
    id: str
    testcase: str
    status: str  # passed|failed|skipped|error
    time: Optional[float] = None
    message: Optional[str] = None


@dataclass
class Project:
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
