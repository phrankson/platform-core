# CI/CD pipeline reference

Full reference for [`.circleci/config.yml`](../../.circleci/config.yml).

## Executor

`local-machine` — `machine: true`, `resource_class:
erikan/local_laptop_runner`. A self-hosted runner is required because jobs
run `docker` and `kind` directly; CircleCI's cloud executors can't do
this.

## Context

`PLATFORM_ADMIN` — applied to every job. Holds `PULUMI_ACCESS_TOKEN`,
shared with `platform-team-administration`'s pipeline rather than
duplicated.

## Reusable commands

| Command | Steps |
|---|---|
| `setup-python` | `uv venv .venv`, activate, `uv pip install -r requirements.txt`. |
| `lint-code` | `black --check --diff`, `mypy --follow-imports=skip`, `isort --check-only`. |
| `static-analysis` | `ruff check`, `bandit -r ... -ll`. |

## Jobs

| Job | Parameters | Steps |
|---|---|---|
| `pulumi-preview` | `pulumi_stack` | Checkout → `setup-python` → `lint-code` → `static-analysis` → select stack → `pulumi preview`. |
| `pulumi-update` | `pulumi_stack` | Checkout → `setup-python` → select stack → `pulumi up --yes --skip-preview`. |
| `validate-infrastructure` | `pulumi_stack` | Checkout → select stack → `bats tests/integration/infrastructure.bats` → clean up `kubeconfig.yaml`. |

## Triggers

| Filter | Matches |
|---|---|
| `on-push-main` | Push to `main`, no tags. |
| `on-tag-main` | Any tag, no plain branches. |

## Workflows

### `preview`

On every push to `main`: `pulumi-preview` → `pulumi-update` → `validate-infrastructure`,
all against `platform-sandbox`. No approval gate — sandbox deploys
automatically.

### `update`

On a version tag:

1. `pulumi-preview` (platform-sandbox)
2. `pulumi-update` → "Deploy to platform-sandbox (tag)"
3. `validate-infrastructure` → "Validate platform-sandbox (tag)"
4. `approve-app-dev-deploy` — manual approval gate
5. `pulumi-update` → "Deploy to app-dev"
6. `validate-infrastructure` → "Validate app-dev"
7. `approve-prod-deploy` ("Approve prod deploy") — manual approval gate
8. `pulumi-update` → "Deploy to app-prod"
9. `validate-infrastructure` → "Validate app-prod"

Each deploy step requires the previous stage's validation to succeed
first — a stage's own deploy and validation both have to pass before the
next approval gate becomes available.

## A note on `type: approval` jobs

`approve-app-dev-deploy` and `approve-prod-deploy` are CircleCI's built-in
approval job type, invoked directly inside the workflow's `jobs:` list.
They must **not** also be declared under the top-level `jobs:` map — doing
so means that job's own `steps:` never run. This is a real bug this
project (and `platform-team-administration`'s pipeline) hit and fixed.
