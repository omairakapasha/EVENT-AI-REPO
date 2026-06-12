from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.config.database import lifespan, get_settings
from src.middleware.security_headers import SecurityHeadersMiddleware
from src.api.health import router as health_router
from src.api.v1.bookings import router as bookings_router
from src.api.v1.auth import router as auth_router, users_router
from src.api.v1.vendors import router as vendors_router
from src.api.v1.public_vendors import router as public_vendors_router
from src.api.v1.categories import router as categories_router
from src.api.v1.admin.approvals import router as admin_approvals_router
from src.api.v1.admin.categories import router as admin_categories_router
from src.api.v1.admin.stats import router as admin_stats_router
from src.api.v1.admin.vendors import router as admin_vendors_router
from src.api.v1.admin.users import router as admin_users_router
from src.api.v1.admin.embeddings import router as admin_embeddings_router
from src.api.v1.services import router as services_router
from src.api.v1.inquiries import router as inquiries_router
from src.api.v1.uploads import router as uploads_router
from src.api.v1.events import router as events_router
from src.api.v1.notifications import router as notifications_router
from src.api.v1.sse import router as sse_router
from src.api.v1.subscriptions import router as subscriptions_router, admin_router as admin_subscriptions_router
from src.api.v1.quotes import router as quotes_router
from src.api.v1.reviews import router as reviews_router

settings = get_settings()

app = FastAPI(
    title="Event-AI Backend Service",
    description="Python FastAPI backend with JWT authentication",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Security headers ───────────────────────────────────────────────────────────
app.add_middleware(SecurityHeadersMiddleware)


# ── Global exception handlers ─────────────────────────────────────────────────

def _extract_error(exc: HTTPException) -> dict:
    """
    If detail is already a dict with 'code' and 'message', pass it through.
    Otherwise infer a code from the status code.
    """
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        return exc.detail

    _status_map = {
        401: "AUTH_UNAUTHORIZED",
        403: "AUTH_FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "AUTH_RATE_LIMITED",
        500: "INTERNAL_ERROR",
    }
    code = _status_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return {"code": code, "message": message}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    error = _extract_error(exc)
    response = JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": error},
    )
    # Preserve WWW-Authenticate header for 401 responses
    if exc.headers:
        for key, value in exc.headers.items():
            response.headers[key] = value
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Build a concise human-readable message from Pydantic errors
    errors = exc.errors()
    messages = []
    for e in errors:
        loc = " -> ".join(str(l) for l in e.get("loc", []))
        msg = e.get("msg", "")
        messages.append(f"{loc}: {msg}" if loc else msg)
    message = "; ".join(messages) if messages else "Validation error"
    return JSONResponse(
        status_code=422,
        content={"success": False, "error": {"code": "VALIDATION_ERROR", "message": message}},
    )


# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health_router, prefix="/api/v1")
app.include_router(bookings_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(vendors_router, prefix="/api/v1/vendors")
app.include_router(public_vendors_router, prefix="/api/v1/public_vendors")
app.include_router(categories_router, prefix="/api/v1/categories")
app.include_router(admin_approvals_router, prefix="/api/v1/admin/approvals")
app.include_router(admin_categories_router, prefix="/api/v1/admin/categories")
app.include_router(admin_stats_router, prefix="/api/v1/admin/stats")
app.include_router(admin_vendors_router, prefix="/api/v1/admin/vendors")
app.include_router(admin_users_router, prefix="/api/v1/admin/users")
app.include_router(admin_embeddings_router, prefix="/api/v1/admin/embeddings")
app.include_router(services_router, prefix="/api/v1/services")
app.include_router(inquiries_router, prefix="/api/v1/inquiries")
app.include_router(uploads_router, prefix="/api/v1/uploads")
app.include_router(events_router, prefix="/api/v1/events")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(sse_router, prefix="/api/v1")
app.include_router(subscriptions_router, prefix="/api/v1/subscriptions")
app.include_router(admin_subscriptions_router, prefix="/api/v1/admin/subscriptions")
app.include_router(quotes_router, prefix="/api/v1")
app.include_router(reviews_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"success": True, "data": {"message": "Event-AI Backend Python API"}, "meta": {}}
