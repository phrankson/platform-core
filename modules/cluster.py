"""Kind cluster provisioning: configuration and IaC resources.

This file is responsible for actually creating a local Kubernetes cluster
using "Kind" (Kubernetes in Docker) and connecting Pulumi to it.
"""

from dataclasses import dataclass

# ResourceOptions lets us control how a Pulumi resource behaves -- here we
# use it to say "don't create the cluster until the network is ready."
from pulumi import ResourceOptions

# Pulumi has no built-in "Kind cluster" resource type (Kind isn't a cloud
# service, just a CLI tool), so we use pulumi_command's `local.Command`,
# which runs an ordinary shell command as a Pulumi-managed step.
from pulumi_command import local

# Once the cluster exists, Pulumi needs to know how to talk to it if we
# ever want to create Kubernetes objects (namespaces, deployments, etc.)
# inside it. `Provider` is that connection -- built from the cluster's
# kubeconfig further down in this file.
from pulumi_kubernetes import Provider


@dataclass
class ClusterConfig:
    """Settings for one Kind cluster, read from the per-environment config file."""

    name: str  # the cluster's name, e.g. "pe-sandbox" or "app-dev"
    kind_image: str | None = None  # which Kubernetes node image/version to use
    wait_seconds: int = 60  # how long to wait for the cluster to become ready


def create_kind_cluster(
    cfg: ClusterConfig,
    cfg_file_path: str,
    docker_network: str,
    depends_on=None,
    replace_triggers: list[str] | None = None,
) -> tuple[local.Command, local.Command, Provider]:
    """Create a Kind cluster on the given Docker network and point kubectl at it.

    Returns three things the caller (__main__.py) will need:
      1. the "create cluster" command itself
      2. the "fetch kubeconfig" command (kubeconfig = the credentials/address
         kubectl and Pulumi use to talk to the cluster)
      3. a ready-to-use Pulumi Kubernetes provider, connected to this cluster
    """

    # Build the exact shell command that creates the cluster, piece by piece.
    # This is equivalent to typing something like this yourself in a terminal:
    #   KIND_EXPERIMENTAL_DOCKER_NETWORK="my-net" kind create cluster \
    #     --name pe-sandbox --config ".pulumi/kind/pe-sandbox.yaml" \
    #     --image kindest/node:v1.31.0 --wait 60s
    create_cmd = (
        # Tell Kind to attach the cluster to the Docker network we already
        # created in network.py, instead of Kind's own default network.
        f'KIND_EXPERIMENTAL_DOCKER_NETWORK="{docker_network}" '
        "kind create cluster"
        f" --name {cfg.name}"
        # The YAML file network.py generated earlier (node roles, pod/service
        # address ranges) -- this is the actual blueprint for the cluster.
        f' --config "{cfg_file_path}"'
        f" --image {cfg.kind_image}"
        # Don't report "done" until the cluster is actually ready to use.
        f" --wait {cfg.wait_seconds}s"
    )

    # depends_on tells Pulumi "don't run this step until these other
    # resources exist first" -- here, that means the Docker network and the
    # Kind config file must already be created before we try to use them.
    create_opts = ResourceOptions(depends_on=depends_on if depends_on else None)

    create = local.Command(
        "kind:create",
        create=create_cmd,
        # What to run if this resource is ever destroyed (e.g. `pulumi destroy`).
        delete=f"kind delete cluster --name {cfg.name}",
        # `triggers` tells Pulumi "re-run the create command if any of these
        # values change" -- without it, Pulumi would assume "already did
        # this" forever, even if the cluster's config actually changed.
        triggers=replace_triggers or [],
        opts=create_opts,
    )

    # A second step, run only after the cluster is created (depends_on=[create]):
    # ask Kind for the cluster's kubeconfig -- the file kubectl (and Pulumi)
    # need in order to authenticate to and communicate with the cluster.
    kubeconfig = local.Command(
        "kind:kubeconfig",
        create=f"kind get kubeconfig --name {cfg.name}",
        opts=ResourceOptions(depends_on=[create]),
    )

    # Build a Pulumi provider for this specific cluster, using the
    # kubeconfig text captured above (`.stdout` is the command's output).
    # Any future Kubernetes resources (namespaces, deployments, etc.) would
    # be created through this provider so they land in *this* cluster.
    provider = Provider(
        "k8s",
        kubeconfig=kubeconfig.stdout,
        enable_server_side_apply=True,
    )

    return create, kubeconfig, provider
