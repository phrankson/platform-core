"""Local network configuration for the Kind cluster: Docker network + CIDRs.

This file builds the "plumbing" a Kubernetes cluster needs before it can
exist: a Docker network for the cluster's containers to live on, and a
config file telling Kind what internal addressing to use.
"""

import base64
from dataclasses import dataclass
from typing import Any

import yaml

# Pulumi has no built-in "Docker network" resource (Docker isn't a cloud
# provider Pulumi has a plugin for), so we use pulumi_command's
# `local.Command` -- Pulumi's escape hatch for "just run this shell command
# as a managed step."
from pulumi_command import local


@dataclass
class PortMap:
    """One port-forwarding rule: expose a container port on the host machine."""

    hostPort: int  # the port on your actual machine, e.g. 8080
    containerPort: int  # the port inside the cluster's container, e.g. 80
    protocol: str = "TCP"


@dataclass
class NetworkConfig:
    """Settings for one environment's network, read from its config file."""

    dockerNetwork: str  # name of the Docker network to create, e.g. "app-dev-net"
    vpcCidr: str  # IP range for the real Docker network on your machine
    # podCidr and serviceCidr are NOT real network ranges -- they're
    # addresses Kubernetes makes up internally for its own bookkeeping
    # (pod-to-pod and service traffic). Nothing outside the cluster ever
    # sees or routes to them, so they're safe to reuse across environments.
    podCidr: str
    serviceCidr: str
    extraPortMappings: list[PortMap] | None = (
        None  # optional host<->container port rules
    )


def ensure_docker_network(cfg: NetworkConfig) -> local.Command:
    """Create (or ensure) the Docker bridge network.

    This is the literal equivalent of running, in a terminal:
        docker network create <name> --subnet <cidr>
    `|| true` means "don't treat it as an error if the network already
    exists" -- this makes the command safe to run repeatedly.
    """
    return local.Command(
        "docker:net",
        create=f"docker network create {cfg.dockerNetwork} --subnet {cfg.vpcCidr} || true",
        # What to run if this resource is ever destroyed (e.g. `pulumi destroy`).
        delete=f"docker network rm {cfg.dockerNetwork} || true",
    )


def render_kind_config(cluster_name: str, net: NetworkConfig) -> str:
    """Produce a Kind config YAML bound to the Docker network + CIDRs.

    This function doesn't create anything on its own -- it just builds the
    *contents* of a config file, in memory, as a Python dictionary, then
    converts it to a YAML string. Kind (the tool that actually creates
    Kubernetes clusters) reads a file like this to know what to build:
    one control-plane node, one worker node, and which address ranges to
    use for pod/service traffic.
    """
    node: dict[str, Any] = {"role": "control-plane"}
    if net.extraPortMappings:
        # vars(pm) turns each PortMap dataclass into a plain dict, which is
        # what the YAML output needs.
        node["extraPortMappings"] = [vars(pm) for pm in net.extraPortMappings]

    kind_cfg: dict[str, Any] = {
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
    """Write the Kind config YAML to a stable path for Pulumi runs.

    render_kind_config() only builds the YAML text -- this function is what
    actually saves it to disk, at .pulumi/kind/<cluster_name>.yaml, so Kind
    can read it when the cluster is created (see modules/cluster.py).

    The content is base64-encoded before being written out through the
    shell, purely so special characters in the YAML (quotes, colons, etc.)
    can't accidentally break the shell command that writes the file.
    """
    path = f".pulumi/kind/{cluster_name}.yaml"
    b64 = base64.b64encode(yaml_content.encode("utf-8")).decode("ascii")
    script = f"mkdir -p .pulumi/kind && echo {b64} | base64 -d > {path}"

    return local.Command(
        "kind:cfg",
        create=script,
        delete=f'rm -f "{path}"',
        # `triggers` tells Pulumi "re-run this step if any of these values
        # change." Without it, Pulumi would assume "already wrote this
        # file" forever, even after you change your network config.
        triggers=[yaml_content, path],
    )
