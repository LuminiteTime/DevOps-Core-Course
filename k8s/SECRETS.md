# LAB11 - Kubernetes Secrets & HashiCorp Vault

## 1. Kubernetes Secrets Fundamentals

### Secret creation (imperative kubectl)

```text
$ kubectl create secret generic app-credentials \
  --from-literal=username=student \
  --from-literal=password='S3cr3t!2026'
secret/app-credentials created

$ kubectl get secret app-credentials -o yaml
apiVersion: v1
data:
  password: UzNjcjN0ITIwMjY=
  username: c3R1ZGVudA==
kind: Secret
metadata:
  name: app-credentials
  namespace: default
type: Opaque
```

### Base64 decode demonstration

```text
$ kubectl get secret app-credentials -o jsonpath='{.data.username}' | base64 -d
student

$ kubectl get secret app-credentials -o jsonpath='{.data.password}' | base64 -d
S3cr3t!2026
```

### Encoding vs encryption

- Base64 is only encoding. It is reversible and does not protect confidentiality.
- Encryption means data is transformed with a cryptographic key and cannot be read without decryption.
- Kubernetes Secret objects are base64-encoded in manifests/API payloads, but that alone is not secure storage.

### Are Kubernetes Secrets encrypted at rest by default?

By default, no. In this minikube cluster, kube-apiserver has no `--encryption-provider-config` flag configured.

```text
$ kubectl -n kube-system get pod kube-apiserver-minikube -o yaml | rg -n -- '--encryption-provider-config|encryption-provider-config'
# no output
```

This means secret data in etcd is not using API-server-managed encryption at rest unless configured explicitly.

### What is etcd encryption and when to enable it?

- etcd encryption at rest is configured on kube-apiserver with `EncryptionConfiguration`.
- It encrypts sensitive API resources (for example `secrets`) before writing to etcd.
- It should be enabled in production clusters, especially for compliance and incident blast-radius reduction.

## 2. Helm-Managed Secrets

### Chart structure

I extended `k8s/devops-info` with secret and service account templates:

```text
$ find k8s/devops-info -maxdepth 2 -type f | sort
k8s/devops-info/Chart.lock
k8s/devops-info/Chart.yaml
k8s/devops-info/charts/common-lib-0.1.0.tgz
k8s/devops-info/templates/NOTES.txt
k8s/devops-info/templates/_helpers.tpl
k8s/devops-info/templates/deployment.yaml
k8s/devops-info/templates/secrets.yaml
k8s/devops-info/templates/service.yaml
k8s/devops-info/templates/serviceaccount.yaml
k8s/devops-info/values-dev.yaml
k8s/devops-info/values-prod.yaml
k8s/devops-info/values.yaml
```

### Secret template and values

- `templates/secrets.yaml` creates `Opaque` Secret using `stringData`.
- `values.yaml` now contains `secret.data.username` and `secret.data.password` placeholders.
- Secret name is templated via helper `devops-info.secretName`.

### Secret consumption in Deployment

Deployment consumes all Secret keys via `envFrom.secretRef`:

```yaml
envFrom:
  - secretRef:
      name: {{ include "devops-info.secretName" . }}
```

### Named template for env vars (bonus DRY)

`_helpers.tpl`:

```yaml
{{- define "devops-info.envVars" -}}
- name: APP_NAME
  value: {{ .Values.env.APP_NAME | quote }}
- name: APP_DESCRIPTION
  value: {{ .Values.env.APP_DESCRIPTION | quote }}
- name: APP_VERSION
  value: {{ .Values.env.APP_VERSION | quote }}
- name: APP_VARIANT
  value: {{ .Values.env.APP_VARIANT | quote }}
{{- end }}
```

`deployment.yaml`:

```yaml
env:
  {{- include "devops-info.envVars" . | nindent 12 }}
```

### Deployment and verification

```text
$ helm dependency update k8s/devops-info
Saving 1 charts
Deleting outdated charts

$ helm lint k8s/devops-info
1 chart(s) linted, 0 chart(s) failed

$ helm upgrade --install lab11-devops k8s/devops-info --wait --timeout 4m --reset-values
Release "lab11-devops" has been upgraded. Happy Helming!
REVISION: 4
STATUS: deployed
```

```text
$ kubectl get pods -l app.kubernetes.io/instance=lab11-devops -o wide
NAME                                        READY   STATUS    RESTARTS   AGE
lab11-devops-devops-info-769cbb9d9d-fnpsr   2/2     Running   0          54s
lab11-devops-devops-info-769cbb9d9d-gqfqd   2/2     Running   0          41s
lab11-devops-devops-info-769cbb9d9d-r54sx   2/2     Running   0          28s
```

Secrets are available in pod env (sanitized):

```text
$ kubectl exec <pod> -c devops-info -- sh -lc 'env | grep -E "^(username|password)=" | sed -E "s/=.+$/=<redacted>/"'
username=<redacted>
password=<redacted>
```

Secret values are not exposed in pod description output:

```text
$ kubectl describe pod <pod> | rg -n "helm-pass-123|vault-pass-2026|S3cr3t!2026|helm-user|vault-user"
# no output
```

### Resource limits and requests

Configured in `values.yaml`:

```yaml
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 300m
    memory: 256Mi
```

- `requests` reserve guaranteed minimum resources for scheduling.
- `limits` cap maximum container usage to prevent noisy-neighbor behavior.
- Current values are suitable for low-traffic lab workload and can be increased based on real metrics.

