from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.realtime import presence
from app.realtime.schemas import Heartbeat
from app.security.security import check_agent_key, check_dashboard

router = APIRouter()


@router.post("/api/heartbeat")
def heartbeat(payload: Heartbeat, _=Depends(check_agent_key)):
    """L'agent y pousse son état courant (~10 s) -> présence temps réel."""
    presence.update(payload.employee_id, payload.model_dump())
    return {"status": "ok"}


@router.get("/api/live")
async def live(_=Depends(check_dashboard)):
    """Flux SSE de la présence pour le dashboard."""
    return StreamingResponse(
        presence.event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # desactive le buffering proxy (Railway)
        },
    )
