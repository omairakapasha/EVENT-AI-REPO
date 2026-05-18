# TriageAgent Slow Routing Bugfix Design

## Overview

The `TriageAgent` in `packages/agentic_event_orchestrator` is built on `gemini-2.5-flash`, which enables extended thinking by default. Because `main.py` constructs `RunConfig` with a bare `ModelSettings()` (no arguments), the TriageAgent burns extended thinking tokens on every routing decision — even trivially simple ones like "photographers in Karachi" → `VendorDiscoveryAgent`. This wastes LLM credits and adds unnecessary latency to every chat turn.

The fix is surgical: attach `model_settings=ModelSettings(thinking_budget_tokens=0)` directly to the `TriageAgent` object (disabling extended thinking entirely for routing), and attach `model_settings=ModelSettings(thinking_budget_tokens=1024)` to each specialist agent (VendorDiscoveryAgent, EventPlannerAgent, BookingAgent, OrchestratorAgent) to cap their thinking at a small, appropriate budget. The shared `RunConfig` in `main.py` and the `chat.py` router are left completely untouched.

The OpenAI Agents SDK resolves `model_settings` with agent-level settings taking precedence over `RunConfig`-level settings, so per-agent overrides work without any changes to the shared infrastructure.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug — the TriageAgent is invoked with a `ModelSettings` that has no `thinking_budget_tokens` cap, causing Gemini 2.5 Flash to enter an extended thinking loop before issuing a handoff.
- **Property (P)**: The desired behavior when the bug condition holds — the TriageAgent SHALL complete routing in 1 turn with zero thinking tokens consumed.
- **Preservation**: All existing routing targets, guardrail behavior, and specialist agent functionality that must remain unchanged by the fix.
- **TriageAgent**: The sole entry point for all agent interactions, built in `pipeline/triage.py`. Performs keyword-based routing only — no complex reasoning required.
- **ModelSettings**: OpenAI Agents SDK class that controls per-agent model parameters, including `thinking_budget_tokens`.
- **thinking_budget_tokens**: The `ModelSettings` field that controls how many tokens the model may spend on extended thinking/reasoning. Setting it to `0` disables extended thinking entirely.
- **RunConfig**: The shared run-level configuration in `main.py` that applies as a fallback default across all agents. Agent-level `model_settings` override it.
- **Specialist agents**: VendorDiscoveryAgent, EventPlannerAgent, BookingAgent, OrchestratorAgent — agents that perform complex multi-step reasoning and benefit from a small thinking budget.

## Bug Details

### Bug Condition

The bug manifests whenever the TriageAgent is invoked. Because `ModelSettings()` is constructed with no arguments in `main.py` and no `model_settings` is set on the `TriageAgent` object itself, Gemini 2.5 Flash applies its default extended-thinking budget to every TriageAgent turn. The TriageAgent only needs to match a user query to one of four routing targets — it does not need extended reasoning — so every thinking token it consumes is wasted.

**Formal Specification:**
```
FUNCTION isBugCondition(X)
  INPUT: X of type AgentRunRequest
  OUTPUT: boolean

  RETURN X.agent.name = "TriageAgent"
     AND X.agent.model_settings IS NULL
         OR X.agent.model_settings.thinking_budget_tokens = DEFAULT (uncapped)
END FUNCTION
```

### Examples

