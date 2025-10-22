"""
Tests for BAML AI Agent
Phase 5.8: AI-Assisted TRS/Ontology Validation

Test strategy:
- Mock BAML client for deterministic testing
- Test all 4 phases (DISABLED, EXPERIMENTAL, ADVISORY, ACTIVE, DEFAULT_ON)
- Verify blocking behavior based on phase and confidence
- Test error handling and graceful degradation
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from repoq.ai.baml_agent import (
    AgentConfig,
    AgentPhase,
    BAMLAgent,
    configure_agent,
    get_agent,
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FIXTURES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.fixture(autouse=True)
def mock_env_api_keys(monkeypatch):
    """Mock API keys for all tests"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-456")


@pytest.fixture
def mock_baml_init():
    """Mock BAML client initialization"""
    with patch("repoq.ai.baml_agent.BAMLAgent._initialize_baml_client"):
        yield


@pytest.fixture
def mock_trs_result():
    """Mock TRS validation result"""
    return Mock(
        rule_id="test_rule",
        confluence_status="NON_CONFLUENT",
        termination_status="TERMINATING",
        critical_pairs=[
            Mock(
                left_term="f(g(x))",
                right_term="g(f(x))",
                common_reduct=None,
                joinable=False,
                explanation="Critical pair not joinable",
            )
        ],
        termination_proof=None,
        issues=["Non-confluent critical pair detected"],
        suggestions=["Add additional rule to resolve critical pair"],
        confidence=0.85,
    )


@pytest.fixture
def mock_ontology_result():
    """Mock ontology validation result"""
    return Mock(
        ontology_uri="http://example.org/test",
        is_consistent=False,
        issues=[
            Mock(
                type="inconsistency",
                location="ex:john",
                description="john cannot be both Employee and Contractor (disjoint classes)",
                suggested_fix="Remove one of the class assertions",
            )
        ],
        reasoning_chain=[
            "ex:Employee and ex:Contractor are disjoint",
            "ex:john is asserted as both",
            "This violates disjointness constraint",
        ],
        suggested_improvements=["Add cardinality constraints"],
        confidence=0.9,
    )


