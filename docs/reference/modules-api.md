# Reference: modules API

## `modules/network.py`

### `PortMap` (dataclass)

One host↔container port-forwarding rule.

| Field | Type | Default |
|---|---|---|
| `hostPort` | `int` | — |
| `containerPort` | `int` | — |
| `protocol` | `str` | `"TCP"` |

### `NetworkConfig` (dataclass)

| Field | Type | Default |
|---|---|---|
| `dockerNetwork` | `str` | — |
| `vpcCidr` | `str` | — |
| `podCidr` | `str` | — |
| `serviceCidr` | `str` | — |
| `extraPortMappings` | `list[PortMap] \| None` | `None` |

### `ensure_docker_network(cfg: NetworkConfig) -> local.Command`

Creates (or no-ops if it already exists, via `\|\| true`) the Docker bridge network named
`cfg.dockerNetwork` with subnet `cfg.vpcCidr`. On resource deletion, runs `docker network rm`
(also with `\|\| true`).

### `render_kind_config(cluster_name: str, net: NetworkConfig) -> str`

Pure function — builds and returns a Kind cluster config as a YAML string (one control-plane
node, one worker node, `net.podCidr`/`net.serviceCidr` as the cluster's internal addressing, and
`net.extraPortMappings` attached to the control-plane node if present). Does not touch disk or
create anything.

### `write_kind_config(cluster_name: str, yaml_content: str) -> local.Command`

Writes `yaml_content` to `.pulumi/kind/<cluster_name>.yaml`. `triggers=[yaml_content, path]`
means this re-runs whenever the generated config actually changes — without it, Pulumi would
consider the file "already written" forever, even after a config change.

## `modules/cluster.py`

### `ClusterConfig` (dataclass)

| Field | Type | Default |
|---|---|---|
| `name` | `str` | — |
| `kind_image` | `str \| None` | `None` |
| `wait_seconds` | `int` | `60` |

### `create_kind_cluster(cfg, cfg_file_path, docker_network, depends_on=None, replace_triggers=None) -> tuple[local.Command, local.Command, Provider]`

| Parameter | Type | Meaning |
|---|---|---|
| `cfg` | `ClusterConfig` | The cluster's name/image/wait settings. |
| `cfg_file_path` | `str` | Path to the Kind config YAML (from `write_kind_config`). |
| `docker_network` | `str` | Name of the Docker network to attach the cluster to. |
| `depends_on` | list of resources | Resources that must exist first — in practice, the Docker network and the config file. |
| `replace_triggers` | `list[str] \| None` | Values that, if changed, force the cluster to be recreated rather than left alone. |

Returns a 3-tuple:
1. **`create`** — the `local.Command` running `kind create cluster ...`.
2. **`kubeconfig`** — the `local.Command` running `kind get kubeconfig --name <name>`, depends on
   `create`. Its `.stdout` is the kubeconfig text.
3. **`provider`** — a `pulumi_kubernetes.Provider` built from `kubeconfig.stdout`, for any future
   Kubernetes-object resources targeting this specific cluster.

Internally builds this shell command:

```
KIND_EXPERIMENTAL_DOCKER_NETWORK="<docker_network>" kind create cluster \
  --name <cfg.name> \
  --config "<cfg_file_path>" \
  --image <cfg.kind_image> \
  --wait <cfg.wait_seconds>s
```

On deletion, runs `kind delete cluster --name <cfg.name>`.

## How `__main__.py` wires these together

```python
cls_cfg = cluster.ClusterConfig(name=..., kind_image=..., wait_seconds=...)
net_cfg = network.NetworkConfig(dockerNetwork=..., vpcCidr=..., podCidr=..., serviceCidr=...)

docker_net = network.ensure_docker_network(net_cfg)
kind_yaml = network.render_kind_config(cls_cfg.name, net_cfg)
kind_cfg_file = network.write_kind_config(cls_cfg.name, kind_yaml)

create, kubeconfig, k8s = cluster.create_kind_cluster(
    cls_cfg,
    cfg_file_path=f".pulumi/kind/{cls_cfg.name}.yaml",
    docker_network=net_cfg.dockerNetwork,
    depends_on=[docker_net, kind_cfg_file],
    replace_triggers=[kind_yaml, net_cfg.dockerNetwork, cls_cfg.kind_image or ""],
)

pulumi.export("cluster_name", cls_cfg.name)
pulumi.export("docker_network", net_cfg.dockerNetwork)
pulumi.export("kubeconfig", kubeconfig.stdout)
```

These three exports (`cluster_name`, `docker_network`, `kubeconfig`) are what
`tests/integration/infrastructure.bats` reads via `pulumi stack output` — see
[run-the-integration-tests.md](../how-to/run-the-integration-tests.md).
