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

Report-only review. v0 does not fail the GitHub check. Normative schema: `.github/actions/rubric-gate/schema.json`. Thresholds: ADR-0007. Bench reuse: ADR-0008.

## Run

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/actions/rubric-gate -p 'test_*.py'
python3 .github/actions/rubric-gate/cli.py all --base origin/<base> --out rubric-gate-results
```

Set `RUBRIC_GATE_FETCH_BENCH=never` to skip the GitHub poll. Read `rubric-gate-results/verdict.json`.

## Dimensions

Each score is an integer 0-3 with a non-empty evidence array.

| score | meaning |
|---:|---|
| 3 | meets the bar |
| 2 | gap |
| 1 | must fix |
| 0 | escalate |

| dimension | scorer |
|---|---|
| correctness, tests | affected-build. No product module: 3. Root `pom.xml`: 2. Compile failure: correctness 0. Test failure: tests 0 |
| compat | japicmp on bound modules (`compat/*` listed in `score.py`, `impl/maven-core`). `api/` public or protected signature line: 2, because japicmp is not bound there |
| clarity | minimum of spotless (trailing whitespace, optional `spotless:check`) and comment-density |
| perf | bench-delta. See ADR-0008 |
| security | hard rules below. A failed security rule scores 0 |
| intent | 1 when `action.yml` is added and no `llms.txt` is in the diff, or when an added line contains a banned marker (`score_intent`) |
| architecture | 2 when a path is outside the product tree and outside `docs/`, `.cursor/`, `.github/`, `.mvn/`, `AGENTS.md`, `llms.txt`. New actions only under `build-speedup-bench` or `rubric-gate` |
| determinism | 1 when added Python calls `random.`, `datetime.now(`, or `time.time(`. `time.sleep` is allowed |

Comment-density uses added lines of `.py`, `.java`, `.sh`, `.yml`, `.yaml` after the leading header. Redundant phrases: `this function`, `this method`, `note that`, `it is important`, `please note`. Ratio above 0.45 or any redundant phrase scores 1. Ratio above 0.25 scores 2.

## Hard rules

Any failure yields `ESCALATE`.

| id | failure |
|---|---|
| secrets | added line matches a private key block, `ghp_` plus 20 alphanumerics, `github_pat_`, or `AKIA` plus 16 |
| contents-write | added workflow line grants `contents: write` |
| third-party-push | one added line names apache/maven and also runs a git write or the gh cli create command (`scan_third_party`) |
| report-only | `.github/workflows/rubric-gate.yml` grants `contents: write` or a line is `exit 1` |
| gate-unit-tests | rubric-gate unit tests exit non-zero |

## Thresholds

| condition | verdict |
|---|---|
| any hard rule failed, or any score is 0 | `ESCALATE` |
| every score is 3 | `AUTO_MERGE_OK` |
| any score is 1 or 2, and `loop` is 0 or 1 | `AUTO_FIX` |
| any score is 1 or 2, and `loop` is 2 or more | `ESCALATE` |

`blocking` is always false. `loop` is the number of `AUTO_FIX` attempts already consumed. Maximum fix loops: 2.

## Tie-break

`adr`, `stated_priorities`, `existing_code_pattern`, `prior_verdict`, `simpler_reversible`.

## verdict.json

Required: `schema_version` 1, `verdict` (`AUTO_MERGE_OK`, `AUTO_FIX`, `ESCALATE`), `blocking` false, `loop`, `head_sha`, `base_sha`, `tie_break` (the five names above, in that order), `dimensions` (the nine names), `hard_rules`, `scorers` (`affected-build`, `japicmp`, `spotless`, `comment-density`, `bench-delta`), `llm_hook`.

`llm_hook.enabled` defaults false. Status is `disabled`, `missing_command`, `failed`, or `ok`. When enabled, argv in `llm-hook-command` receives dimension JSON on stdin and may print `{"notes": ["..."]}`. Notes are stored. Scores do not change.

## CI

`.github/workflows/rubric-gate.yml` runs the five scorers in parallel, then merges. The check stays green. Java CI remains the blocking build.
