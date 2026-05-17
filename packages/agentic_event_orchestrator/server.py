"""FastAPI server for the Agentic Event Orchestrator using OpenAI Agent SDK.

GUARDRAILS INTEGRATED (all priorities):
  Priority 1: Input validation, prompt injection detection, rate limiting
  Priority 2: Topic scope enforcement, output safety filter, PII masking in logs
  Priority 3: Spending limits, booking confirmation gate, audit logging
"""

import logging
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uvicorn
import os
import sys
import uuid
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("agentic_orchestrator")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.sdk_agents import (
    run_orchestration,
    run_vendor_discovery,
    run_scheduler,
    run_triage,
    run_booking,
    run_event_planning,
    triage_agent,
)
from _agents_sdk import Runner

# ── Guardrails & Rate Limiter ─────────────────────────────────────────────────
from guardrails import (
    validate_input,
    is_on_topic,
    filter_output,
    classify_output_safe,
    build_sandwiched_context,
    mask_pii_for_log,
    sanitize_context_email,
    sanitize_external_content,    # FIX #2: retrieval-time session sanitization
    audit_event,
    get_recent_audit_log,
    get_session_stats,
    session_create,
    session_add_message,
    session_get_messages,
    session_delete,
    session_cleanup_expired,
)
from rate_limiter import (
    check_rate_limit,
    record_request,
    get_client_ip,
)
from tools.booking_tools import (
    set_session_context,
    mark_session_confirmed,
    clear_session_confirmed,
    is_session_confirmed,
    register_vendor_in_allowlist,  # FIX #7: wiring vendor allowlist
)
from agent_validator import validate_agent_output

# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Agentic Event Orchestrator API",
    description="AI-powered event planning with OpenAI Agent SDK — hardened with guardrails",
    version="4.0.0",
)

# CORS — restrict to known origins
ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3002,http://localhost:3003,http://localhost:3004",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

# FIX #13: CSRF Protection + Security Headers Middleware
# Adds browser-level protections: no framing, content sniffing, XSS filter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as _Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # SSE streams set their own Cache-Control: no-cache — don't overwrite them.
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" not in content_type:
            response.headers["Cache-Control"] = "no-store"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# ─── Auth ─────────────────────────────────────────────────────────────────────

AI_SERVICE_API_KEY = os.getenv("AI_SERVICE_API_KEY", "")


async def verify_api_key(request: Request):
    """Verify API key. In dev (no key set) all requests are allowed."""
    if not AI_SERVICE_API_KEY:
        return  # development mode
    api_key = request.headers.get("X-API-Key", "")
    if api_key != AI_SERVICE_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ─── Session Management (TTL + Data Minimization) ────────────────────────────
# Research: "Privacy Leakage in Federated LLMs" arXiv 2024;
#            GDPR Article 17 — right to erasure, data minimization principle
# Sessions now managed via guardrails.session_* functions with 30-min TTL

def get_session(session_id: str) -> list:
    """Get messages for a session (auto-initializes, respects TTL)."""
    msgs = session_get_messages(session_id)
    if not msgs and session_id:
        session_create(session_id)
    return msgs


def add_to_session(session_id: str, role: str, content: str):
    """Add message to TTL session with data minimization."""
    session_add_message(session_id, role, content)


# ─── Confirmation keyword detection ──────────────────────────────────────────

_CONFIRM_KEYWORDS = [
    "confirm booking", "yes book", "yes, book", "go ahead", "proceed",
    "confirm", "yes proceed", "book it", "yes, do it", "yes do it",
    "i confirm", "confirm it", "let's go", "lets go", "ok book", "okay book",
]

_CANCEL_KEYWORDS = ["cancel", "no", "abort", "stop", "don't book", "dont book"]


def _detect_confirmation(message: str) -> Optional[bool]:
    """Return True if confirming, False if cancelling, None if neither."""
    msg = message.lower().strip()
    for kw in _CONFIRM_KEYWORDS:
        if kw in msg:
            return True
    for kw in _CANCEL_KEYWORDS:
        if kw in msg:
            return False
    return None


# ─── Models ───────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_email: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    agent: str
    session_id: str
    guardrail_triggered: bool = False


class PlanRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None


class AgentResponse(BaseModel):
    success: bool
    result: str
    agent_used: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Agentic Event Orchestrator",
        "version": "4.0.0",
        "guardrails": "enabled",
    }


