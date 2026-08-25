# How to: update dependencies and lint rules

## Adding a Python dependency

Add it to `requirements.txt`, then reinstall into your local venv:

```bash
uv pip install -p .venv -r requirements.txt
```

CI does the same thing fresh on every run via the `setup-python` command in
`.circleci/config.yml` — see [pipeline-reference.md](../reference/pipeline-reference.md).

## Running the lint/static-analysis suite locally

Before pushing, run the exact checks CI runs, so you're not waiting on a CI job to tell you about
a formatting nit:

```bash
export VIRTUAL_ENV=$(pwd)/.venv
export PATH="$VIRTUAL_ENV/bin:$PATH"

black --check --diff __main__.py modules/
mypy __main__.py modules/ --ignore-missing-imports --follow-imports=skip
isort --check-only __main__.py modules/
ruff check __main__.py modules/
bandit -r __main__.py modules/ -ll
```

To auto-fix what can be auto-fixed:

```bash
black __main__.py modules/
isort __main__.py modules/
ruff check --fix __main__.py modules/
```

## Two real gotchas in this exact toolchain

**`mypy` will hang without `--follow-imports=skip`.** By default, mypy follows every import and
type-checks it too — including `pulumi_kubernetes`, which is an enormous auto-generated SDK
(thousands of resource classes). Without this flag, a `mypy` run that should take under a second
can hang indefinitely. Always include `--follow-imports=skip` when running mypy in this repo.

**`isort` and `black` disagree on blank lines around individually-commented imports**, unless
isort is told to use black's formatting profile. This repo's `.isort.cfg`:

```ini
[settings]
profile = black
```

fixes it. If you ever see `isort` and `black --check` fighting each other (one wants a blank line
between two imports, the other wants it removed), check that `.isort.cfg` is present and that
your isort invocation isn't overriding it with a conflicting `--profile` flag.

## Adding a new lint/security tool

Follow the existing pattern in `.circleci/config.yml`'s `commands:` section — either extend
`lint-code` or `static-analysis` with a new `run:` step, or add a new named command if the tool
represents a genuinely separate concern (the way `policy-check` is scaffolded, commented out,
waiting for `policy/`/`environments/` to exist). Always add the corresponding package to
`requirements.txt` in the same change.
