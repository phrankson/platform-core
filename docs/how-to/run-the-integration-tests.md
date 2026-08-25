# How to: run the integration tests

`tests/integration/infrastructure.bats` is the independent, after-the-fact check that a deployed
environment actually works — see
[Tutorial 2](../tutorials/02-deploy-and-verify-a-cluster.md) for why this matters, and
[modules-api.md](../reference/modules-api.md) / [cli-cheatsheet.md](../reference/cli-cheatsheet.md)
for related reference material.

## Run it against the currently-selected stack

```bash
bats tests/integration/infrastructure.bats
```

If you don't set `PULUMI_STACK`, the test suite defaults to whatever `pulumi stack --show-name`
currently returns.

## Run it against a specific stack

```bash
PULUMI_STACK=app-dev bats tests/integration/infrastructure.bats
```

This is the form the CircleCI pipeline actually uses, since a CI job doesn't have an implicit
"currently selected" stack from a prior interactive session.

## What each check does

| Test | What it actually checks | Why |
|---|---|---|
| `docker network exists` | `docker network inspect "$DOCKER_NETWORK"` exits 0 | The `docker:net` Pulumi resource's create command ends in `\|\| true`, so Pulumi can report success even if the network was never actually created (e.g. a permissions failure). This test catches that gap. |
| `kubernetes cluster is accessible` | `kubectl get nodes` exits 0 and returns at least one node | Confirms the cluster isn't just "created" per Pulumi's bookkeeping, but is genuinely reachable and has compute in it. |

## How `setup_file()` gets its inputs

Before either test runs, `setup_file()`:
1. Fetches the stack's `kubeconfig` output (`pulumi stack output kubeconfig --show-secrets`) and
   writes it to `kubeconfig.yaml`, then points `KUBECONFIG` at that file.
2. Reads `docker_network` and `cluster_name` from the same stack's outputs.

If the `kubeconfig` output is stale — for example, because a cluster was deleted and manually
recreated outside of Pulumi — this test will fail even though the cluster is genuinely healthy.
See [Troubleshoot a failed Kind cluster](troubleshoot-a-failed-kind-cluster.md#stale-kubeconfig)
for the fix.

`teardown_file()` deletes the local `kubeconfig.yaml` afterward, so it can't accidentally leak
into git or confuse a later test run against a different stack.
