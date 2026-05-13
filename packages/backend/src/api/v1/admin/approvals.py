import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import require_admin, get_session
from src.models.user import User
from src.models.approval import ApprovalRequest
from src.schemas.approval import ApprovalRequestRead, ApprovalRequestUpdate
from src.services.approval_service import approval_service

router = APIRouter(tags=["Admin Approvals"])


def _err(code: str, message: str) -> dict:
    return {"code": code, "message": message}


@router.get("/", response_model=List[ApprovalRequestRead])
async def list_pending_approvals(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Admin-only: List all pending approval requests."""
    return await approval_service.list_pending_approvals(session, limit, offset)


@router.post("/{approval_id}/process", response_model=ApprovalRequestRead)
async def process_approval(
    approval_id: uuid.UUID,
    decision_data: ApprovalRequestUpdate,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Admin-only: Approve, Reject or request more info on a vendor application."""
    approval = await approval_service.get_approval(session, approval_id)
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_err("NOT_FOUND_APPROVAL", "Approval request not found."),
        )

    return await approval_service.process_approval(
        session, approval, current_user.id, decision_data
    )
