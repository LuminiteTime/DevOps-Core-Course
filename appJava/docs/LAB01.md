# LAB01 – DevOps Info Service (Java / Spring Boot)

## 1. Overview

This Java service implements the same DevOps info API as the Python app, using a Spring Boot application generated from an OpenAPI spec. It exposes `GET /` and `GET /health` and uses the same JSON structure.

## 2. Architecture

- OpenAPI-first: `src/main/resources/openapi.yaml` defines both endpoints and all models (`RootResponse`, `ServiceInfo`, etc.).
- Generated layer: Gradle + `org.openapi.generator` generates controllers, delegates, and models into `build/generated`.
- Operation layer: `luminais.tech.appjava.operation.DevopsSystemInfoApiDelegateImpl` implements the generated delegate and just forwards to the service.
- Service layer: `luminais.tech.appjava.service.DevopsInfoService` builds all response objects and encapsulates uptime, system, and request logic.

## 3. Configuration & Environment

- Application YAML: `src/main/resources/application.yml`
  - `server.port` = `${PORT:8081}`
  - `server.address` = `${HOST:0.0.0.0}`
  - `devops.service.*` and `devops.endpoints[]` configure `ServiceInfo` and the endpoints list.
- ENV variables:
  - `PORT` – override HTTP port (e.g. `PORT=9090`)
  - `HOST` – bind address (e.g. `HOST=127.0.0.1`)
  - `DEBUG` – when `true`, sets `logging.level.root=DEBUG` before Spring starts.

## 4. Build & Run

```bash
cd appJava
./gradlew clean build
./gradlew bootRun
# or
java -jar build/libs/appJava-0.0.1-SNAPSHOT.jar
```

Test endpoints (default port 8081):

```bash
curl http://localhost:8081/ | jq
curl http://localhost:8081/health | jq
```

## 5. Mapping to Lab Requirements

- Endpoints: `/` and `/health` return the same JSON structure as the Python version.
- Structure:
  - Root response: `service`, `system`, `runtime`, `request`, `endpoints`.
  - Health response: `status`, `timestamp`, `uptime_seconds`.
- Best practices:
  - OpenAPI-driven models (no manual Java DTOs).
  - Clear service/operation separation with constructor injection.
  - Config-driven constants via `DevopsProperties`.
  - Env-based host, port, and logging level.

## 6. Testing Evidence

Commands used during manual verification:

```bash
cd appJava
./gradlew bootRun

curl http://localhost:8081/ | jq '.service, .system, .runtime, .request, .endpoints'
curl http://localhost:8081/health | jq
```

Screenshots (to be stored under `appJava/docs/screenshots/`):
- Java service running and responding to `/`.
- Java service responding to `/health`.