## 3. HashiCorp Vault Integration

### Vault install via Helm

```text
$ helm repo add hashicorp https://helm.releases.hashicorp.com
$ helm repo update

$ helm upgrade --install vault hashicorp/vault \
  -n vault --create-namespace \
  --set server.dev.enabled=true \
  --set injector.enabled=true \
  --server-side=true --force-conflicts
Release "vault" has been upgraded. Happy Helming!
NAME: vault
NAMESPACE: vault
STATUS: deployed
REVISION: 4
```

```text
$ kubectl get pods -n vault -o wide
NAME                                   READY   STATUS    RESTARTS   AGE
vault-0                                1/1     Running   0          19h
vault-agent-injector-6b4f84b6c-gg6b5   1/1     Running   0          19h
```

### Vault configuration (KV + auth + policy + role)

Executed inside `vault-0` (dev mode token `root`):

- wrote KV secret to `secret/devops-info/config`
- enabled/configured Kubernetes auth method
- created policy `devops-info-policy`
- created role `devops-info-role` bound to service account `lab11-devops-devops-info` in namespace `default`

Verification output:

```text
$ vault auth list
Path           Type          Accessor                    Description
kubernetes/    kubernetes    auth_kubernetes_5f1b0715    n/a
token/         token         auth_token_6a6ad9c4         token based credentials

$ vault policy read devops-info-policy
path "secret/data/devops-info/config" {
  capabilities = ["read"]
}
path "secret/metadata/devops-info/config" {
  capabilities = ["read"]
}

$ vault read auth/kubernetes/role/devops-info-role
bound_service_account_names      [lab11-devops-devops-info]
bound_service_account_namespaces [default]
policies                         [devops-info-policy]
token_ttl                        24h
```

Service account exists in Kubernetes:

```text
$ kubectl get sa lab11-devops-devops-info -o yaml
kind: ServiceAccount
metadata:
  name: lab11-devops-devops-info
  namespace: default
```

### Vault Agent injection proof

Injected file exists in application pod:

```text
$ kubectl exec <pod> -c devops-info -- ls -la /vault/secrets
total 4
drwxrwxrwt 2 root root 60 Apr  5 15:01 .
drwxr-xr-x 1 root root 14 Apr  5 15:01 ..
-r--r--r-- 1 app  1000 77 Apr  5 15:01 config.env
```

Rendered secret file (sanitized):

```text
$ kubectl exec <pod> -c devops-info -- sh -lc 'sed -E "s/=.+$/=<redacted>/" /vault/secrets/config.env'
APP_USERNAME=<redacted>
APP_PASSWORD=<redacted>
APP_TOKEN=<redacted>
```

### Sidecar injection pattern explanation

- Vault Agent Injector mutates the pod at admission time based on annotations.
- It adds agent/init behavior and shared volume for rendered files (`/vault/secrets/*`).
- Application container reads secrets as files, not hardcoded env vars in manifests.

## 4. Bonus Task - Vault Agent Templates

### Template annotation implementation

`deployment.yaml` generates annotations dynamically:

```yaml
vault.hashicorp.com/agent-inject-secret-{{ .Values.vault.injectFile }}: {{ .Values.vault.secretPath | quote }}
vault.hashicorp.com/agent-inject-template-{{ .Values.vault.injectFile }}: |
{{ .Values.vault.template | nindent 10 }}
vault.hashicorp.com/agent-inject-command-{{ .Values.vault.injectFile }}: {{ .Values.vault.command | quote }}
```

This renders multiple secret keys into one `.env` file (`config.env`).

### Dynamic refresh / rotation behavior

According to Vault Agent template behavior:

- Renewable secrets: renewed around 2/3 of lease duration.
- Non-renewable non-leased secrets (for example KV v2): re-fetched every 5 minutes by default.
- Interval is configurable with `template_config.static_secret_render_interval`.
- Non-renewable leased secrets are refreshed near lease end (default threshold 90%).

### `agent-inject-command` usage

- `vault.hashicorp.com/agent-inject-command-*` runs after rendering the template file.
- In this lab I use it to enforce read-only mode:
  `chmod 0444 /vault/secrets/config.env`.

## 5. Security Analysis

### Kubernetes Secrets vs Vault

| Aspect | Kubernetes Secret | Vault |
|--------|-------------------|-------|
| Storage | etcd (base64 object data) | dedicated secret manager |
| Encryption at rest | optional, cluster-admin configured | built-in encryption and secret engines |
| Access model | Kubernetes RBAC | fine-grained Vault policies + auth methods |
| Rotation | mostly manual/app-level | native lease/renewal/rotation workflows |
| Audit | Kubernetes audit logs | dedicated audit devices and secret lifecycle visibility |

### When to use each

- Use Kubernetes Secrets for simple low-risk in-cluster configs and bootstrap credentials.
- Use Vault for production-grade secret governance, dynamic credentials, rotation, and auditability.

### Production recommendations

1. Enable etcd encryption at rest (`EncryptionConfiguration`) for `secrets`.
2. Apply strict RBAC and namespace isolation for secret access.
3. Never commit real credentials to Git; keep placeholders in `values.yaml`.
4. Prefer external secret manager integration (Vault or cloud SM) for sensitive workloads.
5. Add secret rotation runbooks and alerting for injection/auth failures.
