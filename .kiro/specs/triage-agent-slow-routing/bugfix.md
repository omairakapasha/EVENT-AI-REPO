# Bugfix Requirements Document

## Introduction

The `TriageAgent` in `packages/agentic_event_orchestrator` enters extended thinking/reasoning loops before routing user queries to specialist agents. Because the model is `gemini-2.5-flash` — which has extended thinking enabled by default — and `ModelSettings()` is instantiated with no parameters in `main.py`, the agent burns unnecessary LLM tokens "reasoning" about simple keyword-based routing decisions (e.g., "photographers in Karachi" → `VendorDiscoveryAgent`). This inflates credit usage and increases response latency for every chat turn. The fix is to set a zero (or near-zero) thinking budget on the `TriageAgent`'s `ModelSettings` while allowing specialist agents to retain a small thinking budget for their more complex work.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user sends a routing query (e.g., "photographers in Karachi") THEN the system spends extended thinking tokens reasoning before issuing a handoff, wasting LLM credits and increasing latency.

1.2 WHEN `ModelSettings()` is constructed with no arguments in `main.py` THEN the system applies Gemini 2.5 Flash's default extended-thinking budget to every agent turn, including the TriageAgent which only needs keyword pattern-matching.

1.3 WHEN the `RunConfig` is built with a default `ModelSettings()` THEN the system uses the same thinking budget for both the TriageAgent (pure routing) and specialist agents (complex reasoning), providing no differentiation.

### Expected Behavior (Correct)

2.1 WHEN a user sends a routing query THEN the system SHALL route to the correct specialist agent in 1 turn with zero or near-zero thinking tokens consumed by the TriageAgent.

2.2 WHEN `ModelSettings` is constructed for the TriageAgent THEN the system SHALL set `thinking_budget_tokens=0` (or the SDK-equivalent field that disables extended thinking) so the TriageAgent never enters a reasoning loop.

2.3 WHEN `ModelSettings` is constructed for specialist agents (VendorDiscoveryAgent, EventPlannerAgent, BookingAgent, OrchestratorAgent) THEN the system SHALL allow a small, capped thinking budget (e.g., ≤1024 tokens) appropriate for their more complex multi-step work.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user sends a vendor query (e.g., "photographers in Karachi") THEN the system SHALL CONTINUE TO route to `VendorDiscoveryAgent` with correct handoff context.

3.2 WHEN a user sends an event planning query (e.g., "plan my wedding") THEN the system SHALL CONTINUE TO route to `EventPlannerAgent`.

3.3 WHEN a user sends a booking query (e.g., "book this vendor") THEN the system SHALL CONTINUE TO route to `BookingAgent`.

3.4 WHEN a user sends a complex multi-step query (e.g., "find and book a caterer for my wedding") THEN the system SHALL CONTINUE TO route to `OrchestratorAgent`.

3.5 WHEN a user sends a prompt injection attempt THEN the system SHALL CONTINUE TO block it via the existing `injection_guardrail` and return the standard redirect message.

3.6 WHEN a user sends a vendor registration query THEN the system SHALL CONTINUE TO respond directly with the vendor portal URL without routing.

3.7 WHEN the TriageAgent routes a query THEN the system SHALL CONTINUE TO complete routing within the existing `max_turns=10` limit in `chat.py`.

---

## Bug Condition Pseudocode

**Bug Condition Function** — identifies inputs that trigger the bug:

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type AgentRunRequest
  OUTPUT: boolean

  // Bug is triggered whenever the TriageAgent is invoked with a
  // ModelSettings that has no thinking budget cap on gemini-2.5-flash
  RETURN X.agent = TriageAgent
     AND X.model_settings.thinking_budget_tokens = DEFAULT (uncapped)
END FUNCTION
```

**Property: Fix Checking**

```pascal
FOR ALL X WHERE isBugCondition(X) DO
  result ← TriageAgent'(X)   // TriageAgent with patched ModelSettings
  ASSERT result.thinking_tokens_used = 0
     AND result.handoff_issued = true
     AND result.turns = 1
END FOR
```

**Property: Preservation Checking**

```pascal
FOR ALL X WHERE NOT isBugCondition(X) DO
  // Specialist agents and non-routing paths
  ASSERT TriageAgent(X).routing_target = TriageAgent'(X).routing_target
END FOR
```
