# Modules API reference

## `modules/network.py`

### `PortMap` (dataclass)

```python
hostPort: int
containerPort: int
protocol: str = "TCP"
```

### `NetworkConfig` (dataclass)

```python
dockerNetwork: str
vpcCidr: str
podCidr: str
serviceCidr: str
extraPortMappings: list[PortMap] | None = None
```

### `ensure_docker_network(cfg: NetworkConfig) -> local.Command`

Runs `docker network create <dockerNetwork> --subnet <vpcCidr> || true`.
Delete action runs `docker network rm <dockerNetwork> || true`. See
[Troubleshooting](../how-to/troubleshooting.md#a-docker-networks-actual-subnet-doesnt-match-its-config)
for the `|| true` caveat.

### `render_kind_config(cluster_name: str, net: NetworkConfig) -> str`

Returns a YAML string (not written to disk) describing a two-node Kind
cluster (`control-plane` + `worker`) using `net.podCidr` /
`net.serviceCidr`, with `net.extraPortMappings` attached to the
control-plane node if provided.

### `write_kind_config(cluster_name: str, yaml_content: str) -> local.Command`

Writes `yaml_content` to `.pulumi/kind/<cluster_name>.yaml`, base64-encoded
through the shell to avoid YAML special characters breaking the write
command. `triggers=[yaml_content, path]` — re-runs if the content changes.

## `modules/cluster.py`

### `ClusterConfig` (dataclass)

```python
name: str
kind_image: str | None = None
wait_seconds: int = 60
```

### `create_kind_cluster(cfg, cfg_file_path, docker_network, depends_on=None, replace_triggers=None) -> tuple[local.Command, local.Command, Provider]`

| Parameter | Type | Effect |
|---|---|---|
| `cfg` | `ClusterConfig` | Cluster name, image, wait time. |
| `cfg_file_path` | `str` | Path to the Kind config YAML written by `write_kind_config`. |
| `docker_network` | `str` | Docker network name to attach the cluster to. |
| `depends_on` | list of resources | Resources that must exist before cluster creation runs. |
| `replace_triggers` | list of strings | Values that, if changed, force the cluster to be destroyed and recreated. |

Returns `(create, kubeconfig, provider)`:

- `create` — the `kind create cluster` command resource. Delete action
  runs `kind delete cluster --name <name>`.
- `kubeconfig` — the `kind get kubeconfig --name <name>` command resource.
  `.stdout` holds the kubeconfig text.
- `provider` — a `pulumi_kubernetes.Provider` built from `kubeconfig.stdout`,
  with `enable_server_side_apply=True`.

## `modules/argocd.py`

### `ArgoCDConfig` (dataclass)

```python
version: Optional[str] = None
```

### `install(provider, namespace="argocd", version=None) -> helm.v3.Release`

Installs the `argo-cd` chart from
`https://argoproj.github.io/argo-helm`, with `create_namespace=True`.

### `seed_gitops(provider, *, namespace="argocd", repo_url, path, name="platform-gitops", depends_on=None) -> apiextensions.CustomResource`

Creates one Argo `Application` (`argoproj.io/v1alpha1`) named `name` in
`namespace`, with:

- `spec.source.repoURL = repo_url`, `spec.source.targetRevision = "main"`,
  `spec.source.path = path`
- `spec.destination.server = "https://kubernetes.default.svc"`,
  `spec.destination.namespace = namespace`
- `spec.syncPolicy.automated = {prune: true, selfHeal: true}`,
  `syncOptions: ["CreateNamespace=true"]`

Called from [`__main__.py`](../../__main__.py) with `path=f"environments/{pulumi.get_stack()}"`
— note this uses the Pulumi stack name, not `cfg.name` (the Kind cluster's
own name), since `platform-gitops`'s folders are named after the stack.
