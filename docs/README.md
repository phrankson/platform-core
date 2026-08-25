# platform-core documentation

This documentation is organized using the [Diátaxis](https://diataxis.fr/) framework. Diátaxis
splits documentation into four modes, each answering a different kind of question. Knowing which
mode you're in tells you what to expect from a page — and, when you're the one writing it, what
belongs on it.

| Folder | Answers | You reach for it when... |
|---|---|---|
| [`tutorials/`](tutorials/) | "Can you walk me through it?" | You're new here and want a guided, hands-on first experience. |
| [`how-to/`](how-to/) | "How do I do X?" | You have a specific task and already know the basics. |
| [`reference/`](reference/) | "What exactly does X take/return/mean?" | You need the precise facts — a schema, a signature, a full command list. |
| [`explanation/`](explanation/) | "Why does it work this way?" | You want the reasoning and trade-offs, not just the mechanics. |

Tutorials and how-to guides are both about *doing*; reference and explanation are both about
*understanding*. But tutorials and explanation are written for someone learning, while how-to
guides and reference assume you already know the territory and just need the specific answer.

## Suggested reading order (junior dev, first time in this repo)

1. [`explanation/platform-engineering-primer.md`](explanation/platform-engineering-primer.md) —
   read this first. It gives you the vocabulary and the "why" for everything else.
2. [`tutorials/01-getting-started.md`](tutorials/01-getting-started.md) — get your environment
   working and see your first `pulumi preview`.
3. [`tutorials/02-deploy-and-verify-a-cluster.md`](tutorials/02-deploy-and-verify-a-cluster.md) —
   deploy something real, then independently verify it actually works.
4. [`tutorials/03-promote-a-change-through-the-pipeline.md`](tutorials/03-promote-a-change-through-the-pipeline.md) —
   walk a change through all three environments, including the approval gates.

From there, dip into `how-to/` whenever you have a specific task, and `reference/` whenever you
need to look something up. Read the rest of `explanation/` whenever you want the "why" behind a
specific design decision rather than all at once.

## What this repo actually is

`platform-core` is the Pulumi program that provisions the platform team's local Kubernetes
runtime: a [Kind](https://kind.sigs.k8s.io/) (Kubernetes-in-Docker) cluster per environment
(`platform-sandbox`, `app-dev`, `app-prod`), plus the network scaffolding each one sits on and a
CircleCI pipeline that promotes changes between them.

It's a small repo, but every piece in it is a real, working example of a platform engineering
practice: infrastructure as code, config-driven environments, independent post-deploy validation,
and a deliberate push-vs-tag release gate. The docs below try to teach those practices through
this repo, not just document its API surface.

## Documentation roadmap

This is a living set of docs — it grows as the repo does. What's covered now, and what's
explicitly on deck:

**Covered today:**
- [x] The three-environment Pulumi setup (`platform-sandbox`, `app-dev`, `app-prod`)
- [x] The network + cluster provisioning modules (`modules/network.py`, `modules/cluster.py`)
- [x] The BATS integration test suite
- [x] The CircleCI pipeline: lint/static-analysis, preview-on-push, tag-gated promotion with
      manual approvals
- [x] The CircleCI self-hosted runner setup and its rough edges

**Deferred in the code, and so deferred here too** (see the `TODO` comments in
`.circleci/config.yml`) — docs for these land in the same change that builds them, not before:
- [ ] OPA/conftest policy checks (`policy-check` command, commented out — no `policy/` or
      `environments/` directories exist yet)
- [ ] Flux GitOps reconciliation + smoke testing (commented out in `validate-infrastructure` —
      Flux hasn't been introduced into this project yet)
- [ ] Observability (mentioned in `Pulumi.yaml`'s description, not yet implemented)

If you build one of the deferred items, the expectation is: add or extend a how-to guide for
using it, a reference page for its config surface, and — if it introduces a new concept — an
explanation page for why it works the way it does. Update the checklist above in the same PR.
