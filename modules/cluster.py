"""Kind cluster provisioning: configuration and IaC resources."""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from pulumi import ResourceOptions
from pulumi_command import local
from pulumi_kubernetes import Provider


@dataclass
class ClusterConfig:
    name: str
    kind_image: Optional[str] = None
    wait_seconds: int = 60


def create_kind_cluster(
    cfg: ClusterConfig,
    cfg_file_path: str,
    docker_network: str,
    depends_on=None,
    replace_triggers: Optional[List[str]] = None,
) -> Tuple[local.Command, local.Command, Provider]:
    """Create a Kind cluster on the given Docker network and point kubectl at it."""
    create_cmd = (
        f'KIND_EXPERIMENTAL_DOCKER_NETWORK="{docker_network}" '
        "kind create cluster"
        f" --name {cfg.name}"
        f' --config "{cfg_file_path}"'
        f" --image {cfg.kind_image}"
        f" --wait {cfg.wait_seconds}s"
    )

    create_opts = ResourceOptions(depends_on=depends_on if depends_on else None)
    create = local.Command(
        "kind:create",
        create=create_cmd,
        delete=f"kind delete cluster --name {cfg.name}",
        triggers=replace_triggers or [],
        opts=create_opts,
    )

    kubeconfig = local.Command(
        "kind:kubeconfig",
        create=f"kind get kubeconfig --name {cfg.name}",
        opts=ResourceOptions(depends_on=[create]),
    )

    provider = Provider(
        "k8s",
        kubeconfig=kubeconfig.stdout,
        enable_server_side_apply=True,
    )

    return create, kubeconfig, provider
