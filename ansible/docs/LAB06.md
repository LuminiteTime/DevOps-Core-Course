[![Ansible Deploy Python](https://github.com/LuminiteTime/DevOps-Core-Course/actions/workflows/ansible-deploy.yml/badge.svg)](https://github.com/LuminiteTime/DevOps-Core-Course/actions/workflows/ansible-deploy.yml)
[![Ansible Deploy Java](https://github.com/LuminiteTime/DevOps-Core-Course/actions/workflows/ansible-deploy-java.yml/badge.svg)](https://github.com/LuminiteTime/DevOps-Core-Course/actions/workflows/ansible-deploy-java.yml)

# LAB06 - Advanced Ansible and CI/CD

## 1. Overview

Technologies: Ansible 2.20, Docker Compose v2, GitHub Actions, Jinja2 templating.

## 2. Blocks and Tags

### Block usage in each role

**common role** - package installation tasks are wrapped in a `block` with a `rescue` that runs `apt-get update --fix-missing` on failure, and an `always` that logs completion to `/tmp/ansible_common_done`. The block carries tag `packages`.

**docker role** - installation tasks (GPG key, repository, packages) are grouped in a block tagged `docker_install` with a rescue that pauses 10 seconds and retries apt update, and an always that ensures the Docker service is enabled. Configuration tasks (user group, python3-docker) are in a separate block tagged `docker_config`.

### Tag strategy

```text
provision.yml tags: common, docker, docker_install, docker_config, packages
deploy.yml     tags: app_deploy, compose, docker_install, docker_config, web_app_wipe
```

### Selective execution

```text
$ ansible-playbook playbooks/provision.yml --tags "docker"
PLAY RECAP
lab04-vm: ok=9  changed=0  (only docker tasks ran, common skipped)

$ ansible-playbook playbooks/provision.yml --list-tags
  TASK TAGS: [common, docker, docker_config, docker_install, packages]
```

### Rescue block evidence

The Java app deployment triggered the rescue block when the health check failed (Spring Boot startup latency):

```text
TASK [web_app : Verify health endpoint]  fatal (connection reset by peer)
TASK [web_app : Log deployment failure]  ok => "Deployment of devops-java failed"
PLAY RECAP: rescued=1
```

## 3. Docker Compose Migration

### Template

File: `roles/web_app/templates/docker-compose.yml.j2`

```yaml
services:
  {{ app_name }}:
    image: {{ docker_image }}:{{ docker_tag }}
    container_name: {{ app_name }}
    ports:
      - "{{ app_port }}:{{ app_internal_port }}"
    restart: {{ app_restart_policy }}
```

### Before/after comparison

Before (Lab 5): individual `docker_container` module calls, manual stop/remove/run sequence.
After (Lab 6): a single `docker compose up -d --pull always` manages the full lifecycle from a templated YAML file. Compose handles container recreation, image pulling, and restart policy declaratively.

### Role dependencies

`roles/web_app/meta/main.yml` declares `docker` as a dependency. Running `deploy.yml` automatically provisions Docker first without requiring `provision.yml` to be run separately.

### Idempotency

Second provision run: `ok=13 changed=1` (only the timestamped log file changes). All Docker and package tasks report `ok`.

## 4. Wipe Logic

### Implementation

Controlled by two gates:
1. Variable `web_app_wipe` (default: `false`) in `roles/web_app/defaults/main.yml`
2. Tag `web_app_wipe` on the `include_tasks` and the wipe block

Both must be active for wipe to execute. The wipe tasks are included at the top of `main.yml` so a clean-reinstall flow (wipe then deploy) works in a single playbook run.

### Test results

**Scenario 1 - normal deployment (wipe should NOT run):**

```text
$ ansible-playbook playbooks/deploy_python.yml
TASK [web_app : Include wipe tasks]        included
TASK [web_app : Stop and remove ...]        skipping (web_app_wipe=false)
TASK [web_app : Create application dir]     changed
TASK [web_app : Verify health endpoint]     ok
```

**Scenario 2 - wipe only:**

```text
$ ansible-playbook playbooks/deploy_python.yml -e "web_app_wipe=true" --tags web_app_wipe
TASK [web_app : Stop and remove containers]   changed
TASK [web_app : Remove docker-compose file]   changed
TASK [web_app : Remove application directory] changed
TASK [web_app : Log wipe completion]          "Application devops-python wiped successfully"
PLAY RECAP: ok=6  changed=3
```

Verified: `docker ps` shows no Python container; `/opt/devops-python` removed; Java app still running.

**Scenario 3 - clean reinstall (wipe then deploy):**

```text
$ ansible-playbook playbooks/deploy_python.yml -e "web_app_wipe=true"
TASK [web_app : Stop and remove ...]       ignoring (dir already absent)
TASK [web_app : Create application dir]    changed
TASK [web_app : Pull and start]            changed
TASK [web_app : Verify health endpoint]    ok => {"status": "healthy"}
PLAY RECAP: ok=20  changed=3  ignored=1
```

**Scenario 4a - tag specified, variable false (blocked by when):**

```text
$ ansible-playbook playbooks/deploy_python.yml --tags web_app_wipe
TASK [web_app : Stop and remove ...]   skipping
TASK [web_app : Remove ...]            skipping
TASK [web_app : Remove ...]            skipping
TASK [web_app : Log wipe ...]          skipping
PLAY RECAP: ok=2  changed=0  skipped=4
```

### Research answers

1. Why use both variable AND tag? Neither alone is sufficient. The variable alone still allows accidental wipe during `ansible-playbook deploy.yml -e "web_app_wipe=true"` without intent to wipe. The tag alone requires the user to explicitly request wipe via `--tags`, but without the variable check a stray tag inclusion could still trigger it. Together they form a double safety mechanism.

2. Difference from `never` tag: the `never` tag makes tasks unconditionally skipped unless explicitly included. The variable+tag approach is more flexible - it allows the clean-reinstall pattern (run without `--tags` filter but with `web_app_wipe=true`) which the `never` tag cannot support.

3. Why must wipe come BEFORE deployment? This enables the clean-reinstall use case: old state is removed first, then fresh deployment follows in the same playbook run.

4. Clean reinstall vs rolling update: clean reinstall is safer when the application state is corrupt or the Docker image/tag changed significantly. Rolling update (just `compose up`) is faster for routine updates where no cleanup is needed.

5. Extending to wipe images/volumes: add `docker image prune -f` and `docker volume rm {{ app_name }}_*` tasks after removing containers.

## 5. CI/CD Integration

### Workflow architecture

Two separate GitHub Actions workflows:
- `ansible-deploy.yml` - deploys the Python app on push to `master` when `ansible/` files change
- `ansible-deploy-java.yml` - deploys the Java app independently

Each workflow has two jobs:
1. `lint` - runs `ansible-lint` on all playbooks
2. `deploy` (needs: lint, push-only) - sets up SSH, writes vault password from secrets, runs `ansible-playbook`, verifies health endpoint, cleans up

### Required GitHub Secrets

- `ANSIBLE_VAULT_PASSWORD` - decrypts `group_vars/all.yml`
- `SSH_PRIVATE_KEY` - ed25519 private key for `yc-user`
- `VM_HOST` - target VM IP

### Path filters

Python workflow triggers on: `ansible/vars/app_python.yml`, `ansible/playbooks/deploy_python.yml`, `ansible/roles/web_app/**`.
Java workflow triggers on: `ansible/vars/app_java.yml`, `ansible/playbooks/deploy_java.yml`, `ansible/roles/web_app/**`.
Both exclude `ansible/docs/**`. A role change triggers both workflows.

### Research answers

1. Security of SSH keys in GitHub Secrets: secrets are encrypted at rest and masked in logs, but any workflow in the repository can access them. Limit write access to the repository, use environment-scoped secrets for production, and consider short-lived credentials.

2. Staging-to-production pipeline: add separate inventory files (`staging.ini`, `production.ini`), use GitHub environments with approval gates, deploy to staging first, run smoke tests, then promote to production.

3. Rollbacks: pin Docker image tags (e.g., `sha-abc123` instead of `latest`), store the previous tag as a variable, and create a rollback playbook that sets the tag to the previous value and re-runs deployment.

4. Self-hosted runner security: the runner has direct network access to the VM (no SSH key in CI), secrets never leave the infrastructure, and the attack surface is smaller than sharing keys with GitHub-hosted runners.

## 6. Testing Results

### Both apps running

```text
$ ssh yc-user@VM "docker ps"
NAMES           IMAGE                                            STATUS              PORTS
devops-java     luminitetime/devops-info-service-java:latest     Up About a minute   0.0.0.0:5001->8081/tcp
devops-python   luminitetime/devops-info-service-python:latest   Up 4 minutes        0.0.0.0:5000->8080/tcp
```

### Health checks (from inside the VM)

```text
$ curl http://localhost:5000/health
{"status":"healthy","timestamp":"2026-02-26T18:15:40.365237+00:00","uptime_seconds":259}

$ curl http://localhost:5001/health
{"status":"healthy","timestamp":"2026-02-26T18:15:40.350962273Z","uptime_seconds":68}
```

### Independent wipe

Wiping only the Python app removed its container and `/opt/devops-python` directory while the Java app continued running unaffected (verified via `docker ps`).

## 7. Challenges and Solutions

- Java app internal port: the Spring Boot image listens on 8081, not 8080 as initially assumed. Discovered via `docker logs`; fixed `app_internal_port` in `vars/app_java.yml`.
- Health check timeout: Java/Spring Boot takes 5-8 seconds to start. Increased `wait_for` timeout to 60 seconds and `delay` to 5. The first deployment still hit the rescue block, which logged the failure gracefully.
- Ansible deprecation warning: `ansible_distribution_release` triggers INJECT_FACTS_AS_VARS deprecation in Ansible 2.20. Switched to `ansible_facts['distribution_release']`.
- group_vars placement: Ansible searches for `group_vars` adjacent to the inventory file, not the project root. Moved to `inventory/group_vars/all.yml`.

## Bonus Part 1 - Multi-App Deployment

### Architecture

The `web_app` role is parameterized and reused for both applications. Each app has its own variable file (`vars/app_python.yml`, `vars/app_java.yml`) that overrides `app_name`, `docker_image`, `app_port`, and `app_internal_port`. Separate playbooks (`deploy_python.yml`, `deploy_java.yml`) include the same role with different vars. A combined `deploy_all.yml` deploys both using `include_role`.

### Port allocation

Python app: host 5000 -> container 8080.
Java app: host 5001 -> container 8081.

### Role reusability

The `web_app` role has no hardcoded values. The Jinja2 template generates a unique `docker-compose.yml` per app in `/opt/{{ app_name }}/`. Wipe logic is also app-specific because `compose_project_dir` differs per app.

## Bonus Part 2 - Multi-App CI/CD

### Workflow strategy

Separate workflows (Approach A) - one per app. Each workflow has its own path filter, deployment playbook reference, and verification port.

### Path filter strategy

Changes to `ansible/roles/web_app/**` trigger both workflows (shared role). Changes to `ansible/vars/app_python.yml` trigger only the Python workflow. Changes to `ansible/vars/app_java.yml` trigger only the Java workflow.

### Files

- `.github/workflows/ansible-deploy.yml` - Python app
- `.github/workflows/ansible-deploy-java.yml` - Java app
