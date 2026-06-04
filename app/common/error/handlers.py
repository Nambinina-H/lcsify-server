from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.logging_config import get_logger

logger = get_logger()


def register_exception_handlers(app: FastAPI):
    """Branche les gestionnaires d'erreurs globaux sur l'application.

    Toutes les erreurs renvoient une forme uniforme : {message, api, method},
    sans fuite de stack trace au client.
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code >= 500:
            logger.error("%s %s -> %s", request.method, request.url.path, exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "message": exc.detail,
                "api": request.url.path,
                "method": request.method,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(
            "%s %s -> exception non geree", request.method, request.url.path
        )
        return JSONResponse(
            status_code=500,
            content={
                "message": "Erreur interne du serveur.",
                "api": request.url.path,
                "method": request.method,
            },
        )
