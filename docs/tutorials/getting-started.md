# Getting started

This tutorial takes you from a fresh clone to a successful `pulumi
preview` against the real, currently-deployed infrastructure. By the end
you'll have a working local setup and have seen exactly what this project
manages.

## Prerequisites

- [Pulumi CLI](https://www.pulumi.com/docs/install/)
- [uv](https://docs.astral.sh/uv/)
- [Docker](https://docs.docker.com/get-docker/)
- [Kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- A Pulumi Cloud access token exported as `PULUMI_ACCESS_TOKEN`

## Step 1: Clone the repository

```console
$ git clone https://github.com/phrankson/platform-core.git
$ cd platform-core
```

## Step 2: Install Python dependencies

This project manages its own virtual environment with `uv`:

```console
$ uv venv .venv
$ source .venv/bin/activate
$ uv pip install -r requirements.txt
```

## Step 3: Select a stack

This project has three stacks — `platform-sandbox`, `app-dev`, and
`app-prod` — each a fully separate local Kubernetes cluster. Select the
sandbox stack, the one meant for exactly this kind of exploration:

```console
$ pulumi stack select platform-sandbox
```

## Step 4: Preview the current state

```console
$ pulumi preview
```

If the sandbox stack is already deployed (it is, in this project), you
should see something like:

```console
Previewing update (platform-sandbox)

Resources:
    8 unchanged
```

`8 unchanged` means Pulumi checked the Docker network, the Kind cluster,
and the Argo CD installation this stack manages, and found no drift —
reality matches what's declared, with nothing to change.

If you're running this against a stack that hasn't been deployed yet,
`pulumi preview` will instead show what *would* be created — a Docker
network, a Kind cluster, an Argo CD Helm release, and a root Argo
`Application`. See [Deploy a stack](../how-to/deploy-a-stack.md) to
actually create it.

## What you've done

You now have a working local setup that can read the true state of a real,
independent local Kubernetes cluster, without having changed anything.
From here:

- To deploy a stack for real, see [Deploy a stack](../how-to/deploy-a-stack.md).
- To understand every config field you just previewed against, see the
  [configuration schema reference](../reference/config-schema.md).
