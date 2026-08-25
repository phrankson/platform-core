# How to: troubleshoot a failed Kind cluster

These are real failure modes hit while building and operating this repo's three environments, not
hypothetical ones.

## "failed to join node with kubeadm" / `nodes "X-worker" not found`

**Symptom:** `pulumi up` (or a raw `kind create cluster`) fails after "Joining worker nodes 🚜",
with a `kubeadm join` error and repeated `404 Not Found` polls for the worker node, taking
roughly 100+ seconds before giving up.

**Root cause:** `modules/cluster.py` creates each cluster with
`KIND_EXPERIMENTAL_DOCKER_NETWORK` set, so every environment gets its own dedicated Docker
network. Kind itself flags this as unsupported (`WARNING: Here be dragons!`), and in practice:
**bootstrapping a *new* Kind cluster while *another* one from this repo is already running
reliably breaks the new cluster's worker-node join.** This was confirmed by reproducing the
failure twice, then succeeding immediately after pausing the other cluster's containers.

**Fix:** before creating a new cluster, pause every other Kind cluster's containers from this
repo:

```bash
docker ps --format '{{.Names}}' | grep -E 'control-plane|worker'
docker stop <other-cluster>-control-plane <other-cluster>-worker
pulumi up --yes
docker start <other-cluster>-control-plane <other-cluster>-worker
```

Once a cluster is fully bootstrapped, **multiple clusters coexist fine simultaneously** — the
conflict is specifically during the bootstrap/join window of a new one, not ongoing operation.
Verify with `kubectl --context kind-<name> get nodes` for each cluster after restarting them.

This is a real limitation to keep in mind for the CI pipeline too: the `update` workflow deploys
all three environments in sequence on the same self-hosted runner machine, so this pause/resume
step may need to become part of the automated pipeline (see the roadmap in
[`docs/README.md`](../README.md)).

## A cluster gets stuck mid-boot after `docker stop`/`docker start`

**Symptom:** after pausing and restarting a cluster's containers, `kubectl get nodes` against it
hangs or returns `Unable to connect to the server: EOF` indefinitely — and `docker logs
<name>-control-plane` shows the exact same last few lines no matter how long you wait (it's
genuinely stuck, not just slow to boot).

**Why:** a `docker stop`/`docker start` cycle fully restarts the container's init system
(systemd), not just the Kubernetes processes inside it. On this repo's experimental
custom-network setup, that restart doesn't always come back cleanly.

**Fix:** don't wait for it — delete and recreate just that cluster, with the same
pause-other-clusters precaution as above:

```bash
kind delete cluster --name <name>

# pause every OTHER cluster's containers first (see above), then:
KIND_EXPERIMENTAL_DOCKER_NETWORK="<name>-net" kind create cluster \
  --name <name> \
  --config ".pulumi/kind/<name>.yaml" \
  --image kindest/node:v1.31.0 \
  --wait 60s

# restart the other clusters
```

After this, Pulumi's own state still thinks the old `kind:create`/`kind:kubeconfig` resources are
fine (nothing about this manual recreation went through Pulumi) — see the next section.

## Stale kubeconfig after a manual cluster recreation {#stale-kubeconfig}

**Symptom:** the cluster is genuinely healthy (`kubectl --context kind-<name> get nodes` works),
but `bats tests/integration/infrastructure.bats` fails on `kubernetes cluster is accessible`.

**Root cause:** recreating a cluster outside of Pulumi (as in the previous section) generates
fresh TLS certificates. Pulumi's stack state still has the **old** kubeconfig cached from the
original `kind:kubeconfig` resource, since nothing told Pulumi that resource is now invalid.

**Fix:** force Pulumi to re-run the kubeconfig fetch (and its dependent Kubernetes provider):

```bash
pulumi stack export --show-secrets=false \
  | python3 -c "import json,sys; [print(r['urn']) for r in json.load(sys.stdin)['deployment']['resources'] if 'kind:kubeconfig' in r.get('urn','')]"

pulumi up --yes \
  --target-replace "<the urn printed above>" \
  --target-dependents
```

`--target-dependents` is required — replacing `kind:kubeconfig` alone will be rejected, since the
`k8s` Kubernetes provider resource depends on its output and would otherwise need to be
destroyed without being rebuilt.

## General debugging commands

```bash
kind get clusters                                  # which clusters currently exist
docker ps -a | grep -E 'control-plane|worker'       # their containers' actual state
docker logs <name>-control-plane --tail 30          # boot progress / stuck-boot diagnosis
kubectl --context kind-<name> get nodes             # is it actually reachable
pulumi stack export --show-secrets=false | jq .     # what Pulumi thinks exists
```
