# LAB02 — Docker Containerization (Java / Spring Boot, Multi-Stage)

## 1. Multi-Stage Build Strategy

This image uses two stages:

- Builder stage: compiles the Spring Boot application into an executable JAR using Gradle.
- Runtime stage: runs only the JRE and the compiled JAR.

Relevant Dockerfile excerpt:

```dockerfile
FROM eclipse-temurin:25-jdk AS builder
WORKDIR /workspace
COPY gradlew build.gradle settings.gradle ./
COPY gradle/ gradle/
COPY src/ src/
RUN ./gradlew --no-daemon clean bootJar

FROM eclipse-temurin:25-jre
WORKDIR /app
COPY --from=builder /workspace/build/libs/appJava-0.0.1-SNAPSHOT.jar /app/app.jar
CMD ["java", "-jar", "/app/app.jar"]
```

## 2. Size Comparison & Analysis

Builder image size vs final image size:

```text
devops-info-service-java-builder:lab02 = 751MB
devops-info-service-java:lab02 = 390MB
```

Why this matters:

- Smaller runtime images reduce the attack surface (fewer tools/libraries available).
- Smaller images pull faster and start faster, improving deploy times.

## 3. Build & Run Evidence

### 3.1 Build output

```text
#0 building with "orbstack" instance using docker driver

#1 [internal] load build definition from Dockerfile
#1 transferring dockerfile: 557B done
#1 DONE 0.0s

#2 [internal] load metadata for docker.io/library/eclipse-temurin:25-jdk
#2 DONE 2.7s

#3 [internal] load metadata for docker.io/library/eclipse-temurin:25-jre
#3 DONE 3.0s

#4 [internal] load .dockerignore
#4 transferring context: 145B done
#4 DONE 0.0s

#5 [builder 1/8] FROM docker.io/library/eclipse-temurin:25-jdk@sha256:42fc3fe6804ec612f5ef8a613f8c06d8dd578de6207336077387d4cb32edaa9b
#5 ...

#6 [internal] load build context
#6 transferring context: 69.00kB 0.0s done
#6 DONE 0.1s

#7 [stage-1 1/5] FROM docker.io/library/eclipse-temurin:25-jre@sha256:9d1d3068b16f2c4127be238ca06439012ff14a8fdf38f8f62472160f9058464a
#7 ...

#8 [stage-1 2/5] WORKDIR /app
#8 DONE 0.3s

#9 [builder 2/8] WORKDIR /workspace
#9 DONE 0.2s

#10 [builder 3/8] COPY gradlew build.gradle settings.gradle ./
#10 DONE 0.0s

#11 [builder 4/8] COPY gradle/ gradle/
#11 DONE 0.0s

#12 [builder 5/8] RUN chmod +x gradlew
#12 DONE 0.1s

#13 [stage-1 3/5] RUN addgroup --system app && adduser --system --ingroup app app
#13 DONE 0.2s

#14 [builder 6/8] RUN ./gradlew --no-daemon --version
#14 DONE 10.4s

#15 [builder 7/8] COPY src/ src/
#15 DONE 0.0s

#16 [builder 8/8] RUN ./gradlew --no-daemon clean bootJar
#16 DONE 52.9s

#23 [stage-1 4/5] COPY --from=builder /workspace/build/libs/appJava-0.0.1-SNAPSHOT.jar /app/app.jar
#23 DONE 0.1s

#24 [stage-1 5/5] RUN chown -R app:app /app
#24 DONE 0.1s

#25 exporting to image
#25 writing image sha256:4391bcb658ad6acae8f3fe5e4d3bcf5c1e48b8e8c22a44b87a83a70380db0294 done
#25 naming to docker.io/library/devops-info-service-java:lab02 done
#25 DONE 0.1s
```

### 3.2 Image sizes output

```text
REPOSITORY                                TAG         IMAGE ID       CREATED             SIZE
devops-info-service-java                  lab02       4391bcb658ad   9 seconds ago       390MB
devops-info-service-java-builder          lab02       9e5402ef437f   9 seconds ago       751MB
```

### 3.3 Container running output

```text
b835816bfad0262f3818428796ffb07d47f36b1a1e1ae9d4e176eb157ba9f9b6
CONTAINER ID   IMAGE                            COMMAND                  CREATED        STATUS        PORTS                                         NAMES
b835816bfad0   devops-info-service-java:lab02   "/__cacert_entrypoin…"   1 second ago   Up 1 second   0.0.0.0:8084->8081/tcp, [::]:8084->8081/tcp   devops-info-java-ps
```

### 3.4 Endpoint tests

```text
GET /health
{
  "status": "healthy",
  "timestamp": "2026-01-31T11:11:06.847230599Z",
  "uptime_seconds": 1
}

GET /
{
  "service": {
    "name": "devops-info-service",
    "version": "1.0.0",
    "description": "DevOps course info service (Java implementation)",
    "framework": "Spring Boot"
  },
  "system": {
    "hostname": "8507a1b302a1",
    "platform": "Linux",
    "platform_version": "6.17.8-orbstack-00308-g8f9c941121b1",
    "architecture": "aarch64",
    "cpu_count": 12,
    "python_version": "25.0.1"
  },
  "runtime": {
    "uptime_seconds": 1,
    "uptime_human": "0 hours, 0 minutes",
    "current_time": "2026-01-31T11:11:06.888902979Z",
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
```

## 4. Technical Notes

- Each stage purpose:
  - Builder: provides JDK + Gradle wrapper to produce the JAR.
  - Runtime: contains only what is needed to execute the JAR.
- Trade-offs:
  - The builder stage can be large and includes build tooling; the final stage does not.

Security notes:

- The final image runs as a non-root user (`uid=100(app)`).
