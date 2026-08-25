# Reference: stack configuration

Each Pulumi stack (environment) has its own `Pulumi.<stack>.yaml`, holding two config objects
under the `app` namespace. `pulumi stack init` alone does **not** create this file — it only
registers the stack with the backend. The file is created lazily, the first time you run
`pulumi config set` against that stack (or the first time `pulumi preview`/`up` writes a default).

## `app:cluster-info`

Read in `__main__.py` via `app_cfg.require_object("cluster-info")`, mapped onto
`cluster.ClusterConfig` (see [modules-api.md](modules-api.md)).

| Field | Type | Required | Meaning |
|---|---|---|---|
| `name` | string | yes | The Kind cluster's name, and the value used to key its config file path (`.pulumi/kind/<name>.yaml`) and its `kubeconfig` context (`kind-<name>`). |
| `kind-image` | string | no | The Kubernetes node image/version, e.g. `kindest/node:v1.31.0`. Passed to `kind create cluster --image`. |
| `wait-seconds` | int | no (defaults to `60` in `ClusterConfig`) | How long `kind create cluster --wait` waits for the cluster to report ready before giving up. |

## `app:network`

Read via `app_cfg.require_object("network")`, mapped onto `network.NetworkConfig`.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `dockerNetwork` | string | yes | Name of the dedicated Docker bridge network for this environment. |
| `vpcCidr` | string | yes | The **real** IP range for that Docker network. Must be unique per environment (see below) — this is an actual host-level network range. |
| `podCidr` | string | yes | A **virtual**, Kubernetes-internal address range for pod-to-pod traffic. Never routed outside the cluster — safe to reuse across environments. |
| `serviceCidr` | string | yes | Same idea as `podCidr`, but for Kubernetes Service IPs. |
| `extraPortMappings` | list of `{hostPort, containerPort, protocol}` | no | Optional host↔container port forwards on the control-plane node. Defaults to none. |

See [why-local-kind-clusters.md](../explanation/why-local-kind-clusters.md) for why `vpcCidr`
needs to be unique while `podCidr`/`serviceCidr` don't.

## Current values across all three stacks

| Stack | `cluster-info.name` | `network.dockerNetwork` | `network.vpcCidr` |
|---|---|---|---|
| `platform-sandbox` | `pe-sandbox` | `platform-sandbox-net` | `10.0.0.0/16` |
| `app-dev` | `app-dev` | `app-dev-net` | `10.1.0.0/16` |
| `app-prod` | `app-prod` | `app-prod-net` | `10.2.0.0/16` |

All three currently share `kind-image: kindest/node:v1.31.0`, `wait-seconds: 60`,
`podCidr: 10.244.0.0/16`, `serviceCidr: 10.96.0.0/12`. When adding a new stack, the next free
`vpcCidr` in this sequence is `10.3.0.0/16`.

## Setting a value

Because these are nested objects, use `--path` rather than a flat `pulumi config set`:

```bash
pulumi config set --path app:cluster-info.name app-staging
pulumi config set --path app:network.vpcCidr 10.3.0.0/16
```

A flat `pulumi config set app:cluster-info value` would overwrite the *entire* object with a
plain string, not add a field to it.
