from typing import List, Optional

from pydantic import BaseModel


class Event(BaseModel):
    client_id: Optional[int] = None
    employee_id: str
    employee_name: Optional[str] = None
    client: Optional[str] = None          # nom du client
    app: Optional[str] = None
    window_title: Optional[str] = None
    project: Optional[str] = None          # nom de la video
    version: Optional[str] = None          # V1, V2, ...
    state: str
    start_ts: str
    end_ts: str
    duration_sec: int


class EventBatch(BaseModel):
    events: List[Event]
