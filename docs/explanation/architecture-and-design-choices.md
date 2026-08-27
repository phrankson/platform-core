# Architecture and design choices

This document explains the reasoning behind decisions in this codebase,
for anyone maintaining or extending it.

## Why three separate clusters instead of three namespaces

`platform-sandbox`, `app-dev`, and `app-prod` are each a fully independent
Kind cluster — separate Docker network, separate control plane, separate
compute — rather than three namespaces inside one shared cluster. This
trades resource efficiency (three control planes instead of one) for
strict isolation: nothing running in one environment can affect another
by a misconfigured namespace boundary or a shared control-plane outage,
because there's no shared control plane to begin with. For a project where
each environment needs to be provably independent, that trade is worth
the extra overhead of running three clusters on one machine.

## Why `local.Command` instead of a native resource type

Pulumi's typed resource model works by having a provider (a plugin) that
knows how to create, read, update, and delete one specific kind of thing —
an AWS EC2 instance, a GitHub repository. Kind isn't a service any
provider models, because it isn't a cloud API — it's a CLI tool that
drives Docker directly. `pulumi_command.local.Command` is Pulumi's escape
hatch for exactly this situation: it lets an arbitrary shell command
participate in Pulumi's resource graph, with real create/delete actions
and dependency tracking, at the cost of losing the type safety and
built-in diffing a native resource would provide.

This is why `triggers` has to be specified explicitly wherever
`local.Command` is used in this project (`cluster.py`'s cluster creation,
`network.py`'s config file writes) — Pulumi has no way to inspect an
arbitrary shell command's own state the way it can inspect a typed
resource's fields, so it has to be told explicitly what values, if
changed, mean "this needs to be redone."

## Why Argo CD, not Flux

Both are GitOps controllers with the same underlying job: watch a Git
repository and keep the cluster matching what it declares. This project
uses Argo CD's `Application` custom resource, which combines "which
repository and path to watch" and "where and how to deploy it" into a
single object. Flux splits the same job across two separate objects (a
`GitRepository` for the source, a `Kustomization` for what to do with it).
Either is a reasonable choice; this project's `argocd.py` is built around
Argo CD's single-object model specifically, which is why `seed_gitops()`
creates exactly one `CustomResource` rather than two.

## The IaC / configuration-code boundary

`argocd.py`'s `install()` and `seed_gitops()` are the last things this
repo's Pulumi program does. After `seed_gitops()` runs, Pulumi never
touches anything Argo CD manages again — no application manifest, no
`Deployment`, nothing inside the cluster that Argo CD reconciles. This is
a deliberate boundary: Pulumi is well suited to provisioning things that
change rarely and can be safely torn down and rebuilt (a cluster, a
network). It's a poor fit for continuously-changing application state,
which is what a GitOps controller exists to manage with its own
versioning and rollback model. Mixing the two — using Pulumi to manage
what Argo CD also manages — creates two systems that can each believe they
own the same resource's true state.

## Why `depends_on` is explicit throughout `__main__.py`

Pulumi builds a dependency graph from your program, but for `local.Command`
resources it can't infer dependencies the way it can for typed resources
whose fields reference each other. Every `depends_on` in this codebase
(the Kind cluster depending on the Docker network and Kind config file;
`seed_gitops()` depending on the Argo CD Helm release) exists because
Pulumi has no other way to know these steps must happen in that order —
without it, Pulumi could attempt to create the cluster before its network
exists, or bootstrap Argo CD before it's installed.
