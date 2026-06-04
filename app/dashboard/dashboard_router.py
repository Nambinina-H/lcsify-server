import os

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.env.settings import STATIC_DIR

router = APIRouter()


@router.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))
