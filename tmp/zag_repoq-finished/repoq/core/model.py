from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class File:
    id: str
    path: str
    language: Optional[str] = None
    lines_of_code: int = 0
    complexity: Optional[float] = None
    commits_count: int = 0
    code_churn: int = 0
    last_modified: Optional[str] = None
    contributors: Dict[str, Dict[str, int]] = field(default_factory=dict)  # id -> {linesAdded,linesDeleted,commits}
    issues: List[str] = field(default_factory=list)
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
    contains_files: List[str] = field(default_factory=list)  # file ids
    total_loc: int = 0
    main_language: Optional[str] = None

@dataclass
class Issue:
    id: str
    type: str
    file: Optional[str] = None
    description: Optional[str] = None
    severity: str = "low"

@dataclass
class CouplingEdge:
    a: str
    b: str
    weight: float

@dataclass
class Project:
    id: str
    name: str
    repository_url: Optional[str] = None
    description: Optional[str] = None
    license: Optional[str] = None
    programming_languages: Dict[str, int] = field(default_factory=dict)
    modules: Dict[str, Module] = field(default_factory=dict)
    files: Dict[str, File] = field(default_factory=dict)
    contributors: Dict[str, Dict[str, int]] = field(default_factory=dict)  # author id -> {commits,linesAdded,linesDeleted}
    issues: Dict[str, Issue] = field(default_factory=dict)
    coupling: List[CouplingEdge] = field(default_factory=list)
    ci_configured: bool = False
    tests_results: List[dict] = field(default_factory=list)
