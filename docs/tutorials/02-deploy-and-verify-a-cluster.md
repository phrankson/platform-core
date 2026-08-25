# Tutorial 2: Deploy and verify a cluster

In Tutorial 1 you previewed a plan without applying it. Here you'll actually create a real local
Kubernetes cluster, then — critically — verify it independently rather than just trusting that
Pulumi said it worked.

## Step 1: Deploy

Make sure you're on `platform-sandbox` and your virtual environment is active (see
[Tutorial 1](01-getting-started.md) if not), then:

```bash
pulumi up
```

Confirm the plan when prompted. This runs for real: it creates a Docker network, writes a Kind
config file, and runs `kind create cluster` — which pulls a Kubernetes node image (if you don't
already have it cached) and boots a two-node cluster (one control-plane, one worker) inside
Docker. Expect this to take one to a few minutes on a fresh machine.

If it fails partway through with a `kubeadm join` error mentioning a node "not found," you likely
have another one of this repo's Kind clusters already running — see
[Troubleshoot a failed Kind cluster](../how-to/troubleshoot-a-failed-kind-cluster.md) before
retrying.

## Step 2: Don't just trust it — verify independently

`pulumi up` reporting success means "the commands I ran didn't error." That's not quite the same
claim as "the infrastructure genuinely works." This repo has a real example of that gap: one of
its own resources creates the Docker network with a command that ends in `|| true`, which means
Pulumi will report success even if the underlying `docker network create` actually failed for a
reason like a permissions problem. See
[why-local-kind-clusters.md](../explanation/why-local-kind-clusters.md) if you want the full
story, but the takeaway for right now is: verify for yourself.

Check the cluster is really there with `kubectl`:

```bash
kubectl config get-contexts
kubectl --context kind-pe-sandbox get nodes
```

You should see two `Ready` nodes.

## Step 3: Run the real verification suite

This repo ships an automated version of exactly that independent check, using
[BATS](https://bats-core.readthedocs.io/) (Bash Automated Testing System):

```bash
bats tests/integration/infrastructure.bats
```

Expected output:

```
1..2
ok 1 docker network exists
ok 2 kubernetes cluster is accessible
```

This test doesn't just assume things worked — it independently asks Docker "does this network
exist?" and asks the cluster "are you actually reachable and do you have nodes?" Read
[Run the integration tests](../how-to/run-the-integration-tests.md) for what each check does and
how to point it at a different stack.

## Step 4 (optional): See it fail on purpose

If you want to see why this verification step earns its place, try this: stop the cluster's
containers without telling Pulumi, then re-run the tests.

```bash
docker stop pe-sandbox-control-plane pe-sandbox-worker
bats tests/integration/infrastructure.bats
docker start pe-sandbox-control-plane pe-sandbox-worker
```

The second test should fail — the cluster genuinely isn't reachable right now — even though
Pulumi's own state still says everything is fine. That's the gap independent verification exists
to catch.

## What you just did

You deployed real infrastructure and proved to yourself — not just to Pulumi — that it actually
works. Continue to
[Tutorial 3](03-promote-a-change-through-the-pipeline.md) to see how a change moves through all
three environments.
