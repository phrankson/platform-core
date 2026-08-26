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
from pulumi_kubernetes import Provider, apiextensions, helm


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


def seed_gitops(
    provider: Provider,
    *,
    namespace: str = "argocd",
    repo_url: str,
    path: str,
    name: str = "platform-gitops",
    depends_on=None,
) -> apiextensions.CustomResource:
    """Bootstrap Argo CD by pointing it at the platform-gitops App of Apps repo.

    This is the root Application. Once it's applied, Argo CD starts watching
    repo_url/path itself and discovers + manages every child Application
    declared there (e.g. tenants/platform-services/platform-services.yaml)
    on its own -- no further manual `kubectl apply` needed as tenants or
    environments are added later.

    The book's version of this is two Flux CRDs (GitRepository +
    Kustomization) -- same simplification as platform-services.yaml: Argo
    CD folds "which repo/path" and "where/how to deploy it" into one
    Application CRD, so one CustomResource replaces both of the book's.
    """
    create_opts = ResourceOptions(
        provider=provider, depends_on=depends_on if depends_on else None
    )

    return apiextensions.CustomResource(
        "argocd-root-app",
        api_version="argoproj.io/v1alpha1",
        kind="Application",
        metadata={"name": name, "namespace": namespace},
        spec={
            "project": "default",
            "source": {
                "repoURL": repo_url,
                "targetRevision": "main",
                "path": path,
            },
            "destination": {
                "server": "https://kubernetes.default.svc",
                "namespace": namespace,
            },
            "syncPolicy": {
                "automated": {"prune": True, "selfHeal": True},
                "syncOptions": ["CreateNamespace=true"],
            },
        },
        opts=create_opts,
    )
