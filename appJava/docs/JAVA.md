# JAVA – Language Justification

## 1. Why Java / Spring Boot

- Strong ecosystem: Spring Boot is a de-facto standard for microservices in many companies.
- Tooling: great support for OpenAPI generation, testing, and observability libraries.
- Consistency: easy to align with enterprise stacks that already use Java.

## 2. Fit for the DevOps Info Service

- HTTP API: Spring Boot + WebMVC make it trivial to expose JSON endpoints.
- Spec-first: the OpenAPI generator integrates cleanly into Gradle, keeping the contract as the single source of truth.
- Configuration: Spring’s configuration properties system maps to the env variable and config requirements.

## 3. Comparison with Alternatives

- Go: produces smaller static binaries and very fast startup, but tooling and ecosystem for spec-first APIs and enterprise integrations is less standardized.
- Rust: excellent safety and performance, but slower to develop and overkill for a simple JSON info service.
- Java/Spring Boot: slightly heavier runtime, but very productive, well-known, and easy to integrate with existing DevOps tooling.

## 4. Build & Runtime Notes

- Build command: `./gradlew clean build`.
- Typical jar size: tens of MBs vs a few MBs for Go, but fine for this lab and realistic for enterprise Java services.
- The same JSON contract as in the Python service is documented in the OpenAPI spec.
