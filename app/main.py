import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.agent_config.config_router import router as agent_config_router
from app.common.error.handlers import register_exception_handlers
from app.dashboard.dashboard_router import router as dashboard_router
from app.env.settings import CORS_ORIGINS, STATIC_DIR
from app.ingest.ingest_router import router as ingest_router
from app.logging_config import get_logger, setup_logging
from app.report.report_router import router as report_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Demarrage : on configure les logs puis on applique les migrations.
    setup_logging()
    logger.info("Serveur demarre.")
    yield
    logger.info("Serveur arrete.")


logger = get_logger()
app = FastAPI(title="LCSify - Serveur central", lifespan=lifespan)

register_exception_handlers(app)

# Autorise le frontend Next.js (origine differente) a appeler l'API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest_router)
app.include_router(report_router)
app.include_router(agent_config_router)
app.include_router(dashboard_router)

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
