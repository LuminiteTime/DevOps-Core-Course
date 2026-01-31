# LAB02 — Docker Containerization (Python / FastAPI)

## 1. Docker Best Practices Applied

- Non-root user
  - Why it matters: limits damage if the process is compromised; avoids privileged filesystem access inside the container.
- Specific base image version
  - Why it matters: reproducible builds; reduces surprise changes from upstream.
- Layer caching (dependencies before code)
  - Why it matters: rebuilding after a code change does not reinstall dependencies.
- Only copy runtime files
  - Why it matters: smaller image and less accidental leakage of dev artifacts.
- `.dockerignore`
  - Why it matters: smaller build context, faster builds, fewer irrelevant files included in layers.

Relevant Dockerfile excerpt:

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN addgroup --system app && adduser --system --ingroup app app
USER app
```

## 2. Image Information & Decisions

- Base image: `python:3.13-slim`
  - Reason: small Debian-based image with wide compatibility; specific Python major/minor pinned.
- Optimization choices:
  - `--no-cache-dir` for pip to avoid caching wheels in the final image.
  - Minimal COPY set (`requirements.txt`, then `app.py`).

Image size:

```text
devops-info-service-python:lab02 = 181MB
```

- The size is reasonable for `python:3.13-slim` plus FastAPI + uvicorn[standard]. The biggest contributors are the Python runtime and binary wheels for `uvicorn[standard]` extras.

Layer structure notes:

- `requirements.txt` copied and installed before application code to maximize cache reuse.
- Application code copied last so code changes invalidate the smallest possible part of the build.

## 3. Build & Run Process

### 3.1 Build output

```text
#0 building with "orbstack" instance using docker driver

#1 [internal] load build definition from Dockerfile
#1 transferring dockerfile: 362B done
#1 DONE 0.0s

#2 [internal] load metadata for docker.io/library/python:3.13-slim
#2 DONE 0.0s

#3 [internal] load .dockerignore
#3 transferring context: 163B done
#3 DONE 0.0s

#4 [1/7] FROM docker.io/library/python:3.13-slim
#4 DONE 0.0s

#5 [internal] load build context
#5 transferring context: 6.39kB done
#5 DONE 0.0s

#6 [2/7] WORKDIR /app
#6 DONE 0.0s

#7 [3/7] RUN addgroup --system app && adduser --system --ingroup app app
#7 DONE 0.2s

#8 [4/7] COPY requirements.txt .
#8 DONE 0.0s

