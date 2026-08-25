# Explanation: why infrastructure as code

It's easy to think "infrastructure as code" only applies to cloud resources — VPCs, load
balancers, managed databases. But the underlying idea is broader: **anything with state that
drifts if managed by hand benefits from being described declaratively instead.** A local Kind
cluster and its Docker network qualify just as much as a cloud VPC does.

## Why Pulumi specifically

Pulumi's distinguishing feature versus something like Terraform is that the program is written in
a real, general-purpose language — here, Python — rather than a declarative DSL. That matters
concretely in this repo:

- `__main__.py` maps arbitrary nested config (`app:cluster-info`, `app:network`) onto typed
  dataclasses with a few lines of ordinary Python — no special templating syntax needed.
- `modules/network.py`'s `render_kind_config` builds a YAML document by constructing a plain
  Python dict and calling `yaml.safe_dump` — logic any Python developer already knows, not a
  DSL-specific pattern to learn.
- Default handling (`kind_image: Optional[str] = None`, `wait_seconds: int = 60`) is just
  dataclass defaults, not a separate "variables" mechanism.

None of that is exotic — it's exactly the kind of config-shaping code you'd write for any Python
program. That's the actual argument for Pulumi over a declarative tool: when the interesting
complexity is in *how config gets shaped and validated*, not in the cloud resources themselves, a
general-purpose language pays for itself quickly.

## The honest trade-off

Terraform (HCL) is just as valid a choice, and arguably has a gentler learning curve for someone
who's never touched infrastructure code before — `for_each`/`dynamic` blocks express the same
"loop over config" pattern this repo uses, just declaratively. If an organization already
standardizes on Terraform, that's a perfectly good reason to prefer it here too. Pulumi's win is
specifically the general-purpose-language ergonomics, not some inherent technical superiority.

## `local.Command`: the escape hatch that makes this repo possible

Pulumi has no native resource type for "a Docker network" or "a Kind cluster" — Docker and Kind
aren't cloud providers with a Pulumi plugin. The `pulumi_command` package's `local.Command`
resource is the escape hatch: it wraps an arbitrary shell command as a Pulumi-managed step, with a
paired `create`/`delete` command and a `depends_on` ordering mechanism. `modules/network.py` and
`modules/cluster.py` both lean on this heavily — see
[modules-api.md](../reference/modules-api.md) for exactly how.

This is a useful pattern to recognize in general: when a tool doesn't have first-class support
for something, wrapping the CLI you'd run by hand — with Pulumi tracking its lifecycle — is often
more practical than waiting for (or building) a real provider.
