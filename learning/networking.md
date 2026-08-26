# Networking: the utility hookup

Part of the [platform-core learning companion](README.md). Read the
[index](README.md) first for the "three houses, not three rooms" framing
this builds on.

---

## Two addresses, and only one of them is real

Before any house gets built, it needs a utility hookup: a real street
address the power company can find, and a meter number. But *inside* the
house, the electrician also draws up an internal wiring diagram — which
outlet is on which circuit — and that diagram means nothing to anyone
outside the house. Two neighboring houses can both have "Circuit 3" wired
to the kitchen without the slightest conflict, because nobody outside
either house's walls ever needs to reference "Circuit 3" directly.

[`modules/network.py`](../modules/network.py) creates exactly these two
categories of address, and treats them very differently on purpose:

- **`vpcCidr`** — a *real* address on your actual machine's Docker network:
  `10.0.0.0/16` for `platform-sandbox`, `10.1.0.0/16` for `app-dev`,
  `10.2.0.0/16` for `app-prod`. These have to be different per house, the
  same way three houses need three different street addresses.
- **`podCidr` / `serviceCidr`** — the internal wiring diagram. Kubernetes
  invents these purely for its own bookkeeping (which pod talks to which
  service, inside one cluster). Nothing outside that one cluster ever
  routes to them, so every house reuses the identical values
  (`10.244.0.0/16` / `10.96.0.0/12`) with zero conflict.

`ensure_docker_network()` is the literal, one-line equivalent of calling
the utility company and requesting a hookup at a specific address:

```python
return local.Command(
    "docker:net",
    create=f"docker network create {cfg.dockerNetwork} --subnet {cfg.vpcCidr} || true",
    delete=f"docker network rm {cfg.dockerNetwork} || true",
)
```

That `|| true` is a normal idempotency trick — don't treat "the hookup
already exists" as an error worth failing over. But it has a sharp edge
worth discovering yourself before I explain it, because the discovery *is*
the lesson.

<details>
<summary><strong>Predict before reading on:</strong> <code>Pulumi.platform-sandbox.yaml</code> declares <code>vpcCidr: 10.0.0.0/16</code>. If the utility hookup at that address already existed under a <em>different</em> meter number the very first time this command ever ran, what does <code>|| true</code> do to that mismatch on every single call since?</summary>

Run this yourself, right now, on this project's real, live infrastructure:

```console
$ docker network inspect app-dev-net --format '{{json .IPAM.Config}}'
[{"Subnet":"10.1.0.0/16","Gateway":"10.1.0.1"}]

$ docker network inspect platform-sandbox-net --format '{{json .IPAM.Config}}'
[{"Subnet":"fc00:19bf:c38:776c::/64","Gateway":"fc00:19bf:c38:776c::1"},{"Subnet":"172.18.0.0/16","Gateway":"172.18.0.1"}]
```

`app-dev-net` matches its config exactly: `10.1.0.0/16`. But
`platform-sandbox-net` — right now, in this real project, as you read this
— is running on `172.18.0.0/16`, Kind's own default addressing, **not**
the `10.0.0.0/16` the config declares.

Here's the mechanism: `docker network create` fails with an error if a
network by that name already exists — it does **not** silently update an
existing network to match new flags you pass it. `|| true` swallows that
failure so Pulumi doesn't treat "already exists" as a problem. But it
swallows *every* failure that way, including "exists, with the wrong
address." Since `platform-sandbox` was almost certainly the very first
house ever built in this whole project — before `vpcCidr` was even a
config value anyone was checking carefully — the network was created once
under Docker's own default addressing, and every hookup request since has
quietly no-op'd past the mismatch instead of correcting it.

**This is still true right now, unfixed.** Nothing breaks because of it —
pods still get valid addresses — but reading the config file alone would
tell you the wrong subnet, and `pulumi preview` will never flag it as
drift. The general lesson outlasts Docker entirely: **an idempotent
"create if it doesn't already exist" is a different guarantee than "make
reality match this config" — and the gap between them is invisible until
you check by hand, the way you just did.**
</details>

## Writing the blueprint without letting the shell mangle it

`render_kind_config()` builds the actual wiring-diagram document Kind reads
to know which internal addresses to use — a plain YAML file, generated in
memory, before anything touches disk:

```console
$ cat .pulumi/kind/pe-sandbox.yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
networking:
  podSubnet: 10.244.0.0/16
  serviceSubnet: 10.96.0.0/12
nodes:
- role: control-plane
- role: worker
```

Getting that document safely onto disk is a smaller problem with a
genuinely reusable fix. The book's original approach inlined the YAML text
directly into a shell command — and YAML is full of exactly the characters
that break shell parsing: colons, quotes, dashes. A config value containing
any of those could silently corrupt the file being written, or break the
command outright — like handing a contractor a spec sheet where a stray
comma in the address turned "10.0.0.0/16, Suite 2" into two separate,
garbled instructions.

The fix sidesteps the problem entirely rather than trying to escape every
dangerous character correctly:

```python
b64 = base64.b64encode(yaml_content.encode("utf-8")).decode("ascii")
script = f"mkdir -p .pulumi/kind && echo {b64} | base64 -d > {path}"
```

Base64 output is guaranteed to be plain letters, digits, `+`, `/`, and `=`
— nothing a shell could ever misinterpret as a command or a special
character. This is a genuinely common, reusable pattern any time you're
handing structured text through a shell: encode first, decode on the other
side, and the shell never gets a chance to "helpfully" reinterpret your
content.

---

Continue to [**Cluster Provisioning**](cluster-provisioning.md) for what
happens once the hookup exists: actually pouring the foundation.
