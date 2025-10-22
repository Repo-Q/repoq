# Tutorial 2: Writing a Custom Analyzer

!!! tip "Learning Objectives"
    - Understand the BaseAnalyzer pattern
    - Implement a custom analyzer
    - Register and configure your analyzer
    - Test your analyzer

## Prerequisites

- Completed [Tutorial 1: First Analysis](01-first-analysis.md)
- Python programming knowledge
- Understanding of AST (Abstract Syntax Trees) basics

## Why Custom Analyzers?

RepoQ's built-in analyzers cover common quality metrics, but every team has unique needs:

- **Domain-specific rules**: Banking security, medical compliance
- **Team conventions**: Naming patterns, code organization
- **Project-specific**: Framework usage, API patterns
- **Custom metrics**: Business logic complexity, feature flags

## Analyzer Architecture

### BaseAnalyzer Pattern

All analyzers inherit from `BaseAnalyzer`:

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict

class BaseAnalyzer(ABC):
    """Abstract base for all analyzers."""
    
    name: str  # Unique identifier
    
    @classmethod
    @abstractmethod
    def dependencies(cls) -> list[str]:
        """Return list of analyzer names this depends on."""
        return []
    
    @abstractmethod
    async def analyze(
        self,
        repo: Repository,
        deps: Dict[str, Any],
    ) -> Any:
        """Perform analysis with dependency results."""
        pass
```

## Example 1: Simple Security Analyzer

Let's build an analyzer that finds hardcoded secrets:

### Step 1: Create Analyzer File

```bash
# In your repoq project
mkdir -p repoq_custom/analyzers
touch repoq_custom/analyzers/__init__.py
touch repoq_custom/analyzers/security.py
```

### Step 2: Implement Analyzer

```python
# repoq_custom/analyzers/security.py

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from repoq.analyzers.base import BaseAnalyzer
from repoq.core.model import Repository


@dataclass
class SecurityFinding:
    """A security issue found in code."""
    file_path: str
    line_number: int
    severity: str  # "critical", "high", "medium", "low"
    category: str  # "secret", "sql_injection", "xss", etc.
    description: str
    code_snippet: str


@dataclass
class SecurityReport:
    """Security analysis results."""
    findings: List[SecurityFinding]
    total_files_scanned: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    
    @property
    def severity_score(self) -> float:
        """Calculate severity score (0-10, lower is better)."""
        weights = {"critical": 10, "high": 5, "medium": 2, "low": 1}
        total = sum(weights[f.severity] for f in self.findings)
        # Normalize to 0-10 scale
        return min(10.0, total / 10.0)


class SecurityAnalyzer(BaseAnalyzer):
    """Detect hardcoded secrets and security issues."""
    
    name = "security"
    
    # Patterns to detect
    SECRET_PATTERNS = {
        "api_key": re.compile(r'["\']?(?:api[_-]?key|apikey)["\']?\s*[:=]\s*["\']([a-zA-Z0-9_\-]{20,})["\']', re.IGNORECASE),
        "password": re.compile(r'["\']?(?:password|passwd|pwd)["\']?\s*[:=]\s*["\']([^"\']{8,})["\']', re.IGNORECASE),
        "token": re.compile(r'["\']?(?:token|auth[_-]?token)["\']?\s*[:=]\s*["\']([a-zA-Z0-9_\-]{20,})["\']', re.IGNORECASE),
        "aws_key": re.compile(r'AKIA[0-9A-Z]{16}'),
        "private_key": re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    }
    
    @classmethod
    def dependencies(cls) -> List[str]:
        """No dependencies - can run first."""
        return []
    
    async def analyze(
        self,
        repo: Repository,
        deps: Dict[str, Any],
    ) -> SecurityReport:
        """Scan repository for security issues."""
        
        findings: List[SecurityFinding] = []
        files_scanned = 0
        
        # Scan all code files
        for file_path in repo.get_files():
            if not self._should_scan(file_path):
                continue
            
            files_scanned += 1
            file_findings = self._scan_file(file_path)
            findings.extend(file_findings)
        
        # Count by severity
        severity_counts = {
            "critical": len([f for f in findings if f.severity == "critical"]),
            "high": len([f for f in findings if f.severity == "high"]),
            "medium": len([f for f in findings if f.severity == "medium"]),
            "low": len([f for f in findings if f.severity == "low"]),
        }
        
        return SecurityReport(
            findings=findings,
            total_files_scanned=files_scanned,
            critical_count=severity_counts["critical"],
            high_count=severity_counts["high"],
            medium_count=severity_counts["medium"],
            low_count=severity_counts["low"],
        )
    
    def _should_scan(self, file_path: Path) -> bool:
        """Check if file should be scanned."""
        # Skip binary files, images, etc.
        skip_extensions = {".png", ".jpg", ".gif", ".pdf", ".zip", ".pyc"}
        if file_path.suffix.lower() in skip_extensions:
            return False
        
        # Skip large files (> 1MB)
        if file_path.stat().st_size > 1024 * 1024:
            return False
        
        return True
    
    def _scan_file(self, file_path: Path) -> List[SecurityFinding]:
        """Scan single file for security issues."""
        findings = []
        
        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, start=1):
                    # Check each pattern
                    for category, pattern in self.SECRET_PATTERNS.items():
                        if match := pattern.search(line):
                            finding = SecurityFinding(
                                file_path=str(file_path),
                                line_number=line_num,
                                severity=self._get_severity(category),
                                category=category,
                                description=f"Potential {category} found in code",
                                code_snippet=line.strip(),
                            )
                            findings.append(finding)
        except Exception as e:
            # Log error but continue
            print(f"Error scanning {file_path}: {e}")
        
        return findings
    
    def _get_severity(self, category: str) -> str:
        """Map category to severity level."""
        severity_map = {
            "private_key": "critical",
            "aws_key": "critical",
            "api_key": "high",
            "token": "high",
            "password": "medium",
        }
        return severity_map.get(category, "low")