- **Vendor query**: User sends "photographers in Karachi" → TriageAgent spends ~N thinking tokens reasoning before issuing handoff to VendorDiscoveryAgent. Expected: 0 thinking tokens, immediate handoff.
- **Event planning query**: User sends "help me plan my wedding" → TriageAgent spends thinking tokens before routing to EventPlannerAgent. Expected: 0 thinking tokens, immediate handoff.
- **Booking query**: User sends "book this vendor" → TriageAgent spends thinking tokens before routing to BookingAgent. Expected: 0 thinking tokens, immediate handoff.
- **Injection attempt**: User sends a prompt injection payload → `injection_guardrail` fires BEFORE the LLM is invoked, so no thinking tokens are consumed regardless. This path is unaffected by the fix.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Vendor queries (e.g., "photographers in Karachi") MUST continue to route to `VendorDiscoveryAgent` with correct handoff context.
- Event planning queries (e.g., "plan my wedding") MUST continue to route to `EventPlannerAgent`.
- Booking queries (e.g., "book this vendor") MUST continue to route to `BookingAgent`.
- Complex multi-step queries (e.g., "find and book a caterer for my wedding") MUST continue to route to `OrchestratorAgent`.
- Prompt injection attempts MUST continue to be blocked by `injection_guardrail` with the standard redirect message.
- Vendor registration queries MUST continue to receive a direct response with the vendor portal URL without routing.
- All routing MUST continue to complete within the existing `max_turns=10` limit in `chat.py`.
- Specialist agents (VendorDiscoveryAgent, EventPlannerAgent, BookingAgent, OrchestratorAgent) MUST retain their ability to use extended thinking up to 1024 tokens for complex reasoning.

**Scope:**
All inputs that do NOT involve the TriageAgent's `model_settings` configuration are completely unaffected by this fix. The `RunConfig` in `main.py`, the `chat.py` router, and all specialist agent logic are untouched.

## Hypothesized Root Cause

Based on the bug description and code inspection, the root cause is straightforward:

1. **Missing `model_settings` on TriageAgent**: `pipeline/triage.py` constructs the `Agent` with no `model_settings` parameter. The OpenAI Agents SDK falls back to the `RunConfig`-level `ModelSettings()`, which has no `thinking_budget_tokens` set.

2. **Bare `ModelSettings()` in RunConfig**: `main.py` constructs `RunConfig(model=model, model_settings=ModelSettings())` with no arguments to `ModelSettings`. On Gemini 2.5 Flash, this means the model's default extended-thinking behavior applies — which is to use thinking tokens freely.

3. **No per-agent differentiation**: All five agents (TriageAgent + four specialists) share the same `RunConfig` and none override `model_settings` at the agent level. There is no mechanism to give the TriageAgent a zero budget while giving specialists a small budget.

4. **Gemini 2.5 Flash default behavior**: Unlike models that have thinking disabled by default, Gemini 2.5 Flash enables extended thinking by default. The absence of an explicit `thinking_budget_tokens=0` is therefore an active bug, not a neutral omission.

## Correctness Properties

Property 1: Bug Condition - TriageAgent Zero Thinking Budget

_For any_ `AgentRunRequest` where `isBugCondition` returns true (i.e., the TriageAgent is invoked), the fixed `build_triage_agent` function SHALL produce an `Agent` whose `model_settings.thinking_budget_tokens` equals `0`, ensuring the TriageAgent never enters an extended thinking loop and completes routing in 1 turn with zero thinking tokens consumed.

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation - Specialist Agent Thinking Budget Cap

_For any_ specialist agent built by `build_vendor_discovery_agent`, `build_event_planner_agent`, `build_booking_agent`, or `build_orchestrator_agent`, the fixed builder functions SHALL produce an `Agent` whose `model_settings.thinking_budget_tokens` equals `1024`, preserving the ability to perform complex multi-step reasoning within a capped budget.

**Validates: Requirements 2.3**

Property 3: Preservation - Routing Correctness

_For any_ user query where `isBugCondition` does NOT hold (i.e., routing behavior is evaluated), the fixed pipeline SHALL route to the same specialist agent as the original pipeline, preserving all existing routing targets (VendorDiscoveryAgent, EventPlannerAgent, BookingAgent, OrchestratorAgent) and the injection guardrail behavior.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct, only the five pipeline builder files need to change. `main.py` and `chat.py` are untouched.

**File**: `packages/agentic_event_orchestrator/pipeline/triage.py`

**Function**: `build_triage_agent`