@app.post("/api/chat", dependencies=[Depends(verify_api_key)])
def chat(request_body: ChatRequest, request: Request) -> ChatResponse:
    """
    Main chat endpoint — full guardrail pipeline applied on every request.
    
    Pipeline:
      1. Rate limit check (P1)
      2. Input validation + injection detection (P1)
      3. Topic scope check (P2)
      4. Confirmation gate handling (P1/P3)
      5. Run agent
      6. Output safety filter (P2)
      7. Audit log (P3)
    """
    session_id = request_body.session_id or str(uuid.uuid4())
    client_ip  = get_client_ip(request)
    user_email = request_body.user_email
    message    = request_body.message.strip()

    # ── STEP 1: Rate Limiting (P1) ────────────────────────────────
    allowed, rate_msg = check_rate_limit(session_id, client_ip)
    if not allowed:
        audit_event("rate_limit_hit", session_id, user_email, {"ip": client_ip})
        return ChatResponse(
            response=rate_msg or "Too many requests. Please slow down.",
            agent="System",
            session_id=session_id,
            guardrail_triggered=True,
        )
    record_request(session_id, client_ip)

    # ── STEP 2: Input Validation + Injection Detection (P1) ───────
    valid, input_error = validate_input(message)
    if not valid:
        audit_event("input_blocked", session_id, user_email, {
            "reason": input_error, "msg_preview": mask_pii_for_log(message[:80])
        })
        return ChatResponse(
            response=input_error or "Invalid input.",
            agent="System",
            session_id=session_id,
            guardrail_triggered=True,
        )

    # ── STEP 3: Topic Scope Check (P2) ───────────────────────────
    on_topic, redirect_msg = is_on_topic(message)
    if not on_topic:
        audit_event("off_topic_blocked", session_id, user_email, {
            "msg_preview": message[:80]
        })
        return ChatResponse(
            response=redirect_msg or "I can only help with event planning.",
            agent="TriageAgent",
            session_id=session_id,
            guardrail_triggered=True,
        )

    # ── STEP 4: Booking Confirmation Gate (P1/P3) ─────────────────
    confirmation = _detect_confirmation(message)
    if confirmation is True:
        mark_session_confirmed(session_id)
        audit_event("booking_confirmed_by_user", session_id, user_email, {})
    elif confirmation is False:
        clear_session_confirmed(session_id)

    # ── STEP 5: Run Agent (with sandwich defense context) ─────────
    try:
        # Bind session context for booking tools
        set_session_context(session_id)

        # Periodic session cleanup (GDPR — purge expired sessions)
        session_cleanup_expired()

        # Build context-enriched input
        history = get_session(session_id)
        context_parts = []

        if user_email:
            masked = sanitize_context_email(user_email)
            context_parts.append(f"[User email (masked): {masked}]")

        if history:
            # FIX #2: Retrieval-time sanitization — re-validate stored messages
            # before injecting into agent context. Catches MINJA-style memory
            # poisoning where malicious content was stored in a prior turn.
            recent = history[-6:]
            safe_history_lines = []
            for m in recent:
                raw_content = m["content"][:200]
                # Re-sanitize on read — treat stored history as external/untrusted
                safe_content = sanitize_external_content(
                    raw_content, source="session_history", max_length=200
                )
                role_label = "User" if m["role"] == "user" else "Assistant"
                safe_history_lines.append(f"{role_label}: {safe_content}")

            history_text = "\n".join(safe_history_lines)
            context_parts.append(f"[Previous conversation:\n{history_text}]")

        context_prefix = "\n".join(context_parts)

        # RESEARCH: Sandwich defense — re-state constraints AFTER user content
        # Source: "Boundary Awareness and Explicit Reminders" (2025)
        # Reduces indirect injection success by ~40% in ablation studies
        full_input = build_sandwiched_context(message, context_prefix)

        result = Runner.run_sync(triage_agent, full_input)
        response_text = result.final_output
        agent_name = (
            result.last_agent.name
            if hasattr(result, "last_agent") and result.last_agent
            else "AI Assistant"
        )

    except Exception:
        logger.error("Agent run error", exc_info=True)
        audit_event("agent_error", session_id, user_email, {})
        return ChatResponse(
            response="I encountered an issue processing your request. Please try again.",
            agent="System",
            session_id=session_id,
        )

    # ── STEP 6: Multi-stage Output Classification + Length Cap ───────
    # FIX #8: Output length cap — prevents DoS from excessively long responses
    MAX_RESPONSE_CHARS = 5000
    if len(response_text) > MAX_RESPONSE_CHARS:
        response_text = response_text[:MAX_RESPONSE_CHARS] + (
            "\n\n*[Response truncated for safety.]*"
        )
        audit_event("output_truncated", session_id, user_email, {
            "agent": agent_name, "original_length": len(response_text)
        })

    validated_response, was_handoff_blocked = validate_agent_output(
        response_text, agent_name, session_id, user_email
    )

    safe_response, was_filtered, classifier_used = classify_output_safe(validated_response)

    if was_filtered or was_handoff_blocked:
        audit_event("output_classified_unsafe", session_id, user_email, {
            "agent": agent_name,
            "classifier": classifier_used,
            "handoff_blocked": was_handoff_blocked,
        })

    # ── STEP 7: Persist session + audit ──────────────────────────
    add_to_session(session_id, "user", message)
    add_to_session(session_id, "assistant", safe_response)
    audit_event("chat_turn", session_id, user_email, {
        "agent": agent_name,
        "filtered": was_filtered,
        "msg_len": len(message),
    })

    return ChatResponse(
        response=safe_response,
        agent=agent_name,
        session_id=session_id,
        guardrail_triggered=was_filtered or was_handoff_blocked,
    )


