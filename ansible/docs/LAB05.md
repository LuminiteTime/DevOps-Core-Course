# LAB05 - Ansible Fundamentals

## 1. Architecture Overview

Ansible version: 2.20.2 (ansible-core), installed via Homebrew.

Target VM: Ubuntu 22.04 LTS on Yandex Cloud (recreated from Lab 4 Terraform code), 2 cores at 20%, 1 GB RAM.

Role structure:

```text
ansible/
  ansible.cfg
  .vault_pass                  (gitignored)
  inventory/
    hosts.ini
    group_vars/
      all.yml                  (encrypted with ansible-vault)
  roles/
    common/
      tasks/main.yml
      defaults/main.yml
    docker/
      tasks/main.yml
      handlers/main.yml
      defaults/main.yml
    app_deploy/
      tasks/main.yml
      handlers/main.yml
      defaults/main.yml
  playbooks/
    site.yml
    provision.yml
    deploy.yml
```

Why roles instead of monolithic playbooks: roles isolate concerns (system setup, Docker, app deployment) into reusable units with standardized directory layouts. Each role can be tested, shared, and maintained independently. Playbooks become thin orchestration layers that compose roles.

## 2. Roles Documentation

### common

- Purpose: updates apt cache, installs essential system packages, sets timezone.
- Variables: `common_packages` (list of apt packages), `common_timezone` (default `UTC`).
- Handlers: none.
- Dependencies: none.

### docker

- Purpose: installs Docker CE from the official Docker repository, enables the service, adds the SSH user to the `docker` group, installs `python3-docker` for Ansible Docker modules.
- Variables: `docker_user` (defaults to `ansible_user`).
- Handlers: `Restart docker` -- triggered after Docker packages are installed.
- Dependencies: none (but typically runs after `common`).

### app_deploy

- Purpose: authenticates to Docker Hub, pulls the application image, runs a container with port mapping and restart policy, waits for the port to open, and verifies the health endpoint.
- Variables (stored in encrypted vault): `dockerhub_username`, `dockerhub_password`, `app_name`, `docker_image`, `docker_image_tag`, `app_port`, `app_container_name`. Role defaults: `app_port: 5000`, `app_restart_policy: unless-stopped`.
- Handlers: `Restart app container` -- restarts the running container.
- Dependencies: `docker` role must have been applied first.

## 3. Idempotency Demonstration

### First run

```text
TASK [common : Update apt cache]                changed
TASK [common : Install common packages]         changed
TASK [common : Set timezone]                    changed
TASK [docker : Install prerequisite packages]   ok
TASK [docker : Create keyrings directory]       ok
TASK [docker : Add Docker GPG key]              changed
TASK [docker : Add Docker repository]           changed
TASK [docker : Install Docker packages]         changed
TASK [docker : Ensure Docker service running]   ok
TASK [docker : Add user to docker group]        changed
TASK [docker : Install python3-docker]          changed
RUNNING HANDLER [docker : Restart docker]       changed

PLAY RECAP
lab04-vm: ok=13  changed=9  unreachable=0  failed=0
```

### Second run

```text
TASK [common : Update apt cache]                ok
TASK [common : Install common packages]         ok
TASK [common : Set timezone]                    ok
TASK [docker : Install prerequisite packages]   ok
TASK [docker : Create keyrings directory]       ok
TASK [docker : Add Docker GPG key]              ok
TASK [docker : Add Docker repository]           ok
TASK [docker : Install Docker packages]         ok
TASK [docker : Ensure Docker service running]   ok
TASK [docker : Add user to docker group]        ok
TASK [docker : Install python3-docker]          ok

PLAY RECAP
lab04-vm: ok=12  changed=0  unreachable=0  failed=0
```

Analysis: On the first run, 9 tasks changed - packages were installed, the Docker GPG key and repository were added, the Docker service was restarted by the handler, and the user was added to the `docker` group. On the second run, every task reported `ok` with zero changes because each module checks the current state before acting (`apt` verifies packages are present, `service` checks running status, `user` checks group membership). The handler did not fire because nothing notified it. This is idempotency: the playbook converges to the desired state and makes no further modifications.

