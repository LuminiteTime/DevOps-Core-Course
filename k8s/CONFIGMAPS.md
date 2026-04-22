# LAB12 - ConfigMaps & Persistent Volumes

## 1. Application Changes

### Visits counter implementation

The application was extended with a file-based visits counter in `app_python/app.py`.

- `GET /` increments the counter on every request.
- `GET /visits` returns the current stored value.
- The counter is stored in the file referenced by `VISITS_FILE_PATH`.
- If the file does not exist, the counter starts from `0`.
- File updates use a process-local lock and atomic replace to avoid corruption during concurrent access in one process.

For local execution the default path is `./data/visits`. In Kubernetes the value is injected through the environment ConfigMap and points to `/data/visits`.

### New endpoint

The new endpoint returns the persisted counter value:

```json
{"visits": 2}
```

### Local Docker testing

`app_python/docker-compose.yml` mounts `./data` from the host to `/data` inside the container. This makes the visits file persistent across container restarts.

Docker Compose status:

```text
$ docker compose ps
NAME                 IMAGE                    COMMAND           SERVICE       CREATED          STATUS          PORTS
devops-info-python   app_python-devops-info   "python app.py"   devops-info   39 seconds ago   Up 11 seconds   0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp
```

Counter value after two requests:

```text
$ curl -sS http://localhost:8080/visits
{"visits":2}

$ cat app_python/data/visits
2
```

Counter value after container restart:

```text
$ docker compose restart
 Container devops-info-python  Restarting
 Container devops-info-python  Started

$ curl -sS http://localhost:8080/visits
{"visits":2}

$ cat app_python/data/visits
2
```

The result confirms that the counter survives container restarts when the volume is mounted.

`app_python/README.md` was updated with the `/visits` endpoint and the Docker Compose persistence example.

## 2. ConfigMap Implementation

### `config.json` file

The Helm chart now contains `k8s/devops-info/files/config.json`. The file stores non-sensitive application configuration:

```json
{
  "application": {
    "name": "devops-info-service",
    "environment": "dev",
    "variant": "dev"
  },
  "features": {
    "visitsCounter": true,
    "metrics": true,
    "hotReloadStrategy": "checksum-rollout"
  },
  "settings": {
    "visitsFile": "/data/visits",
    "logLevel": "DEBUG"
  }
}
```

### ConfigMap template structure

`k8s/devops-info/templates/configmap.yaml` creates two ConfigMaps:

- `lab12-devops-devops-info-config` for file-based configuration
- `lab12-devops-devops-info-env` for key-value environment variables

The file-based ConfigMap loads `files/config.json` through Helm `.Files.Get`.

### ConfigMap mounted as file

The Deployment mounts the file-based ConfigMap at `/config`. The mounted file is available inside the pod:

```text
$ kubectl exec lab12-devops-devops-info-546746bd9f-qd78z -- cat /config/config.json
{
  "application": {
    "name": "devops-info-service",
    "environment": "dev",
    "variant": "dev"
  },
  "features": {
    "visitsCounter": true,
    "metrics": true,
    "hotReloadStrategy": "checksum-rollout"
  },
  "settings": {
    "visitsFile": "/data/visits",
    "logLevel": "DEBUG"
  }
}
```

### ConfigMap as environment variables

The second ConfigMap is injected with `envFrom.configMapRef`. The following variables were present in the running pod:

```text
$ kubectl exec lab12-devops-devops-info-546746bd9f-qd78z -- printenv | grep -E '^(APP_ENV|LOG_LEVEL|FEATURE_VISITS_COUNTER|APP_CONFIG_PATH|VISITS_FILE_PATH)='
LOG_LEVEL=DEBUG
VISITS_FILE_PATH=/data/visits
APP_CONFIG_PATH=/config/config.json
APP_ENV=dev
FEATURE_VISITS_COUNTER=true
```

## 3. Persistent Volume

### PVC configuration

`k8s/devops-info/templates/pvc.yaml` creates a `PersistentVolumeClaim` with:

- access mode `ReadWriteOnce`
- size `100Mi`
- configurable storage class through `values.yaml`

The Deployment mounts this PVC at `/data`, and the application stores the visits file in that directory.

### `kubectl get configmap,pvc`

Required resource output:

```text
$ kubectl get configmap,pvc
NAME                                        DATA   AGE
configmap/kube-root-ca.crt                  1      88s
configmap/lab12-devops-devops-info-config   1      45s
configmap/lab12-devops-devops-info-env      5      45s

NAME                                                  STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   VOLUMEATTRIBUTESCLASS   AGE
persistentvolumeclaim/lab12-devops-devops-info-data   Bound    pvc-d052e170-2b86-4b4e-a7cd-af977a9f1b61   100Mi      RWO            standard       <unset>                 45s
```

### Persistence test

Pod before deletion:

```text
$ kubectl get pods -l app.kubernetes.io/instance=lab12-devops -o wide
NAME                                        READY   STATUS    RESTARTS   AGE   IP           NODE    NOMINATED NODE   READINESS GATES
lab12-devops-devops-info-546746bd9f-qd78z   1/1     Running   0          45s   10.244.0.4   lab12   <none>           <none>
```

Counter before pod deletion:

```text
$ kubectl exec lab12-devops-devops-info-546746bd9f-qd78z -- cat /data/visits
2

$ curl -sS http://127.0.0.1:58064/visits
{"visits":2}
```

Pod deletion command:

