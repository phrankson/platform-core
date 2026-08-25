# Explanation: why local Kind clusters

## What Kind actually is

[Kind](https://kind.sigs.k8s.io/) ("Kubernetes IN Docker") runs a full, real, standards-compliant
Kubernetes cluster using Docker containers as its "nodes" — no cloud account, no VM, no cost
beyond your own machine's resources. A two-node Kind cluster is genuinely a control-plane node and
a worker node, each running as its own Docker container with `kubelet`, `containerd`, and the
Kubernetes control-plane components inside.

## Why local, disposable clusters at all

Cloud Kubernetes (EKS, GKE, AKS) costs money and takes minutes to provision even for a throwaway
test. A platform team iterating on cluster provisioning logic, network configuration, or
validation tooling doesn't want that cost or latency in the loop. Kind gives you the real thing —
actual `kubectl`, actual scheduling, actual networking — in the time it takes to pull an image and
boot two containers.

## The two networking layers, and why only one needs to be unique

`modules/network.py`'s `NetworkConfig` has three CIDR-shaped fields, and they are not the same
kind of thing:

- **`vpcCidr`** is a *real* IP range, assigned to an actual Docker bridge network on your machine
  (`docker network create ... --subnet <vpcCidr>`). If two environments used the same `vpcCidr`
  and their networks somehow needed to coexist at the routing layer, you'd get a real conflict.
  This is why each stack has a distinct value (`10.0.0.0/16`, `10.1.0.0/16`, `10.2.0.0/16`... —
  see [stack-configuration.md](../reference/stack-configuration.md)).

- **`podCidr`** and **`serviceCidr`** are *virtual* — addresses the Kubernetes CNI plugin hands
  out internally for pod-to-pod and Service traffic, entirely inside the cluster's own network
  namespace. Nothing outside the cluster ever sees or routes to them. Every stack in this repo
  safely reuses the same values (`10.244.0.0/16` / `10.96.0.0/12`) — these are also, not
  coincidentally, extremely common Kubernetes defaults across many distributions.

The practical rule: if you're choosing a CIDR value for a *new* environment, only `vpcCidr` needs
to be checked against what already exists. `podCidr`/`serviceCidr` don't.

## The custom-network trade-off (and its real cost)

This repo pins each cluster to its own dedicated Docker network via
`KIND_EXPERIMENTAL_DOCKER_NETWORK`, specifically so environments are network-isolated from each
other rather than sharing Kind's single default network. Kind itself flags this feature as
unsupported ("Here be dragons!") — and that warning is not decorative. In practice, it causes a
real, reproducible failure: **bootstrapping a new cluster while another one from this repo is
already running breaks the new cluster's worker-node join.** See
[troubleshoot-a-failed-kind-cluster.md](../how-to/troubleshoot-a-failed-kind-cluster.md) for the
exact symptom and the pause-other-clusters workaround.

This is a genuine, currently-unresolved architectural tension worth knowing about rather than
being surprised by: per-environment network isolation is valuable, but the specific mechanism
used to get it here is fragile. A future improvement might explore whether the isolation is worth
keeping given this cost, or whether a different approach (e.g. one shared Kind network, relying on
distinct cluster/namespace names for isolation instead) is more robust.
