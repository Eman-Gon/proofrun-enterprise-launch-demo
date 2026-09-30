# Northstar CRM — the release before the big meeting

A complete synthetic release demo for **ProofRun**. An engineer is about to
present an enterprise onboarding update. The release adds a real **CSV import
preview** with row validation, duplicate detection, and readiness counts.
The existing tests pass, but shared customer-ID handling breaks existing imports.

**Intentionally vulnerable to correctness regressions. Synthetic records only.
This is a local demonstration, not a production CRM.** It stores no records,
uses no external services, and needs no credentials to run.

## Three real revisions

| Ref | Product behavior | Purpose |
| --- | --- | --- |
| `v1.0.0` | Existing single-customer import; identifiers preserved | Working baseline |
| `v1.1.0-rc1` / `main` | Adds CSV preview; shared ID normalization introduces a regression | The important update under review |
| `v1.1.0-fixed` / `codex/reference-fix` | Keeps CSV preview and restores identifier preservation | Prepared reference repair |

The fixed revision is a prepared example, not an AI-generated patch. Git history
contains the actual feature change and repair. The default branch deliberately
keeps the release candidate's bug available for demonstrations.

## Run it

Requires Python 3.12. No packages need installing.

```bash
git clone https://github.com/Eman-Gon/proofrun-enterprise-launch-demo.git
cd proofrun-enterprise-launch-demo
python3.12 -m northstar --port 8080
```

Open [Northstar CRM](http://127.0.0.1:8080). Preview the ordinary sample CSV to
show the new feature. Then use the existing customer-import presets to show
what the update breaks. Every displayed result comes from the local API.

For side-by-side versions, create separate checkouts and run each command in
its own terminal:

```bash
git worktree add --detach ../northstar-baseline v1.0.0
git worktree add --detach ../northstar-fixed v1.1.0-fixed
# In ../northstar-baseline:
python3.12 -m northstar --port 8081
# In ../northstar-fixed:
python3.12 -m northstar --port 8082
```

## The reveal

The [product contract](docs/product-contract.md) treats identifiers as opaque
strings. The update reuses a numeric-normalization helper across old and new
flows, causing two customer-visible regressions:

| Customer ID | Baseline | Release candidate | Reference fix |
| --- | --- | --- | --- |
| `12345` | HTTP 201; `12345` | HTTP 201; `12345` | HTTP 201; `12345` |
| `00123` | HTTP 201; `00123` | HTTP 201; **`123`** | HTTP 201; `00123` |
| `abc-123` | HTTP 201; `abc-123` | **HTTP 422** | HTTP 201; `abc-123` |
| Two ordinary CSV records | Feature unavailable | 2 ready | 2 ready |

The reference fix retains the feature. It does not roll back the release.
CSV records with identifiers `00123` and `123` also illustrate why interpreting
identifiers as numbers can create a false duplicate.

## Reproduce the entire demonstration

```bash
python3.12 scripts/verify-demo.py
```

The replay exports the three exact Git revisions into fresh temporary working
directories under `.demo-results/`, runs their ordinary tests and real local
HTTP checks, and saves logs and a receipt. The original checkout stays intact.
It returns success only when the expected broken candidate and working repair
are both reproduced, including preservation of the new CSV feature.

These are **operator-selected checks**, without model calls. They do not claim
an autonomous ProofRun investigation, staging verification, or a deployment.
The complete script is inspectable under `scripts/`.

The intentionally incomplete ordinary suite remains green:

```bash
python3.12 -m unittest discover -s tests -v
```

The additional contract checks expose the regression on the candidate:

```bash
python3.12 -m unittest discover -s checks -v
```

A passing ordinary suite is part of the story, not a declaration that the
candidate is correct. Do not weaken assertions to make the contract checks pass.
GitHub Actions runs the ordinary suite and a replay that expects the deliberate
regression. A green workflow means the demo behaves as documented.

## Use this repository with ProofRun

Use ProofRun's **release investigation** for the flagship baseline-versus-update
story. Public repository scanning inspects the default-branch source and is a
separate flow; pasting a URL does not configure two executable releases.

With Docker running and a trusted Python 3.12 image available locally:

```bash
docker pull python:3.12-slim
python3.12 scripts/configure-proofrun.py \
  --image "$(docker image inspect python:3.12-slim --format '{{.Id}}')"
```

The helper writes a local target registry and release request, resolving full
commit IDs from the tags and pinning the execution image by immutable ID.
It excludes walkthroughs, reference checks, and replay scripts from the agent's
snapshot while retaining the actual product contract, source, and ordinary tests.

In your separate [ProofRun checkout](https://github.com/Eman-Gon/ProofRun), with
its dependencies installed and authorized `OPENROUTER_API_KEY` / `PROOFRUN_MODEL`
already in the process environment, use the generated files:

```bash
python3.12 -m src.proofrun.release_api \
  --targets /absolute/path/to/proofrun-enterprise-launch-demo/.demo-results/proofrun-config/targets.json \
  --once /absolute/path/to/proofrun-enterprise-launch-demo/.demo-results/proofrun-config/request.json \
  --artifacts /absolute/path/to/a-new-evidence-directory
```

Use a new artifact directory per run. Model availability and decisions may vary;
read the actual result. A verified repair is separate from the original release
recommendation. The setup helper creates configuration only and does not launch
a model, install dependencies, modify an existing worker, or deploy the app.

## Present it

[Presenter script](docs/DEMO.md) contains the launch story and exact actions.
The customer and commercial stakes are fictional; the feature and HTTP behavior
are runnable. This project is intentionally small so the audience can inspect
the whole change. It makes no claim of exhaustive or production-scale coverage.
