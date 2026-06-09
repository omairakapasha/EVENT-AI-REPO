"""Smoke tests for vendor tool instruction content and agent wiring.

Tasks 14.1-14.4: instruction content assertions.
Tasks 15.1-15.3: agent tool-list wiring assertions.
"""
from unittest.mock import MagicMock

from pipeline.booking import build_booking_agent
from pipeline.instructions import (
    BOOKING_INSTRUCTIONS,
    ORCHESTRATOR_INSTRUCTIONS,
    VENDOR_DISCOVERY_INSTRUCTIONS,
    EVENT_PLANNER_INSTRUCTIONS,
    TRIAGE_INSTRUCTIONS,
    MAX_INSTRUCTION_CHARS,
)
from pipeline.orchestrator import build_orchestrator_agent
from pipeline.vendor_discovery import build_vendor_discovery_agent


# ── Task 14: Instruction content ──────────────────────────────────────────────


def test_all_instructions_under_3200_chars():
    for name, inst in [
        ("TRIAGE", TRIAGE_INSTRUCTIONS),
        ("EVENT_PLANNER", EVENT_PLANNER_INSTRUCTIONS),
        ("VENDOR_DISCOVERY", VENDOR_DISCOVERY_INSTRUCTIONS),
        ("BOOKING", BOOKING_INSTRUCTIONS),
        ("ORCHESTRATOR", ORCHESTRATOR_INSTRUCTIONS),
    ]:
        assert len(inst) <= MAX_INSTRUCTION_CHARS, (
            f"{name} is {len(inst)} chars, limit {MAX_INSTRUCTION_CHARS}"
        )


def test_vendor_discovery_instructions_contain_mode_guidance():
    assert 'mode="semantic"' in VENDOR_DISCOVERY_INSTRUCTIONS
    assert 'mode="keyword"' in VENDOR_DISCOVERY_INSTRUCTIONS
    assert 'mode="hybrid"' in VENDOR_DISCOVERY_INSTRUCTIONS


def test_orchestrator_instructions_contain_workflow_steps():
    assert "search_vendors" in ORCHESTRATOR_INSTRUCTIONS
    assert "check_vendor_availability" in ORCHESTRATOR_INSTRUCTIONS
    assert "compare_vendors" in ORCHESTRATOR_INSTRUCTIONS


def test_booking_instructions_contain_confirmation_gate():
    assert "CRITICAL VIOLATION" in BOOKING_INSTRUCTIONS or "confirm" in BOOKING_INSTRUCTIONS.lower()
    assert "confirm" in BOOKING_INSTRUCTIONS.lower()


# ── Task 15: Agent tool wiring ─────────────────────────────────────────────────


def test_vendor_discovery_agent_has_new_tools():
    bk = build_booking_agent("fake-model")
    vd = build_vendor_discovery_agent("fake-model", booking=bk)
    tool_names = {t.name for t in vd.tools}
    assert "check_vendor_availability" in tool_names
    assert "get_vendor_services" in tool_names
    assert "compare_vendors" in tool_names


def test_orchestrator_agent_has_new_tools():
    bk = build_booking_agent("fake-model")
    vd = build_vendor_discovery_agent("fake-model", booking=bk)
    ep = MagicMock()
    orch = build_orchestrator_agent("fake-model", ep, vd, bk)
    tool_names = {t.name for t in orch.tools}
    assert "search_vendors" in tool_names
    assert "check_vendor_availability" in tool_names
    assert "compare_vendors" in tool_names


def test_booking_agent_has_get_vendor_services():
    bk = build_booking_agent("fake-model")
    tool_names = {t.name for t in bk.tools}
    assert "get_vendor_services" in tool_names