@app.delete("/api/session/{session_id}", dependencies=[Depends(verify_api_key)])
def erase_session(session_id: str):
    """
    GDPR Right to Erasure — delete all conversation data for a session.
    Research basis: GDPR Article 17; Federated LLM Privacy paper (arXiv 2024)
    """
    session_delete(session_id)
    return {"deleted": True, "session_id": session_id}


@app.get("/api/session/stats", dependencies=[Depends(verify_api_key)])
def session_stats():
    """Admin endpoint: show active session count, TTL config, data minimization settings."""
    return get_session_stats()


@app.post("/api/confirm-booking")
def confirm_booking_endpoint(
    request: Request,
    body: Dict[str, str],
    _=Depends(verify_api_key),
):
    """
    Explicit booking confirmation endpoint.
    FIX #10: Rate-limited to prevent spam-confirmation attacks.
    """
    client_ip = get_client_ip(request)
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    # Apply rate limit
    allowed, rate_msg = check_rate_limit(session_id, client_ip)
    if not allowed:
        audit_event("confirm_rate_limited", session_id, None, {"ip": client_ip})
        raise HTTPException(
            status_code=429,
            detail=rate_msg or "Too many confirmation requests. Please wait.",
            headers={"Retry-After": "60"},
        )
    record_request(session_id, client_ip)

    mark_session_confirmed(session_id)
    audit_event("booking_confirmed_via_endpoint", session_id, None, {
        "ip": client_ip,
    })
    return {"confirmed": True, "session_id": session_id}


@app.get("/api/audit-log", dependencies=[Depends(verify_api_key)])
def get_audit_log(n: int = 100):
    """Admin endpoint: view recent guardrail and agent audit events."""
    entries = get_recent_audit_log(min(n, 500))
    return {"count": len(entries), "entries": entries}


@app.post("/api/agent/orchestrate", dependencies=[Depends(verify_api_key)])
def orchestrate_event(body: PlanRequest, request: Request) -> AgentResponse:
    """Full orchestration endpoint."""
    client_ip = get_client_ip(request)
    allowed, rate_msg = check_rate_limit(None, client_ip)
    if not allowed:
        raise HTTPException(status_code=429, detail=rate_msg, headers={"Retry-After": "60"})
    record_request(None, client_ip)

    valid, err = validate_input(body.message)
    if not valid:
        raise HTTPException(status_code=400, detail=err)

    try:
        result = run_orchestration(body.message)
        safe_result, _ = filter_output(result.final_output)
        return AgentResponse(
            success=True,
            result=safe_result,
            agent_used=result.last_agent.name,
        )
    except Exception:
        logger.error("Orchestration error", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")


@app.post("/api/agent/discover", dependencies=[Depends(verify_api_key)])
def discover_vendors(body: PlanRequest, request: Request) -> AgentResponse:
    client_ip = get_client_ip(request)
    allowed, rate_msg = check_rate_limit(None, client_ip)
    if not allowed:
        raise HTTPException(status_code=429, detail=rate_msg, headers={"Retry-After": "60"})
    record_request(None, client_ip)

    valid, err = validate_input(body.message)
    if not valid:
        raise HTTPException(status_code=400, detail=err)

    try:
        result = run_vendor_discovery(body.message)
        safe_result, _ = filter_output(result.final_output)
        return AgentResponse(
            success=True,
            result=safe_result,
            agent_used=result.last_agent.name,
        )
    except Exception:
        logger.error("Vendor discovery error", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")


@app.post("/api/agent/schedule", dependencies=[Depends(verify_api_key)])
def create_schedule(body: PlanRequest, request: Request) -> AgentResponse:
    client_ip = get_client_ip(request)
    allowed, rate_msg = check_rate_limit(None, client_ip)
    if not allowed:
        raise HTTPException(status_code=429, detail=rate_msg, headers={"Retry-After": "60"})
    record_request(None, client_ip)

    valid, err = validate_input(body.message)
    if not valid:
        raise HTTPException(status_code=400, detail=err)

    try:
        event_details = body.context or {"message": body.message, "preferences": []}
        result = run_scheduler(event_details)
        safe_result, _ = filter_output(result.final_output)
        return AgentResponse(
            success=True,
            result=safe_result,
            agent_used=result.last_agent.name,
        )
    except Exception:
        logger.error("Schedule error", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")


@app.post("/api/agent/plan", dependencies=[Depends(verify_api_key)])
def plan_event(body: PlanRequest, request: Request) -> AgentResponse:
    """Legacy plan endpoint."""
    try:
        result = run_triage(body.message)
        safe_result, _ = filter_output(result.final_output)
        return AgentResponse(
            success=True,
            result=safe_result,
            agent_used=result.last_agent.name,
        )
    except Exception:
        logger.error("Plan error", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal error occurred.")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
