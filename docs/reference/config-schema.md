# Configuration schema

Full field reference for `Pulumi.<stack-name>.yaml`, read by
[`__main__.py`](../../__main__.py) via `pulumi.Config("app")`.

## `app:cluster-info`

| Field | Type | Required | Default | Effect |
|---|---|---|---|---|
| `name` | string | Yes | — | The Kind cluster's own name. Not always the same as the Pulumi stack name (`platform-sandbox`'s cluster is named `pe-sandbox`). |
| `kind-image` | string | No | `None` | Node image passed to `kind create cluster --image`, e.g. `kindest/node:v1.31.0`. |
| `wait-seconds` | integer | No | `60` | Passed to `kind create cluster --wait`. |

## `app:network`

| Field | Type | Required | Default | Effect |
|---|---|---|---|---|
| `dockerNetwork` | string | Yes | — | Name of the Docker network the cluster attaches to. |
| `vpcCidr` | string | Yes | — | Real Docker network subnet. Must be unique per environment. |
| `podCidr` | string | Yes | — | Kubernetes-internal pod address range. Safe to reuse identically across environments. |
| `serviceCidr` | string | Yes | — | Kubernetes-internal service address range. Safe to reuse identically across environments. |
| `extraPortMappings` | list of objects | No | `None` | Each entry: `hostPort` (int), `containerPort` (int), `protocol` (string, default `TCP`). |

## `app:argocd`

Optional block — a stack can omit this entirely and simply not install
Argo CD.

| Field | Type | Required | Default | Effect |
|---|---|---|---|---|
| `version` | string | No | `None` (latest) | Argo CD Helm chart version. |

## Current values in use

| Stack | cluster name | vpcCidr | argocd version |
|---|---|---|---|
| `platform-sandbox` | `pe-sandbox` | `10.0.0.0/16` | `8.0.9` |
| `app-dev` | `app-dev` | `10.1.0.0/16` | `8.0.9` |
| `app-prod` | `app-prod` | `10.2.0.0/16` | `8.0.9` |

All three currently use `podCidr: 10.244.0.0/16` and `serviceCidr:
10.96.0.0/12`.
