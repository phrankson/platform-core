# Tutorial 3: Promote a change through the pipeline

This repo manages three environments in a deliberate sequence: `platform-sandbox` deploys
automatically on every push to `main`; `app-dev` and `app-prod` only deploy on a tagged release,
each behind its own manual approval. This tutorial walks that whole chain by hand, the same way
it was actually exercised while this repo was being built — which is also the most honest way to
learn it, since the automated version (CircleCI) depends on a self-hosted runner that may or may
not be healthy on any given day. See
[Troubleshoot the self-hosted runner](../how-to/troubleshoot-the-self-hosted-runner.md) if you
want the CI version to actually run.

Read [why-push-vs-tag-releases.md](../explanation/why-push-vs-tag-releases.md) and
[why-manual-approval-gates.md](../explanation/why-manual-approval-gates.md) first if you haven't
— this tutorial assumes you know *why* the chain looks like this, not just *how* to run it.

## The chain you're about to walk

```
push to main → preview → deploy platform-sandbox → validate
     (a tag) → preview → deploy platform-sandbox → validate
                        → [approve] → deploy app-dev → validate
                        → [approve] → deploy app-prod → validate
```

## Step 1: Make a small, real change

Pick something low-risk — e.g. bump `wait-seconds` in `Pulumi.app-dev.yaml` from `60` to `90`.
Commit it on a branch and merge to `main` (this repo's `main` is branch-protected: you'll need a
PR, not a direct push). Merging to `main` triggers the `preview` workflow in CircleCI, which
previews and deploys `platform-sandbox` automatically — no approval needed, since sandbox is
meant to be disposable.

## Step 2: Tag a release

```bash
git tag -a v0.2.0 -m "v0.2.0: bump app-dev readiness wait"
git push origin v0.2.0
```

Pushing a tag (not a branch) triggers the separate `update` workflow — see
[pipeline-reference.md](../reference/pipeline-reference.md) for exactly how the `on-tag-main`
filter distinguishes this from a plain push.

## Step 3: Walk the chain locally

Whether or not CircleCI's runner is healthy right now, you can walk the exact same sequence by
hand — this is what "promotion" actually means underneath the YAML:

```bash
export VIRTUAL_ENV=$(pwd)/.venv
export PATH="$VIRTUAL_ENV/bin:$PATH"

# 1. Re-validate sandbox against the tagged commit
pulumi stack select platform-sandbox
pulumi up --yes
PULUMI_STACK=platform-sandbox bats tests/integration/infrastructure.bats

# 2. [This is where a human approves in the real pipeline]

# 3. Deploy and validate app-dev
pulumi stack select app-dev
pulumi up --yes
PULUMI_STACK=app-dev bats tests/integration/infrastructure.bats

# 4. [Second approval]

# 5. Deploy and validate app-prod
pulumi stack select app-prod
pulumi up --yes
PULUMI_STACK=app-prod bats tests/integration/infrastructure.bats
```

**One real gotcha you will hit:** creating a *new* Kind cluster while another one from this repo
is already running can fail a worker-node join. If `app-dev` or `app-prod` doesn't exist yet, and
another stack's cluster is currently up, pause the other cluster's containers first:

```bash
docker stop pe-sandbox-control-plane pe-sandbox-worker   # if it's already running
pulumi up --yes   # now safe to create the new cluster
docker start pe-sandbox-control-plane pe-sandbox-worker  # bring it back afterward
```

Full explanation and the recovery steps if something gets stuck mid-restart:
[Troubleshoot a failed Kind cluster](../how-to/troubleshoot-a-failed-kind-cluster.md).

## What you just did

You walked a real, gated, multi-environment release — the same sequence of deploy → independently
verify → get human sign-off → promote, repeated once per environment, that a production platform
team would run through CI. The only thing missing when you do it by hand is CircleCI clicking the
approval buttons for you; the actual safety properties (nothing skips validation, nothing reaches
prod without going through dev first) are identical.
