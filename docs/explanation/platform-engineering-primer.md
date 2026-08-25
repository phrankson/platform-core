# Explanation: a platform engineering primer

If you're new to the term: **platform engineering** is the discipline of building the internal
tooling, infrastructure, and workflows that let other engineering teams ship software safely and
quickly, without each team having to become infrastructure experts themselves. The output isn't a
product feature — it's the road other features get built on.

This repo is small, but every piece of it is a real, working example of the core practices, not
just a toy demonstration.

## The "paved road"

A paved road is a pre-built, well-tested, sanctioned way to do something — the path of least
resistance is also the safe path. Nobody using `pulumi up` against `platform-core` needs to know
how Kind's experimental Docker networking behaves, or how CircleCI resource classes work, or why
BATS is the verification tool of choice. They just run the documented commands, and get a
correctly-networked, independently-verified Kubernetes cluster.

## Config-driven, not code-driven

Every environment-specific value — cluster name, node image, network ranges — lives in
`Pulumi.<stack>.yaml`, not hardcoded in `__main__.py` or the modules. Adding a fourth environment
means editing YAML and running a command, not changing Python. See
[stack-configuration.md](../reference/stack-configuration.md) for the actual schema and
[add-a-new-environment-stack.md](../how-to/add-a-new-environment-stack.md) for the walkthrough.
This is what makes the difference between "one working script" and "a pattern the team can repeat
without re-deriving it each time."

## Blast-radius control

Several small decisions in this repo exist purely to contain how much damage a mistake can do:
- `platform-sandbox` deploys automatically on every push; `app-dev`/`app-prod` require a tagged
  release *and* a human approval — see
  [why-push-vs-tag-releases.md](../explanation/why-push-vs-tag-releases.md).
- Each environment gets its own Docker network and CIDR range, so a networking mistake in one
  can't leak into another.
- The BATS suite exists specifically because "the tool reported success" and "the thing actually
  works" are different claims — see
  [Tutorial 2](../tutorials/02-deploy-and-verify-a-cluster.md).

## Don't trust, verify

This repo has a real, concrete example of why: the Docker network creation command ends in
`|| true`, meaning Pulumi can report success even when the underlying `docker network create`
silently failed. `tests/integration/infrastructure.bats` exists precisely to catch that gap by
independently asking Docker and Kubernetes "are you actually there," rather than trusting Pulumi's
own bookkeeping.

## Automation as an aspiration, not a prerequisite

The CircleCI pipeline defined in `.circleci/config.yml` is real and fully valid — but the
self-hosted runner it depends on has had genuine reliability problems (see
[troubleshoot-the-self-hosted-runner.md](../how-to/troubleshoot-the-self-hosted-runner.md)). The
practical lesson: a documented, understood *manual* process (walking the promotion chain by hand,
as in [Tutorial 3](../tutorials/03-promote-a-change-through-the-pipeline.md)) is worth more than
an automated pipeline nobody can currently run. Automate it fully once it's reliable — don't let a
broken automation layer block the actual work.

## What to read next

Each design decision above has its own explanation page with more depth:
[why-infrastructure-as-code.md](why-infrastructure-as-code.md),
[why-local-kind-clusters.md](why-local-kind-clusters.md),
[why-push-vs-tag-releases.md](why-push-vs-tag-releases.md),
[why-manual-approval-gates.md](why-manual-approval-gates.md).
