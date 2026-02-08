# DevOps Info Service (Python / FastAPI)

[![Python CI](https://github.com/LuminiteTime/DevOps-Core-Course/actions/workflows/python-ci.yml/badge.svg?branch=master)](https://github.com/LuminiteTime/DevOps-Core-Course/actions/workflows/python-ci.yml)
[![Coverage](https://codecov.io/gh/LuminiteTime/DevOps-Core-Course/branch/master/graph/badge.svg)](https://codecov.io/gh/LuminiteTime/DevOps-Core-Course)

## Overview

This service exposes a small HTTP API that reports information about the running host, the Python runtime, and the incoming request. It is used as a base for later DevOps labs.

The API provides:
- `GET /` – service, system, runtime, and request metadata
- `GET /health` – simple health check with uptime info

## Prerequisites

- Python 3.11+

Python dependencies are listed and pinned with versions in [app_python/requirements.txt](app_python/requirements.txt).

## Installation

```bash
cd app_python
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the Application

Default configuration (HOST=0.0.0.0, PORT=8080, DEBUG=false):

```bash
cd app_python
source venv/bin/activate
python app.py
```

Custom configuration with environment variables:

```bash
# Run on localhost:8080
cd app_python
source venv/bin/activate
PORT=8080 python app.py

# Run on 127.0.0.1:3000 with debug reload
HOST=127.0.0.1 PORT=3000 DEBUG=true python app.py
```

After start, you can test the endpoints with curl (default app config used in commands):

```bash
curl http://localhost:8080/
curl http://localhost:8080/health
```

## Docker

### Build (local)

```bash
cd app_python
docker build -t <local-tag> .
```

### Run

```bash
docker run --rm --name <container-name> -p <host-port>:8080 <local-tag>
```

Test endpoints:

```bash
curl http://localhost:<host-port>/
curl http://localhost:<host-port>/health
```

### Pull from Docker Hub

```bash
docker pull <dockerhub-username>/<repo>:<tag>
docker run --rm -p <host-port>:8080 <dockerhub-username>/<repo>:<tag>
```

## Testing

Install dev dependencies and run tests:

```bash
cd app_python
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

ruff check .
pytest
```

## API Endpoints

- `GET /`
  - Returns JSON with the following top-level sections:
    - `service` – name, version, description, framework
    - `system` – hostname, platform, platform_version, architecture, cpu_count, python_version
    - `runtime` – uptime_seconds, uptime_human, current_time, timezone
    - `request` – client_ip, user_agent, method, path
    - `endpoints` – list of available paths and their purpose

- `GET /health`
  - Returns a compact health document:
    - `status` – string status ("healthy")
    - `timestamp` – current UTC timestamp in ISO 8601 format
    - `uptime_seconds` – number of seconds the process has been running

## Configuration

The application is configured via environment variables read in [app_python/app.py](app_python/app.py):

| Variable | Default    | Description                           |
|----------|------------|---------------------------------------|
| `HOST`   | `0.0.0.0`  | Address app binds to                  |
| `PORT`   | `8080`     | TCP port app listens on               |
| `DEBUG`  | `False`    | When `true`, enables app reload       |

All variables are optional. If they are not set, the defaults above are used.
