<!--
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
-->

# ADR-0030 A decision-code edit cannot replay to AUTO_MERGE_OK

- status: accepted
- date: 2026-10-13
- decided-by: base-ref replay of `gate-self-edit.json` on `ebc3dc1ab5` returned `AUTO_MERGE_OK`. ADR-0014.

## Context

`replay_fixture` scores a gaming fixture with fixture replay suppressed. `gate-self-edit` changes `merge.py` so that executing the patch would return `AUTO_MERGE_OK`. No hard rule looked at that path, every applicable score was 3, and the replay verdict was `AUTO_MERGE_OK`. `scan_fixture_replay` then failed every gate-touching diff, including `lying-scope`, whose only failed rule was that replay. The golden for `gate-self-edit` recorded `ESCALATE` because of the recursive failure, not because the diff itself was rejected.

## Decision

Hard rule `decision-edit` fails when a path is gate decision code (`merge.py`, `score.py`, `structure.py`, `cli.py`, `doctrine.py`, `validate.py`, `tighten.py`, `action.yml`, `run.sh`, `schema.json`) or any file under `.github/actions/rubric-gate/testdata/`. Replay of `gate-self-edit` is `ESCALATE`, and that stays the fixture's `expected_verdict`. `lying-scope` expected verdict is `AUTO_FIX`.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | leave the replay at `AUTO_MERGE_OK` | 0 | every gate-touching diff escalates for a fixture that is itself a pass |
| B | fail `decision-edit` and set each fixture's expected verdict to the replay | 3 | the redteam diff cannot be `AUTO_MERGE_OK`; other fixtures are not blamed for it |
| C | fail the GitHub check when decision code changes | 1 | ADR-0006 keeps the rubric report-only |

## Trade-off

A real fix to `merge.py`, a fixture, or `schema.json` is `ESCALATE`. The owner can still merge. `lying-scope` on the gate README is `AUTO_FIX` again: a scope lie is intent score 1 (ADR-0013), not the same signal as a decision-code edit.

## Revisit when

A pull request must edit `schema.json` or `action.yml` and the owner treats `ESCALATE` as a blocker.