#9 [5/7] RUN pip install --no-cache-dir -r requirements.txt
#9 1.053 Collecting fastapi==0.115.0 (from -r requirements.txt (line 1))
#9 1.390   Downloading fastapi-0.115.0-py3-none-any.whl.metadata (27 kB)
#9 1.504 Collecting uvicorn==0.32.0 (from uvicorn[standard]==0.32.0->-r requirements.txt (line 2))
#9 1.560   Downloading uvicorn-0.32.0-py3-none-any.whl.metadata (6.6 kB)
#9 1.661 Collecting starlette<0.39.0,>=0.37.2 (from fastapi==0.115.0->-r requirements.txt (line 1))
#9 1.716   Downloading starlette-0.38.6-py3-none-any.whl.metadata (6.0 kB)
#9 1.938 Collecting pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4 (from fastapi==0.115.0->-r requirements.txt (line 1))
#9 1.992   Downloading pydantic-2.12.5-py3-none-any.whl.metadata (90 kB)
#9 2.124 Collecting typing-extensions>=4.8.0 (from fastapi==0.115.0->-r requirements.txt (line 1))
#9 2.180   Downloading typing_extensions-4.15.0-py3-none-any.whl.metadata (3.3 kB)
#9 2.264 Collecting click>=7.0 (from uvicorn==0.32.0->uvicorn[standard]==0.32.0->-r requirements.txt (line 2))
#9 2.318   Downloading click-8.3.1-py3-none-any.whl.metadata (2.6 kB)
#9 2.384 Collecting h11>=0.8 (from uvicorn==0.32.0->uvicorn[standard]==0.32.0->-r requirements.txt (line 2))
#9 2.438   Downloading h11-0.16.0-py3-none-any.whl.metadata (8.3 kB)
#9 2.529 Collecting httptools>=0.5.0 (from uvicorn[standard]==0.32.0->-r requirements.txt (line 2))
#9 2.585   Downloading httptools-0.7.1-cp313-cp313-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl.metadata (3.5 kB)
#9 2.666 Collecting python-dotenv>=0.13 (from uvicorn[standard]==0.32.0->-r requirements.txt (line 2))
#9 2.723   Downloading python_dotenv-1.2.1-py3-none-any.whl.metadata (25 kB)
#9 2.827 Collecting pyyaml>=5.1 (from uvicorn[standard]==0.32.0->-r requirements.txt (line 2))
#9 2.882   Downloading pyyaml-6.0.3-cp313-cp313-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl.metadata (2.4 kB)
#9 2.994 Collecting uvloop!=0.15.0,!=0.15.1,>=0.14.0 (from uvicorn[standard]==0.32.0->-r requirements.txt (line 2))
#9 3.051   Downloading uvloop-0.22.1-cp313-cp313-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl.metadata (4.9 kB)
#9 3.174 Collecting watchfiles>=0.13 (from uvicorn[standard]==0.32.0->-r requirements.txt (line 2))
#9 3.230   Downloading watchfiles-1.1.1-cp313-cp313-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (4.9 kB)
#9 3.363 Collecting websockets>=10.4 (from uvicorn[standard]==0.32.0->-r requirements.txt (line 2))
#9 3.417   Downloading websockets-16.0-cp313-cp313-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl.metadata (6.8 kB)
#9 3.480 Collecting annotated-types>=0.6.0 (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi==0.115.0->-r requirements.txt (line 1))
#9 3.538   Downloading annotated_types-0.7.0-py3-none-any.whl.metadata (15 kB)
#9 3.955 Collecting pydantic-core==2.41.5 (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi==0.115.0->-r requirements.txt (line 1))
#9 4.008   Downloading pydantic_core-2.41.5-cp313-cp313-manylinux_2_17_aarch64.manylinux2014_aarch64.whl.metadata (7.3 kB)
#9 4.068 Collecting typing-inspection>=0.4.2 (from pydantic!=1.8,!=1.8.1,!=2.0.0,!=2.0.1,!=2.1.0,<3.0.0,>=1.7.4->fastapi==0.115.0->-r requirements.txt (line 1))
#9 4.122   Downloading typing_inspection-0.4.2-py3-none-any.whl.metadata (2.6 kB)
#9 4.213 Collecting anyio<5,>=3.4.0 (from starlette<0.39.0,>=0.37.2->fastapi==0.115.0->-r requirements.txt (line 1))
#9 4.270   Downloading anyio-4.12.1-py3-none-any.whl.metadata (4.3 kB)
#9 4.346 Collecting idna>=2.8 (from anyio<5,>=3.4.0->starlette<0.39.0,>=0.37.2->fastapi==0.115.0->-r requirements.txt (line 1))
#9 4.404   Downloading idna-3.11-py3-none-any.whl.metadata (8.4 kB)
#9 4.487 Downloading fastapi-0.115.0-py3-none-any.whl (94 kB)
#9 4.558 Downloading uvicorn-0.32.0-py3-none-any.whl (63 kB)
#9 4.619 Downloading pydantic-2.12.5-py3-none-any.whl (463 kB)
#9 4.749 Downloading pydantic_core-2.41.5-cp313-cp313-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (1.9 MB)
#9 4.935 Downloading starlette-0.38.6-py3-none-any.whl (71 kB)
#9 4.999 Downloading anyio-4.12.1-py3-none-any.whl (113 kB)
#9 5.058 Downloading annotated_types-0.7.0-py3-none-any.whl (13 kB)
#9 5.114 Downloading click-8.3.1-py3-none-any.whl (108 kB)
#9 5.181 Downloading h11-0.16.0-py3-none-any.whl (37 kB)
#9 5.240 Downloading httptools-0.7.1-cp313-cp313-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (473 kB)
#9 5.317 Downloading idna-3.11-py3-none-any.whl (71 kB)
#9 5.376 Downloading python_dotenv-1.2.1-py3-none-any.whl (21 kB)
#9 5.434 Downloading pyyaml-6.0.3-cp313-cp313-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (767 kB)
#9 5.548 Downloading typing_extensions-4.15.0-py3-none-any.whl (44 kB)
#9 5.605 Downloading typing_inspection-0.4.2-py3-none-any.whl (14 kB)
#9 5.664 Downloading uvloop-0.22.1-cp313-cp313-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (4.3 MB)
#9 5.912 Downloading watchfiles-1.1.1-cp313-cp313-manylinux_2_17_aarch64.manylinux2014_aarch64.whl (449 kB)
#9 5.987 Downloading websockets-16.0-cp313-cp313-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl (186 kB)
#9 6.048 Installing collected packages: websockets, uvloop, typing-extensions, pyyaml, python-dotenv, idna, httptools, h11, click, annotated-types, uvicorn, typing-inspection, pydantic-core, anyio, watchfiles, starlette, pydantic, fastapi
#9 6.524 Successfully installed annotated-types-0.7.0 anyio-4.12.1 click-8.3.1 fastapi-0.115.0 h11-0.16.0 httptools-0.7.1 idna-3.11 pydantic-2.12.5 pydantic-core-2.41.5 python-dotenv-1.2.1 pyyaml-6.0.3 starlette-0.38.6 typing-extensions-4.15.0 typing-inspection-0.4.2 uvicorn-0.32.0 uvloop-0.22.1 watchfiles-1.1.1 websockets-16.0
#9 DONE 6.9s

