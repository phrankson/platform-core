# How to tear down an environment

## Destroy the stack's resources

```console
$ pulumi stack select <stack-name>
$ pulumi destroy
```

This deletes the Argo `Application`, the Argo CD Helm release, the Kind
cluster (`kind delete cluster --name <cluster-name>`), and the Docker
network, in dependency order.

Unlike `platform-team-administration`'s repositories, **none of the
resources in this project set `protect=True`**. `pulumi destroy` here
will actually remove everything, with no safeguard. This is intentional:
a Kind cluster is cheap to recreate, and there's no equivalent to a
repository's unrecoverable history to protect.

## Remove the stack entirely

Once resources are destroyed, remove the stack itself if you don't intend
to reuse it:

```console
$ pulumi stack rm <stack-name>
```

This does not delete `Pulumi.<stack-name>.yaml` from disk — remove that
file separately if the environment is being permanently retired, and
remove its corresponding job wiring from
[`.circleci/config.yml`](../../.circleci/config.yml).

## If you only need to pause it, not destroy it

Kind clusters are just Docker containers. Pausing them keeps everything
intact and is much faster than a full destroy/recreate cycle:

```console
$ docker pause <cluster-name>-control-plane <cluster-name>-worker
$ docker unpause <cluster-name>-control-plane <cluster-name>-worker
```

This is also the workaround for the multi-cluster bootstrap conflict — see
[Troubleshooting](troubleshooting.md#a-new-cluster-fails-to-join-its-own-worker-node).
