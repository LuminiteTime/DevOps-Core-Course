"""DevOps Info Service application.

Main application module. 
For now it is all contained in a single file for simplicity, but is planned to be modularized later.
"""

from __future__ import annotations

import logging
import os
import platform
import socket
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn

# Configuration
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8080"))
DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

APP_VERSION: str = "1.0.0"
APP_NAME: str = "devops-info-service"
APP_DESCRIPTION: str = "DevOps course info service"
APP_FRAMEWORK: str = "FastAPI"

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(APP_NAME)

# Application start time
START_TIME: datetime = datetime.now(timezone.utc)


def get_system_info() -> Dict[str, Any]:
    """Return information about the current host and Python runtime."""

    return {
        "hostname": socket.gethostname(),
        "platform": platform.system(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "cpu_count": os.cpu_count() or 1,
        "python_version": platform.python_version(),
    }


def get_uptime() -> Dict[str, Any]:
    """Calculate uptime in seconds and a human readable form."""

    delta = datetime.now(timezone.utc) - START_TIME
    seconds = int(delta.total_seconds())
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return {
        "uptime_seconds": seconds,
        "uptime_human": f"{hours} hours, {minutes} minutes",
    }


def get_runtime_info() -> Dict[str, Any]:
    """Build runtime information including uptime and current UTC time."""

    uptime = get_uptime()
    return {
        "uptime_seconds": uptime["uptime_seconds"],
        "uptime_human": uptime["uptime_human"],
        "current_time": datetime.now(timezone.utc).isoformat(),
        "timezone": "UTC",
    }


def get_request_info(request: Request) -> Dict[str, Any]:
    """Extract client and request metadata from the incoming HTTP request."""

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    return {
        "client_ip": client_ip,
        "user_agent": user_agent,
        "method": request.method,
        "path": request.url.path,
    }


def get_endpoints() -> List[Dict[str, str]]:
    """Describe public endpoints exposed by this service."""

    return [
        {
            "path": "/",
            "method": "GET",
            "description": "Service information",
        },
        {
            "path": "/health",
            "method": "GET",
            "description": "Health check",
        },
    ]


app: FastAPI = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Return structured JSON for HTTP errors such as 404."""

    logger.warning("HTTP error %s on %s", exc.status_code, request.url.path)
    if exc.status_code == 404:
        return JSONResponse(
            status_code=404,
            content={
                "error": "Not Found",
                "message": "Endpoint does not exist",
            },
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "message": exc.detail,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
        request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI request validation errors with JSON details."""

    logger.warning("Validation error on %s: %s",
                   request.url.path, exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "message": "Request parameters failed validation",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
        request: Request, exc: Exception
) -> JSONResponse:
    """Catch and log unexpected exceptions as HTTP 500 responses."""

    logger.exception("Unhandled error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
        },
    )


@app.get("/")
async def index(request: Request) -> Dict[str, Any]:
    """Main endpoint returning service information."""

    logger.info("Handling request on %s %s from %s",
                request.method,
                request.url.path,
                request.client.host if request.client else "unknown"
                )

    response: Dict[str, Any] = {
        "service": {
            "name": APP_NAME,
            "version": APP_VERSION,
            "description": APP_DESCRIPTION,
            "framework": APP_FRAMEWORK,
        },
        "system": get_system_info(),
        "runtime": get_runtime_info(),
        "request": get_request_info(request),
        "endpoints": get_endpoints(),
    }
    return response


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Health check endpoint returning service status and uptime seconds."""

    uptime = get_uptime()
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime["uptime_seconds"],
    }


def main() -> None:
    """Run the FastAPI application using uvicorn with configured settings."""

    logger.info(
        "Starting DevOps Info Service on %s:%s (debug=%s)",
        HOST,
        PORT,
        DEBUG,
    )
    uvicorn.run("app:app", host=HOST, port=PORT, reload=DEBUG)


if __name__ == "__main__":
    main()
