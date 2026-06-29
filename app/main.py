import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.agent_config.config_router import router as agent_config_router
from app.audit.audit_router import router as audit_router
from app.auth import auth_service
from app.auth.auth_router import router as auth_router
from app.auth.users_router import router as users_router
from app.clients.client_router import router as clients_router
from app.common.error.handlers import register_exception_handlers
from app.dashboard.dashboard_router import router as dashboard_router
from app.database.migrate import run_migrations
from app.env.settings import CORS_ORIGINS, STATIC_DIR
from app.ingest.ingest_router import router as ingest_router
from app.leaves.leaves_router import router as leaves_router
from app.logging_config import get_logger, setup_logging
from app.projects.project_router import router as projects_router
from app.realtime.realtime_router import router as realtime_router
from app.report.report_router import router as report_router
from app.spaces.space_router import router as spaces_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Demarrage : logs -> migrations (cree le schema) -> compte admin initial.
    setup_logging()
    run_migrations()
    auth_service.ensure_admin()
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

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(ingest_router)
app.include_router(report_router)
app.include_router(agent_config_router)
app.include_router(projects_router)
app.include_router(clients_router)
app.include_router(realtime_router)
app.include_router(dashboard_router)
app.include_router(audit_router)
app.include_router(spaces_router)
app.include_router(leaves_router)

if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
