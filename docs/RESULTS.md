# Measured release demo

Rehearsed September 30, 2026 UTC (September 29 Pacific), using Python 3.12.2 and
actual local HTTP applications. The [machine-readable summary](verification.json)
preserves exact revisions, requests, responses, repeated observations and suite
counts. This is an operator-selected replay, not a model investigation.

| Version | Commit | Ordinary suite | Frozen original suite | Selected compatibility checks | CSV preview |
| --- | --- | --- | --- | --- | --- |
| Baseline | `2faecc5f99c1` | 14 passed | 14 passed | IDs preserved | Not available |
| Release candidate | `641de102d613` | 24 passed | 14 passed | `00123` changes; `abc-123` rejected | 2 records ready |
| Reference fix | `6ffbc6b9f4c8` | 24 passed | 14 passed | IDs preserved | 2 records ready |

The two separate acceptance checks both pass on baseline and reference-fixed
source. On the candidate, the leading-zero assertion fails and the partner-ID
check raises a validation error. These failures are intentional and retained.
The existing baseline test files are unchanged in both later revisions.

Browser rehearsal confirmed that the release candidate previews two CSV records,
visibly reports the successful-but-changed identifier, and displays HTTP 422 for
the partner account. The baseline preserves the legacy ID and disables CSV
preview. The fixed browser version preserves the legacy ID and previews all
three legacy/partner sample records successfully. All response cards use actual
API responses.

The generated registry and request were also validated with ProofRun's real
configuration schema, then the three exact snapshots were exercised through
its actual Docker test and HTTP runtime. All ordinary suites passed, the same
candidate regressions were reproduced, and the reference fix retained CSV
preview. That separate [runtime receipt](runtime-verification.json) records
immutable image IDs, isolated network execution, read-only source mounts and
the independent HTTP collector. These checks were operator-selected with zero
model calls; they do not establish an autonomous agent discovery.

The reference fix changes the ID helper and release label. It retains the new
CSV endpoint, preview implementation and ten feature tests. It is prepared
source, not an AI-generated repair. No staging system or production deployment
was involved.

Run `python3.12 scripts/verify-demo.py` to collect a fresh local receipt. The
script exits successfully only when the complete documented story is reproduced,
including the candidate's deliberate failures. A successful replay or green
workflow is not a passing compatibility verdict for the candidate.