## 4. Ansible Vault Usage

Credentials and app configuration are stored in `inventory/group_vars/all.yml`, encrypted with `ansible-vault`.

Vault password management: a `.vault_pass` file (mode 0600, gitignored) stores the password locally. The path is set in `ansible.cfg` via `vault_password_file`, so no `--ask-vault-pass` flag is needed.

Encrypted file content (first five lines):

```text
$ANSIBLE_VAULT;1.1;AES256
39306161353663386163333465633132653565656336333236643634653862333864656638393436
3663343237663039323566313065323761303565636661650a663662633733393561313732636330
34623830353238656635316463643332613634613531343163386463646662313936666464626163
3938383532363437370a613962383231323263663162393431646234613239346337313766343762
```

Why Ansible Vault is important: without it, Docker Hub tokens or other secrets would appear in plaintext in version-controlled files. Vault encrypts them with AES-256 so the YAML can be committed safely. The `no_log: true` flag on the `docker_login` task prevents credentials from leaking into Ansible output.

## 5. Deployment Verification

### deploy.yml output

```text
TASK [app_deploy : Log in to Docker Hub]          ignored (placeholder token)
TASK [app_deploy : Pull Docker image]             changed
TASK [app_deploy : Run application container]      changed
TASK [app_deploy : Wait for application port]      ok
TASK [app_deploy : Verify health endpoint]         ok
TASK [app_deploy : Show health check result]       ok
  health_check.json: {"status": "healthy", "timestamp": "2026-02-24T08:57:55", "uptime_seconds": 3}
RUNNING HANDLER [app_deploy : Restart app container]  changed

PLAY RECAP
lab04-vm: ok=8  changed=3  unreachable=0  failed=0  ignored=1
```

### docker ps

```text
CONTAINER ID   IMAGE                                            COMMAND           STATUS         PORTS                    NAMES
abd8cebdcc2b   luminitetime/devops-info-service-python:latest   "python app.py"   Up 7 seconds   0.0.0.0:5000->8080/tcp   devops-info-service-python
```

### Health check (curl from local machine)

```text
$ curl http://93.77.176.203:5000/health
{"status":"healthy","timestamp":"2026-02-24T08:58:04.818449+00:00","uptime_seconds":6}

$ curl http://93.77.176.203:5000/
{"service":{"name":"devops-info-service","version":"1.0.0", ...}, "system":{"hostname":"abd8cebdcc2b","platform":"Linux", ...}}
```

## 6. Key Decisions

- Why use roles instead of plain playbooks? Roles enforce a standard directory layout that separates tasks, handlers, defaults, and templates. This makes each concern independently testable and reusable across projects without copy-pasting.
- How do roles improve reusability? The `docker` role can provision Docker on any Ubuntu host without modification. Only the variables change. Teams can share roles via Ansible Galaxy or internal repositories.
- What makes a task idempotent? Using declarative modules (`apt: state=present`, `service: state=started`) that check current state before acting. If the desired state already matches, no change is made. Avoid raw `command`/`shell` tasks that always report changed.
- How do handlers improve efficiency? Handlers run only once at the end of the play, even if notified multiple times. This avoids redundant service restarts; for example, Docker is restarted once after all packages are installed rather than after each package individually.
- Why is Ansible Vault necessary? Infrastructure code belongs in version control, but secrets (API tokens, passwords) must not appear in plaintext. Vault encrypts sensitive files with AES-256 so they can be committed alongside the rest of the code without exposing credentials.

## 7. Challenges

- `group_vars/all.yml` was not loaded because Ansible searches for `group_vars` adjacent to the inventory or playbook directory, not the project root. Fixed by moving it to `inventory/group_vars/all.yml`.
- The `ansible_distribution_release` fact triggered a deprecation warning in Ansible 2.20. Switched to `ansible_facts['distribution_release']`.
- Docker login fails with a placeholder token. Added `ignore_errors: true` since the image is public and can be pulled without authentication. In production the vault would contain a real access token.

