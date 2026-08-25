# How to: troubleshoot the CircleCI self-hosted runner

`.circleci/config.yml`'s jobs run on `resource_class: erikan/local_laptop_runner` — a real
machine you register with CircleCI, not one of its cloud executors. That's required here because
the pipeline creates *persistent* local Kind clusters; a cloud executor would spin up, create a
cluster, and immediately throw it away. See
[why-local-kind-clusters.md](../explanation/why-local-kind-clusters.md) for the full reasoning.

Setting this up correctly took several real, non-obvious fixes. This page is the condensed
runbook.

## Install

```bash
curl -s "https://packagecloud.io/install/repositories/circleci/runner/script.deb.sh?any=true" | sudo bash
sudo apt-get install circleci-runner
```

The `?any=true` query param matters — without it, the install script's OS-detection can reject
distros it doesn't explicitly recognize (this machine runs Linux Mint, which isn't in its default
list, but is Ubuntu-based and works fine once detection is bypassed).

## `runner.name` must NOT contain a slash

The resource class you register in CircleCI's UI/CLI (e.g. `erikan/local_laptop_runner`) *looks*
like it belongs whole in the config file, but it doesn't. The config's `runner.name` field only
accepts `letters, numbers, .()_-, and spaces` — no `/`. Putting the full `namespace/name` there
crashes the service on startup:

```
error: machine: runner.name must contain only letters, numbers, .()_-, and spaces
```

**Fix:** `runner.name` is just the resource-class name *without* the namespace:

```yaml
runner:
  name: local_laptop_runner    # NOT erikan/local_laptop_runner
```

The namespace (`erikan`) is tied to the auth token itself, generated per-namespace on CircleCI's
side.

**A related trap:** the official installer's config template auto-fills `runner.name` with your
machine's **hostname** (e.g. `dell`), which is an entirely different value from the resource
class name and just as wrong. Always check and correct this field explicitly after install —
don't assume the generated default is meaningful.

## `mkdir /home/circleci: permission denied`

**Symptom:** the service crash-loops immediately with this error.

**Cause:** the runner process runs as a dedicated `circleci` system user, whose home directory
(`/home/circleci`) doesn't exist — typically because it was deleted during a previous uninstall
(`sudo rm -rf /home/circleci`) and the package reinstall didn't recreate it.

**Fix:**

```bash
sudo mkdir -p /home/circleci
sudo chown circleci:circleci /home/circleci
sudo chmod 750 /home/circleci
sudo systemctl restart circleci-runner
```

## The task-agent download times out every ~5 minutes

**Symptom:** the service runs and successfully polls `/api/v2/tasks/download` (HTTP 200), but
every cycle ends in:

```
error downloading task agent: could not write file ".../circleci-agent.tmp":
context deadline exceeded (Client.Timeout or context cancellation while reading body)
```

**Diagnosis approach — don't guess, measure.** Download the exact same URL manually with `curl`
and time it:

```bash
time curl -s -o /dev/null "https://circleci-binary-releases.s3.amazonaws.com/circleci-agent/<version>/linux/amd64/circleci-agent"
```

Compare against an unrelated large file (rules out "this one S3 bucket specifically is
throttled") and against `docker info`/`docker network create` (rules out Docker itself):

```bash
time curl -s -o /dev/null "https://download.docker.com/linux/ubuntu/dists/noble/pool/stable/amd64/docker-ce-cli_28.0.1-1~ubuntu.24.04~noble_amd64.deb"
```

If both are slow and inconsistent (tens of KB/s, varying run to run), this is a genuine local
network throughput problem, not a CircleCI-side or config issue — no amount of retrying or
reconfiguring fixes a slow connection.

**Mitigation, not a fix:** set `cache_task_agent: true` under `runner:` in the config, so once a
download *does* succeed, it's reused instead of re-fetched on every restart. Note: this does
**not** mean you can manually pre-place a matching, checksum-verified binary at the expected path
ahead of time — in practice the runner still re-attempts the download regardless of what's
already on disk. The setting only helps after a genuine successful download.

## Ruled out: account credits

CircleCI's docs mention self-hosted runners need at least one credit on the account. Worth
checking (`Organization Settings → Plan Overview`) — but if you're on any paid or free tier with
a non-zero monthly allotment (e.g. the Free plan's 30,000 credits/month), this is not your
problem. Don't spend time here unless the balance is genuinely zero.

## Confirming it's actually connected

Don't rely solely on the CircleCI web UI's Self-Hosted Runners page — check via the CLI directly,
which gives clearer errors:

```bash
export CIRCLE_TOKEN="<a personal API token from app.circleci.com/settings/user>"
circleci runner resource-class list       # run from inside a repo with a GitHub/GitLab/Bitbucket remote
circleci runner instance list erikan/local_laptop_runner
```

`circleci runner instance list` returning "No runner instances found" even after the service is
running cleanly (no crash, correct `runner.name`) means it has never successfully launched the
task-agent — go back to the download-timeout section above.

## The cheapest real test

A minimal throwaway pipeline, pushed on its own branch, confirms end-to-end whether a job
actually gets picked up and runs — a much stronger signal than log-watching:

```yaml
version: 2.1
workflows:
  testing:
    jobs:
      - runner-test
jobs:
  runner-test:
    machine: true
    resource_class: erikan/local_laptop_runner
    steps:
      - run: echo "Hi I'm on Runners!"
```
