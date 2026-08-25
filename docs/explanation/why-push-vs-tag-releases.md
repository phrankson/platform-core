# Explanation: why push-vs-tag releases

## The two Git events, and what each means

A `push` to a branch happens constantly — every commit, on every branch, many times a day. A tag
is different: someone deliberately decided "this exact commit is a release." CircleCI's
`on-push-main`/`on-tag-main` filters (see
[pipeline-reference.md](../reference/pipeline-reference.md)) route these two kinds of events to
two entirely separate workflows.

## Why sandbox reacts to push, but app-dev/app-prod don't

`platform-sandbox` deploys automatically on every push to `main`, with no approval gate. That's
deliberate: sandbox is meant to be disposable and low-stakes, so getting fast feedback on every
change matters more than gating it. If a change breaks sandbox, the cost is a few minutes to fix
and redeploy — nothing else depends on it.

`app-dev` and `app-prod` only ever move on a **tag**, and even then only after a human approves
(see [why-manual-approval-gates.md](why-manual-approval-gates.md)). Merging a PR to `main` and
releasing a change to those environments are treated as two separate, deliberate decisions — not
one automatic consequence of the other.

## Why that separation is worth the friction

If `pulumi up` against `app-dev`/`app-prod` ran on every push to `main`, then merging a PR would
silently deploy to those environments. That collapses two genuinely different questions — "is
this code good enough to merge?" and "should this specific change go live right now?" — into one.
Decoupling them means:

- A merge can happen the moment code review passes, without needing to also be a release
  decision.
- A tag becomes a permanent, meaningful marker: "this commit is what `v0.2.0` actually was" — a
  real rollback point and changelog anchor, which `main`'s constantly-moving history can't give
  you on its own.
- The genuinely risky operation (`pulumi up` against `app-dev`/`app-prod`, which changes real
  local infrastructure) only runs when someone intended it to, not as a side effect of routine
  merging.

## `pulumi preview` vs `pulumi up`, and why `preview` runs so much more often

`pulumi preview` is read-only — it computes and prints a diff without touching anything. Running
it on every push (as the `preview` workflow does) is essentially free and catches a broken config
within a minute, long before anyone would think to run Pulumi by hand. `pulumi up` is the
expensive, consequential operation this whole pattern exists to gate.
