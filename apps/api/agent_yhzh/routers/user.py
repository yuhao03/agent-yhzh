from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from agent_yhzh.database import get_session
from agent_yhzh.schemas import InteractionCreate
from agent_yhzh.security import UserContext, get_user_context
from agent_yhzh.services.learning import capture_interaction


router = APIRouter(prefix="/api/v1/user", tags=["user"])


@router.post("/interaction", status_code=202)
async def post_interaction(
    payload: InteractionCreate,
    context: UserContext = Depends(get_user_context),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    await capture_interaction(
        session,
        user_id=context.user_id,
        session_id=context.session_id,
        event_type=payload.event_type,
        content=payload.content,
        consent=payload.consent,
    )
    return {"status": "accepted"}


@router.get("/experience")
async def get_experience() -> dict[str, str]:
    return {
        "status": "ready",
        "message": "The assistant learns from validated usage signals without exposing its internal knowledge base.",
    }
