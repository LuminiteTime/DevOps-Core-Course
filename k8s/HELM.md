# LAB10 - Helm Package Manager

## 1. Helm Setup

Helm 4.x is the current major release (November 2025). It is fully backwards-compatible with Helm 3 charts (apiVersion v2), supports OCI registries natively, and no longer needs Tiller.

```text
$ helm version
version.BuildInfo{Version:"v4.1.0", GitCommit:"4553a0a96e5205595079b6757236cc6f969ed1b9", GitTreeState:"clean", GoVersion:"go1.25.6", KubeClientVersion:"v1.35"}
```

### Why Helm

Helm solves the problem of managing raw Kubernetes manifests at scale. It gives me:

- **Templating** — reuse the same manifest for dev, staging, and production by swapping a values file.
- **Versioning** — every `helm install` / `upgrade` creates a numbered revision I can roll back to.
- **Dependency management** — library charts let me share helper templates across applications.
- **Lifecycle hooks** — run one-off jobs before or after install / upgrade / delete.

### Repository exploration

```text
$ helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
"prometheus-community" has been added to your repositories

$ helm search repo prometheus-community/prometheus --versions | head -5
NAME                                 CHART VERSION  APP VERSION  DESCRIPTION
prometheus-community/prometheus      28.14.1        v3.10.0      Prometheus is a monitoring system and time seri...
prometheus-community/prometheus      28.14.0        v3.10.0      Prometheus is a monitoring system and time seri...
prometheus-community/prometheus      28.13.0        v3.10.0      Prometheus is a monitoring system and time seri...
prometheus-community/prometheus      28.12.0        v3.10.0      Prometheus is a monitoring system and time seri...

$ helm show chart prometheus-community/prometheus | head -15
annotations:
  artifacthub.io/license: Apache-2.0
apiVersion: v2
appVersion: v3.10.0
dependencies:
- condition: alertmanager.enabled
  name: alertmanager
  repository: https://prometheus-community.github.io/helm-charts
  version: 1.34.*
...
description: Prometheus is a monitoring system and time series database.
home: https://prometheus.io/
```

The Prometheus chart is a good example of a production chart: it declares sub-chart dependencies, pins versions with wildcards, and ships sensible defaults through a large `values.yaml`.

## 2. Chart Structure

I created three charts under `k8s/`:

```
k8s/
├── common-lib/                  # library chart (type: library)
│   ├── Chart.yaml
│   └── templates/
│       ├── _labels.tpl          # common.labels, common.selectorLabels
│       └── _names.tpl           # common.name, common.fullname, common.chart
│
├── devops-info/                 # primary application chart
│   ├── Chart.yaml               # depends on common-lib
│   ├── values.yaml              # default values (3 replicas, NodePort)
│   ├── values-dev.yaml          # dev overrides (1 replica, relaxed resources)
│   ├── values-prod.yaml         # prod overrides (5 replicas, LoadBalancer)
│   └── templates/
│       ├── _helpers.tpl         # chart-specific helpers delegating to common.*
│       ├── deployment.yaml
│       ├── service.yaml
│       ├── NOTES.txt
│       └── hooks/
│           ├── pre-install-job.yaml
│           └── post-install-job.yaml
│
└── devops-info-bonus/           # second application chart (bonus)
    ├── Chart.yaml               # depends on common-lib
    ├── values.yaml
    └── templates/
        ├── _helpers.tpl
        ├── deployment.yaml
        ├── service.yaml
        └── NOTES.txt
```

### Key template files

| File | Purpose |
|------|---------|
| `_helpers.tpl` | Chart-specific name/label helpers that delegate to `common.*` templates from the library |
| `deployment.yaml` | Templatized Deployment with configurable replicas, image, resources, probes, env vars |
| `service.yaml` | Templatized Service with configurable type, ports, nodePort |
| `hooks/pre-install-job.yaml` | Pre-install Job that validates cluster DNS before deployment |
| `hooks/post-install-job.yaml` | Post-install Job that runs a smoke test against the service |

