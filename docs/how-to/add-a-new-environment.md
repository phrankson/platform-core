# How to add a new environment

This mirrors exactly how `app-dev` and `app-prod` were added to this
project.

## 1. Initialize the stack

```console
$ pulumi stack init <new-stack-name>
```

This does **not** create `Pulumi.<new-stack-name>.yaml` yet — that file
only appears after the first `pulumi config set` or `pulumi
preview`/`up` against the new stack.

## 2. Set the configuration

Every field under `app:cluster-info` and `app:network` is required. Use a
Docker network CIDR (`vpcCidr`) that doesn't overlap any existing
environment's — see [Configuration schema](../reference/config-schema.md)
for the full field list and the current values in use.

```console
$ pulumi config set --path app:cluster-info.name <cluster-name>
$ pulumi config set --path app:cluster-info.kind-image kindest/node:v1.31.0
$ pulumi config set --path app:cluster-info.wait-seconds 60
$ pulumi config set --path app:network.dockerNetwork <env>-net
$ pulumi config set --path app:network.vpcCidr 10.3.0.0/16
$ pulumi config set --path app:network.podCidr 10.244.0.0/16
$ pulumi config set --path app:network.serviceCidr 10.96.0.0/12
$ pulumi config set --path app:argocd.version 8.0.9
```

`podCidr` and `serviceCidr` are internal to Kubernetes and safe to reuse
identically across every environment. `vpcCidr` must be unique per
environment — it's a real Docker network address.

## 3. Deploy it

```console
$ pulumi up
```

See [Deploy a stack](deploy-a-stack.md) for what this actually does.

## 4. Wire it into the CI/CD pipeline

Add a new `pulumi-update` / `validate-infrastructure` pair to the
`update` workflow in
[`.circleci/config.yml`](../../.circleci/config.yml), requiring an
approval gate after the previous environment's validation succeeds —
follow the existing `app-dev` → `approve-prod-deploy` → `app-prod` chain
as the template. See
[CI/CD pipeline reference](../reference/cicd-pipeline.md) for the exact
current structure.

## 5. Register it with platform-gitops and platform-services

This repo only provisions the cluster and bootstraps Argo CD — it doesn't
create the corresponding `environments/<new-stack-name>/` folders in
`platform-gitops` or `platform-services`. Those need to be added
separately in each of those repos before Argo CD has anything to
reconcile against. Until then, `pulumi up` will succeed here, but the
Argo `Application` it creates will have nothing to sync.