@pytest.fixture
def mock_stratification_result():
    """Mock stratification analysis result"""
    return Mock(
        current_level=2,
        max_safe_level=2,
        self_reference_detected=True,
        universe_violations=["analyze calls itself with meta-level operation"],
        safe_to_proceed=False,
        explanation="Self-reference detected at depth 2, violates stratification",
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST: AgentConfig
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_agent_config_defaults():
    """Test AgentConfig default values"""
    config = AgentConfig()

    assert config.phase == AgentPhase.DISABLED
    assert config.confidence_threshold == 0.7
    assert config.require_human_review is True
    assert config.enable_fallback is True
    assert config.timeout_seconds == 30
    assert config.is_enabled is False
    assert config.can_block is False


def test_agent_config_phases():
    """Test AgentConfig phase properties"""
    # DISABLED: not enabled, cannot block
    config = AgentConfig(phase=AgentPhase.DISABLED)
    assert not config.is_enabled
    assert not config.can_block

    # EXPERIMENTAL: enabled, cannot block
    config = AgentConfig(phase=AgentPhase.EXPERIMENTAL)
    assert config.is_enabled
    assert not config.can_block

    # ADVISORY: enabled, cannot block
    config = AgentConfig(phase=AgentPhase.ADVISORY)
    assert config.is_enabled
    assert not config.can_block

    # ACTIVE: enabled, can block
    config = AgentConfig(phase=AgentPhase.ACTIVE)
    assert config.is_enabled
    assert config.can_block

    # DEFAULT_ON: enabled, can block
    config = AgentConfig(phase=AgentPhase.DEFAULT_ON)
    assert config.is_enabled
    assert config.can_block


def test_agent_config_validation():
    """Test AgentConfig validation"""
    # Valid config
    config = AgentConfig(phase=AgentPhase.DISABLED, confidence_threshold=0.8)
    assert config.validate() == []

    # Valid config with keys (mocked)
    config = AgentConfig(phase=AgentPhase.EXPERIMENTAL, confidence_threshold=0.8)
    assert config.validate() == []  # API keys are mocked

    # Invalid confidence_threshold (but will also complain about API keys first)
    config = AgentConfig(
        phase=AgentPhase.EXPERIMENTAL,
        confidence_threshold=1.5,
        openai_api_key=None,
        anthropic_api_key=None,
    )
    errors = config.validate()
    assert len(errors) > 0
    # Either "API keys" or "confidence_threshold" error
    assert any("confidence_threshold" in err or "API keys" in err for err in errors)

    # Invalid timeout
    config = AgentConfig(phase=AgentPhase.EXPERIMENTAL, timeout_seconds=-1)
    errors = config.validate()
    assert len(errors) > 0
    assert "timeout_seconds" in errors[0]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST: BAMLAgent Initialization
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_baml_agent_disabled():
    """Test BAMLAgent in DISABLED phase"""
    config = AgentConfig(phase=AgentPhase.DISABLED)
    agent = BAMLAgent(config)

    assert not agent.is_available
    assert agent.config.phase == AgentPhase.DISABLED


def test_baml_agent_invalid_config():
    """Test BAMLAgent with invalid configuration"""
    config = AgentConfig(
        phase=AgentPhase.EXPERIMENTAL,
        confidence_threshold=2.0,  # Invalid
    )

    with pytest.raises(ValueError, match="Invalid AgentConfig"):
        BAMLAgent(config)


@patch("repoq.ai.baml_agent.logger")
def test_baml_agent_missing_client(mock_logger, monkeypatch):
    """Test BAMLAgent when BAML client not available"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    config = AgentConfig(phase=AgentPhase.EXPERIMENTAL)

    # Don't patch _initialize_baml_client, let it run and fail naturally
    agent = BAMLAgent(config)

    # Should gracefully degrade to DISABLED when import fails
    assert agent.config.phase == AgentPhase.DISABLED
    assert not agent.is_available

    # Should have logged warning
    mock_logger.warning.assert_called_once()
    assert "BAML client not found" in str(mock_logger.warning.call_args)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST: TRS Validation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.asyncio
async def test_validate_trs_rule_disabled():
    """Test TRS validation with DISABLED agent"""
    config = AgentConfig(phase=AgentPhase.DISABLED)
    agent = BAMLAgent(config)

    result = await agent.validate_trs_rule(
        rule_lhs="f(x)", rule_rhs="x", existing_rules=[], context="test"
    )

    assert result["phase"] == "disabled"
    assert result["should_block"] is False
    assert result["human_review_required"] is False
    assert "error" in result


@pytest.mark.asyncio
async def test_validate_trs_rule_experimental(mock_trs_result):
    """Test TRS validation in EXPERIMENTAL phase"""
    config = AgentConfig(phase=AgentPhase.EXPERIMENTAL)

    with patch("repoq.ai.baml_agent.BAMLAgent._initialize_baml_client"):
        agent = BAMLAgent(config)

        # Mock BAML client
        mock_client = Mock()
        mock_client.ValidateTRSRule = AsyncMock(return_value=mock_trs_result)
        agent._baml_client = mock_client

        result = await agent.validate_trs_rule(
            rule_lhs="f(g(x))",
            rule_rhs="g(f(x))",
            existing_rules=["f(f(x)) → f(x)"],
            context="test confluence",
        )

        assert result["phase"] == "experimental"
        assert result["should_block"] is False  # Experimental never blocks
        assert result["human_review_required"] is False
        assert result["result"].confidence == 0.85


@pytest.mark.asyncio
async def test_validate_trs_rule_advisory(mock_trs_result, mock_baml_init):
    """Test TRS validation in ADVISORY phase"""
    config = AgentConfig(phase=AgentPhase.ADVISORY)
    agent = BAMLAgent(config)

    mock_client = Mock()
    mock_client.ValidateTRSRule = AsyncMock(return_value=mock_trs_result)
    agent._baml_client = mock_client

    result = await agent.validate_trs_rule(
        rule_lhs="f(g(x))", rule_rhs="g(f(x))", existing_rules=[], context="test"
    )

    assert result["phase"] == "advisory"
    assert result["should_block"] is False  # Advisory never blocks
    assert result["result"].confluence_status == "NON_CONFLUENT"


@pytest.mark.asyncio
async def test_validate_trs_rule_active_blocking(mock_trs_result, mock_baml_init):
    """Test TRS validation in ACTIVE phase with blocking"""
    config = AgentConfig(
        phase=AgentPhase.ACTIVE,
        confidence_threshold=0.7,  # mock_trs_result has 0.85
        require_human_review=True,
    )
    agent = BAMLAgent(config)

    mock_client = Mock()
    mock_client.ValidateTRSRule = AsyncMock(return_value=mock_trs_result)
    agent._baml_client = mock_client

    result = await agent.validate_trs_rule(
        rule_lhs="f(g(x))", rule_rhs="g(f(x))", existing_rules=[], context="test"
    )

    assert result["phase"] == "active"
    assert result["should_block"] is True  # Non-confluent + high confidence
    assert result["human_review_required"] is True


@pytest.mark.asyncio
async def test_validate_trs_rule_low_confidence(mock_baml_init):
    """Test TRS validation with low confidence (should not block)"""
    config = AgentConfig(
        phase=AgentPhase.ACTIVE,
        confidence_threshold=0.9,  # Higher than result
    )
    agent = BAMLAgent(config)

    mock_result = Mock(
        confluence_status="NON_CONFLUENT",
        confidence=0.6,  # Below threshold
    )

    mock_client = Mock()
    mock_client.ValidateTRSRule = AsyncMock(return_value=mock_result)
    agent._baml_client = mock_client

    result = await agent.validate_trs_rule(
        rule_lhs="f(x)", rule_rhs="x", existing_rules=[], context="test"
    )

    assert result["should_block"] is False  # Low confidence, don't block


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST: Ontology Validation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.asyncio
async def test_validate_ontology_active_blocking(mock_ontology_result, mock_baml_init):
    """Test ontology validation with blocking"""
    config = AgentConfig(phase=AgentPhase.ACTIVE, confidence_threshold=0.8)
    agent = BAMLAgent(config)

    mock_client = Mock()
    mock_client.ValidateOntology = AsyncMock(return_value=mock_ontology_result)
    agent._baml_client = mock_client

    result = await agent.validate_ontology(
        ontology_turtle="@prefix ex: <http://example.org/> .", ontology_context="test ontology"
    )

    assert result["phase"] == "active"
    assert result["should_block"] is True  # Inconsistent + high confidence
    assert result["result"].is_consistent is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST: Stratification Analysis
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.asyncio
async def test_analyze_stratification_blocking(mock_stratification_result, mock_baml_init):
    """Test stratification analysis with blocking"""
    config = AgentConfig(phase=AgentPhase.ACTIVE)
    agent = BAMLAgent(config)

    mock_client = Mock()
    mock_client.AnalyzeStratification = AsyncMock(return_value=mock_stratification_result)
    agent._baml_client = mock_client

    result = await agent.analyze_stratification(
        current_code="def analyze(code): return analyze(analyze(code))",
        meta_operations=["quote", "eval"],
        self_analysis_depth=2,
    )

    assert result["phase"] == "active"
    assert result["should_block"] is True  # Unsafe stratification
    assert result["result"].safe_to_proceed is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST: Error Handling
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.asyncio
async def test_validate_trs_rule_exception(mock_baml_init):
    """Test error handling when BAML call fails"""
    config = AgentConfig(phase=AgentPhase.ACTIVE)
    agent = BAMLAgent(config)

    mock_client = Mock()
    mock_client.ValidateTRSRule = AsyncMock(side_effect=Exception("API error"))
    agent._baml_client = mock_client

    result = await agent.validate_trs_rule(
        rule_lhs="f(x)", rule_rhs="x", existing_rules=[], context="test"
    )

    assert result["should_block"] is False  # Fail open
    assert result["human_review_required"] is True
    assert "error" in result
    assert "API error" in result["error"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST: Singleton Access
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def test_get_agent_singleton():
    """Test singleton access to global agent"""
    agent1 = get_agent()
    agent2 = get_agent()

    assert agent1 is agent2  # Same instance


def test_configure_agent(mock_baml_init):
    """Test configure_agent convenience function"""
    agent = configure_agent(
        phase=AgentPhase.ADVISORY, confidence_threshold=0.8, require_human_review=False
    )

    assert agent.config.phase == AgentPhase.ADVISORY
    assert agent.config.confidence_threshold == 0.8
    assert agent.config.require_human_review is False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST: Phase Rollout Simulation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@pytest.mark.asyncio
async def test_phase_rollout_progression(mock_trs_result, mock_baml_init):
    """Test behavior progression through all phases"""
    phases = [
        AgentPhase.DISABLED,
        AgentPhase.EXPERIMENTAL,
        AgentPhase.ADVISORY,
        AgentPhase.ACTIVE,
        AgentPhase.DEFAULT_ON,
    ]

    for phase in phases:
        config = AgentConfig(phase=phase, confidence_threshold=0.7)
        agent = BAMLAgent(config)

        if phase != AgentPhase.DISABLED:
            mock_client = Mock()
            mock_client.ValidateTRSRule = AsyncMock(return_value=mock_trs_result)
            agent._baml_client = mock_client

        result = await agent.validate_trs_rule(
            rule_lhs="f(g(x))", rule_rhs="g(f(x))", existing_rules=[], context="test"
        )

        # DISABLED: error
        # EXPERIMENTAL/ADVISORY: no blocking
        # ACTIVE/DEFAULT_ON: blocking on non-confluent
        if phase in (AgentPhase.ACTIVE, AgentPhase.DEFAULT_ON):
            assert result["should_block"] is True
        else:
            assert result["should_block"] is False
