"""Quality Policy Configuration Parser and Validator.

TDD Cycle 4 - GREEN Phase.

Features:
- YAML policy parsing with schema validation
- Default values for optional fields
- Gate configuration (soundness, confluence, termination)
- Stratification policy integration
- Quality thresholds validation

YAML Schema (.github/quality-policy.yml):
```yaml
version: "1.0"
project:
  name: "repoq"
  language: "python"

gates:
  soundness:
    enabled: true
    fail_on_error: true
  confluence:
    enabled: true
    check_critical_pairs: true
    completion_strategy: "knuth-bendix"
  termination:
    enabled: true
    max_iterations: 1000
    timeout_seconds: 30

stratification:
  max_level: 10
  allow_self_analysis: true
  self_analysis_max_level: 2

quality_thresholds:
  test_coverage_min: 0.80
  complexity_max: 15
  duplication_max: 0.05
```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Default values
DEFAULT_VERSION = "1.0"
DEFAULT_MAX_LEVEL = 10
DEFAULT_SELF_ANALYSIS_MAX_LEVEL = 2
DEFAULT_TEST_COVERAGE_MIN = 0.70
DEFAULT_COMPLEXITY_MAX = 15
DEFAULT_DUPLICATION_MAX = 0.10


@dataclass
class GateConfig:
    """Configuration for a single quality gate.

    Attributes:
        enabled: Whether gate is enabled.
        fail_on_error: Whether to fail build on gate error.
    """

    enabled: bool = True
    fail_on_error: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GateConfig:
        """Create GateConfig from dict."""
        return cls(enabled=data.get("enabled", True), fail_on_error=data.get("fail_on_error", True))


@dataclass
class SoundnessGateConfig(GateConfig):
    """Soundness gate configuration."""

    pass


@dataclass
class ConfluenceGateConfig(GateConfig):
    """Confluence gate configuration.

    Attributes:
        check_critical_pairs: Whether to check critical pairs.
        completion_strategy: Completion strategy (knuth-bendix, etc.).
    """

    check_critical_pairs: bool = True
    completion_strategy: str = "knuth-bendix"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConfluenceGateConfig:
        """Create ConfluenceGateConfig from dict."""
        return cls(
            enabled=data.get("enabled", True),
            fail_on_error=data.get("fail_on_error", True),
            check_critical_pairs=data.get("check_critical_pairs", True),
            completion_strategy=data.get("completion_strategy", "knuth-bendix"),
        )


@dataclass
class TerminationGateConfig(GateConfig):
    """Termination gate configuration.

    Attributes:
        max_iterations: Maximum iterations before timeout.
        timeout_seconds: Timeout in seconds.
    """

    max_iterations: int = 1000
    timeout_seconds: int = 30

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TerminationGateConfig:
        """Create TerminationGateConfig from dict."""
        return cls(
            enabled=data.get("enabled", True),
            fail_on_error=data.get("fail_on_error", True),
            max_iterations=data.get("max_iterations", 1000),
            timeout_seconds=data.get("timeout_seconds", 30),
        )


@dataclass
class GatesConfig:
    """Configuration for all quality gates.

    Attributes:
        soundness: Soundness gate config.
        confluence: Confluence gate config.
        termination: Termination gate config.
    """

    soundness: SoundnessGateConfig = field(default_factory=SoundnessGateConfig)
    confluence: ConfluenceGateConfig = field(default_factory=ConfluenceGateConfig)
    termination: TerminationGateConfig = field(default_factory=TerminationGateConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GatesConfig:
        """Create GatesConfig from dict."""
        return cls(
            soundness=SoundnessGateConfig.from_dict(data.get("soundness", {})),
            confluence=ConfluenceGateConfig.from_dict(data.get("confluence", {})),
            termination=TerminationGateConfig.from_dict(data.get("termination", {})),
        )


@dataclass
class StratificationConfig:
    """Stratification policy configuration.

    Attributes:
        max_level: Maximum stratification level.
        allow_self_analysis: Whether self-analysis is allowed.
        self_analysis_max_level: Maximum level for self-analysis.
    """

    max_level: int = DEFAULT_MAX_LEVEL
    allow_self_analysis: bool = True
    self_analysis_max_level: int = DEFAULT_SELF_ANALYSIS_MAX_LEVEL

    def is_valid_self_analysis_level(self, level: int) -> bool:
        """Check if level is valid for self-analysis.

        Args:
            level: Level to check.

        Returns:
            True if level <= self_analysis_max_level, False otherwise.
        """
        if not self.allow_self_analysis:
            return False
        return level <= self.self_analysis_max_level

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StratificationConfig:
        """Create StratificationConfig from dict."""
        return cls(
            max_level=data.get("max_level", DEFAULT_MAX_LEVEL),
            allow_self_analysis=data.get("allow_self_analysis", True),
            self_analysis_max_level=data.get(
                "self_analysis_max_level", DEFAULT_SELF_ANALYSIS_MAX_LEVEL
            ),
        )


@dataclass
class QualityThresholdsConfig:
    """Quality thresholds configuration.

    Attributes:
        test_coverage_min: Minimum test coverage (0.0-1.0).
        complexity_max: Maximum cyclomatic complexity.
        duplication_max: Maximum code duplication (0.0-1.0).
    """

    test_coverage_min: float = DEFAULT_TEST_COVERAGE_MIN
    complexity_max: int = DEFAULT_COMPLEXITY_MAX
    duplication_max: float = DEFAULT_DUPLICATION_MAX

    def validate_coverage(self, coverage: float) -> bool:
        """Validate test coverage against threshold.

        Args:
            coverage: Actual coverage (0.0-1.0).

        Returns:
            True if coverage >= test_coverage_min, False otherwise.
        """
        return coverage >= self.test_coverage_min

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QualityThresholdsConfig:
        """Create QualityThresholdsConfig from dict."""
        return cls(
            test_coverage_min=data.get("test_coverage_min", DEFAULT_TEST_COVERAGE_MIN),
            complexity_max=data.get("complexity_max", DEFAULT_COMPLEXITY_MAX),
            duplication_max=data.get("duplication_max", DEFAULT_DUPLICATION_MAX),
        )


@dataclass
class ProjectConfig:
    """Project metadata configuration.

    Attributes:
        name: Project name.
        language: Primary programming language.
    """

    name: str
    language: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectConfig:
        """Create ProjectConfig from dict."""
        if "name" not in data:
            raise ValueError("Missing required field: project.name")
        if "language" not in data:
            raise ValueError("Missing required field: project.language")

        return cls(name=data["name"], language=data["language"])


@dataclass
class QualityPolicy:
    """Quality policy configuration.

    Attributes:
        version: Policy schema version.
        project: Project metadata.
        gates: Gate configurations.
        stratification: Stratification policy.
        quality_thresholds: Quality thresholds.
    """

    version: str
    project: ProjectConfig
    gates: GatesConfig = field(default_factory=GatesConfig)
    stratification: StratificationConfig = field(default_factory=StratificationConfig)
    quality_thresholds: QualityThresholdsConfig = field(default_factory=QualityThresholdsConfig)

    def __init__(
        self,
        version: str,
        project: dict[str, Any] | ProjectConfig,
        gates: dict[str, Any] | GatesConfig | None = None,
        stratification: dict[str, Any] | StratificationConfig | None = None,
        quality_thresholds: dict[str, Any] | QualityThresholdsConfig | None = None,
    ):
        """Initialize QualityPolicy."""
        self.version = version

        # Convert project dict to ProjectConfig
        if isinstance(project, dict):
            self.project = ProjectConfig.from_dict(project)
        else:
            self.project = project

        # Convert gates dict to GatesConfig
        if gates is None:
            self.gates = GatesConfig()
        elif isinstance(gates, dict):
            self.gates = GatesConfig.from_dict(gates)
        else:
            self.gates = gates

        # Convert stratification dict to StratificationConfig
        if stratification is None:
            self.stratification = StratificationConfig()
        elif isinstance(stratification, dict):
            self.stratification = StratificationConfig.from_dict(stratification)
        else:
            self.stratification = stratification

        # Convert quality_thresholds dict to QualityThresholdsConfig
        if quality_thresholds is None:
            self.quality_thresholds = QualityThresholdsConfig()
        elif isinstance(quality_thresholds, dict):
            self.quality_thresholds = QualityThresholdsConfig.from_dict(quality_thresholds)
        else:
            self.quality_thresholds = quality_thresholds


class QualityPolicyParser:
    """Parser for quality policy YAML files."""

    def parse(self, file_path: Path | str) -> QualityPolicy:
        """Parse quality policy from YAML file.

        Args:
            file_path: Path to YAML file.

        Returns:
            QualityPolicy instance.

        Raises:
            ValueError: If YAML is invalid or missing required fields.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise ValueError(f"Policy file not found: {file_path}")

        # Parse YAML
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax: {e}")

        # Validate required fields
        if "version" not in data:
            raise ValueError("Missing required field: version")
        if "project" not in data:
            raise ValueError("Missing required field: project")

        # Create policy
        return QualityPolicy(
            version=data["version"],
            project=data["project"],
            gates=data.get("gates"),
            stratification=data.get("stratification"),
            quality_thresholds=data.get("quality_thresholds"),
        )


