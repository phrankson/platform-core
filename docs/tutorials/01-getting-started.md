# Tutorial 1: Getting started

By the end of this tutorial you'll have a working local environment and will have seen Pulumi
compute a real plan against this repo — without changing anything on your machine yet. That
matters: `pulumi preview` is completely safe. It's the tool telling you what it *would* do, not
doing it.

## Prerequisites

You'll need these installed already: `git`, `docker`, `pulumi`, `kind`, `kubectl`, `bats`, and
[`uv`](https://docs.astral.sh/uv/) (a fast Python package/venv manager). If you're missing one,
install it before continuing — this tutorial doesn't cover installing the tools themselves.

Check Docker is actually running:

```bash
docker info
```

If that fails, start Docker before continuing — everything downstream depends on it.

## Step 1: Clone and set up the Python environment

```bash
git clone https://github.com/phrankson/platform-core.git
cd platform-core
uv venv .venv
uv pip install -r requirements.txt
```

`requirements.txt` installs the Pulumi SDK plus the Kubernetes and local-command provider
packages this program uses, and the lint/security tools (`black`, `mypy`, `isort`, `ruff`,
`bandit`) the CI pipeline runs on every change.

## Step 2: Point your shell at the virtual environment

Pulumi needs to know which Python interpreter has these packages installed. Unlike a plain
`source .venv/bin/activate`, this repo's `Pulumi.yaml` doesn't declare a `virtualenv:` path, so
you activate it manually for each new terminal session:

```bash
export VIRTUAL_ENV=$(pwd)/.venv
export PATH="$VIRTUAL_ENV/bin:$PATH"
```

Confirm it worked:

```bash
which python3
# should print .../platform-core/.venv/bin/python3, not a system path
```

## Step 3: Select an environment (a "stack")

This repo manages three separate environments, each called a Pulumi **stack**:
`platform-sandbox`, `app-dev`, and `app-prod`. Start with the safest one:

```bash
pulumi stack select platform-sandbox
```

## Step 4: Preview

```bash
pulumi preview
```

If everything's already deployed, you'll see `Resources: 6 unchanged` — Pulumi found nothing to
do. If this is a completely fresh setup, you'll instead see a plan to create 6 resources (a
Docker network, a Kind config file, the cluster itself, its kubeconfig, and the Kubernetes
provider). Either way: **nothing was created or changed**. `pulumi preview` only computes and
prints a diff.

## What you just did

You didn't create any infrastructure — that's the point of this first step. You now have a
working Python environment wired to Pulumi, and you've seen the tool reason about this repo's
actual state without touching anything. Continue to
[Tutorial 2](02-deploy-and-verify-a-cluster.md) to actually deploy something.
