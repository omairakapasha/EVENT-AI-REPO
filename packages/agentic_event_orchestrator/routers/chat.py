"""Chat router — non-streaming and SSE streaming endpoints."""
import json
import logging
import time
import uuid

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

# ── SDK imports ───────────────────────────────────────────────────
from agents import Runner, ItemHelpers
from agents.run import RunConfig
from openai.types.responses import ResponseTextDeltaEvent

# ── SSE ───────────────────────────────────────────────────────────
try:
    from sse_starlette.sse import EventSourceResponse
    SSE_AVAILABLE = True
except ImportError:
    SSE_AVAILABLE = False

from config.dependencies import get_session, get_settings_dep
from services.agent_context import AgentContext
from services.guardrail_service import GuardrailService
from services.chat_service import ChatService
from services.memory_service import MemoryService
from services.context_builder import build_agent_input
from services.output_leak_detector import OutputLeakDetector

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ai", tags=["chat"])

# Module-level stateless singleton — no firewall injected here.
# Each request handler creates a firewall-aware instance from app.state.
_chat_service = ChatService()


# ── Request / Response models ─────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    success: bool
    data: dict


# ── Auth helper ───────────────────────────────────────────────────

def _get_user_id(request: Request) -> str:
    """Extract user_id from JWT or X-User-Id header. Returns a UUID-compatible string."""
    user_id = request.headers.get("X-User-Id", "")
    if not user_id:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            import hashlib
            # Use full 32-char hex digest so it's a valid UUID format
            user_id = hashlib.sha256(auth[7:].encode()).hexdigest()[:32]
    return user_id or "0" * 32


# ── POST /api/v1/ai/chat — non-streaming ─────────────────────────

@router.post("/chat")
async def chat(
    body: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
    settings=Depends(get_settings_dep),
):
    user_id = body.user_id or _get_user_id(request)
    message = body.message.strip()

    # 1. Guardrail input pipeline
    firewall = getattr(request.app.state, "firewall", None)
    guardrail_svc = GuardrailService(firewall=firewall)
    guardrail_result = await guardrail_svc.run_input_pipeline(message, user_id, settings)

    if guardrail_result.blocked:
        guardrail_svc.audit("input_blocked", body.session_id, user_id, {"reason": guardrail_result.reason})
        return JSONResponse(content={
            "success": True,
            "data": {
                "response": guardrail_result.message,
                "agent": "GuardrailService",
                "session_id": body.session_id or "",
                "guardrail_triggered": True,
            }
        })

    # Use sanitized message from firewall
    safe_message = guardrail_result.message

    # 2. Session management
    chat_session = await _chat_service.get_or_create_session(db, user_id, body.session_id)

    # 3. Memory injection — semantic search scoped to current message
    memory_svc = MemoryService(api_key=settings.mem0_api_key)
    memory_context = await memory_svc.search_user_memory(user_id, safe_message, top_k=5)

    # 4. Build conversation history
    history_msgs = await _chat_service.get_session_messages(db, chat_session.id, limit=6)
    history = [{"role": m.role if isinstance(m.role, str) else m.role.value, "content": m.content} for m in history_msgs]

    # 5. Build sandwiched agent input
    canary_token = getattr(request.app.state, "canary_token", "")
    agent_input = build_agent_input(safe_message, memory_context, history, canary_token, firewall)

    # 6. Run agent pipeline
    triage_agent = request.app.state.triage_agent
    run_config: RunConfig = request.app.state.run_config

    try:
        start = time.monotonic()
        try:
            agent_ctx = AgentContext(db=db, user_id=uuid.UUID(user_id))
        except (ValueError, AttributeError):
            agent_ctx = AgentContext(db=db, user_id=uuid.UUID(int=0))
        result = await Runner.run(triage_agent, agent_input, run_config=run_config, max_turns=10, context=agent_ctx)
        latency_ms = int((time.monotonic() - start) * 1000)
        response_text = result.final_output or ""
        agent_name = result.last_agent.name if hasattr(result, "last_agent") and result.last_agent else "TriageAgent"
    except Exception as e:
        # Check for SDK guardrail tripwires
        exc_name = type(e).__name__
        if "InputGuardrailTripwireTriggered" in exc_name:
            guardrail_svc.audit("sdk_input_guardrail_tripped", str(chat_session.id), user_id, {})
            return JSONResponse(content={
                "success": True,
                "data": {
                    "response": "I only help with event planning. What event can I help you with? 🎉",
                    "agent": "GuardrailService",
                    "session_id": str(chat_session.id),
                    "guardrail_triggered": True,
                }
            })
        if "OutputGuardrailTripwireTriggered" in exc_name:
            guardrail_svc.audit("sdk_output_guardrail_tripped", str(chat_session.id), user_id, {})
            return JSONResponse(content={
                "success": True,
                "data": {
                    "response": "I'm sorry, I encountered an issue. Please try again.",
                    "agent": "GuardrailService",
                    "session_id": str(chat_session.id),
                    "guardrail_triggered": True,
                }
            })
        if "MaxTurnsExceeded" in exc_name:
            logger.warning("MaxTurnsExceeded for session %s", chat_session.id)
            return JSONResponse(content={
                "success": True,
                "data": {
                    "response": "I wasn't able to complete that in time. Could you simplify your request or try again?",
                    "agent": "TriageAgent",
                    "session_id": str(chat_session.id),
                    "guardrail_triggered": False,
                }
            })
        # Rate limit — return 200 with a polite message so the UI doesn't show an error
        if "RateLimitError" in exc_name or "429" in str(e):
            logger.warning("Rate limit hit for session %s — %s: %s", chat_session.id, exc_name, e)
            return JSONResponse(content={
                "success": True,
                "data": {
                    "response": "I'm a bit busy right now — please wait a moment and try again. 🙏",
                    "agent": "TriageAgent",
                    "session_id": str(chat_session.id),
                    "guardrail_triggered": False,
                }
            })
        logger.error("Agent run error [%s]: %s", exc_name, e, exc_info=True)
        guardrail_svc.audit("agent_error", str(chat_session.id), user_id, {"error": str(e), "exc_type": exc_name})
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": {"code": "AGENT_ERROR", "message": "I encountered an issue. Please try again."}
        })
    # 7. Output leak detection
    leak_detector: OutputLeakDetector = getattr(request.app.state, "leak_detector", None)
    if leak_detector:
        leak_result = leak_detector.scan(response_text)
        if leak_result.leaked:
            guardrail_svc.audit("output_leak", str(chat_session.id), user_id, {"leak_type": leak_result.leak_type})
            response_text = leak_result.safe_response

    # 8. Output filter (PII redaction + length cap)
    safe_response = guardrail_svc.filter_output(response_text, max_chars=settings.max_response_chars)

    # 9. Persist turn
    try:
        await _chat_service.save_turn(db, chat_session, safe_message, safe_response, agent_name, latency_ms)
    except Exception as e:
        logger.warning("Failed to persist chat turn: %s", e)

    # 10. Save turn to Mem0 (fire-and-forget — never block the response)
    try:
        memory_svc_write = MemoryService(api_key=settings.mem0_api_key)
        await memory_svc_write.update_user_memory(
            user_id=user_id,
            messages=[
                {"role": "user", "content": safe_message},
                {"role": "assistant", "content": safe_response},
            ],
        )
    except Exception as e:
        logger.warning("Mem0 turn save failed — skipping: %s", e)

    # 11. Audit
    guardrail_svc.audit("chat_turn", str(chat_session.id), user_id, {
        "agent": agent_name, "latency_ms": latency_ms
    })

    return JSONResponse(content={
        "success": True,
        "data": {
            "response": safe_response,
            "agent": agent_name,
            "session_id": str(chat_session.id),
            "guardrail_triggered": False,
        }
    })


