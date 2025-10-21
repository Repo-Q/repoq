"""
TDD Cycle 4 - RED Phase: Quality Policy Configuration Tests

Tests for:
- YAML schema validation
- Quality policy parsing
- Default values handling
- Gate configuration (soundness, confluence, termination)
- Integration with StratificationGuard
"""

import pytest
from pathlib import Path
from typing import Any


class TestQualityPolicyParser:
    """Test YAML policy parsing and validation."""
    
    def test_parse_valid_policy(self, tmp_path):
        """RED: Parse valid quality-policy.yml."""
        from repoq.config.quality_policy import QualityPolicyParser
        
        # Create valid policy file
        policy_file = tmp_path / "quality-policy.yml"
        policy_file.write_text("""
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
  
  termination:
    enabled: true
    max_iterations: 1000

stratification:
  max_level: 3
  allow_self_analysis: true
  self_analysis_max_level: 2

quality_thresholds:
  test_coverage_min: 0.80
  complexity_max: 15
  duplication_max: 0.05
""")
        
        parser = QualityPolicyParser()
        policy = parser.parse(policy_file)
        
        assert policy.version == "1.0"
        assert policy.project.name == "repoq"
        assert policy.gates.soundness.enabled is True
        assert policy.stratification.max_level == 3
        assert policy.quality_thresholds.test_coverage_min == 0.80
    
    def test_parse_missing_required_fields(self, tmp_path):
        """RED: Parser rejects YAML missing required fields."""
        from repoq.config.quality_policy import QualityPolicyParser
        
        # Missing 'version' field
        policy_file = tmp_path / "invalid-policy.yml"
        policy_file.write_text("""
project:
  name: "test"
""")
        
        parser = QualityPolicyParser()
        
        with pytest.raises(ValueError, match="(?i)missing required field.*version"):
            parser.parse(policy_file)
    
    def test_parse_invalid_yaml_syntax(self, tmp_path):
        """RED: Parser rejects invalid YAML syntax."""
        from repoq.config.quality_policy import QualityPolicyParser
        
        policy_file = tmp_path / "bad-syntax.yml"
        policy_file.write_text("""
version: "1.0"
project:
  name: "test"
  invalid syntax here: [unclosed bracket
""")
        
        parser = QualityPolicyParser()
        
        with pytest.raises(ValueError, match="(?i)invalid yaml"):
            parser.parse(policy_file)
    
    def test_default_values_applied(self, tmp_path):
        """RED: Parser applies default values for optional fields."""
        from repoq.config.quality_policy import QualityPolicyParser
        
        # Minimal valid policy (only required fields)
        policy_file = tmp_path / "minimal-policy.yml"
        policy_file.write_text("""
version: "1.0"
project:
  name: "test"
  language: "python"
""")
        
        parser = QualityPolicyParser()
        policy = parser.parse(policy_file)
        
        # Check defaults
        assert policy.gates.soundness.enabled is True  # default
        assert policy.stratification.max_level == 10  # default
        assert policy.quality_thresholds.test_coverage_min == 0.70  # default


class TestQualityPolicyGates:
    """Test gate configuration and validation."""
    
    def test_soundness_gate_configuration(self):
        """RED: Soundness gate reads config correctly."""
        from repoq.config.quality_policy import QualityPolicy, GateConfig
        
        policy = QualityPolicy(
            version="1.0",
            project={"name": "test", "language": "python"},
            gates={
                "soundness": {"enabled": True, "fail_on_error": True}
            }
        )
        
        gate = policy.gates.soundness
        assert gate.enabled is True
        assert gate.fail_on_error is True
    
    def test_confluence_gate_configuration(self):
        """RED: Confluence gate reads config correctly."""
        from repoq.config.quality_policy import QualityPolicy
        
        policy = QualityPolicy(
            version="1.0",
            project={"name": "test", "language": "python"},
            gates={
                "confluence": {
                    "enabled": True,
                    "check_critical_pairs": True,
                    "completion_strategy": "knuth-bendix"
                }
            }
        )
        
        gate = policy.gates.confluence
        assert gate.enabled is True
        assert gate.check_critical_pairs is True
        assert gate.completion_strategy == "knuth-bendix"
    
    def test_termination_gate_configuration(self):
        """RED: Termination gate reads config correctly."""
        from repoq.config.quality_policy import QualityPolicy
        
        policy = QualityPolicy(
            version="1.0",
            project={"name": "test", "language": "python"},
            gates={
                "termination": {
                    "enabled": True,
                    "max_iterations": 1000,
                    "timeout_seconds": 30
                }
            }
        )
        
        gate = policy.gates.termination
        assert gate.enabled is True
        assert gate.max_iterations == 1000
        assert gate.timeout_seconds == 30


