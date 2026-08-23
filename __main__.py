"""Provisions the local Kind cluster's network scaffolding via Pulumi."""

from dataclasses import dataclass

import pulumi

from modules import network

app_cfg = pulumi.Config("app")

cluster_info = app_cfg.require_object("cluster-info")
network_obj = app_cfg.require_object("network")


@dataclass
class ClusterInfo:
    name: str
    kind_image: str
    wait_seconds: int


cls_cfg = ClusterInfo(
    name=cluster_info["name"],
    kind_image=cluster_info["kind-image"],
    wait_seconds=cluster_info["wait-seconds"],
)

# Map config -> dataclasses
net_cfg = network.NetworkConfig(
    dockerNetwork=network_obj["dockerNetwork"],
    vpcCidr=network_obj["vpcCidr"],
    podCidr=network_obj["podCidr"],
    serviceCidr=network_obj["serviceCidr"],
    extraPortMappings=[
        network.PortMap(**pm) for pm in network_obj.get("extraPortMappings", [])
    ]
    or None,
)

# Network scaffolding + kind config
docker_net = network.ensure_docker_network(net_cfg)
kind_yaml = network.render_kind_config(cls_cfg.name, net_cfg)
kind_cfg_file = network.write_kind_config(cls_cfg.name, kind_yaml)

pulumi.export("cluster_name", cls_cfg.name)
pulumi.export("docker_network", net_cfg.dockerNetwork)
