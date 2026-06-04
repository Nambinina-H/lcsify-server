from fastapi import APIRouter, Depends

from app.ingest import ingest_service
from app.ingest.schemas import EventBatch
from app.security.security import check_agent_key

router = APIRouter()


@router.post("/api/events")
def ingest(batch: EventBatch, _=Depends(check_agent_key)):
    return ingest_service.ingest_events(batch)
