# How to: add a new environment stack

This is exactly the sequence used to add `app-prod` to this repo. Follow it to add another
environment (say, `app-staging`).

## 1. Initialize the stack

```bash
export VIRTUAL_ENV=$(pwd)/.venv
export PATH="$VIRTUAL_ENV/bin:$PATH"
pulumi stack init app-staging
pulumi stack select app-staging
```

`pulumi stack init` only registers the stack with the Pulumi Cloud backend — it does **not**
create a `Pulumi.<stack>.yaml` file yet. That file only appears once you actually set config
against the stack (see [stack-configuration.md](../reference/stack-configuration.md) for why).

## 2. Set the cluster and network config

Pick a `vpcCidr` that doesn't overlap any existing stack's — check
[stack-configuration.md](../reference/stack-configuration.md) for the ones already in use.

```bash
pulumi config set --path app:cluster-info.name app-staging
pulumi config set --path app:cluster-info.kind-image kindest/node:v1.31.0
pulumi config set --path app:cluster-info.wait-seconds 60

pulumi config set --path app:network.dockerNetwork app-staging-net
pulumi config set --path app:network.vpcCidr 10.3.0.0/16
pulumi config set --path app:network.podCidr 10.244.0.0/16
pulumi config set --path app:network.serviceCidr 10.96.0.0/12
```

`podCidr`/`serviceCidr` are safe to reuse across every stack — they're virtual, internal-only
addresses (see [why-local-kind-clusters.md](../explanation/why-local-kind-clusters.md)). Only
`vpcCidr` and `dockerNetwork` need to be unique per environment.

## 3. Verify with a preview

```bash
pulumi preview
```

You should see 6 resources to create, with correct `cluster_name`/`docker_network` outputs. If
another stack's Kind cluster is currently running, the actual `pulumi up` later may hit the
multi-cluster bootstrap issue — see
[Troubleshoot a failed Kind cluster](troubleshoot-a-failed-kind-cluster.md).

## 4. Add it to the CI pipeline

Open `.circleci/config.yml`'s `update` workflow (see
[pipeline-reference.md](../reference/pipeline-reference.md) for the full structure) and add a new
approval-gated stage after the last one, following the existing pattern exactly:

```yaml
- approve-staging-deploy:
    name: "Approve staging deploy"
    type: approval
    requires:
      - Validate app-dev        # or whichever stage should gate this one
    filters: *on-tag-main

- pulumi-update:
    name: "Deploy to app-staging"
    context: *context
    pulumi_stack: app-staging
    requires:
      - Approve staging deploy
    filters: *on-tag-main
- validate-infrastructure:
    name: "Validate app-staging"
    context: *context
    pulumi_stack: app-staging
    requires:
      - Deploy to app-staging
    filters: *on-tag-main
```

**Do not** declare the approval job under the top-level `jobs:` section — `type: approval` jobs
are invoked directly inside a workflow and never run their own `steps:`. See
[why-manual-approval-gates.md](../explanation/why-manual-approval-gates.md) for why this bug is
easy to introduce and how to spot it.

## 5. Validate the pipeline config

```bash
circleci config validate .circleci/config.yml
circleci config process .circleci/config.yml   # sanity-check the resolved dependency chain
```

## 6. Commit, PR, and deploy

Merge the config change through a PR (main is branch-protected), then either let CircleCI's
`update` workflow run on the next tag, or deploy locally as in
[Tutorial 3](../tutorials/03-promote-a-change-through-the-pipeline.md).
