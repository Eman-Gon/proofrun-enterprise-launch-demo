# Flagship demo: the release before the big meeting

Allow 6–7 minutes. The enterprise customer and meeting are fictional. Use the
actual execution result when describing a run. The repository's reference fix
is prepared; a fresh ProofRun proposal can be called generated only when that
run records model provenance and verification.

## 0:00 — The release matters

Show the candidate at port 8080.

“I'm the engineer preparing an enterprise onboarding update. Our customer
presentation starts in thirty minutes. The new feature lets the team preview
an entire CSV of customers, validate each row, and catch duplicates before
import. Before we roll out that update, we need to know what happens to the
customer imports that already work.”

## 0:45 — Show the real new feature

Choose the ordinary CSV sample and select **Preview import**. Show ready rows
and summary counts. Compare the baseline tab, where CSV preview is unavailable.

“Here is the feature the customer is waiting for. The candidate can preview
multiple records and identify problems before import. The existing release
handles customers one at a time.”

## 1:20 — The existing checks pass

Show the ordinary suite's actual output or the replay receipt. The baseline
has its original HTTP tests; the update adds feature tests. The original tests
and new numeric-CSV tests are green on the update.

“The existing checks pass, and the new feature works with the team's sample
data. We use ProofRun to investigate whether the release preserves the customer
import contract at the same time.”

For an actual ProofRun run, use the generated registry and request. Its contract
is general response preservation for the existing import endpoint. If presenting
the local replay instead, say “This is the operator-selected comparison replay.”
A replay is not evidence that a model independently discovered these inputs.

## 2:00 — Successful response, changed customer identifier

On baseline, use the legacy-ID preset (`00123`) and run the import. Repeat the
same request on the candidate. Point to the requested and returned identifiers.

“The current release returns the identifier unchanged. The update reports
success but changes 00123 into 123. A real integration could now fail to match
that record to the customer's existing account. The local demo is stateless;
what we have measured is an incompatible response.”

Use the partner-ID preset (`abc-123`) on both versions.

“A second valid customer record used to work, and now the update rejects it.
The feature's shared normalization helper changed an existing workflow.”

## 3:00 — Reproduce and inspect

Show the recorded request/response comparison, revision IDs, and the narrow
source diff at `northstar/customers.py`. A real ProofRun result can also show
repeated experiments, scope, hypothesis, and runtime verdict.

“We can inspect the exact requests, the versions tested, and the source change.
The new preview reuses a helper that converts identifiers into integers. That
loses leading zeros and rejects mixed-format identifiers.”

## 4:00 — Preserve the feature while fixing the regression

Open the reference-fixed version at port 8082. Repeat both customer imports,
then preview the ordinary CSV again. If desired, preview a CSV containing both
`00123` and `123`: they should remain distinct IDs.

“The correction preserves identifiers as strings. Both existing customer
formats work again. The new CSV preview still works, including validation and
duplicate detection. We preserve the feature and restore compatibility.”

“This reference repair is prepared. In a fresh generated-repair investigation,
we show the actual proposed patch and the verifier's result separately.”

## 5:00 — Decide on the original release

Show an actual release verdict when available. Otherwise show the replay's
before/after matrix and explain the engineer's decision, without fabricating a
ProofRun UI status.

“The original candidate still contains the regression. Passing checks on a
repaired copy gives us a correction to review and recheck; it does not change
the original commit or perform a deployment.”

## 5:45 — Close

“We began with an important feature, passing tests, and a customer meeting
approaching. Now the engineer knows what broke, how to reproduce it, and how to
preserve the new feature while restoring the customer contract.”

“Before you ship the feature everyone is waiting for, find out what it breaks.”

## Recording notes

Keep baseline, candidate, and fixed browser tabs labeled by their visible
release badges. Record a rehearsal before the presentation. If live provider
access is unavailable, show that state and explicitly switch to a dated recorded
run or the deterministic local replay. Avoid presenting an older successful run
as new execution. The public repository scan is a useful optional add-on after
the main release story.
