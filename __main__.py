"""Provisions the local Kind cluster and its network scaffolding via Pulumi."""

import pulumi

from modules import cluster, network

app_cfg = pulumi.Config("app")

cluster_info = app_cfg.require_object("cluster-info")
network_obj = app_cfg.require_object("network")

cls_cfg = cluster.ClusterConfig(
    name=cluster_info["name"],
    kind_image=cluster_info.get("kind-image"),
    wait_seconds=cluster_info.get("wait-seconds"),
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

# Cluster + k8s provider
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