class TestStratificationPolicyIntegration:
    """Test stratification policy integration with StratificationGuard."""
    
    def test_stratification_policy_max_level(self):
        """RED: Stratification policy enforces max_level."""
        from repoq.config.quality_policy import QualityPolicy
        from repoq.core.stratification_guard import StratificationGuard
        
        policy = QualityPolicy(
            version="1.0",
            project={"name": "test", "language": "python"},
            stratification={
                "max_level": 3,
                "allow_self_analysis": True,
                "self_analysis_max_level": 2
            }
        )
        
        guard = StratificationGuard.from_policy(policy)
        
        # L0 → L3: Should be allowed (max_level=3)
        result = guard.check_transition(from_level=0, to_level=3)
        assert result.is_safe is True
        
        # L0 → L4: Should be rejected (exceeds max_level)
        result = guard.check_transition_with_policy(from_level=0, to_level=4, policy=policy)
        assert result.is_safe is False
        assert "max level" in result.reason.lower()
    
    def test_self_analysis_level_constraint(self):
        """RED: Self-analysis respects policy max level."""
        from repoq.config.quality_policy import QualityPolicy
        
        policy = QualityPolicy(
            version="1.0",
            project={"name": "test", "language": "python"},
            stratification={
                "allow_self_analysis": True,
                "self_analysis_max_level": 2
            }
        )
        
        # Self-analysis at L2: VALID
        assert policy.stratification.is_valid_self_analysis_level(2) is True
        
        # Self-analysis at L3: INVALID (exceeds limit)
        assert policy.stratification.is_valid_self_analysis_level(3) is False


class TestQualityThresholds:
    """Test quality threshold configuration."""
    
    def test_test_coverage_threshold(self):
        """RED: Test coverage threshold reads correctly."""
        from repoq.config.quality_policy import QualityPolicy
        
        policy = QualityPolicy(
            version="1.0",
            project={"name": "test", "language": "python"},
            quality_thresholds={
                "test_coverage_min": 0.80,
                "complexity_max": 15,
                "duplication_max": 0.05
            }
        )
        
        thresholds = policy.quality_thresholds
        assert thresholds.test_coverage_min == 0.80
        assert thresholds.complexity_max == 15
        assert thresholds.duplication_max == 0.05
    
    def test_threshold_validation(self):
        """RED: Thresholds validate against actual metrics."""
        from repoq.config.quality_policy import QualityPolicy
        
        policy = QualityPolicy(
            version="1.0",
            project={"name": "test", "language": "python"},
            quality_thresholds={"test_coverage_min": 0.80}
        )
        
        # Coverage 0.85 > 0.80: PASS
        assert policy.quality_thresholds.validate_coverage(0.85) is True
        
        # Coverage 0.75 < 0.80: FAIL
        assert policy.quality_thresholds.validate_coverage(0.75) is False


class TestGitHubPolicyFileGeneration:
    """Test .github/quality-policy.yml generation."""
    
    def test_generate_default_policy_file(self, tmp_path):
        """RED: Generate default .github/quality-policy.yml."""
        from repoq.config.quality_policy import QualityPolicyGenerator
        
        output_file = tmp_path / "quality-policy.yml"
        
        generator = QualityPolicyGenerator()
        generator.generate_default(output_file)
        
        # Verify file created
        assert output_file.exists()
        
        # Verify parseable
        from repoq.config.quality_policy import QualityPolicyParser
        parser = QualityPolicyParser()
        policy = parser.parse(output_file)
        
        assert policy.version == "1.0"
        assert policy.project.name == "repoq"
    
    def test_validate_schema_compliance(self):
        """RED: Validate policy against JSON Schema."""
        from repoq.config.quality_policy import QualityPolicyValidator
        
        policy_data = {
            "version": "1.0",
            "project": {
                "name": "test",
                "language": "python"
            },
            "gates": {
                "soundness": {"enabled": True}
            }
        }
        
        validator = QualityPolicyValidator()
        is_valid, errors = validator.validate(policy_data)
        
        assert is_valid is True
        assert len(errors) == 0


class TestPolicyLoaderIntegration:
    """Test policy loader integration with existing config system."""
    
    def test_load_from_github_directory(self, tmp_path):
        """RED: Load policy from .github/quality-policy.yml."""
        from repoq.config.quality_policy import load_policy
        
        # Create .github directory
        github_dir = tmp_path / ".github"
        github_dir.mkdir()
        
        policy_file = github_dir / "quality-policy.yml"
        policy_file.write_text("""
version: "1.0"
project:
  name: "test"
  language: "python"
""")
        
        # Load policy (should auto-discover .github/quality-policy.yml)
        policy = load_policy(repo_root=tmp_path)
        
        assert policy.version == "1.0"
        assert policy.project.name == "test"
    
    def test_fallback_to_default_policy(self, tmp_path):
        """RED: Fallback to default policy if file not found."""
        from repoq.config.quality_policy import load_policy
        
        # No policy file exists
        policy = load_policy(repo_root=tmp_path, use_defaults=True)
        
        # Should return default policy
        assert policy.version == "1.0"
        assert policy.gates.soundness.enabled is True
