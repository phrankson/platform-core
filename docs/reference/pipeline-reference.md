# Reference: CircleCI pipeline

Full structure of `.circleci/config.yml`. See
[why-push-vs-tag-releases.md](../explanation/why-push-vs-tag-releases.md) and
[why-manual-approval-gates.md](../explanation/why-manual-approval-gates.md) for the reasoning
behind this shape.

## Executor

`local-machine` — `machine: true` on `resource_class: erikan/local_laptop_runner`, a self-hosted
runner (see [troubleshoot-the-self-hosted-runner.md](../how-to/troubleshoot-the-self-hosted-runner.md)).
`machine: true` (a real VM, not a container) is required because jobs run `docker` and `kind`
themselves.

## Context

`PLATFORM_ADMIN` — the same CircleCI context already created for `platform-team-administration`,
reused here rather than duplicated, holding `PULUMI_ACCESS_TOKEN`.

## Filters (YAML anchors)

| Anchor | Branches | Tags | Used by |
|---|---|---|---|
| `on-push-main` | only `main` | ignore all | `preview` workflow |
| `on-tag-main` | ignore all | only (any tag) | `update` workflow |

## Reusable commands

| Command | What it does |
|---|---|
| `setup-python` | `uv venv .venv` + `uv pip install -r requirements.txt` |
| `lint-code` | `black --check`, `mypy --follow-imports=skip`, `isort --check-only` |
| `static-analysis` | `ruff check`, `bandit -r ... -ll` |
| `policy-check` *(commented out)* | Planned: `conftest test environments/ --policy policy/` — not yet built. |

## Jobs

| Job | Parameters | Steps |
|---|---|---|
| `pulumi-preview` | `pulumi_stack: string` | checkout → setup-python → lint-code → static-analysis → `pulumi stack select` + `pulumi preview` |
| `pulumi-update` | `pulumi_stack: string` | checkout → setup-python → `pulumi stack select` + `pulumi up --yes --skip-preview` |
| `validate-infrastructure` | `pulumi_stack: string` | checkout → select stack → `PULUMI_STACK=... bats tests/integration/infrastructure.bats` → cleanup kubeconfig (`when: always`) |

`pulumi-update` uses `--skip-preview` safely because the workflow's `requires:` already forces
`pulumi-preview` to succeed first.

## Workflows

### `preview` — triggered by `on-push-main`

```
pulumi-preview(platform-sandbox)
  → "Deploy to platform-sandbox"       [pulumi-update]
    → "Validate platform-sandbox"      [validate-infrastructure]
```

No approval gate — sandbox deploys automatically on every push to `main`.

### `update` — triggered by `on-tag-main`

```
pulumi-preview(platform-sandbox)
  → "Deploy to platform-sandbox (tag)"
    → "Validate platform-sandbox (tag)"
      → [approve-app-dev-deploy]                    ← manual approval
        → "Deploy to app-dev"
          → "Validate app-dev"
            → [Approve prod deploy]                 ← manual approval
              → "Deploy to app-prod"
                → "Validate app-prod"
```

Both approval jobs (`approve-app-dev-deploy`, `approve-prod-deploy`) are declared **only** inline
in this workflow — `type: approval` jobs must never also appear under the top-level `jobs:`
section, or their (never-executed) `steps:` become dead code. See
[why-manual-approval-gates.md](../explanation/why-manual-approval-gates.md).

## Deferred (commented out, not yet built)

- `policy-check` command (OPA/conftest) — waiting on `policy/` and `environments/` directories.
- Flux GitOps reconciliation + smoke test step inside `validate-infrastructure` — waiting on Flux
  being introduced into this project.

## Validating changes to this file

```bash
circleci config validate .circleci/config.yml
circleci config process .circleci/config.yml   # see the fully resolved job graph
```

Always run both after editing — CircleCI's schema has non-obvious constraints (e.g. `context`
is only valid on a job *invocation* inside a workflow, never inside the job's own `jobs:`
definition) that a passing `config validate` will catch even when the YAML looks reasonable.
