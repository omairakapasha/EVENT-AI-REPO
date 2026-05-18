"""
Thinking budget tests — TriageAgent and specialist agents.

Context: The pipeline uses OpenAIChatCompletionsModel pointed at Gemini's
OpenAI-compatible REST endpoint. That endpoint does NOT support a
`thinking_budget` parameter via the Chat Completions API — passing it via
`extra_args` causes a TypeError at runtime.

The correct fix is to NOT set any `model_settings` with `extra_args` on any
agent. The Gemini OpenAI-compatible endpoint does not perform extended thinking
via the Chat Completions path, so no per-agent override is needed.

These tests verify that no agent has a `model_settings` with `extra_args` that
would break the Gemini OpenAI-compatible endpoint.

Validates: Requirements 1.1, 1.2, 1.3, 2.1, 2.2, 2.3
"""
from unittest.mock import MagicMock
from hypothesis import given, strategies as st, settings, HealthCheck

from pipeline.triage import build_triage_agent
from pipeline.vendor_discovery import build_vendor_discovery_agent
from pipeline.event_planner import build_event_planner_agent
from pipeline.booking import build_booking_agent
from pipeline.orchestrator import build_orchestrator_agent
from pipeline import build_pipeline


model_strategy = st.just("gemini/gemini-2.5-flash")


class TestNoBreakingExtraArgs:
    """
    No agent may have extra_args that would break the Gemini OpenAI-compatible
    Chat Completions endpoint (e.g. 'thinking_budget').
    """

    @given(model=model_strategy)
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_triage_agent_no_breaking_extra_args(self, model):
        mock_ep = MagicMock()
        mock_vd = MagicMock()
        mock_bk = MagicMock()
        mock_orch = MagicMock()
        agent = build_triage_agent(model, mock_ep, mock_vd, mock_bk, mock_orch)
        if agent.model_settings is not None and agent.model_settings.extra_args:
            assert "thinking_budget" not in agent.model_settings.extra_args, (
                "thinking_budget in extra_args breaks Gemini OpenAI-compatible endpoint"
            )

    @given(model=model_strategy)
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_vendor_discovery_no_breaking_extra_args(self, model):
        agent = build_vendor_discovery_agent(model)
        if agent.model_settings is not None and agent.model_settings.extra_args:
            assert "thinking_budget" not in agent.model_settings.extra_args

    @given(model=model_strategy)
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_event_planner_no_breaking_extra_args(self, model):
        agent = build_event_planner_agent(model)
        if agent.model_settings is not None and agent.model_settings.extra_args:
            assert "thinking_budget" not in agent.model_settings.extra_args

    @given(model=model_strategy)
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_booking_no_breaking_extra_args(self, model):
        agent = build_booking_agent(model)
        if agent.model_settings is not None and agent.model_settings.extra_args:
            assert "thinking_budget" not in agent.model_settings.extra_args

    @given(model=model_strategy)
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_orchestrator_no_breaking_extra_args(self, model):
        mock_ep = MagicMock()
        mock_vd = MagicMock()
        mock_bk = MagicMock()
        agent = build_orchestrator_agent(model, mock_ep, mock_vd, mock_bk)
        if agent.model_settings is not None and agent.model_settings.extra_args:
            assert "thinking_budget" not in agent.model_settings.extra_args

    @given(model=model_strategy)
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_pipeline_no_breaking_extra_args(self, model):
        triage = build_pipeline(model)
        agents_to_check = [triage] + [
            getattr(h, "agent", h) for h in triage.handoffs
        ]
        for agent in agents_to_check:
            if agent.model_settings is not None and agent.model_settings.extra_args:
                assert "thinking_budget" not in agent.model_settings.extra_args, (
                    f"Agent '{agent.name}' has thinking_budget in extra_args — "
                    "this breaks the Gemini OpenAI-compatible endpoint"
                )
