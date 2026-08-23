"""Local network configuration for the Kind cluster: Docker network + CIDRs."""

import base64
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import yaml
from pulumi_command import local


@dataclass
class PortMap:
    hostPort: int
    containerPort: int
    protocol: str = "TCP"


@dataclass
class NetworkConfig:
    dockerNetwork: str
    vpcCidr: str
    podCidr: str
    serviceCidr: str
    extraPortMappings: Optional[List[PortMap]] = None


def ensure_docker_network(cfg: NetworkConfig) -> local.Command:
    """Create (or ensure) the Docker bridge network."""
    return local.Command(
        "docker:net",
        create=f"docker network create {cfg.dockerNetwork} --subnet {cfg.vpcCidr} || true",
        delete=f"docker network rm {cfg.dockerNetwork} || true",
    )


def render_kind_config(cluster_name: str, net: NetworkConfig) -> str:
    """Produce a Kind config YAML bound to the Docker network + CIDRs."""
    node: Dict[str, Any] = {"role": "control-plane"}
    if net.extraPortMappings:
        node["extraPortMappings"] = [vars(pm) for pm in net.extraPortMappings]

    kind_cfg: Dict[str, Any] = {
        "kind": "Cluster",
        "apiVersion": "kind.x-k8s.io/v1alpha4",
        "networking": {
            "podSubnet": net.podCidr,
            "serviceSubnet": net.serviceCidr,
        },
        "nodes": [node, {"role": "worker"}],
    }
    return yaml.safe_dump(kind_cfg, sort_keys=False)


def write_kind_config(cluster_name: str, yaml_content: str) -> local.Command:
    """Write the Kind config YAML to a stable path for Pulumi runs."""
    path = f".pulumi/kind/{cluster_name}.yaml"
    b64 = base64.b64encode(yaml_content.encode("utf-8")).decode("ascii")
    script = f"mkdir -p .pulumi/kind && echo {b64} | base64 -d > {path}"

    return local.Command(
        "kind:cfg",
        create=script,
        delete=f'rm -f "{path}"',
        # re-run when content/path changes
        triggers=[yaml_content, path],
    )