```

### Step 3: Register Analyzer

```python
# repoq_custom/__init__.py

from repoq.analyzers import registry
from .analyzers.security import SecurityAnalyzer

# Register custom analyzer
registry.register(SecurityAnalyzer.name, SecurityAnalyzer)
```

### Step 4: Use Your Analyzer

```python
# analyze_with_custom.py

from pathlib import Path
from repoq.pipeline import AnalysisPipeline
from repoq.config import QualityPolicy
from repoq_custom.analyzers.security import SecurityAnalyzer

async def main():
    # Create pipeline with custom analyzer
    pipeline = AnalysisPipeline(
        analyzers=[SecurityAnalyzer],
        config=QualityPolicy.load("quality_policy.yaml"),
    )
    
    # Run analysis
    result = await pipeline.analyze(
        repo_path=Path("."),
        output_dir=Path("output"),
        formats=["json", "markdown"],
    )
    
    # Access security results
    security = result.security
    print(f"Found {len(security.findings)} security issues")
    print(f"Critical: {security.critical_count}")
    print(f"High: {security.high_count}")
    print(f"Severity Score: {security.severity_score:.1f}/10")
    
    # Print findings
    for finding in security.findings:
        print(f"\n{finding.severity.upper()}: {finding.category}")
        print(f"  File: {finding.file_path}:{finding.line_number}")
        print(f"  Code: {finding.code_snippet}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Step 5: Test Your Analyzer

```python
# tests/test_security_analyzer.py

import pytest
from pathlib import Path
from repoq_custom.analyzers.security import SecurityAnalyzer, SecurityFinding
from repoq.core.model import Repository

@pytest.mark.asyncio
async def test_detects_api_key(tmp_path):
    """Test API key detection."""
    
    # Create test file with hardcoded key
    test_file = tmp_path / "config.py"
    test_file.write_text("""
API_KEY = "sk_live_abcdefghijklmnopqrstuvwxyz123456"
DATABASE_URL = "postgresql://localhost/db"
    """)
    
    # Create mock repository
    repo = Repository(path=tmp_path, files=[test_file])
    
    # Run analyzer
    analyzer = SecurityAnalyzer()
    result = await analyzer.analyze(repo, {})
    
    # Verify results
    assert len(result.findings) == 1
    assert result.findings[0].category == "api_key"
    assert result.findings[0].severity == "high"
    assert result.findings[0].line_number == 2

@pytest.mark.asyncio
async def test_no_false_positives(tmp_path):
    """Test no false positives on safe code."""
    
    test_file = tmp_path / "safe.py"
    test_file.write_text("""
# This is safe - no secrets
def get_api_key():
    return os.environ.get("API_KEY")
    """)
    
    repo = Repository(path=tmp_path, files=[test_file])
    analyzer = SecurityAnalyzer()
    result = await analyzer.analyze(repo, {})
    
    assert len(result.findings) == 0
```

Run tests:
```bash
pytest tests/test_security_analyzer.py -v
```

## Example 2: Dependency Analyzer

Analyzes external dependencies and checks for updates:

```python
# repoq_custom/analyzers/dependencies.py

import asyncio
import httpx
from dataclasses import dataclass
from typing import Dict, List
from packaging import version

from repoq.analyzers.base import BaseAnalyzer


@dataclass
class DependencyInfo:
    """Information about a dependency."""
    name: str
    current_version: str
    latest_version: str
    is_outdated: bool
    security_issues: int


class DependencyAnalyzer(BaseAnalyzer):
    """Analyze project dependencies for updates and security."""
    
    name = "dependencies"
    
    @classmethod
    def dependencies(cls) -> List[str]:
        """Depends on structure analysis."""
        return ["structure"]
    
    async def analyze(self, repo, deps):
        """Analyze dependencies."""
        structure = deps["structure"]
        
        # Find dependency files
        dep_files = self._find_dependency_files(structure)
        
        # Parse dependencies
        dependencies = await self._parse_dependencies(dep_files)
        
        # Check for updates
        results = await self._check_updates(dependencies)
        
        return results
    
    def _find_dependency_files(self, structure):
        """Find requirements.txt, pyproject.toml, etc."""
        patterns = ["requirements.txt", "pyproject.toml", "Pipfile"]
        return [f for f in structure.files if f.name in patterns]
    
    async def _check_updates(self, dependencies: List[str]):
        """Check PyPI for latest versions."""
        async with httpx.AsyncClient() as client:
            tasks = [
                self._check_package(client, dep)
                for dep in dependencies
            ]
            return await asyncio.gather(*tasks)
    
    async def _check_package(self, client, package_name):
        """Check single package on PyPI."""
        try:
            response = await client.get(
                f"https://pypi.org/pypi/{package_name}/json"
            )
            data = response.json()
            return {
                "name": package_name,
                "latest": data["info"]["version"],
            }
        except Exception:
            return None
```

## Example 3: Documentation Coverage

Checks docstring coverage:

```python
# repoq_custom/analyzers/docs_coverage.py

import ast
from dataclasses import dataclass
from typing import List

from repoq.analyzers.base import BaseAnalyzer


@dataclass
class DocsCoverageReport:
    """Documentation coverage statistics."""
    total_functions: int
    documented_functions: int
    total_classes: int
    documented_classes: int
    
    @property
    def function_coverage(self) -> float:
        """Function documentation coverage percentage."""
        if self.total_functions == 0:
            return 100.0
        return (self.documented_functions / self.total_functions) * 100
    
    @property
    def class_coverage(self) -> float:
        """Class documentation coverage percentage."""
        if self.total_classes == 0:
            return 100.0
        return (self.documented_classes / self.total_classes) * 100
    
    @property
    def overall_coverage(self) -> float:
        """Overall documentation coverage."""
        total = self.total_functions + self.total_classes
        documented = self.documented_functions + self.documented_classes
        if total == 0:
            return 100.0
        return (documented / total) * 100


class DocsAnalyzer(BaseAnalyzer):
    """Analyze documentation coverage."""
    
    name = "docs_coverage"
    
    @classmethod
    def dependencies(cls) -> List[str]:
        return ["structure"]
    
    async def analyze(self, repo, deps):
        """Analyze documentation coverage."""
        structure = deps["structure"]
        
        total_funcs = 0
        documented_funcs = 0
        total_classes = 0
        documented_classes = 0
        
        # Analyze each Python file
        for file in structure.files:
            if not file.path.endswith(".py"):
                continue
            
            with open(file.path) as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    total_funcs += 1
                    if ast.get_docstring(node):
                        documented_funcs += 1
                
                elif isinstance(node, ast.ClassDef):
                    total_classes += 1
                    if ast.get_docstring(node):
                        documented_classes += 1
        
        return DocsCoverageReport(
            total_functions=total_funcs,
            documented_functions=documented_funcs,
            total_classes=total_classes,
            documented_classes=documented_classes,
        )
```

## Best Practices

### 1. Keep Analyzers Focused

**Bad** (does too much):
```python
class MegaAnalyzer(BaseAnalyzer):
    """Analyzes everything."""
    async def analyze(self, repo, deps):
        # complexity + security + docs + dependencies
        ...  # 1000 lines
```

**Good** (single responsibility):
```python
class ComplexityAnalyzer(BaseAnalyzer):
    """Analyzes code complexity only."""
    async def analyze(self, repo, deps):
        ...  # 100 lines
```

### 2. Declare Dependencies

```python
class HotspotsAnalyzer(BaseAnalyzer):
    """Needs complexity AND history."""
    
    @classmethod
    def dependencies(cls):
        return ["complexity", "history"]  # Will run after these
```

### 3. Handle Errors Gracefully

```python
async def analyze(self, repo, deps):
    try:
        result = await self._analyze_impl(repo, deps)
        return result
    except FileNotFoundError:
        # Return empty result, not error
        return EmptyResult()
    except Exception as e:
        # Log but don't crash pipeline
        logger.error(f"Analyzer failed: {e}")
        return PartialResult(error=str(e))
```

### 4. Make Analyzers Configurable

```python
class CustomAnalyzer(BaseAnalyzer):
    def __init__(self, config):
        self.threshold = config.get("threshold", 10)
        self.enabled = config.get("enabled", True)
    
    async def analyze(self, repo, deps):
        if not self.enabled:
            return None
        ...
```

## Next Steps

- **[Tutorial 3: CI/CD Integration](03-ci-cd-integration.md)** - Run custom analyzers in CI
- **[Tutorial 4: Advanced Filtering](04-advanced-filtering.md)** - Target specific files
- **[Architecture: Analyzer Pipeline](../architecture/analyzer-pipeline.md)** - Deep dive

## Summary

You learned how to:

- ✅ Create custom analyzers with `BaseAnalyzer`
- ✅ Implement security, dependency, and docs analyzers
- ✅ Register and configure analyzers
- ✅ Test analyzers with pytest
- ✅ Follow best practices for maintainability

**Key Takeaways:**

1. **Focused analyzers**: One responsibility per analyzer
2. **Dependency management**: Declare what you need
3. **Error handling**: Fail gracefully
4. **Testability**: Write unit tests
5. **Configuration**: Make it flexible

---

!!! tip "Share Your Analyzer"
    Built something useful? Consider contributing it back to RepoQ!
    See [Contributing Guide](../development/CONTRIBUTING.md)
