# Implementation Plan

## Overview

Fix the TriageAgent's extended thinking budget by adding `ModelSettings(thinking_budget_tokens=0)` to the TriageAgent and `ModelSettings(thinking_budget_tokens=1024)` to each specialist agent. The workflow follows the exploratory bugfix methodology: write tests on unfixed code first, then apply the fix, then verify.

## Task Dependency Graph

```json
{
  "waves": [
    { "wave": 1, "tasks": ["1", "2"] },
    { "wave": 2, "tasks": ["3.1", "3.2", "3.3", "3.4", "3.5"] },
    { "wave": 3, "tasks": ["3.6", "3.7"] },
    { "wave": 4, "tasks": ["4"] }
  ]
}
```

## Tasks

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - TriageAgent Zero Thinking Budget
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Use Hypothesis to generate arbitrary mock model objects and assert `build_triage_agent(model, ...).model_settings.thinking_budget_tokens == 0` for all of them
  - Create `packages/agentic_event_orchestrator/tests/test_triage_thinking_budget.py`
  - Import `build_triage_agent` from `pipeline.triage` and `build_pipeline` from `pipeline`
  - Use a `MagicMock()` as the model object (zero real LLM calls)
  - Write a Hypothesis `@given` strategy that generates mock model objects (e.g., `st.just(MagicMock())` or `st.builds(MagicMock)`)
  - For each generated model, call `build_triage_agent(model, mock_ep, mock_vd, mock_bk, mock_orch)` and assert `agent.model_settings is not None` and `agent.model_settings.thinking_budget_tokens == 0`
  - Also assert the same for specialist agents built by their respective builders (they should have `thinking_budget_tokens == 1024`)
  - Run test on UNFIXED code: `uv run pytest tests/test_triage_thinking_budget.py -v`
  - **EXPECTED OUTCOME**: Test FAILS — counterexample will show `agent.model_settings is None` (no per-agent override set on unfixed code)
  - Document counterexamples found (e.g., `triage_agent.model_settings is None` for any mock model input)
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Routing Wiring and Specialist Agent Configuration
  - **IMPORTANT**: Follow observation-first methodology
  - Observe on UNFIXED code: `triage_agent.handoffs` contains all four specialist agents
  - Observe on UNFIXED code: `triage_agent.input_guardrails` contains `injection_guardrail`
  - Observe on UNFIXED code: `triage_agent.output_guardrails` contains `leak_detection_guardrail`
  - Observe on UNFIXED code: each specialist agent has its expected `name`, `tools`, and `handoffs`
  - Create `packages/agentic_event_orchestrator/tests/test_triage_preservation.py`
  - Use Hypothesis `@given` with mock model strategies to verify the following properties hold for ALL mock model inputs:
    - `triage_agent.handoffs` contains exactly the four specialist agents (VendorDiscoveryAgent, EventPlannerAgent, BookingAgent, OrchestratorAgent)
    - `triage_agent.input_guardrails` is unchanged (contains `injection_guardrail`)
    - `triage_agent.output_guardrails` is unchanged (contains `leak_detection_guardrail`)
    - Each specialist agent's `name` matches its expected value
    - Each specialist agent's `tools` list is unchanged
  - Run tests on UNFIXED code: `uv run pytest tests/test_triage_preservation.py -v`
  - **EXPECTED OUTCOME**: Tests PASS — confirms baseline wiring behavior to preserve
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [x] 3. Fix TriageAgent and specialist agent thinking budgets

  - [x] 3.1 Fix `pipeline/triage.py` — set zero thinking budget on TriageAgent
    - Open `packages/agentic_event_orchestrator/pipeline/triage.py`
    - Add `ModelSettings` to the import from `agents`: `from agents import Agent, ModelSettings`
    - Add `model_settings=ModelSettings(thinking_budget_tokens=0)` to the `Agent(...)` constructor call in `build_triage_agent`
    - Do NOT change any other parameter (`name`, `model`, `instructions`, `handoffs`, `input_guardrails`, `output_guardrails`)
    - _Bug_Condition: isBugCondition(X) where X.agent.name = "TriageAgent" AND X.agent.model_settings IS NULL OR thinking_budget_tokens = DEFAULT_
    - _Expected_Behavior: build_triage_agent returns Agent with model_settings.thinking_budget_tokens == 0_
    - _Preservation: handoffs, input_guardrails, output_guardrails, instructions, name all unchanged_
    - _Requirements: 2.1, 2.2_

  - [x] 3.2 Fix `pipeline/vendor_discovery.py` — cap specialist thinking budget
    - Add `ModelSettings` to the import from `agents`
    - Add `model_settings=ModelSettings(thinking_budget_tokens=1024)` to the `Agent(...)` constructor in `build_vendor_discovery_agent`
    - _Requirements: 2.3_

  - [x] 3.3 Fix `pipeline/event_planner.py` — cap specialist thinking budget
    - Add `ModelSettings` to the import from `agents`
    - Add `model_settings=ModelSettings(thinking_budget_tokens=1024)` to the `Agent(...)` constructor in `build_event_planner_agent`
    - _Requirements: 2.3_

  - [x] 3.4 Fix `pipeline/booking.py` — cap specialist thinking budget
    - Add `ModelSettings` to the import from `agents`
    - Add `model_settings=ModelSettings(thinking_budget_tokens=1024)` to the `Agent(...)` constructor in `build_booking_agent`
    - _Requirements: 2.3_

  - [x] 3.5 Fix `pipeline/orchestrator.py` — cap specialist thinking budget
    - Add `ModelSettings` to the import from `agents`
    - Add `model_settings=ModelSettings(thinking_budget_tokens=1024)` to the `Agent(...)` constructor in `build_orchestrator_agent`
    - _Requirements: 2.3_

  - [x] 3.6 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - TriageAgent Zero Thinking Budget
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - The test from task 1 encodes the expected behavior: `model_settings.thinking_budget_tokens == 0` for all mock model inputs
    - Run: `uv run pytest tests/test_triage_thinking_budget.py -v`
    - **EXPECTED OUTCOME**: Test PASSES — confirms the bug is fixed and TriageAgent never enters an extended thinking loop
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.7 Verify preservation tests still pass
    - **Property 2: Preservation** - Routing Wiring and Specialist Agent Configuration
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run: `uv run pytest tests/test_triage_preservation.py -v`
    - **EXPECTED OUTCOME**: Tests PASS — confirms no regressions in handoffs, guardrails, tools, or agent names
    - Confirm all routing targets (VendorDiscoveryAgent, EventPlannerAgent, BookingAgent, OrchestratorAgent) are still wired correctly

- [x] 4. Checkpoint — Ensure all tests pass
  - Run the full test suite for the orchestrator package: `uv run pytest -v`
  - Confirm `test_triage_thinking_budget.py` passes (bug fixed)
  - Confirm `test_triage_preservation.py` passes (no regressions)
  - Confirm no other existing tests were broken by the five pipeline file changes
  - Verify `main.py` and `chat.py` were NOT modified (they must remain untouched)
  - Ensure all tests pass; ask the user if questions arise.

## Notes

- All tests use `MagicMock()` model objects — zero real LLM or MCP calls (per project rules)
- Run all Python commands with `uv run` from `packages/agentic_event_orchestrator`
- `main.py` and `chat.py` must NOT be modified — the fix is isolated to the five pipeline builder files
- Hypothesis is the property-based testing library; install via `uv add hypothesis` if not already present
- The exploration test (task 1) is expected to FAIL on unfixed code — this is correct and confirms the bug
- The preservation tests (task 2) are expected to PASS on unfixed code — this establishes the baseline
