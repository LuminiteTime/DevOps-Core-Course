# LAB03 — Continuous Integration (CI/CD)

## 1. Overview

Testing framework: `pytest`

- Why: concise syntax, strong ecosystem, good FastAPI support via `TestClient`, easy coverage integration with `pytest-cov`.

Test coverage:

- `GET /` structure and required fields
- `GET /health` structure and required fields
- Error cases:
  - unknown path returns structured 404
  - method not allowed (405)

CI triggers:

- Runs on `push` / `pull_request` to `master` with path filter `app_python/**` (and workflow file changes).
- Docker push job runs only on non-PR events.

Versioning strategy: Semantic Versioning (SemVer)

- Git tags: `vMAJOR.MINOR.PATCH` (example: `v1.2.3`)
- Docker tags produced in CI:
  - `MAJOR.MINOR.PATCH`, `MAJOR.MINOR`, `MAJOR`
  - `latest` on default branch
  - `sha-<shortsha>` on pushes

Required GitHub Secrets for full CI/CD:

- `DOCKERHUB_TOKEN`: Docker Hub access token for `luminitetime`
- `SNYK_TOKEN`: Snyk API token (enables Snyk scan steps)
- `CODECOV_TOKEN` (optional for public repos): Codecov upload token

## 2. Workflow Evidence

- Workflow file: `.github/workflows/python-ci.yml`
- Actions page: `https://github.com/LuminiteTime/DevOps-Core-Course/actions/workflows/python-ci.yml`

Local tests passing:

```text
All checks passed!
....                                                                     [100%]
================================ tests coverage ================================
______________ coverage: platform darwin, python 3.11.14-final-0 _______________

Name                      Stmts   Miss  Cover
---------------------------------------------
__init__.py                   0      0   100%
app.py                       68      7    90%
tests/__init__.py             0      0   100%
tests/test_endpoints.py      44      0   100%
---------------------------------------------
TOTAL                       112      7    94%
Coverage XML written to file coverage.xml
Required test coverage of 70% reached. Total coverage: 93.75%
4 passed in 0.20s
```

Docker image:

- `https://hub.docker.com/r/luminitetime/devops-info-service-python`
- Verified SemVer tags pushed: `1.0.0`, `1.0`, `1`, `latest`

Docker push evidence (local):

```text
1.0.0: digest: sha256:c795ea48a004f19b8a2c12c33c895522b0fe0dfd477941b8f2ec47b600c16f9e size: 2408
1.0: digest: sha256:c795ea48a004f19b8a2c12c33c895522b0fe0dfd477941b8f2ec47b600c16f9e size: 2408
1: digest: sha256:c795ea48a004f19b8a2c12c33c895522b0fe0dfd477941b8f2ec47b600c16f9e size: 2408
latest: digest: sha256:c795ea48a004f19b8a2c12c33c895522b0fe0dfd477941b8f2ec47b600c16f9e size: 2408
```

Status badge (README):

- `https://github.com/LuminiteTime/DevOps-Core-Course/actions/workflows/python-ci.yml`

## 3. Best Practices Implemented

- Fail-fast matrix: stops quickly on failures.
- Split jobs with dependencies: Docker build/push runs only after tests succeed.
- Path filters: avoids running Python CI when only non-Python parts change.
- Concurrency: cancels outdated runs on the same ref.
- Dependency caching: pip cache via `actions/setup-python` and Gradle cache via `actions/setup-java`.
- Docker layer caching: Buildx cache to GitHub Actions cache (`type=gha`).
- Least privilege: workflow `permissions: contents: read`.
- Snyk: dependency vulnerability scan (high severity threshold).

Caching metrics:

```text
pip install -q -r requirements.txt -r requirements-dev.txt  ... 5.708 total
pip install -q -r requirements.txt -r requirements-dev.txt  ... 5.647 total
```

Snyk results:

```text
Workflow runs `snyk test --file=app_python/requirements.txt --severity-threshold=high`
when `SNYK_TOKEN` is configured as a repository secret.
```

## 4. Key Decisions

- Versioning Strategy:
  - SemVer fits a service with explicit release tags and clear “breaking vs non-breaking” change signaling.
- Docker Tags:
  - `latest` for default branch, SemVer tags for releases, and `sha-*` for traceability on pushes.
- Workflow Triggers:
  - PRs run lint/tests only; pushes to `master` also publish images (when secrets exist).
- Test Coverage:
  - Focused on API contract: structure, required fields, and error handling. Not asserting exact hostname/platform values because they vary by environment.

## 5. Challenges

- Running security scanning in CI requires external credentials (`SNYK_TOKEN`). The workflow is configured to skip Snyk when the secret is not present.

## Multi-App CI + Coverage

Multi-app CI:

- Java workflow: `.github/workflows/java-ci.yml`
- Java tests: `appJava/src/test/java/luminais/tech/appjava/DevopsEndpointsTest.java` (covers `GET /`, `GET /health`, and 404)
- Java linting: Checkstyle (`./gradlew checkstyleMain checkstyleTest`)
- Path filters:
  - Python CI runs only on `app_python/**` changes
  - Java CI runs only on `appJava/**` changes
- Benefit: avoids wasting CI minutes and keeps feedback focused (monorepo-friendly).

Path filter proof plan:

- Commit changing only `app_python/**` → only Python CI should run.
- Commit changing only `appJava/**` → only Java CI should run.
- Commit changing only `labs/**` or `lectures/**` → neither CI should run.

Coverage:

- Coverage is generated by pytest (`coverage.xml`) and uploaded via `codecov/codecov-action@v5`.
- Current local coverage: 93.75% (threshold in CI: 70%).

Java build evidence (local):

```text
> Task :openApiGenerate
Successfully generated code to .../appJava/build/generated
...
> Task :test
BUILD SUCCESSFUL in 8s
```

Java Docker image (bonus):

- `https://hub.docker.com/r/luminitetime/devops-info-service-java`
- Verified SemVer tags pushed: `1.0.0`, `1.0`, `1`, `latest`

Java Docker push evidence (local):

```text
1.0.0: digest: sha256:cadca4df9db5dea4f19829635e7d7330a46b7f52381ac054dd1dbe9c4afd2337 size: 2205
1.0: digest: sha256:cadca4df9db5dea4f19829635e7d7330a46b7f52381ac054dd1dbe9c4afd2337 size: 2205
1: digest: sha256:cadca4df9db5dea4f19829635e7d7330a46b7f52381ac054dd1dbe9c4afd2337 size: 2205
latest: digest: sha256:cadca4df9db5dea4f19829635e7d7330a46b7f52381ac054dd1dbe9c4afd2337 size: 2205
```
