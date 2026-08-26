# Cluster Provisioning: pouring the foundation

Part of the [platform-core learning companion](README.md). Read
[Networking](networking.md) first — the hookup has to exist before the
foundation gets poured.

---

## No prefab kit for this house

Most of what Pulumi does day to day is order from a catalog: "one AWS EC2
instance, please," and a plugin built by AWS's own ecosystem knows exactly
how to build it, check on it, and tear it down cleanly. That catalog has no
listing for "one Kind cluster," because Kind isn't a cloud provider — it's
a CLI tool that runs Docker containers on your own machine and makes them
pretend to be Kubernetes nodes. There's no manufacturer standing behind a
prefab "Kind cluster" resource type.

[`modules/cluster.py`](../modules/cluster.py) handles this the way a crew
handles a house with no available prefab kit: build it on-site, from
scratch, using general-purpose tools. Pulumi's version of "general-purpose
tools" is `pulumi_command.local.Command` — an escape hatch that lets an
*arbitrary shell command* behave like a real, trackable resource, with real
create/delete lifecycle:

```python
create = local.Command(
    "kind:create",
    create=create_cmd,                              # kind create cluster ...
    delete=f"kind delete cluster --name {cfg.name}", # runs on `pulumi destroy`
    triggers=replace_triggers or [],
    opts=create_opts,
)
```

`triggers` exists because Pulumi has no built-in way to know whether an
*arbitrary shell command's* underlying reality has changed — it's not a
typed resource Pulumi understands the shape of. For a prefab AWS instance,
Pulumi can compare every field on its own. For "run this shell command,"
someone has to say explicitly: *rebuild the foundation if any of these
things changed* — the rendered network diagram, the Docker network name,
the node image. Without `triggers`, Pulumi would consider the house
"already built" forever, even after a change that should have meant
tearing it down and starting over.

Once the foundation is poured, a second command asks Kind for the
kubeconfig — the credentials needed to actually talk to this specific
house — and a `pulumi_kubernetes.Provider` is built from it, becoming the
one, single connection every later step in this repo goes through.

## Two crews, one shared power line

Building three houses simultaneously is fine, as long as they're not all
drawing from the exact same temporary generator at the exact same moment.
This project runs all three Kind clusters at once, each supposedly on its
own isolated Docker network — but "isolated" turned out to have a real
limit during actual construction.

<details>
<summary><strong>Predict before reading on:</strong> Kind's multi-cluster networking uses an experimental flag (<code>KIND_EXPERIMENTAL_DOCKER_NETWORK</code>) under the hood. What goes wrong if you try to build a <em>new</em> house while another one, using that same experimental mechanism, is still mid-construction?</summary>

This happened for real while building `app-prod`: creating a new Kind
cluster while another cluster (also mid-bootstrap on
`KIND_EXPERIMENTAL_DOCKER_NETWORK`) was still finishing caused the new
cluster's `kubeadm join` step to fail outright — worker nodes couldn't
find their own control plane, with errors like
`nodes "X-worker" not found`. The experimental flag isn't fully safe for
concurrent multi-cluster bootstraps; the tooling briefly trips over its own
feet, the same way two crews sharing one generator can brown out the whole
site if both fire up power tools at the same instant.

The workaround, confirmed by testing it directly: pause the other houses'
containers while a new one is under construction, then resume them once
it's done.

```console
$ docker pause app-dev-control-plane app-dev-worker app-prod-control-plane app-prod-worker
$ pulumi up --yes   # builds platform-sandbox cleanly, uncontended
$ docker unpause app-dev-control-plane app-dev-worker app-prod-control-plane app-prod-worker
```

This is a real, still-open limitation of building multiple Kind clusters
this way on one machine — not something this codebase fully solves, just
something to know before running `pulumi up` on a house that doesn't exist
yet while the others are actively running.
</details>

## When the paperwork doesn't match the building anymore

A smaller, real incident: after one house got stuck mid-construction from a
`docker stop`/`docker start` cycle, it was rebuilt manually with
`kind delete cluster` + `kind create cluster` — bypassing Pulumi entirely,
the way a crew might rebuild a wall without telling the permit office. That
left Pulumi's *own records* (its stored kubeconfig) pointing at
certificates for a house that, from the paperwork's point of view, no
longer existed in the state it remembered.

The fix is a genuinely reusable Pulumi technique:

```console
$ pulumi up --yes --target-replace 'urn:pulumi:...:kind:kubeconfig' --target-dependents
```

`--target-replace` forces one specific resource to be torn down and
rebuilt (fetch a fresh kubeconfig, this time for real); `--target-dependents`
tells Pulumi to also refresh everything built *from* it — here, the
Kubernetes connection built from that kubeconfig. Skip
`--target-dependents` and you'd end up with fresh paperwork sitting next to
a connection still wired to the old, wrong version of it.

---

Continue to [**Argo CD and the Handoff**](argocd-and-handoff.md) for what
gets installed once the foundation is solid, and the incident that took
down all three houses' power at once.
