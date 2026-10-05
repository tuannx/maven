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

# ADR-0021 Rescore perf when the bench finishes

- status: accepted
- date: 2026-10-05
- decided-by: rubric-gate on PRs #8, #10, and #12 scored perf `no_evidence` with `bench run still in progress` while the bench job for that same head was still running.

## Context

ADR-0012 bounds the bench poll. When the bound expired and the run had no conclusion, perf became `no_evidence`. A later look at the same head, after the bench finished, could score 3. The verdict depended on which job finished first.

## Decision

An in-progress bench run is not a perf score and does not write `verdict.json`. `rubric-gate-rescore` runs when `build-speedup-bench` completes and scores `github.event.workflow_run.head_sha`, which is that pull request head. A miss and a mismatched `head_sha` stay `no_evidence`.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | keep `no_evidence` at the poll bound | 0 | the same head scored differently on #8, #10, and #12 depending on timing |
| B | defer the verdict and rescore on bench completion | 3 | one head has one perf score, written after its bench has a conclusion |
| C | poll until the bench finishes inside the pull request job | 1 | the job timeout would still cut off a long bench and invent a score |

## Trade-off

The pull request gate check can finish before `verdict.json` exists. The rescore workflow writes it when the bench completes.

## Revisit when

The bench workflow and the gate run as one job, so the speedup is always present before the verdict is written.
