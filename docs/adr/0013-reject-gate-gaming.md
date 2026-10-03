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

# ADR-0013 Reject gate gaming

- status: accepted
- date: 2026-10-03
- decided-by: `build_verdict` on 89bb6a0c26 before these rules. hidden-py, hidden-class, hidden-jar, hidden-sh, forged-verdict, tests-weakened, tests-deleted, and perf-claim were `AUTO_MERGE_OK`. hidden-java was `AUTO_FIX`. lying-scope was `AUTO_FIX`. lying-scope on a product path was `ESCALATE` because Maven was missing.

## Context

Path groups are prefixes. A `.py`, `.class`, `.jar`, or `.sh` file under `docs/agents/`, `docs/adr/`, or `.cursor/skills/` is agent-contract, every applicable score can be 3, and the verdict is `AUTO_MERGE_OK`. A committed `verdict.json` is ignored and the gate writes a fresh one. Deleting a test file or removing an assertion still passes `gate-unit-tests` when the remaining tests exit 0. A speedup claim in the pull request body is ignored when bench-delta is `not_applicable`.

## Decision

Four hard rules fail closed. `hidden-code` fails when a path under `docs/` or `.cursor/` ends in `.java`, `.xml`, `.py`, `.class`, `.jar`, `.sh`, or is named `pom.xml`. `forged-verdict` fails when the diff contains `verdict.json` (a `*-verdict.json` golden does not match). `tests-weakened` fails when a test file is deleted or an assertion line is removed and not re-added verbatim. `perf-claim` fails when the pull request body matches `warm-mvnd-speedup` or `speedup` followed by a number and bench-delta status is not `ok`. A `scope:` line that leaves a path out stays intent score 1 (`AUTO_FIX`). Fixtures and the golden verdicts live under `.github/actions/rubric-gate/testdata/gaming/`.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | hard rules for the four cases that reached `AUTO_MERGE_OK`; lying scope stays score 1 | 3 | a hard-rule failure is `ESCALATE` even when every dimension is 3; the scope fix is still to name the missing group |
| B | score each attack 1 and leave the verdict at `AUTO_FIX` | 1 | loop 0 and 1 would still say `AUTO_FIX` with nothing in the dimensions to edit |
| C | drop `docs/` and `.cursor/` out of the agent-contract prefixes | 1 | ADR markdown would become an unclassified path and escalate every contract pull request |

## Trade-off

Editing an assertion, including a real test fix, is `ESCALATE`. The gate stays report-only, so the owner can still merge. A committed `verdict.json` fails even when its `head_sha` and `base_sha` match, because this run writes that file and does not read one from the diff.

## Revisit when

A product pull request must change an assertion and the owner treats `ESCALATE` as a blocker, or the Java CI path filter starts skipping a suffix this rule does not list.
