"""
Preservation property tests — Routing Wiring and Specialist Agent Configuration.

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7

These tests observe baseline wiring on UNFIXED code and must PASS before and
after the fix is applied. They guard against regressions in handoffs, guardrails,
tools, and agent names.

Zero real LLM calls — all agents are built with a plain model name string.
"""
from unittest.mock import MagicMock
from hypothesis import given, strategies as st, settings, HealthCheck

from pipeline.triage import build_triage_agent
from pipeline.vendor_discovery import build_vendor_discovery_agent
from pipeline.event_planner import build_event_planner_agent
from pipeline.booking import build_booking_agent
from pipeline.orchestrator import build_orchestrator_agent
from pipeline import build_pipeline
from services.guardrail_hooks import injection_guardrail, leak_detection_guardrail
from tools import (
    search_vendors,
    get_vendor_details,
    get_vendor_recommendations,
    check_vendor_availability,
    get_vendor_services,
    compare_vendors,
    get_user_events,
    create_event,
    get_event_details,
    update_event_status,
    query_event_types,
    get_my_bookings,
    get_booking_details,
    cancel_booking,
)


# ── Strategy ──────────────────────────────────────────────────────────

model_strategy = st.just("gemini/gemini-2.5-flash")


def _make_specialists(model: str):
    """Build real specialist agents for use as triage handoff targets."""
    mock_bk = build_booking_agent(model)
    vd = build_vendor_discovery_agent(model, booking=mock_bk)
    ep = build_event_planner_agent(model, vendor_discovery=vd)
    orch = build_orchestrator_agent(model, ep, vd, mock_bk)
    return ep, vd, mock_bk, orch


# ── Property 2a: TriageAgent handoffs ─────────────────────────────────

class TestTriageHandoffs:
    """TriageAgent must wire exactly four specialist agents as handoffs."""

    @given(model=model_strategy)
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_triage_has_four_handoffs(self, model):
        ep, vd, bk, orch = _make_specialists(model)
        triage = build_triage_agent(model, ep, vd, bk, orch)
        assert len(triage.handoffs) == 4, (
            f"Expected 4 handoffs, got {len(triage.handoffs)}"
        )

    @given(model=model_strategy)
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_triage_handoff_names(self, model):
        ep, vd, bk, orch = _make_specialists(model)
        triage = build_triage_agent(model, ep, vd, bk, orch)
        names = {getattr(h, "name", getattr(getattr(h, "agent", None), "name", None)) for h in triage.handoffs}
        assert "VendorDiscoveryAgent" in names
        assert "EventPlannerAgent" in names
        assert "BookingAgent" in names
        assert "OrchestratorAgent" in names


# ── Property 2b: TriageAgent guardrails ───────────────────────────────

class TestTriageGuardrails:
    """TriageAgent guardrails must remain unchanged."""

    @given(model=model_strategy)
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_triage_input_guardrail_present(self, model):
        ep, vd, bk, orch = _make_specialists(model)
        triage = build_triage_agent(model, ep, vd, bk, orch)
        assert injection_guardrail in triage.input_guardrails, (
            "injection_guardrail must be in triage input_guardrails"
        )

    @given(model=model_strategy)
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_triage_output_guardrail_present(self, model):
        ep, vd, bk, orch = _make_specialists(model)
        triage = build_triage_agent(model, ep, vd, bk, orch)
        assert leak_detection_guardrail in triage.output_guardrails, (
            "leak_detection_guardrail must be in triage output_guardrails"
        )


# ── Property 2c: Specialist agent names ───────────────────────────────

class TestSpecialistNames:
    """Each specialist agent must have its canonical name."""

    @given(model=model_strategy)
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_specialist_names(self, model):
        bk = build_booking_agent(model)
        vd = build_vendor_discovery_agent(model, booking=bk)
        ep = build_event_planner_agent(model, vendor_discovery=vd)
        orch = build_orchestrator_agent(model, ep, vd, bk)

        assert bk.name == "BookingAgent"
        assert vd.name == "VendorDiscoveryAgent"
        assert ep.name == "EventPlannerAgent"
        assert orch.name == "OrchestratorAgent"


# ── Property 2d: Specialist agent tools ───────────────────────────────

class TestSpecialistTools:
    """Each specialist agent must retain its full tool list."""

    @given(model=model_strategy)
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_vendor_discovery_tools(self, model):
        bk = build_booking_agent(model)
        vd = build_vendor_discovery_agent(model, booking=bk)
        tool_names = {t.name for t in vd.tools}
        assert "search_vendors" in tool_names
        assert "get_vendor_details" in tool_names
        assert "get_vendor_recommendations" in tool_names
        assert "check_vendor_availability" in tool_names
        assert "get_vendor_services" in tool_names
        assert "compare_vendors" in tool_names

    @given(model=model_strategy)
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_event_planner_tools(self, model):
        vd = build_vendor_discovery_agent(model)
        ep = build_event_planner_agent(model, vendor_discovery=vd)
        tool_names = {t.name for t in ep.tools}
        assert "get_user_events" in tool_names
        assert "create_event" in tool_names
        assert "get_event_details" in tool_names
        assert "update_event_status" in tool_names
        assert "query_event_types" in tool_names

    @given(model=model_strategy)
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_booking_agent_tools(self, model):
        bk = build_booking_agent(model)
        tool_names = {t.name for t in bk.tools}
        assert "create_booking_request" in tool_names
        assert "get_my_bookings" in tool_names
        assert "get_booking_details" in tool_names
        assert "cancel_booking" in tool_names
        assert "get_vendor_services" in tool_names

    @given(model=model_strategy)
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_orchestrator_tools(self, model):
        bk = build_booking_agent(model)
        vd = build_vendor_discovery_agent(model, booking=bk)
        ep = build_event_planner_agent(model, vendor_discovery=vd)
        orch = build_orchestrator_agent(model, ep, vd, bk)
        tool_names = {t.name for t in orch.tools}
        assert "search_vendors" in tool_names
        assert "check_vendor_availability" in tool_names
        assert "compare_vendors" in tool_names


# ── Property 2e: Pipeline integration ─────────────────────────────────

class TestPipelineWiring:
    """build_pipeline must return a correctly wired TriageAgent."""

    @given(model=model_strategy)
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_pipeline_returns_triage_agent(self, model):
        triage = build_pipeline(model)
        assert triage.name == "TriageAgent"

    @given(model=model_strategy)
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_pipeline_triage_has_four_handoffs(self, model):
        triage = build_pipeline(model)
        assert len(triage.handoffs) == 4

    @given(model=model_strategy)
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_pipeline_guardrails_intact(self, model):
        triage = build_pipeline(model)
        assert injection_guardrail in triage.input_guardrails
        assert leak_detection_guardrail in triage.output_guardrails