### Values organization

Values follow a nested structure grouped by concern:

- `image.*` — repository, tag, pullPolicy
- `service.*` — type, port, targetPort, nodePort
- `resources.*` — CPU/memory requests and limits
- `livenessProbe.*` / `readinessProbe.*` — full probe configuration (never commented out)
- `env.*` — application environment variables
- `securityContext.*` / `containerSecurityContext.*` — pod and container security

Everything from the original Lab 9 manifests is configurable through values. Health probes have sensible defaults and are always enabled.

## 3. Configuration Guide

### Important values

| Value | Default | Description |
|-------|---------|-------------|
| `replicaCount` | 3 | Number of pod replicas |
| `image.repository` | `luminitetime/devops-info-service-python` | Container image |
| `image.tag` | `lab09` | Image tag |
| `service.type` | `NodePort` | Kubernetes service type |
| `service.port` | 80 | Service port |
| `service.targetPort` | 8080 | Container port |
| `resources.limits.cpu` | 300m | CPU limit |
| `resources.limits.memory` | 256Mi | Memory limit |
| `livenessProbe.initialDelaySeconds` | 15 | Liveness probe initial delay |
| `readinessProbe.initialDelaySeconds` | 5 | Readiness probe initial delay |

### Environment overrides

**Dev** (`values-dev.yaml`): 1 replica, 100m/128Mi limits, NodePort, relaxed probe timings, `latest`-style tagging.

**Prod** (`values-prod.yaml`): 5 replicas, 500m/512Mi limits, LoadBalancer, tighter probe timings, pinned image tag.

### Example installations

```bash
# Development
helm install devops-info-dev k8s/devops-info -f k8s/devops-info/values-dev.yaml

# Production
helm install devops-info-prod k8s/devops-info -f k8s/devops-info/values-prod.yaml

# Override a single value on the fly
helm install devops-info k8s/devops-info --set replicaCount=10
```

## 4. Hook Implementation

### Pre-install hook

The pre-install hook runs a lightweight validation Job **before** any application resources are created. It checks cluster DNS resolution to confirm the cluster is healthy.

```yaml
annotations:
  "helm.sh/hook": pre-install
  "helm.sh/hook-weight": "-5"
  "helm.sh/hook-delete-policy": hook-succeeded
```

### Post-install hook

The post-install hook runs **after** all application resources are installed. It performs a basic smoke test by calling the `/health` endpoint of the deployed service.

```yaml
annotations:
  "helm.sh/hook": post-install
  "helm.sh/hook-weight": "5"
  "helm.sh/hook-delete-policy": hook-succeeded
```

### Execution order

1. Pre-install Job (weight −5) runs first
2. Kubernetes resources (Deployment, Service) are created
3. Post-install Job (weight +5) runs last

### Deletion policy

Both hooks use `hook-succeeded`: Helm deletes the Job automatically once it completes successfully. This keeps the namespace clean. After a successful install, `kubectl get jobs` returns no resources — proof that the policy works.

```text
$ kubectl get jobs
No resources found in default namespace.
```

## 5. Installation Evidence

### helm list

```text
$ helm list
NAME              NAMESPACE  REVISION  UPDATED                              STATUS    CHART                    APP VERSION
devops-info-bonus default    1         2026-03-28 15:06:32.356877 +0300 MSK deployed  devops-info-bonus-0.1.0  2.0.0
devops-info-dev   default    3         2026-03-28 15:05:52.546575 +0300 MSK deployed  devops-info-0.1.0        1.0.0
```

### kubectl get all