```text
$ kubectl delete pod lab12-devops-devops-info-546746bd9f-qd78z
pod "lab12-devops-devops-info-546746bd9f-qd78z" deleted from default namespace

$ kubectl wait --for=condition=ready pod -l app.kubernetes.io/instance=lab12-devops --timeout=180s
pod/lab12-devops-devops-info-546746bd9f-dtbdk condition met
```

Replacement pod:

```text
$ kubectl get pods -l app.kubernetes.io/instance=lab12-devops -o wide
NAME                                        READY   STATUS    RESTARTS   AGE   IP           NODE    NOMINATED NODE   READINESS GATES
lab12-devops-devops-info-546746bd9f-dtbdk   1/1     Running   0          29s   10.244.0.6   lab12   <none>           <none>
```

Counter after the new pod started:

```text
$ kubectl exec lab12-devops-devops-info-546746bd9f-dtbdk -- cat /data/visits
2

$ curl -sS http://127.0.0.1:58064/visits
{"visits":2}
```

The result confirms that the visits file is stored on the PVC and survives pod recreation.

## 4. ConfigMap vs Secret

### When to use ConfigMap

ConfigMap should be used for non-sensitive configuration:

- application mode
- log level
- feature flags
- configuration files
- runtime paths and general settings

### When to use Secret

Secret should be used for sensitive data:

- passwords
- tokens
- private keys
- API credentials
- database credentials

### Key differences

- ConfigMap stores non-sensitive configuration, while Secret stores sensitive data.
- ConfigMap is suitable for plain configuration files and ordinary environment variables.
- Secret is intended for confidential values that must not be exposed as normal configuration.
- In this lab, ConfigMaps are used for `config.json` and runtime variables, while credentials remain the responsibility of Secrets.

## 5. Bonus - ConfigMap Hot Reload

### Default update behavior

The mounted ConfigMap file was updated by patching the live ConfigMap and observing when the new value appeared inside the pod.

Observed result:

```text
$ kubectl patch configmap lab12-devops-devops-info-config ...
configmap/lab12-devops-devops-info-config patched

$ <poll mounted file in the pod>
delay_seconds=42
pod=lab12-devops-devops-info-546746bd9f-dtbdk
{
  "application": {
    "name": "devops-info-service",
    "environment": "hot-reload-second",
    "variant": "dev"
  },
  "features": {
    "visitsCounter": true,
    "metrics": true,
    "hotReloadStrategy": "checksum-rollout"
  },
  "settings": {
    "visitsFile": "/data/visits",
    "logLevel": "DEBUG"
  }
}
```

The mounted file reflected the ConfigMap change after 42 seconds. This delay is consistent with kubelet synchronization and ConfigMap refresh timing.

### `subPath` limitation

`subPath` mounts do not receive live ConfigMap updates because the file is mounted as a separate copy created at container start, not as the automatically refreshed directory-based mount used by a full ConfigMap volume.

`subPath` is appropriate when:

- one file must be placed at an exact path
- live updates are not required

`subPath` should be avoided when:

- automatic ConfigMap refresh is required
- configuration changes must appear inside the container without remounting

For this reason, the ConfigMap in this lab is mounted as a directory at `/config`.

### Chosen reload approach

The implemented reload mechanism uses a checksum annotation in the Deployment template:

```yaml
template:
  metadata:
    annotations:
      checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
```

When Helm renders different ConfigMap content, the checksum changes, the pod template changes, and Kubernetes performs a rollout.

### Helm upgrade pattern

Pod name before upgrade:

```text
$ kubectl get pods -l app.kubernetes.io/instance=lab12-devops -o jsonpath='{.items[0].metadata.name}'
lab12-devops-devops-info-546746bd9f-dtbdk
```

Upgrade command:

```text
$ helm upgrade lab12-devops k8s/devops-info -f k8s/devops-info/values-dev.yaml \
    --set config.environment=checksum-rollout \
    --set envConfig.APP_ENV=reload \
    --set envConfig.LOG_LEVEL=TRACE \
    --wait --timeout 4m --force-conflicts
Release "lab12-devops" has been upgraded. Happy Helming!
REVISION: 3
STATUS: deployed
```

`--force-conflicts` was required because the previous manual ConfigMap patch changed a Helm-managed field during the update-behavior experiment.

Pod name after upgrade:

```text
$ kubectl get pods -l app.kubernetes.io/instance=lab12-devops -o wide
NAME                                        READY   STATUS    RESTARTS   AGE   IP           NODE    NOMINATED NODE   READINESS GATES
lab12-devops-devops-info-7887d86654-ddxt6   1/1     Running   0          38s   10.244.0.7   lab12   <none>           <none>
```

The pod name changed, which confirms that the checksum annotation triggered a rollout.

Updated configuration in the new pod:

```text
$ kubectl exec $(kubectl get pods -l app.kubernetes.io/instance=lab12-devops -o jsonpath='{.items[0].metadata.name}') -- cat /config/config.json
{
  "application": {
    "name": "devops-info-service",
    "environment": "checksum-rollout",
    "variant": "dev"
  },
  "features": {
    "visitsCounter": true,
    "metrics": true,
    "hotReloadStrategy": "checksum-rollout"
  },
  "settings": {
    "visitsFile": "/data/visits",
    "logLevel": "TRACE"
  }
}
```

Updated environment variables:

```text
$ kubectl exec $(kubectl get pods -l app.kubernetes.io/instance=lab12-devops -o jsonpath='{.items[0].metadata.name}') -- printenv | grep -E '^(APP_ENV|LOG_LEVEL)='
APP_ENV=reload
LOG_LEVEL=TRACE
```

The result confirms that the checksum-based Helm pattern restarts the pod and applies the updated configuration.