**Specific Changes**:
1. **Import `ModelSettings`**: Add `ModelSettings` to the import from `agents`.
2. **Set zero thinking budget**: Add `model_settings=ModelSettings(thinking_budget_tokens=0)` to the `Agent(...)` constructor call.

```python
from agents import Agent, ModelSettings
from pipeline.instructions import TRIAGE_INSTRUCTIONS
from services.guardrail_hooks import injection_guardrail, leak_detection_guardrail


def build_triage_agent(model, event_planner, vendor_discovery, booking, orchestrator):
    return Agent(
        name="TriageAgent",
        model=model,
        model_settings=ModelSettings(thinking_budget_tokens=0),  # ← FIX
        instructions=TRIAGE_INSTRUCTIONS,
        handoffs=[event_planner, vendor_discovery, booking, orchestrator],
        input_guardrails=[injection_guardrail],
        output_guardrails=[leak_detection_guardrail],
    )
```

---

**File**: `packages/agentic_event_orchestrator/pipeline/vendor_discovery.py`

**Function**: `build_vendor_discovery_agent`

**Specific Changes**:
1. **Import `ModelSettings`**: Add `ModelSettings` to the import from `agents`.
2. **Cap thinking budget**: Add `model_settings=ModelSettings(thinking_budget_tokens=1024)` to the `Agent(...)` constructor call.

---

**File**: `packages/agentic_event_orchestrator/pipeline/event_planner.py`

**Function**: `build_event_planner_agent`

**Specific Changes**:
1. **Import `ModelSettings`**: Add `ModelSettings` to the import from `agents`.
2. **Cap thinking budget**: Add `model_settings=ModelSettings(thinking_budget_tokens=1024)` to the `Agent(...)` constructor call.

---

**File**: `packages/agentic_event_orchestrator/pipeline/booking.py`

**Function**: `build_booking_agent`

**Specific Changes**:
1. **Import `ModelSettings`**: Add `ModelSettings` to the import from `agents`.
2. **Cap thinking budget**: Add `model_settings=ModelSettings(thinking_budget_tokens=1024)` to the `Agent(...)` constructor call.

---

**File**: `packages/agentic_event_orchestrator/pipeline/orchestrator.py`

**Function**: `build_orchestrator_agent`

**Specific Changes**:
1. **Import `ModelSettings`**: Add `ModelSettings` to the import from `agents`.
2. **Cap thinking budget**: Add `model_settings=ModelSettings(thinking_budget_tokens=1024)` to the `Agent(...)` constructor call.

---

**No changes to**:
- `main.py` — `RunConfig(model_settings=ModelSettings())` remains as the fallback default.
- `pipeline/__init__.py` — `build_pipeline()` signature and wiring are unchanged.
- `routers/chat.py` — `Runner.run(triage_agent, ..., run_config=run_config)` is unchanged.

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code (exploration), then verify the fix works correctly and preserves existing behavior (fix checking + preservation checking). Because `model_settings` is a plain Python attribute on the `Agent` object, all tests can inspect it directly without making any LLM calls.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that `build_triage_agent` produces an agent with no `thinking_budget_tokens` constraint, and that specialist agents similarly have no cap.

**Test Plan**: Instantiate the pipeline using a mock model object and inspect `agent.model_settings` directly. Run these tests on the UNFIXED code to observe failures and confirm the root cause.

**Test Cases**:
1. **TriageAgent has no model_settings** (will fail on unfixed code): Assert `triage_agent.model_settings` is not `None` and `triage_agent.model_settings.thinking_budget_tokens == 0`.
2. **VendorDiscoveryAgent has no thinking cap** (will fail on unfixed code): Assert `vendor_discovery_agent.model_settings.thinking_budget_tokens == 1024`.
3. **EventPlannerAgent has no thinking cap** (will fail on unfixed code): Assert `event_planner_agent.model_settings.thinking_budget_tokens == 1024`.
4. **BookingAgent has no thinking cap** (will fail on unfixed code): Assert `booking_agent.model_settings.thinking_budget_tokens == 1024`.
5. **OrchestratorAgent has no thinking cap** (will fail on unfixed code): Assert `orchestrator_agent.model_settings.thinking_budget_tokens == 1024`.

