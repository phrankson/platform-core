# Explanation: why manual approval gates

## What a `type: approval` job actually is

In CircleCI, a job invoked with `type: approval` isn't really a job that runs anything — it's a
pause button. The workflow stops there until a human clicks "approve" in the CircleCI UI. Nothing
downstream of it can proceed until someone deliberately decides it should.

## Where the gates sit in this pipeline, and why there specifically

The `update` workflow (see [pipeline-reference.md](../reference/pipeline-reference.md)) has two
approval gates:

```
... → "Validate platform-sandbox (tag)" → [approve-app-dev-deploy] → "Deploy to app-dev" → ...
... → "Validate app-dev"                 → [Approve prod deploy]    → "Deploy to app-prod" → ...
```

Notice the gate comes **after validation, not right after deploy.** That ordering is deliberate:
a human approving a promotion should be approving *a change that has already been shown to work*
in the environment before it — not just "a deploy that didn't error." Requiring
`Validate app-dev` (not merely `Deploy to app-dev`) to succeed before the prod approval gate even
appears means an approver is never asked to sign off on an unverified change.

## The bug this pattern is easy to introduce

A `type: approval` job must be declared **only** as a workflow-level job invocation — never also
under the top-level `jobs:` section. If you write it both ways, expecting the top-level
`jobs.<name>.steps` to run as some kind of confirmation message, they won't: CircleCI treats the
workflow-level `type: approval` invocation specially and never executes the referenced job's own
steps at all. `platform-team-administration`'s `config.yml` had exactly this bug in an early draft
— a job block with `steps: - run: echo "Approved..."` that could never actually run. The fix is to
delete the dead top-level block entirely and keep the approval purely as an inline workflow
invocation, exactly as both gates in this repo's `config.yml` are written.

## Why this is worth the manual step at all

An approval gate is friction by design — that's the point. It's the CI/CD expression of the same
principle behind requiring a second person to review a pull request: some decisions are important
enough that a single automated pipeline shouldn't be allowed to make them unattended. As this
project matures and trust in the pipeline grows, it would be reasonable to relax *how many* gates
exist or *who* can approve them — but removing the concept entirely would mean any tagged commit
could reach production with no human ever having looked at it.