#10 [6/7] COPY app.py .
#10 DONE 0.0s

#11 [7/7] RUN chown -R app:app /app
#11 DONE 0.1s

#12 exporting to image
#12 exporting layers 0.1s done
#12 writing image sha256:9635ee51eeb6a6c1e65741bd2f136a0ff77cd1b2fb38b052ad4c459d21bc812f done
#12 naming to docker.io/library/devops-info-service-python:lab02 done
#12 DONE 0.1s
```

### 3.2 Container running output

```text
43fdf2d5ae55aa3058135566c590c81cd1acd1bc04f7c38b91c38561f7854f42
CONTAINER ID   IMAGE                              COMMAND           CREATED        STATUS        PORTS                                         NAMES
43fdf2d5ae55   devops-info-service-python:lab02   "python app.py"   1 second ago   Up 1 second   0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp   devops-info-python
```

### 3.3 Endpoint tests

```text
GET /
{
  "service": {
    "name": "devops-info-service",
    "version": "1.0.0",
    "description": "DevOps course info service",
    "framework": "FastAPI"
  },
  "system": {
    "hostname": "9d5b7640e4b7",
    "platform": "Linux",
    "platform_version": "#1 SMP PREEMPT Thu Nov 20 09:34:02 UTC 2025",
    "architecture": "aarch64",
    "cpu_count": 12,
    "python_version": "3.13.11"
  },
  "runtime": {
    "uptime_seconds": 0,
    "uptime_human": "0 hours, 0 minutes",
    "current_time": "2026-01-31T11:11:05.687867+00:00",
    "timezone": "UTC"
  },
  "request": {
    "client_ip": "192.168.215.1",
    "user_agent": "curl/8.7.1",
    "method": "GET",
    "path": "/"
  },
  "endpoints": [
    {
      "path": "/",
      "method": "GET",
      "description": "Service information"
    },
    {
      "path": "/health",
      "method": "GET",
      "description": "Health check"
    }
  ]
}

GET /health
{
  "status": "healthy",
  "timestamp": "2026-01-31T11:11:05.696534+00:00",
  "uptime_seconds": 0
}
```

Docker Hub repository:

- `https://hub.docker.com/repository/docker/luminitetime/devops-info-service-python`

Tagging strategy:

