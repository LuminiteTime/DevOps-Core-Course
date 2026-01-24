# DevOps Info Service (Java / Spring Boot)

## Overview

This service exposes a small HTTP API that reports information about the running host, the Java runtime, and the incoming request. It mirrors the Python implementation and is used as a base for later DevOps labs.

The API provides:
- `GET /` – service, system, runtime, and request metadata
- `GET /health` – simple health check with uptime info

## Prerequisites

- Java 25 (JDK)

All Java dependencies are managed via Gradle in [appJava/build.gradle](appJava/build.gradle).

## Installation

You can build the project using the included Gradle wrapper:

```bash
cd appJava
./gradlew clean build
```

This will download the necessary Gradle components (if needed), resolve dependencies, generate code from `openapi.yaml`, compile the application, and run tests.

## Running the Application

Default configuration (HOST=0.0.0.0, PORT=8081, DEBUG=false):

```bash
cd appJava
./gradlew bootRun
```

Running from the executable JAR after a build:

```bash
cd appJava
./gradlew bootJar
java -jar build/libs/appJava-0.0.1-SNAPSHOT.jar
```

Custom configuration with environment variables:

```bash
# Run on localhost:8081
cd appJava
HOST=127.0.0.1 PORT=8081 java -jar build/libs/appJava-0.0.1-SNAPSHOT.jar

# Run on 127.0.0.1:3000 with debug logging
HOST=127.0.0.1 PORT=3000 DEBUG=true java -jar build/libs/appJava-0.0.1-SNAPSHOT.jar
```

After start, you can test the endpoints with curl (default app config used in commands):

```bash
curl http://localhost:8081/
curl http://localhost:8081/health
```

## API Endpoints

- `GET /`
  - Returns JSON with the following top-level sections:
    - `service` – name, version, description, framework (Spring Boot)
    - `system` – hostname, platform, platform_version, architecture, cpu_count, python_version (mapped from Java runtime)
    - `runtime` – uptime_seconds, uptime_human, current_time, timezone
    - `request` – client_ip, user_agent, method, path
    - `endpoints` – list of available paths and their purpose

- `GET /health`
  - Returns a compact health document:
    - `status` – string status ("healthy")
    - `timestamp` – current UTC timestamp in ISO 8601 format
    - `uptime_seconds` – number of seconds the process has been running

## Configuration

The application is configured via environment variables and Spring Boot configuration in [appJava/src/main/resources/application.yml](appJava/src/main/resources/application.yml):

| Variable | Default    | Description                                 |
|----------|------------|---------------------------------------------|
| `HOST`   | `0.0.0.0`  | Address the app binds to                    |
| `PORT`   | `8081`     | TCP port the app listens on                |
| `DEBUG`  | `false`    | When `true`, enables DEBUG logging level   |

All variables are optional. If they are not set, the defaults above are used.