```text
$ kubectl get all
NAME                                     READY   STATUS    RESTARTS   AGE
pod/devops-info-bonus-5b8448c5f8-pwq25   1/1     Running   0          35s
pod/devops-info-bonus-5b8448c5f8-tjsnm   1/1     Running   0          35s
pod/devops-info-dev-7f957dbc89-j899r     1/1     Running   0          56s

NAME                        TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
service/devops-info-bonus   NodePort    10.97.64.245    <none>        80:30081/TCP   35s
service/devops-info-dev     NodePort    10.108.35.195   <none>        80:30080/TCP   4m27s
service/kubernetes          ClusterIP   10.96.0.1       <none>        443/TCP        7m45s

NAME                                READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/devops-info-bonus   2/2     2            2           35s
deployment.apps/devops-info-dev     1/1     1            1           4m27s
```

### Hook execution

Hooks ran successfully and were cleaned up by the `hook-succeeded` deletion policy:

```text
$ kubectl get jobs
No resources found in default namespace.
```

### Dev vs Prod deployment

**Dev install** (1 replica, NodePort):

```text
$ helm install devops-info-dev k8s/devops-info -f k8s/devops-info/values-dev.yaml
NAME: devops-info-dev
STATUS: deployed
REVISION: 1

$ kubectl get pods -l app.kubernetes.io/instance=devops-info-dev
NAME                               READY   STATUS    RESTARTS   AGE
devops-info-dev-7f957dbc89-xjgl5   1/1     Running   0          47s
```

**Upgrade to prod** (5 replicas, LoadBalancer):

```text
$ helm upgrade devops-info-dev k8s/devops-info -f k8s/devops-info/values-prod.yaml
Release "devops-info-dev" has been upgraded. Happy Helming!
REVISION: 2

$ kubectl get pods -l app.kubernetes.io/instance=devops-info-dev
NAME                               READY   STATUS    RESTARTS   AGE
devops-info-dev-7f8457cdf9-g7xb5   1/1     Running   0          66s
devops-info-dev-7f8457cdf9-mfgl6   1/1     Running   0          19s
devops-info-dev-7f8457cdf9-t57jh   1/1     Running   0          50s
devops-info-dev-7f8457cdf9-v497r   1/1     Running   0          95s
devops-info-dev-7f8457cdf9-vkpl6   1/1     Running   0          34s

$ kubectl get svc devops-info-dev
NAME              TYPE           CLUSTER-IP      EXTERNAL-IP   PORT(S)        AGE
devops-info-dev   LoadBalancer   10.108.35.195   <pending>     80:30080/TCP   3m26s
```

### Application health check

```text
$ curl http://localhost:8080/health
{"status":"healthy","timestamp":"2026-03-28T12:04:02.297209+00:00","uptime_seconds":78}
```

## 6. Operations

### Install

```bash
helm dependency update k8s/devops-info
helm install devops-info-dev k8s/devops-info -f k8s/devops-info/values-dev.yaml
```

### Upgrade

```bash
helm upgrade devops-info-dev k8s/devops-info -f k8s/devops-info/values-prod.yaml
```

### Rollback

```bash
helm rollback devops-info-dev 1
```

Evidence of rollback:

```text
$ helm history devops-info-dev
REVISION  UPDATED                   STATUS      CHART              APP VERSION  DESCRIPTION
1         Sat Mar 28 15:02:14 2026  superseded  devops-info-0.1.0  1.0.0        Install complete
2         Sat Mar 28 15:04:11 2026  superseded  devops-info-0.1.0  1.0.0        Upgrade complete
3         Sat Mar 28 15:05:52 2026  deployed    devops-info-0.1.0  1.0.0        Rollback to 1
```

After rollback the deployment went back to 1 replica and NodePort — the original dev configuration.

### Uninstall

```bash
helm uninstall devops-info-dev
helm uninstall devops-info-bonus
```

## 7. Testing and Validation

### helm lint

```text
$ helm lint k8s/devops-info
==> Linting k8s/devops-info
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed

$ helm lint k8s/devops-info-bonus
==> Linting k8s/devops-info-bonus
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

### helm template

```text
$ helm template devops-info k8s/devops-info | head -35
---
# Source: devops-info/templates/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: devops-info
  labels:
    helm.sh/chart: devops-info-0.1.0
    app.kubernetes.io/name: devops-info
    app.kubernetes.io/instance: devops-info
    app.kubernetes.io/version: "1.0.0"
    app.kubernetes.io/managed-by: Helm
