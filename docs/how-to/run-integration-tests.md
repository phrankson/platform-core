# How to run integration tests

[`tests/integration/infrastructure.bats`](../../tests/integration/infrastructure.bats)
independently verifies that a deployed stack's Docker network and Kind
cluster actually work — not just that `pulumi up` reported success.

## Prerequisites

[BATS](https://bats-core.readthedocs.io/) installed
(`brew install bats-core`, or see the BATS docs for other platforms).

## Run

```console
$ export PULUMI_STACK=platform-sandbox   # optional; defaults to the
                                          # currently selected stack
$ bats tests/integration/infrastructure.bats
```

Expected output against a healthy stack:

```
 ✓ docker network exists
 ✓ kubernetes cluster is accessible
```

## What it actually checks

The test file fetches the stack's real kubeconfig from Pulumi's own
outputs (`pulumi stack output kubeconfig --show-secrets`), then:

- Confirms the stack's Docker network (`pulumi stack output
  docker_network`) exists via `docker network inspect`.
- Confirms `kubectl get nodes` against that kubeconfig succeeds and
  returns at least one node.

It cleans up the temporary kubeconfig file it writes (`kubeconfig.yaml`)
whether the tests pass or fail.

## Running against a different environment

```console
$ export PULUMI_STACK=app-dev
$ bats tests/integration/infrastructure.bats
```

The test queries `pulumi stack output ... --stack "$PULUMI_STACK"`
directly, without changing which stack is currently selected in your
shell — so this works for any of the three stacks without editing the
test file or disturbing your active `pulumi stack select`.
