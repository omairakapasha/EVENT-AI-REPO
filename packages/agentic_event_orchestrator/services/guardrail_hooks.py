"""SDK-native guardrail hooks using @input_guardrail and @output_guardrail.

These integrate directly into the OpenAI Agents SDK pipeline:
- input_guardrail: runs BEFORE the LLM (blocking mode) — zero tokens on blocked requests
- output_guardrail: runs AFTER the final agent output
- tool_input_guardrail: runs before each tool call
- tool_output_guardrail: runs after each tool call

Reference: https://openai.github.io/openai-agents-python/guardrails/
"""

import logging
import re
from pydantic import BaseModel
from agents import (
    Agent,
    GuardrailFunctionOutput,
    RunContextWrapper,
    TResponseInputItem,
    input_guardrail,
    output_guardrail,
)
from agents import ToolGuardrailFunctionOutput, tool_input_guardrail, tool_output_guardrail

logger = logging.getLogger(__name__)

# ── Shared firewall/detector instances (set from app.state in lifespan) ──
_firewall = None
_leak_detector = None


def set_guardrail_instances(firewall, leak_detector):
    """Called from lifespan after PromptFirewall and OutputLeakDetector are initialised."""
    global _firewall, _leak_detector
    _firewall = firewall
    _leak_detector = leak_detector
    logger.info("SDK guardrail hooks wired to PromptFirewall and OutputLeakDetector")


# ── Input guardrail output schema ─────────────────────────────────
class InjectionCheckOutput(BaseModel):
    is_injection: bool
    threat_type: str | None = None
    confidence: float = 0.0


# ── Input guardrail: 7-layer PromptFirewall ───────────────────────
@input_guardrail  # blocking — LLM never runs on blocked input
async def injection_guardrail(
    ctx: RunContextWrapper[None],
    agent: Agent,
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    """Block prompt injection attempts before they reach the LLM."""
    if _firewall is None:
        return GuardrailFunctionOutput(
            output_info=InjectionCheckOutput(is_injection=False),
            tripwire_triggered=False,
        )

    # Extract ONLY the current user message — not the full sandwiched context string.
    # The context_builder wraps the raw user message between unique delimiters so we
    # can extract it precisely and avoid false-positives from conversation history.
    DELIM_START = "[USER_MSG_7f3a9b2e]"
    DELIM_END   = "[/USER_MSG_7f3a9b2e]"

    raw_input = input if isinstance(input, str) else ""
    if isinstance(input, list):
        # Structured message list — grab the last user turn
        for item in reversed(input):
            if isinstance(item, dict) and item.get("role") == "user":
                content = item.get("content", "")
                if isinstance(content, str):
                    raw_input = content
                    break
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            raw_input = block.get("text", "")
                            break
                    if raw_input:
                        break

    # If the input is the sandwiched context string, extract only the delimited user message
    if DELIM_START in raw_input and DELIM_END in raw_input:
        start_idx = raw_input.index(DELIM_START) + len(DELIM_START)
        end_idx   = raw_input.index(DELIM_END)
        message = raw_input[start_idx:end_idx].strip()
    else:
        message = raw_input

    result = _firewall.classify(message)

    if result.blocked:
        logger.warning(
            "SDK input guardrail tripped: threat=%s confidence=%.2f rule=%s",
            result.threat_type, result.confidence, result.matched_rule
        )

    return GuardrailFunctionOutput(
        output_info=InjectionCheckOutput(
            is_injection=result.blocked,
            threat_type=result.threat_type,
            confidence=result.confidence,
        ),
        tripwire_triggered=result.blocked,
    )


# ── Output schema for leak detection ─────────────────────────────
class LeakCheckOutput(BaseModel):
    leaked: bool
    leak_type: str | None = None


# ── Output guardrail: OutputLeakDetector ─────────────────────────
@output_guardrail
async def leak_detection_guardrail(
    ctx: RunContextWrapper,
    agent: Agent,
    output,  # str when no output_type; typed object otherwise — always coerce to str
) -> GuardrailFunctionOutput:
    """Scan final agent output for leaked system prompt fragments or canary tokens."""
    if _leak_detector is None:
        return GuardrailFunctionOutput(
            output_info=LeakCheckOutput(leaked=False),
            tripwire_triggered=False,
        )

    # output is the final agent response string
    text = output if isinstance(output, str) else str(output)
    result = _leak_detector.scan(text)

    if result.leaked:
        logger.critical(
            "SDK output guardrail tripped: leak_type=%s", result.leak_type
        )

    return GuardrailFunctionOutput(
        output_info=LeakCheckOutput(leaked=result.leaked, leak_type=result.leak_type),
        tripwire_triggered=result.leaked,
    )


# ── Tool input guardrail: block secrets and injection in tool args ─
@tool_input_guardrail
def tool_injection_guard(data) -> ToolGuardrailFunctionOutput:
    """Block injection patterns and secrets in tool call arguments."""
    import json
    try:
        args_str = json.dumps(data.context.tool_arguments or {})

        # Block API keys / secrets
        if any(pattern in args_str for pattern in ["sk-", "Bearer ", "api_key", "password", "secret"]):
            logger.warning("Tool input guardrail: secret pattern in tool args")
            return ToolGuardrailFunctionOutput.reject_content(
                "Tool call blocked: potential secret in arguments."
            )

        # Block injection in tool args
        if _firewall is not None:
            result = _firewall.classify(args_str)
            if result.blocked:
                logger.warning("Tool input guardrail: injection in tool args threat=%s", result.threat_type)
                return ToolGuardrailFunctionOutput.reject_content(
                    "Tool call blocked: injection pattern detected in arguments."
                )
    except Exception as e:
        logger.debug("Tool input guardrail error: %s", e)

    return ToolGuardrailFunctionOutput.allow()


# ── Tool output guardrail: block tool outputs containing raw PII ──
# NOTE: ToolGuardrailFunctionOutput only supports .allow() and .reject_content().
# The SDK does NOT support mutating/replacing tool output values.
# PII redaction of the final response is handled downstream by
# GuardrailService.filter_output() in the chat router.
#
# Strategy:
#   - CNIC (national ID) → hard block: should never appear in agent context
#   - Email / phone → allow through (common in vendor/booking data);
#     GuardrailService.filter_output() redacts them before the final response
_TOOL_CNIC_RE = re.compile(r"\b\d{5}-\d{7}-\d\b")


@tool_output_guardrail
def tool_pii_redact(data) -> ToolGuardrailFunctionOutput:
    """Block tool outputs that contain raw CNIC numbers.

    Emails and phone numbers are allowed through to the agent context because
    they are legitimately needed for booking/vendor workflows. The chat router's
    GuardrailService.filter_output() redacts them before the final user response.

    The SDK does not support mutating tool output — only block or allow.
    """
    try:
        text = str(data.output or "")
        if _TOOL_CNIC_RE.search(text):
            logger.warning("Tool output guardrail: CNIC detected in tool output — blocking")
            return ToolGuardrailFunctionOutput.reject_content(
                "Tool output blocked: contains sensitive identity number."
            )
    except Exception as e:
        logger.debug("Tool output guardrail error: %s", e)

    return ToolGuardrailFunctionOutput.allow()
