"""
SSE Real-Time Stream endpoint (008).
Browsers connect via EventSource; JWT is read from httpOnly cookie.
(EventSource API does not support custom headers, so cookie auth is used)
"""
import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from src.services.sse_manager import SSEConnectionManager, get_connection_manager
from src.services.auth_service import AuthService
from src.config.database import async_session_maker

router = APIRouter(prefix="/sse", tags=["SSE"])

PING_INTERVAL = 30  # seconds


async def _event_stream(
    user_id, queue: asyncio.Queue, cm: SSEConnectionManager
) -> AsyncGenerator[str, None]:
    yield f"event: connected\ndata: {json.dumps({'user_id': str(user_id)})}\n\n"
    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=PING_INTERVAL)
                yield f"event: {msg['event']}\ndata: {json.dumps(msg['data'], default=str)}\n\n"
            except asyncio.TimeoutError:
                yield "event: ping\ndata: {}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        cm.disconnect(user_id, queue)


@router.get("/stream")
async def sse_stream(
    request: Request,
    cm: SSEConnectionManager = Depends(get_connection_manager),
):
    """
    Server-Sent Events stream. Authenticates via httpOnly access_token cookie.
    Returns a persistent text/event-stream response.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH_UNAUTHORIZED", "message": "No access token cookie found."},
        )

    async with async_session_maker() as session:
        try:
            user = await AuthService.verify_access_token(token, session)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "AUTH_UNAUTHORIZED", "message": "Invalid or expired token."},
            )

    queue = cm.connect(user.id)
    return StreamingResponse(
        _event_stream(user.id, queue, cm),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
