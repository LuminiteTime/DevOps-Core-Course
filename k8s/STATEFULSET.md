# LAB15 - StatefulSets & Persistent Storage

## 1. StatefulSet Overview

StatefulSets are used when pods need stable identity and dedicated storage. This differs from Deployments, which are designed for interchangeable stateless replicas.

Main differences:

| Feature | Deployment | StatefulSet |
|---------|------------|-------------|
| Pod names | random suffixes | stable ordinals (`-0`, `-1`, `-2`) |
| Storage | shared or manually attached PVC | one PVC per pod from `volumeClaimTemplates` |
| Updates | regular rolling update | ordered update with StatefulSet-specific strategies |
| Network identity | generic service access | stable pod DNS through headless service |

Stateful workloads typically include databases, queues, and applications that keep instance-local data.

## 2. Resource Verification

The chart now renders `templates/statefulset.yaml`, keeps `rollout.yaml` for reference, and creates a headless service plus per-pod PVCs.

Deployment result:

```text
$ kubectl get po,sts,svc,pvc -n stateful
NAME                               READY   STATUS    RESTARTS   AGE
pod/lab15-stateful-devops-info-0   1/1     Running   0          17s
pod/lab15-stateful-devops-info-1   1/1     Running   0          10s
pod/lab15-stateful-devops-info-2   0/1     Running   0          4s

NAME                                          READY   AGE
statefulset.apps/lab15-stateful-devops-info   2/3     17s

NAME                                          TYPE        CLUSTER-IP      EXTERNAL-IP   PORT(S)   AGE
service/lab15-stateful-devops-info            ClusterIP   10.110.125.83   <none>        80/TCP    17s
service/lab15-stateful-devops-info-headless   ClusterIP   None            <none>        80/TCP    17s

NAME                                                             STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
persistentvolumeclaim/data-volume-lab15-stateful-devops-info-0   Bound    pvc-2fe4b3ef-9945-4cd5-86cb-a47fc896b031   100Mi      RWO            standard       17s
persistentvolumeclaim/data-volume-lab15-stateful-devops-info-1   Bound    pvc-1dffb45d-9193-4d35-b899-51c7e9d31c94   100Mi      RWO            standard       10s
persistentvolumeclaim/data-volume-lab15-stateful-devops-info-2   Bound    pvc-6c722dd5-dd3b-4e5f-b3c0-f0aa2bf4248c   100Mi      RWO            standard       4s
```

After the startup sequence completed:

```text
$ kubectl rollout status statefulset/lab15-stateful-devops-info -n stateful --timeout=240s
partitioned roll out complete: 3 new pods have been updated...
```

## 3. Network Identity

The headless service provides stable DNS names in the form:

`<pod-name>.<headless-service>.<namespace>.svc.cluster.local`

Resolution test from pod `-0` to pod `-1`:

```text
$ kubectl exec -n stateful lab15-stateful-devops-info-0 -- python -c 'import socket; print(socket.gethostbyname("lab15-stateful-devops-info-1.lab15-stateful-devops-info-headless.stateful.svc.cluster.local"))'
10.244.0.75
```

This confirms that pod-specific DNS is available without using the shared ClusterIP service.

## 4. Per-Pod Storage Evidence

Each pod was accessed directly through its own port-forward and received a different number of requests.

```text
pod0={"visits":1}
pod1={"visits":2}
pod2={"visits":3}
```

The files stored on each pod confirm the same independent values:

```text
$ kubectl exec -n stateful lab15-stateful-devops-info-0 -- cat /data/visits
1

$ kubectl exec -n stateful lab15-stateful-devops-info-1 -- cat /data/visits
2

$ kubectl exec -n stateful lab15-stateful-devops-info-2 -- cat /data/visits
3
```

This shows that every ordinal has its own PVC and does not share the visits counter with other replicas.

## 5. Persistence Test

Pod `lab15-stateful-devops-info-0` was deleted directly, while the StatefulSet kept the same ordinal and reattached the same persistent volume.

```text
before=1
deleted_at=2026-04-16T17:42:17Z
pod "lab15-stateful-devops-info-0" deleted
pod/lab15-stateful-devops-info-0 condition met
after=1
ready_at=2026-04-16T17:42:24Z
```

The value stayed `1`, so the visits file survived pod recreation.

## 6. Bonus - Update Strategies

### Partitioned rolling update

The release was upgraded with `partition: 2`. Only pods with ordinal `>= 2` were updated.

```text
$ helm upgrade lab15-stateful ... -f k8s/devops-info/values-statefulset-partition.yaml
Release "lab15-stateful" has been upgraded. Happy Helming!

$ for pod in 0 1 2; do kubectl exec -n stateful lab15-stateful-devops-info-$pod -- printenv APP_VERSION; done
pod0=1.0.0-stateful
pod1=1.0.0-stateful
pod2=1.1.0-partition
```

This is useful when a higher ordinal should be updated first while lower ordinals remain untouched.

### OnDelete strategy

The next upgrade switched the StatefulSet to `OnDelete`. No pods updated automatically after the Helm upgrade.

```text
before_ondelete
pod0=1.0.0-stateful
pod1=1.0.0-stateful
pod2=1.1.0-partition
```

After deleting only pod `-2`, the recreated pod adopted the new version while pods `-0` and `-1` stayed unchanged.

```text
pod "lab15-stateful-devops-info-2" deleted
pod/lab15-stateful-devops-info-2 condition met
after_ondelete
pod0=1.0.0-stateful
pod1=1.0.0-stateful
pod2=1.2.0-ondelete
```

This strategy is useful when updates must be manually coordinated per pod.