class QualityPolicyGenerator:
    """Generator for default quality policy files."""

    def generate_default(self, output_path: Path | str) -> None:
        """Generate default quality-policy.yml file.

        Args:
            output_path: Path to output file.
        """
        output_path = Path(output_path)

        default_policy = {
            "version": DEFAULT_VERSION,
            "project": {"name": "repoq", "language": "python"},
            "gates": {
                "soundness": {"enabled": True, "fail_on_error": True},
                "confluence": {
                    "enabled": True,
                    "check_critical_pairs": True,
                    "completion_strategy": "knuth-bendix",
                },
                "termination": {"enabled": True, "max_iterations": 1000, "timeout_seconds": 30},
            },
            "stratification": {
                "max_level": DEFAULT_MAX_LEVEL,
                "allow_self_analysis": True,
                "self_analysis_max_level": DEFAULT_SELF_ANALYSIS_MAX_LEVEL,
            },
            "quality_thresholds": {
                "test_coverage_min": 0.80,
                "complexity_max": DEFAULT_COMPLEXITY_MAX,
                "duplication_max": DEFAULT_DUPLICATION_MAX,
            },
        }

        # Write YAML
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(default_policy, f, default_flow_style=False, sort_keys=False)


class QualityPolicyValidator:
    """Validator for quality policy data."""

    def validate(self, policy_data: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate policy data against schema.

        Args:
            policy_data: Policy data dict.

        Returns:
            Tuple of (is_valid, errors).
        """
        errors = []

        # Check required fields
        if "version" not in policy_data:
            errors.append("Missing required field: version")

        if "project" not in policy_data:
            errors.append("Missing required field: project")
        else:
            project = policy_data["project"]
            if "name" not in project:
                errors.append("Missing required field: project.name")
            if "language" not in project:
                errors.append("Missing required field: project.language")

        is_valid = len(errors) == 0
        return is_valid, errors


def load_policy(repo_root: Path | str, use_defaults: bool = False) -> QualityPolicy:
    """Load quality policy from .github/quality-policy.yml.

    Args:
        repo_root: Repository root directory.
        use_defaults: Whether to use default policy if file not found.

    Returns:
        QualityPolicy instance.

    Raises:
        ValueError: If policy file not found and use_defaults=False.
    """
    repo_root = Path(repo_root)
    policy_file = repo_root / ".github" / "quality-policy.yml"

    if not policy_file.exists():
        if use_defaults:
            # Return default policy
            return QualityPolicy(
                version=DEFAULT_VERSION, project={"name": "repoq", "language": "python"}
            )
        else:
            raise ValueError(f"Policy file not found: {policy_file}")

    parser = QualityPolicyParser()
    return parser.parse(policy_file)
