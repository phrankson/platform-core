# Argo CD and the Handoff

Part of the [platform-core learning companion](README.md). Read
[Cluster Provisioning](cluster-provisioning.md) first — the foundation has
to be solid before anything gets installed on top of it.

---

## Installing a hub, then stepping back

Imagine the construction crew's very last job, once the house itself is
built: install a smart-home hub — one device that, once plugged in and
paired to an account, will spend the rest of its life listening for
instructions from that account and carrying them out on its own. The
crew's job is to physically install the hub and pair it. It is emphatically
*not* the crew's job to personally rearrange the furniture every time the
homeowner wants something moved — that's what the hub is for.

[`modules/argocd.py`](../modules/argocd.py) is this repo's last act, and
its docstring says the boundary out loud:

> Pulumi's job stops at getting the controller running. Once Argo CD is up,
> it takes over watching Git and reconciling application manifests on its
> own loop — Pulumi should never again touch a resource Argo CD owns.

This is a specific, important idea worth naming precisely, because it's
easy to blur: **Infrastructure as Code and configuration-as-code solve
different problems, and mixing them up creates real pain.** Pulumi is
excellent at "build the house and its foundation" — things that change
rarely, where "tear it down and rebuild" is an acceptable recovery plan.
It is a poor fit for "what furniture is currently arranged where" — things
that change constantly, where you want a fast, cheap, in-place update
history and an easy rollback, not a foundation-level rebuild. Argo CD (a
**GitOps controller**) exists specifically for that second job: it watches
a Git repository continuously and keeps the cluster's actual state matching
whatever's declared there, on its own, forever — no human running a deploy
command each time something changes.

Two functions in this file do exactly the two things a crew does with a
smart-home hub:

**`install()`** physically installs the hub — a one-time Helm chart
install, run once by Pulumi, exactly like installing any other appliance:

```python
return helm.v3.Release(
    "argocd",
    helm.v3.ReleaseArgs(
        chart="argo-cd",
        version=version,
        repository_opts=helm.v3.RepositoryOptsArgs(
            repo="https://argoproj.github.io/argo-helm",
        ),
        namespace=namespace,
        create_namespace=True,
    ),
    opts=ResourceOptions(provider=provider),
)
```

**`seed_gitops()`** pairs the hub to an account — creating exactly one
object, an Argo `Application`, that tells the freshly-installed hub *which*
account to start listening to:

```python
argocd_root_app = argocd.seed_gitops(
    k8s,
    repo_url="https://github.com/phrankson/platform-gitops.git",
    path=f"environments/{pulumi.get_stack()}",
    depends_on=[argocd_release],
)
```

The instant that object exists, this repo's job is finished for this
house. Every deployment onward is Argo CD discovering the next instruction
in `platform-gitops` on its own — not another `pulumi up`.

Notice `pulumi.get_stack()`, not the cluster's own name — a distinction
worth holding onto. `platform-gitops`'s folders are named after the
*Pulumi stack* (`platform-sandbox`, `app-dev`, `app-prod`); the underlying
Kind house names differ slightly (`pe-sandbox` for the sandbox house).
Using the wrong one would pair the hub to a folder that doesn't exist.

## Argo CD instead of Flux

Flux is the more commonly taught GitOps controller, and it works
differently from Argo CD in a way worth understanding, since Argo CD is
what this project actually runs. Flux needs two separate devices talking
to each other: a `GitRepository` object that says which account to watch,
and a `Kustomization` object that says what to do with what that account
says. Argo CD's single `Application` object does the job of both, because
it bakes the account's address directly into the same object that says
where to deploy. There's no separate "register this account first" step to
manage.

<details>
<summary><strong>Predict before reading on:</strong> the first real attempt to install this hub failed with the installer stuck, and a helper process called <code>redis-secret-init</code> crash-looping with the error <code>dial tcp 10.96.0.1:443: i/o timeout</code> — a total inability to reach the house's own internal address book from inside the house. Nothing about the hub's own settings was wrong. What single thing, shared across <em>all three houses at once</em>, was the actual cause?</summary>