- `luminitetime/devops-info-service-python:lab02` for the lab submission state
- `luminitetime/devops-info-service-python:latest` for the most recent build

Docker push output:

```text
The push refers to repository [docker.io/luminitetime/devops-info-service-python]
4aca6a960a6c: Preparing
6b2fdc7164d9: Preparing
55eb172d93ab: Preparing
1a245b95a27a: Preparing
c8ae99256e9c: Preparing
d0749c8b4e23: Preparing
9661772b6bf6: Preparing
7b42a1e79f8b: Preparing
c66c050e39d8: Preparing
37127a0fa4c7: Preparing
d0749c8b4e23: Waiting
9661772b6bf6: Waiting
7b42a1e79f8b: Waiting
c66c050e39d8: Waiting
37127a0fa4c7: Waiting
1a245b95a27a: Pushed
4aca6a960a6c: Pushed
c8ae99256e9c: Pushed
6b2fdc7164d9: Pushed
55eb172d93ab: Pushed
9661772b6bf6: Pushed
d0749c8b4e23: Pushed
c66c050e39d8: Pushed
7b42a1e79f8b: Pushed
37127a0fa4c7: Pushed
lab02: digest: sha256:c795ea48a004f19b8a2c12c33c895522b0fe0dfd477941b8f2ec47b600c16f9e size: 2408
The push refers to repository [docker.io/luminitetime/devops-info-service-python]
4aca6a960a6c: Preparing
6b2fdc7164d9: Preparing
55eb172d93ab: Preparing
1a245b95a27a: Preparing
c8ae99256e9c: Preparing
d0749c8b4e23: Preparing
9661772b6bf6: Preparing
7b42a1e79f8b: Preparing
c66c050e39d8: Preparing
37127a0fa4c7: Preparing
9661772b6bf6: Waiting
7b42a1e79f8b: Waiting
c66c050e39d8: Waiting
37127a0fa4c7: Waiting
d0749c8b4e23: Waiting
1a245b95a27a: Layer already exists
55eb172d93ab: Layer already exists
c8ae99256e9c: Layer already exists
6b2fdc7164d9: Layer already exists
4aca6a960a6c: Layer already exists
7b42a1e79f8b: Layer already exists
d0749c8b4e23: Layer already exists
9661772b6bf6: Layer already exists
c66c050e39d8: Layer already exists
37127a0fa4c7: Layer already exists
latest: digest: sha256:c795ea48a004f19b8a2c12c33c895522b0fe0dfd477941b8f2ec47b600c16f9e size: 2408
```

Pull and run from Docker Hub:

```text
lab02: Pulling from luminitetime/devops-info-service-python
Digest: sha256:c795ea48a004f19b8a2c12c33c895522b0fe0dfd477941b8f2ec47b600c16f9e
Status: Downloaded newer image for luminitetime/devops-info-service-python:lab02
docker.io/luminitetime/devops-info-service-python:lab02
{
  "status": "healthy",
  "timestamp": "2026-01-31T11:11:05.686163+00:00",
  "uptime_seconds": 0
}
```

## 4. Technical Analysis

- Why the Dockerfile works:
  - Dependencies are installed into the image, then the FastAPI app is started with `python app.py` (uvicorn binds to `0.0.0.0:8080` by default).
- What if layer order changes:
  - Copying the whole project before installing dependencies would invalidate the dependency layer on every code change, slowing rebuilds.
- Security considerations implemented:
  - The container runs as a non-root user and does not require elevated privileges.
- How `.dockerignore` improves the build:
  - It reduces the amount of data sent to the Docker daemon and prevents dev-only files from being added to layers.

## 5. Challenges & Solutions

```text
- Issue: `docker push` initially failed with "denied: requested access to the resource is denied".
  - Cause: the image was tagged with a different Docker Hub namespace than the account actually logged in on this machine.
  - Fix: confirmed the Docker Hub username via `docker login` output (Username: luminitetime), re-tagged the image as `luminitetime/devops-info-service-python:<tag>`, and re-ran `docker push`.
```
