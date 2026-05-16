import logging
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from openai import AsyncOpenAI
from agents import set_tracing_disabled, OpenAIChatCompletionsModel
from agents.run import RunConfig

from config.settings import get_settings

# ── Logging — DEBUG for our routers so stream events are visible ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("routers.chat").setLevel(logging.DEBUG)
logging.getLogger("services.chat_service").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Cache-Control"] = "no-store"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # DB — use async_database_url (sslmode stripped); pass SSL via connect_args
    connect_args = {"ssl": "require"} if settings.ssl_required else {}
    engine = create_async_engine(settings.async_database_url, echo=False, connect_args=connect_args)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    # Shared HTTP client
    http_client = httpx.AsyncClient(timeout=30.0)

    # Disable tracing — Gemini via OpenAI-compatible endpoint, no OpenAI key
    set_tracing_disabled(True)

    # Model via Gemini's OpenAI-compatible REST endpoint (no LiteLLM needed)
    gemini_client = AsyncOpenAI(
        api_key=settings.gemini_api_key,
        base_url=settings.gemini_base_url,
    )
    model = OpenAIChatCompletionsModel(
        model=settings.gemini_model,
        openai_client=gemini_client,
    )
    run_config = RunConfig(model=model)

    # Canary token — generated at startup, never stored in .env or any file
    canary_token = str(uuid.uuid4())

    # Build agent pipeline — triage_agent is the single entry point
    from pipeline import build_pipeline
    triage_agent = build_pipeline(model)

    # Initialise PromptFirewall
    from services.prompt_firewall import PromptFirewall
    firewall = PromptFirewall(settings=settings, blocklist_path=settings.injection_blocklist_path)

    # Initialise OutputLeakDetector
    from services.output_leak_detector import OutputLeakDetector
    leak_detector = OutputLeakDetector(canary_token=canary_token)

    # Initialise GuardrailService with firewall
    from services.guardrail_service import GuardrailService
    guardrail_service = GuardrailService(firewall=firewall)

    # Wire SDK-native guardrail hooks to the firewall and leak detector
    from services.guardrail_hooks import set_guardrail_instances
    set_guardrail_instances(firewall, leak_detector)

    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.http_client = http_client
    app.state.model = model
    app.state.run_config = run_config
    app.state.canary_token = canary_token
    app.state.settings = settings
    app.state.triage_agent = triage_agent
    app.state.firewall = firewall
    app.state.leak_detector = leak_detector
    app.state.guardrail_service = guardrail_service

    logger.info("AI Agent Chat service started")
    yield

    await http_client.aclose()
    await engine.dispose()
    logger.info("AI Agent Chat service shut down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="AI Agent Chat Service",
        description="Multi-agent AI chat service for event planning",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    )

    app.add_middleware(SecurityHeadersMiddleware)

    # Router registration — wrapped in try/except as routers are added in later tasks
    try:
        from routers.chat import router as chat_router
        app.include_router(chat_router)
    except ImportError:
        logger.debug("routers.chat not yet available")

    try:
        from routers.feedback import router as feedback_router
        app.include_router(feedback_router)
    except ImportError:
        logger.debug("routers.feedback not yet available")

    try:
        from routers.memory import router as memory_router
        app.include_router(memory_router)
    except ImportError:
        logger.debug("routers.memory not yet available")

    try:
        from routers.admin_chat import router as admin_chat_router
        app.include_router(admin_chat_router)
    except ImportError:
        logger.debug("routers.admin_chat not yet available")

    try:
        from routers.admin_guardrails import router as admin_guardrails_router
        app.include_router(admin_guardrails_router)
    except ImportError:
        logger.debug("routers.admin_guardrails not yet available")

    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "service": "AI Agent Chat",
            "version": "1.0.0",
        }

    return app


app = create_app()