The real culprit was `kube-proxy` — the component that makes a house's
internal address book (`10.96.0.1`) actually resolve to anything —
crash-looping on **every node of all three houses simultaneously**, with
the telling error `"command failed" err="failed complete: too many open
files"`.

The root cause was one shared limit on the machine itself, not anything
inside any single house:

```console
$ sysctl fs.inotify.max_user_instances
fs.inotify.max_user_instances = 128
```

Think of this as the shared electrical panel for the whole property, not a
per-house circuit — `128` is comfortably enough capacity for *one* house
under construction. Building all three simultaneously — each with its own
address-book service, its own network watcher, its own name-resolution
service, all needing to plug into the same shared panel — tripped the
breaker for the entire property at once. Once the internal address book
stopped resolving, *nothing* inside any of the three houses could find
anything else: not the hub's installer, not name resolution, nothing. The
visible symptom (the hub failing to install) was several layers downstream
of the actual cause (a property-wide electrical limit with zero connection
to Argo CD, Helm, or this codebase).

The fix is a one-time, property-wide change — not a code change:

```console
$ sudo sysctl fs.inotify.max_user_watches=524288
$ sudo sysctl fs.inotify.max_user_instances=512
```

After that, `kube-proxy` recovered on its own on the next restart cycle
(forced immediately rather than waiting out the backoff timer), and the
exact same install that had just failed succeeded cleanly on retry, with
zero code changes.

Worth keeping as a general instinct, not just a fact about this project:
**the deepest layer of a stack — here, the host's own kernel limits — can
produce a symptom that looks exactly like a misconfiguration three layers
up, and the only way to tell the difference is checking the layer the
error message never mentions at all.**
</details>

**Try it yourself** — the whole chain, live, right now:

```console
$ kubectl get applications -n argocd
NAME                SYNC STATUS   HEALTH STATUS
platform-gitops     Synced        Healthy
platform-services   Synced        Healthy
istio-base          OutOfSync     Healthy
istiod              OutOfSync     Healthy
istio-ingress       Synced        Progressing
```

`platform-gitops` is the one object `seed_gitops()` created — the pairing
instruction. Every other row in that list, this repo never created
directly; the hub found those on its own, by following `platform-gitops`.
See [`platform-gitops`'s own learning companion](../../platform-gitops/learning/README.md)
for what those actually are and how the hub discovers them.

## What a postmortem would say about the inotify incident

Site Reliability Engineering has a specific way of writing up an incident
like the one above, and it's worth comparing to what you just read. A good
postmortem stays blameless — it asks what about the system allowed the
failure, not who caused it — and it separates the trigger from the root
cause. The trigger here was running three Kind clusters at once. The root
cause was a host kernel limit nobody had ever needed to think about before
that point. Fixing only the trigger (say, never running more than one
cluster at a time) would have avoided this specific incident without
addressing the actual constraint. Fixing the root cause, which is what
happened, means the same failure won't come back the next time something
else pushes against that same limit.

SRE also has a concept called an error budget: instead of demanding
perfect uptime, you decide in advance how much failure is acceptable, and
you treat that budget as something to spend deliberately rather than
something you're merely failing to avoid. This project has never defined
one. There's no stated target for how reliable these clusters are supposed
to be, which means there's also no defined threshold for when a problem
like this one should have paged someone versus waited until morning. That
absence isn't a criticism of the incident response — it's a genuine gap
worth naming: reacting well to a failure and having a stated reliability
target are two different things, and this project only has the first one.

## The gap: nobody is on call for the platform itself

It's worth being direct about something the last few sections gloss over.
Once Argo CD is installed and paired, it keeps running on its own, but
nothing in this project watches *it*. If Argo CD's own pods crashed at
2 a.m., nothing would notice, and nothing would page anyone. The tests in
the next section check that things worked at the moment they were run, not
continuously. Platform ops — someone or something responsible for the
platform's own health, the way an SRE team is responsible for a product's
uptime — doesn't exist here yet. This project ends at "prove it worked
just now," not "make sure it keeps working."

---

Continue to [**Verification and CI/CD**](verification-and-cicd.md) for how
this project proves a house actually works, rather than trusting that
`pulumi up` said so.