**Expected Counterexamples**:
- `triage_agent.model_settings` is `None` (no per-agent override set).
- Specialist agents also have `model_settings = None`.
- Possible causes: `model_settings` parameter never passed to any `Agent(...)` constructor.

### Fix Checking

**Goal**: Verify that for all agents where the bug condition holds (TriageAgent), the fixed builder produces an agent with `thinking_budget_tokens=0`.

**Pseudocode:**
```
FOR ALL agent WHERE isBugCondition(agent) DO
  result := build_triage_agent_fixed(mock_model, ...)
  ASSERT result.model_settings IS NOT NULL
  ASSERT result.model_settings.thinking_budget_tokens = 0
END FOR
```

### Preservation Checking

**Goal**: Verify that for all agents where the bug condition does NOT hold (specialist agents), the fixed builders produce agents with `thinking_budget_tokens=1024`, and that all routing-relevant attributes (name, handoffs, tools, guardrails) are unchanged.

**Pseudocode:**
```
FOR ALL agent WHERE NOT isBugCondition(agent) DO
  result := build_specialist_agent_fixed(mock_model, ...)
  ASSERT result.model_settings.thinking_budget_tokens = 1024
  ASSERT result.name = original_name
  ASSERT result.handoffs = original_handoffs
  ASSERT result.tools = original_tools
END FOR
```

**Testing Approach**: Direct attribute inspection is used for preservation checking because:
- It requires zero LLM calls (no real Gemini API needed).
- It directly verifies the SDK-level configuration that controls thinking behavior.
- It catches regressions in agent wiring (wrong handoffs, missing tools) that could break routing.
- Property-based testing with Hypothesis can generate many mock model variants to verify the builders are deterministic.

**Test Cases**:
1. **TriageAgent handoffs preserved**: Verify `triage_agent.handoffs` still contains all four specialist agents after the fix.
2. **TriageAgent guardrails preserved**: Verify `input_guardrails` and `output_guardrails` are unchanged.
3. **Specialist agent tools preserved**: Verify each specialist agent's `tools` list is unchanged after adding `model_settings`.
4. **Pipeline wiring preserved**: Verify `build_pipeline()` returns a TriageAgent with the correct handoff graph.

### Unit Tests

- Test that `build_triage_agent` produces `model_settings.thinking_budget_tokens == 0`.
- Test that each specialist builder produces `model_settings.thinking_budget_tokens == 1024`.
- Test that `build_triage_agent` still wires all four handoffs correctly.
- Test that `build_triage_agent` still attaches `injection_guardrail` and `leak_detection_guardrail`.
- Test edge case: verify `ModelSettings(thinking_budget_tokens=0)` is distinct from `ModelSettings()` (i.e., the fix is not a no-op).

### Property-Based Tests

- Generate arbitrary mock model objects and verify `build_triage_agent` always produces `thinking_budget_tokens=0` regardless of the model passed in.
- Generate arbitrary mock model objects and verify each specialist builder always produces `thinking_budget_tokens=1024`.
- Verify that the `thinking_budget_tokens` values on all five agents are mutually consistent: TriageAgent=0, all specialists=1024.

### Integration Tests

- Test that `build_pipeline(mock_model)` returns a TriageAgent with `thinking_budget_tokens=0`.
- Test that all specialist agents reachable via `triage_agent.handoffs` have `thinking_budget_tokens=1024`.
- Test that the full pipeline graph (TriageAgent → specialists → sub-handoffs) has no agent with an uncapped `model_settings` (i.e., `model_settings is None` or `thinking_budget_tokens` not set).