spec:
  type: NodePort
  selector:
    app.kubernetes.io/name: devops-info
    app.kubernetes.io/instance: devops-info
  ports:
    - name: http
      protocol: TCP
      port: 80
      targetPort: http
      nodePort: 30080
---
# Source: devops-info/templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: devops-info
  labels:
    helm.sh/chart: devops-info-0.1.0
    app.kubernetes.io/name: devops-info
    app.kubernetes.io/instance: devops-info
    ...
```

### Dry-run

```text
$ helm install --dry-run --debug test-release k8s/devops-info 2>&1 | head -20
NAME: test-release
LAST DEPLOYED: Sat Mar 28 15:02:09 2026
NAMESPACE: default
STATUS: pending-install
REVISION: 1
DESCRIPTION: Dry run complete
...
COMPUTED VALUES:
  replicaCount: 3
  image:
    repository: luminitetime/devops-info-service-python
    tag: lab09
  ...
```

### Application accessibility

Both services respond to health checks:

```text
$ curl localhost:8080/health   # devops-info-dev
{"status":"healthy","timestamp":"2026-03-28T12:04:02.297209+00:00","uptime_seconds":78}

$ curl localhost:8081/health   # devops-info-bonus
{"status":"healthy","timestamp":"2026-03-28T12:07:16.151329+00:00","uptime_seconds":41}
```

## 8. Bonus — Library Chart

### Problem

Both `devops-info` and `devops-info-bonus` need identical helper templates: name truncation, fullname generation, common labels, selector labels. Duplicating this logic violates DRY and creates maintenance risk.

### Solution

I created `k8s/common-lib/` as a **library chart** (`type: library` in Chart.yaml). It contains only `_*.tpl` files and cannot be installed directly.

```yaml
# common-lib/Chart.yaml
apiVersion: v2
name: common-lib
description: Shared Helm templates for all DevOps Info applications
type: library
version: 0.1.0
```

### Shared templates

| Template | Purpose |
|----------|---------|
| `common.name` | Chart name, truncated to 63 chars |
| `common.fullname` | Release-qualified name |
| `common.chart` | Chart name + version for `helm.sh/chart` label |
| `common.labels` | Standard Kubernetes labels (chart, name, instance, version, managed-by) |
| `common.selectorLabels` | Minimal labels for Deployment selector and Service selector |

### How both apps use it

Each application chart declares the library as a file-based dependency:

```yaml
# devops-info/Chart.yaml (same pattern in devops-info-bonus)
dependencies:
  - name: common-lib
    version: 0.1.0
    repository: "file://../common-lib"
```

Then the app-specific `_helpers.tpl` delegates to library templates:

```yaml
{{- define "devops-info.labels" -}}
{{ include "common.labels" . }}
{{- end }}
```

### Benefits

- **DRY** — label logic defined once, used everywhere.
- **Consistency** — both apps get identical label structure automatically.
- **Maintainability** — changing a label format means editing one file in `common-lib/`.
- **Scalability** — adding a third application means adding the dependency and delegating, no copy-paste.

### Deployment evidence

```text
$ helm list
NAME              NAMESPACE  REVISION  UPDATED                              STATUS    CHART                    APP VERSION
devops-info-bonus default    1         2026-03-28 15:06:32.356877 +0300 MSK deployed  devops-info-bonus-0.1.0  2.0.0
devops-info-dev   default    3         2026-03-28 15:05:52.546575 +0300 MSK deployed  devops-info-0.1.0        1.0.0

$ kubectl get deployments
NAME                READY   UP-TO-DATE   AVAILABLE   AGE
devops-info-bonus   2/2     2            2           35s
devops-info-dev     1/1     1            1           4m27s
```

Both charts installed successfully using the shared library templates.
