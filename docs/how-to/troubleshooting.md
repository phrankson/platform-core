# Troubleshooting

Real problems this project has hit, and how to resolve them.

## A new cluster fails to join its own worker node

**Symptom:** `pulumi up` on a stack whose cluster doesn't exist yet fails
during `kind create cluster`, with errors like `nodes "X-worker" not
found`, while another stack's cluster is also running.

**Cause:** this project attaches each Kind cluster to its own Docker
network via `KIND_EXPERIMENTAL_DOCKER_NETWORK`. That mechanism isn't fully
safe for concurrent multi-cluster bootstraps — creating a new cluster
while another is still finishing its own bootstrap can cause the new
cluster's `kubeadm join` step to fail.

**Fix:** pause the other stacks' containers while the new one is being
created, then resume them:

```console
$ docker pause app-dev-control-plane app-dev-worker app-prod-control-plane app-prod-worker
$ pulumi up --yes
$ docker unpause app-dev-control-plane app-dev-worker app-prod-control-plane app-prod-worker
```

## `pulumi up` fails to reach the Kubernetes API from inside the cluster

**Symptom:** installing Argo CD (or anything else) fails with a helper pod
in `CrashLoopBackOff` logging `dial tcp 10.96.0.1:443: i/o timeout`, and
`kube-proxy` is also crash-looping with `"command failed" err="failed
complete: too many open files"`.

**Cause:** running three Kind clusters simultaneously can exhaust the
host's `fs.inotify.max_user_instances` limit — a value shared across every
process on the machine, not per-container. `128` (a common default) is
enough for one cluster but not three at once.

**Fix:** raise the host's limits (requires `sudo`):

```console
$ sudo sysctl fs.inotify.max_user_watches=524288
$ sudo sysctl fs.inotify.max_user_instances=512
```

If `kube-proxy` is already crash-looping, force an immediate restart
rather than waiting out its backoff timer:

```console
$ kubectl delete pod -n kube-system <kube-proxy-pod-name>
```

Then retry the original `pulumi up`.

## Pulumi's kubeconfig points at a cluster that no longer matches it

**Symptom:** after a cluster was recreated manually (`kind delete cluster`
+ `kind create cluster`, bypassing Pulumi), `kubectl` commands using
Pulumi's stored kubeconfig fail with certificate or connection errors.

**Cause:** Pulumi's stored kubeconfig output still reflects the previous
cluster's certificates. Manually recreating the cluster outside of Pulumi
leaves Pulumi's own state stale.

**Fix:** force Pulumi to refetch the kubeconfig and refresh anything built
from it:

```console
$ pulumi up --yes --target-replace 'urn:pulumi:<stack>::platform-core::command:local:Command::kind:kubeconfig' --target-dependents
```

`--target-dependents` is required — without it, the kubeconfig itself
refreshes but the Kubernetes provider built from it does not.

## A Docker network's actual subnet doesn't match its config

**Symptom:** `docker network inspect <network-name>` shows a different
subnet than `vpcCidr` in `Pulumi.<stack>.yaml`.

**Cause:** `docker network create ... || true` doesn't fail if a network
with that name already exists — but it also doesn't update an existing
network's subnet to match new flags. If a network was ever created once
under a different subnet (for example, before `vpcCidr` was finalized),
every subsequent `pulumi up` silently no-ops past the mismatch instead of
correcting it.

**Fix:** there is no automatic fix — `docker network create` cannot
change an existing network's subnet. To actually correct it, remove the
network and let Pulumi recreate it (this requires the cluster attached to
that network to be destroyed and recreated too, since a running cluster
can't be reattached to a new network):

```console
$ pulumi destroy
$ docker network rm <network-name>
$ pulumi up
```

## `mypy` hangs and never completes

**Cause:** without `--follow-imports=skip`, `mypy` chases into
`pulumi_kubernetes`'s large generated SDK.

**Fix:** always run it with that flag, as
[`.circleci/config.yml`](../../.circleci/config.yml) does:

```console
$ mypy __main__.py modules/ --ignore-missing-imports --follow-imports=skip
```

## `isort` and `black` disagree on formatting

**Cause:** the two tools have different default opinions on blank lines
around individually-commented imports.

**Fix:** this project's [`.isort.cfg`](../../.isort.cfg) sets `profile =
black`, resolving the conflict project-wide. If you see this fight in a
new file, confirm `.isort.cfg` is being picked up (run `isort` from the
repo root).

## `pulumi stack init` didn't create a config file

**Symptom:** after `pulumi stack init <name>`, there's no
`Pulumi.<name>.yaml` on disk.

**Cause:** this is expected, not a bug. The file only appears after the
first `pulumi config set` or `pulumi preview`/`up` against that stack.