# ── POST /api/v1/ai/chat/stream — SSE streaming ──────────────────

@router.post("/chat/stream")
async def chat_stream(
    body: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
    settings=Depends(get_settings_dep),
):
    if not SSE_AVAILABLE:
        raise HTTPException(status_code=501, detail="SSE not available — install sse-starlette")

    user_id = body.user_id or _get_user_id(request)
    message = body.message.strip()

    # Guardrail check (same as non-streaming)
    firewall = getattr(request.app.state, "firewall", None)
    guardrail_svc = GuardrailService(firewall=firewall)
    guardrail_result = await guardrail_svc.run_input_pipeline(message, user_id, settings)

    if guardrail_result.blocked:
        async def blocked_gen():
            yield {"data": json.dumps({"token": guardrail_result.message, "agent": "GuardrailService"})}
            yield {"data": json.dumps({"done": True, "session_id": body.session_id or "", "agent": "GuardrailService"})}
        return EventSourceResponse(blocked_gen())

    safe_message = guardrail_result.message
    chat_session = await _chat_service.get_or_create_session(db, user_id, body.session_id)
    memory_svc = MemoryService(api_key=settings.mem0_api_key)
    memory_context = await memory_svc.search_user_memory(user_id, safe_message, top_k=5)
    history_msgs = await _chat_service.get_session_messages(db, chat_session.id, limit=6)
    history = [{"role": m.role if isinstance(m.role, str) else m.role.value, "content": m.content} for m in history_msgs]
    canary_token = getattr(request.app.state, "canary_token", "")
    agent_input = build_agent_input(safe_message, memory_context, history, canary_token, firewall)

    triage_agent = request.app.state.triage_agent
    run_config: RunConfig = request.app.state.run_config
    leak_detector: OutputLeakDetector = getattr(request.app.state, "leak_detector", None)

    try:
        agent_ctx = AgentContext(db=db, user_id=uuid.UUID(user_id))
    except (ValueError, AttributeError):
        agent_ctx = AgentContext(db=db, user_id=uuid.UUID(int=0))

    async def event_generator():
        full_response: list[str] = []
        agent_name = "TriageAgent"
        stream_buffer = ""
        buffer_checked = False
        start = time.monotonic()

        try:
            stream = Runner.run_streamed(triage_agent, agent_input, run_config=run_config, max_turns=10, context=agent_ctx)
            async for event in stream.stream_events():
                # Check for client disconnect
                if await request.is_disconnected():
                    logger.info("Client disconnected mid-stream")
                    break

                event_type = getattr(event, "type", None)
                logger.debug("[STREAM] event_type=%s", event_type)

                if event_type == "raw_response_event":
                    # Responses API path (OpenAI native) — token-by-token deltas
                    if isinstance(event.data, ResponseTextDeltaEvent):
                        text = event.data.delta
                        if text:
                            full_response.append(text)
                            stream_buffer += text

                            if not buffer_checked and len(stream_buffer) >= 500:
                                buffer_checked = True
                                if leak_detector and leak_detector.scan_stream_buffer(stream_buffer[:500]):
                                    yield {"data": json.dumps({"token": "I encountered an issue. Please try again.", "agent": agent_name})}
                                    yield {"data": json.dumps({"done": True, "session_id": str(chat_session.id), "agent": agent_name})}
                                    return

                            yield {"data": json.dumps({"token": text, "agent": agent_name})}

                elif event_type == "run_item_stream_event":
                    # Chat Completions path (Gemini / OpenAI-compatible) — full message on completion
                    # Only use this if raw_response_event produced no tokens (avoid double-emit)
                    if event.item.type == "message_output_item" and not full_response:
                        text = ItemHelpers.text_message_output(event.item)
                        if text:
                            full_response.append(text)
                            stream_buffer += text

                            if not buffer_checked and len(stream_buffer) >= 500:
                                buffer_checked = True
                                if leak_detector and leak_detector.scan_stream_buffer(stream_buffer[:500]):
                                    yield {"data": json.dumps({"token": "I encountered an issue. Please try again.", "agent": agent_name})}
                                    yield {"data": json.dumps({"done": True, "session_id": str(chat_session.id), "agent": agent_name})}
                                    return

                            yield {"data": json.dumps({"token": text, "agent": agent_name})}

                elif event_type == "agent_updated_stream_event":
                    new_agent = getattr(getattr(event, "new_agent", None), "name", None)
                    if new_agent:
                        agent_name = new_agent

        except Exception as e:
            exc_name = type(e).__name__
            if "MaxTurnsExceeded" in exc_name:
                logger.warning("MaxTurnsExceeded in stream for session %s", chat_session.id)
                yield {"data": json.dumps({"token": "I wasn't able to complete that in time. Could you simplify your request or try again?", "agent": agent_name})}
            elif "RateLimitError" in exc_name or "429" in str(e):
                logger.warning("Rate limit hit in stream for session %s — %s: %s", chat_session.id, exc_name, e)
                yield {"data": json.dumps({"token": "I'm a bit busy right now — please wait a moment and try again. 🙏", "agent": agent_name})}
            else:
                logger.error("Streaming agent error [%s]: %s", exc_name, e, exc_info=True)
                yield {"data": json.dumps({"token": "I encountered an issue. Please try again.", "agent": "System"})}

        latency_ms = int((time.monotonic() - start) * 1000)
        assembled = "".join(full_response)

        # Final leak check on full response
        if leak_detector and assembled:
            leak_result = leak_detector.scan(assembled)
            if leak_result.leaked:
                assembled = leak_result.safe_response

        # PII filter
        safe_assembled = guardrail_svc.filter_output(assembled, max_chars=settings.max_response_chars)

        # Persist
        try:
            await _chat_service.save_turn(db, chat_session, safe_message, safe_assembled, agent_name, latency_ms)
        except Exception as e:
            logger.warning("Failed to persist streaming turn: %s", e)

        # Save turn to Mem0
        try:
            memory_svc_write = MemoryService(api_key=settings.mem0_api_key)
            await memory_svc_write.update_user_memory(
                user_id=user_id,
                messages=[
                    {"role": "user", "content": safe_message},
                    {"role": "assistant", "content": safe_assembled},
                ],
            )
        except Exception as e:
            logger.warning("Mem0 streaming turn save failed — skipping: %s", e)

        yield {"data": json.dumps({"done": True, "session_id": str(chat_session.id), "agent": agent_name})}

    return EventSourceResponse(event_generator())
