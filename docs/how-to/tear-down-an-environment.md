# How to: tear down an environment

```bash
export VIRTUAL_ENV=$(pwd)/.venv
export PATH="$VIRTUAL_ENV/bin:$PATH"
pulumi stack select <stack-name>
pulumi destroy
```

Confirm when prompted. This runs each resource's `delete` command in dependency order: roughly,
`kind delete cluster --name <name>` followed by `docker network rm <name> || true`.

## A deliberate contrast worth knowing

Unlike the GitHub repositories managed in the sibling `platform-team-administration` repo — which
are created with `protect=True` specifically so `pulumi destroy` *can't* remove them by
accident — the Kind cluster resources in `platform-core` have **no delete protection**. This is
intentional, not an oversight: these are local, disposable dev/test clusters, not real
infrastructure other teams depend on. Losing one costs you a few minutes to recreate it; the
GitHub repos in the other project are a different risk profile entirely.

If you ever want to add protection to a specific environment (e.g. before letting other people
depend on `app-prod` locally), pass `opts=ResourceOptions(protect=True)` on the relevant resource
in `modules/cluster.py`, the same pattern used in `platform-team-administration/pulumi_repo_create.py`.

## Removing the stack registration entirely

`pulumi destroy` only removes the *resources*. To also remove the stack itself from the backend
(and delete its `Pulumi.<stack>.yaml`):

```bash
pulumi stack rm <stack-name>
```

Only do this if you genuinely don't need the environment anymore — you'll need to redo the whole
[add-a-new-environment-stack.md](add-a-new-environment-stack.md) sequence to bring it back.

## If it's stuck running elsewhere

If `pulumi destroy` reports the stack is locked (an update is "in progress" that isn't really
running anymore — for example, after a terminal was closed mid-`pulumi up`):

```bash
pulumi cancel --yes
```

Then retry the destroy.
