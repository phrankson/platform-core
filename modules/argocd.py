"""GitOps controller: installs Argo CD into the cluster via Helm.

Pulumi's job stops at getting the controller running. Once Argo CD is up,
it takes over watching Git and reconciling application manifests on its own
loop -- Pulumi should never again touch a resource Argo CD owns (an
Application, a Deployment it manages, etc). This is the IaC-vs-configuration
boundary: Pulumi pours the foundation (the cluster, the controller); Argo CD
manages what's inside the house from here on.
"""

from dataclasses import dataclass
from typing import Optional

from pulumi import ResourceOptions
from pulumi_kubernetes import Provider, helm


@dataclass
class ArgoCDConfig:
    """Settings for the Argo CD install, read from the per-environment config file."""

    version: Optional[str] = None  # chart version; None = latest available


def install(
    provider: Provider,
    namespace: str = "argocd",
    version: Optional[str] = None,
) -> helm.v3.Release:
    """Install Argo CD into the cluster via its official Helm chart.

    Returns the Release resource so the caller (__main__.py) can set up a
    dependency on it -- e.g. before pointing Argo CD at the platform-gitops
    repo.
    """
    return helm.v3.Release(
        "argocd",
        helm.v3.ReleaseArgs(
            chart="argo-cd",
            version=version,
            repository_opts=helm.v3.RepositoryOptsArgs(
                repo="https://argoproj.github.io/argo-helm",
            ),
            namespace=namespace,
            create_namespace=True,
        ),
        opts=ResourceOptions(provider=provider),
    )
