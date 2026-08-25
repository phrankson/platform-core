# Reference: CLI cheatsheet

Every external command this repo actually uses, grouped by tool.

## Environment setup

```bash
export VIRTUAL_ENV=$(pwd)/.venv
export PATH="$VIRTUAL_ENV/bin:$PATH"
uv venv .venv
uv pip install -r requirements.txt
```

## Pulumi

```bash
pulumi stack ls                          # list stacks and their resource counts
pulumi stack init <name>                 # register a new stack (no config file yet)
pulumi stack select <name>               # switch the active stack
pulumi stack --show-name                 # print the currently selected stack's name
pulumi config set --path <key.path> <v>  # set a nested config value
pulumi preview                           # dry-run diff, changes nothing
pulumi up                                # apply for real (prompts to confirm)
pulumi up --yes                          # apply without prompting
pulumi up --yes --skip-preview           # apply without re-previewing (used in CI, after a separate preview job already ran)
pulumi destroy                           # tear down this stack's resources
pulumi stack rm <name>                   # remove the stack registration entirely
pulumi cancel --yes                      # clear a stuck "update in progress" lock
pulumi stack output                      # list this stack's exported outputs
pulumi stack output <name>               # print one output's value
pulumi stack export --show-secrets=false # dump full resource state as JSON (for inspection)
pulumi up --yes --target-replace <urn> --target-dependents  # force-recreate one resource + its dependents
```

## Kind

```bash
kind get clusters                            # list existing clusters
kind create cluster --name <n> --config <f> --image <img> --wait <n>s
kind delete cluster --name <n>
```

## kubectl

```bash
kubectl config get-contexts                       # list available cluster contexts
kubectl --context kind-<name> get nodes           # check a specific cluster's node status
kubectl cluster-info --context kind-<name>
```

## Docker

```bash
docker info                                       # confirm the daemon is reachable
docker ps -a                                       # list all containers, including stopped
docker network ls
docker network inspect <name>
docker stop <container> [<container> ...]
docker start <container> [<container> ...]
docker logs <container> --tail 30
```

## BATS

```bash
bats tests/integration/infrastructure.bats
PULUMI_STACK=<stack> bats tests/integration/infrastructure.bats
bats --count tests/integration/infrastructure.bats   # parse-only, don't run
```

## Lint / static analysis

```bash
black --check --diff __main__.py modules/
mypy __main__.py modules/ --ignore-missing-imports --follow-imports=skip
isort --check-only __main__.py modules/
ruff check __main__.py modules/
bandit -r __main__.py modules/ -ll
```

## CircleCI

```bash
circleci config validate .circleci/config.yml
circleci config process .circleci/config.yml
circleci runner resource-class list
circleci runner instance list <namespace>/<name>
```
