---
name: rubric-gate
description: "Score a pull request with the report-only rubric and write verdict.json. Use when reviewing a change or applying AUTO_MERGE_OK, AUTO_FIX, or ESCALATE."
---

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

# rubric-gate

Report-only review. v0 does not fail the GitHub check. Normative schema: `.github/actions/rubric-gate/schema.json`. Thresholds: ADR-0010. Bench reuse: ADR-0008.

## Run

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/actions/rubric-gate -p 'test_*.py'
python3 .github/actions/rubric-gate/cli.py all --base origin/<base> --out rubric-gate-results
```

Set `RUBRIC_GATE_FETCH_BENCH=never` to skip the GitHub poll. Read `rubric-gate-results/verdict.json`.

## Dimensions

Each dimension has `state` and a non-empty evidence array. Only `scored` and `no_evidence` have `score`.

| state | score | threshold |
|---|---|---|
| `scored` | 0-3 | counted |
| `not_applicable` | absent | excluded. Evidence is the path classification |
| `no_evidence` | at most 2 | counted. On a risky path the verdict is `ESCALATE` |

| score | meaning |
|---:|---|
| 3 | measured and meets the bar |
| 2 | gap, or the `no_evidence` cap |
| 1 | must fix |
| 0 | escalate |

| dimension | scorer |
|---|---|
| correctness, tests | affected-build. No product module: `not_applicable`. Root `pom.xml` or `.mvn/maven.config`: `no_evidence`. Maven missing: `no_evidence`. Compile failure: correctness 0. Test failure: tests 0 |
| compat | japicmp on bound modules (`compat/*` listed in `score.py`, `impl/maven-core`). No bound module and no `api/` signature line: `not_applicable`. An `api/` public or protected signature line without a bound run: `no_evidence` |
| clarity | minimum of the applicable spotless and comment-density parts. Java or XML changed and `spotless:check` did not run: `no_evidence`. No added source lines: `not_applicable` |
| perf | bench-delta. No bench sources and no product path: `not_applicable`. Product path and the bench did not run: `no_evidence`. ADR-0008 still reuses the dogfood run when bench sources change |
| security | hard rules below. A failed security rule scores 0 |
| intent | index and banned-marker check, capped at 2 (ADR-0010). 1 when `action.yml` is added and no `llms.txt` is in the diff, or when an added line contains a banned marker (`score_intent`) |
| architecture | path prefix check, capped at 2 (ADR-0010). Evidence names the cap. 2 when a path is outside the product tree and outside `docs/`, `.cursor/`, `.github/`, `.mvn/`, `AGENTS.md`, `llms.txt`. New actions only under `build-speedup-bench` or `rubric-gate` |
| determinism | No added Python: `not_applicable`. 1 when added Python calls `random.`, `datetime.now(`, or `time.time(`. `time.sleep` is allowed |

Comment-density uses added lines of `.py`, `.java`, `.sh`, `.yml`, `.yaml` after the leading header. Redundant phrases: `this function`, `this method`, `note that`, `it is important`, `please note`. Ratio above 0.45 or any redundant phrase scores 1. Ratio above 0.25 scores 2.

## Risky paths

`api/`, `impl/`, `compat/`, `apache-maven/`. Build config: `pom.xml`, `.mvn/`, any path ending in `pom.xml`. A file under `.github/workflows/` whose added lines grant `contents`, `actions`, `pull-requests`, `checks`, `packages`, `security-events`, or `id-token` `write`.

## Hard rules

Any failure yields `ESCALATE`.

| id | failure |
|---|---|
| secrets | added line matches a private key block, `ghp_` plus 20 alphanumerics, `github_pat_`, or `AKIA` plus 16 |
| contents-write | added workflow line grants `contents: write` |
| third-party-push | one added line names apache/maven and also runs a git write or the gh cli create command (`scan_third_party`) |
| report-only | `.github/workflows/rubric-gate.yml` grants `contents: write` or a line is `exit 1` |
| gate-unit-tests | rubric-gate unit tests exit non-zero |
| no-evidence-risky | a dimension is `no_evidence` and the diff has a risky path |

## Thresholds

`not_applicable` is excluded. ADR-0007 is superseded by ADR-0010.

| condition | verdict |
|---|---|
| any hard rule failed, any applicable score is 0, or `no_evidence` on a risky path | `ESCALATE` |
| every applicable score is 3 | `AUTO_MERGE_OK` |
| an applicable score is 1 or 2, and `loop` is 0 or 1 | `AUTO_FIX` |
| an applicable score is 1 or 2, and `loop` is 2 or more | `ESCALATE` |
| no applicable dimension, and `loop` is 0 or 1 | `AUTO_FIX` |
| no applicable dimension, and `loop` is 2 or more | `ESCALATE` |

Architecture and intent are scored and capped at 2, so `AUTO_MERGE_OK` waits on a structural check this gate does not run. `blocking` is always false. `loop` is the number of `AUTO_FIX` attempts already consumed. Maximum fix loops: 2.

## Tie-break

`adr`, `stated_priorities`, `existing_code_pattern`, `prior_verdict`, `simpler_reversible`.

## verdict.json

Required: `schema_version` 2, `verdict` (`AUTO_MERGE_OK`, `AUTO_FIX`, `ESCALATE`), `blocking` false, `loop`, `head_sha`, `base_sha`, `tie_break` (the five names above, in that order), `dimensions` (the nine names), `hard_rules`, `scorers` (`affected-build`, `japicmp`, `spotless`, `comment-density`, `bench-delta`), `llm_hook`.

A dimension requires `state` (`scored`, `not_applicable`, `no_evidence`) and `evidence`. `score` is present for `scored` and `no_evidence`, and absent for `not_applicable`. `no_evidence` is at most 2.

`llm_hook.enabled` defaults false. Status is `disabled`, `missing_command`, `failed`, or `ok`. When enabled, argv in `llm-hook-command` receives dimension JSON on stdin and may print `{"notes": ["..."]}`. Notes are stored. Scores do not change.

## CI

`.github/workflows/rubric-gate.yml` runs the five scorers in parallel, then merges. The check stays green. Java CI remains the blocking build.
