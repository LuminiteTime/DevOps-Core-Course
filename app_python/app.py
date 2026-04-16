"""DevOps Info Service application.

Main application module. 
For now it is all contained in a single file for simplicity, but is planned to be modularized later.
"""

from __future__ import annotations

import logging
import os
import platform
import socket
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pythonjsonlogger.json import JsonFormatter
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn

# Configuration
HOST: str = os.getenv("HOST", "0.0.0.0")
PORT: int = int(os.getenv("PORT", "8080"))
DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
APP_NAME: str = os.getenv("APP_NAME", "devops-info-service")
APP_DESCRIPTION: str = os.getenv(
    "APP_DESCRIPTION", "DevOps course info service"
)
APP_FRAMEWORK: str = os.getenv("APP_FRAMEWORK", "FastAPI")
APP_VARIANT: str = os.getenv("APP_VARIANT", "default")
VISITS_FILE_PATH: Path = Path(
    os.getenv("VISITS_FILE_PATH", "./data/visits")
).expanduser()

KNOWN_ENDPOINTS: set[str] = {"/", "/health", "/metrics", "/visits"}

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests handled by the service",
    ["method", "endpoint", "status_code"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "status_code"],
)
HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently being processed",
    ["method", "endpoint"],
)
DEVOPS_INFO_ENDPOINT_CALLS = Counter(
    "devops_info_endpoint_calls",
    "Application endpoint usage",
    ["endpoint"],
)
DEVOPS_INFO_SYSTEM_COLLECTION_SECONDS = Histogram(
    "devops_info_system_collection_seconds",
    "Time spent collecting system information",
)


class _AppJsonFormatter(JsonFormatter):
    """Custom JSON formatter that adds service context to every log record."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = datetime.now(timezone.utc).isoformat()
        log_record["level"] = record.levelname
        log_record["service"] = APP_NAME
        log_record.pop("taskName", None)


def _setup_logging() -> logging.Logger:
    """Configure root and application loggers with JSON output.

    Also patches uvicorn loggers so all output is JSON-formatted.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(
        _AppJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s",
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if DEBUG else logging.INFO)

    for name in ("uvicorn", "uvicorn.error"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers.clear()
        uv_logger.propagate = True

    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.propagate = False

    return logging.getLogger(APP_NAME)


logger = _setup_logging()

# Application start time
START_TIME: datetime = datetime.now(timezone.utc)
VISITS_LOCK = threading.Lock()


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
        "pod_name": os.getenv("POD_NAME", socket.gethostname()),
        "node_name": os.getenv("NODE_NAME", "unknown"),
        "namespace": os.getenv("POD_NAMESPACE", "default"),
    }


def read_visit_count() -> int:
    """Read the persisted visit count from disk."""

    try:
        return int(VISITS_FILE_PATH.read_text(encoding="utf-8").strip())
    except FileNotFoundError:
        return 0
    except ValueError:
        logger.warning(
            "Visits counter file %s is invalid, resetting to 0",
            VISITS_FILE_PATH,
        )
        return 0


def write_visit_count(count: int) -> None:
    """Persist the current visit count using an atomic replace."""

    VISITS_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = VISITS_FILE_PATH.with_name(f"{VISITS_FILE_PATH.name}.tmp")
    temp_path.write_text(str(count), encoding="utf-8")
    temp_path.replace(VISITS_FILE_PATH)


def increment_visit_count() -> int:
    """Increment and persist the visit count safely within this process."""

    with VISITS_LOCK:
        count = read_visit_count() + 1
        write_visit_count(count)
        return count


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
        {
            "path": "/metrics",
            "method": "GET",
            "description": "Prometheus metrics",
        },
        {
            "path": "/visits",
            "method": "GET",
            "description": "Current persisted visits counter",
        },
    ]


def normalize_endpoint_label(path: str) -> str:
    """Keep endpoint labels low-cardinality for Prometheus."""

    return path if path in KNOWN_ENDPOINTS else "unmatched"


app: FastAPI = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION
)


@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:
    """Log every request and emit Prometheus RED metrics."""
    client_ip = request.client.host if request.client else "unknown"
    endpoint = normalize_endpoint_label(request.url.path)
    in_progress = HTTP_REQUESTS_IN_PROGRESS.labels(request.method, endpoint)
    start = time.monotonic()
    in_progress.inc()
    try:
        response = await call_next(request)
    except Exception:
        duration_seconds = time.monotonic() - start
        HTTP_REQUESTS_TOTAL.labels(request.method, endpoint, "500").inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(
            request.method, endpoint, "500"
        ).observe(duration_seconds)
        in_progress.dec()
        raise

    duration_seconds = time.monotonic() - start
    duration_ms = round(duration_seconds * 1000, 2)
    status_code = str(response.status_code)
    HTTP_REQUESTS_TOTAL.labels(request.method, endpoint, status_code).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(
        request.method, endpoint, status_code
    ).observe(duration_seconds)
    in_progress.dec()
    logger.info(
        "%s %s %s",
        request.method,
        request.url.path,
        response.status_code,
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "client_ip": client_ip,
            "duration_ms": duration_ms,
        },
    )
    return response


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

    DEVOPS_INFO_ENDPOINT_CALLS.labels("/").inc()
    increment_visit_count()
    with DEVOPS_INFO_SYSTEM_COLLECTION_SECONDS.time():
        system_info = get_system_info()

    response: Dict[str, Any] = {
        "service": {
            "name": APP_NAME,
            "version": APP_VERSION,
            "description": APP_DESCRIPTION,
            "framework": APP_FRAMEWORK,
            "variant": APP_VARIANT,
        },
        "system": system_info,
        "runtime": get_runtime_info(),
        "request": get_request_info(request),
        "endpoints": get_endpoints(),
    }
    return response


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Health check endpoint returning service status and uptime seconds."""

    DEVOPS_INFO_ENDPOINT_CALLS.labels("/health").inc()
    uptime = get_uptime()
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime["uptime_seconds"],
    }


@app.get("/metrics")
async def metrics() -> Response:
    """Expose Prometheus metrics for scraping."""

    DEVOPS_INFO_ENDPOINT_CALLS.labels("/metrics").inc()
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/visits")
async def visits() -> Dict[str, int]:
    """Return the current persisted visit count."""

    DEVOPS_INFO_ENDPOINT_CALLS.labels("/visits").inc()
    with VISITS_LOCK:
        return {"visits": read_visit_count()}


def main() -> None:
    """Run the FastAPI application using uvicorn with configured settings."""

    logger.info(
        "Starting DevOps Info Service on %s:%s (debug=%s)",
        HOST,
        PORT,
        DEBUG,
    )
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
