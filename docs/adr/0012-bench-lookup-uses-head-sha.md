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

# ADR-0012 Bench lookup uses the pull request head SHA

- status: accepted
- date: 2026-10-03
- decided-by: rubric-gate run 37138710060. bench-delta queried merge SHA 4e4978c17149387c6251c1a32a937d6c7ff02342 for ten minutes and reported `bench run not found`. The bench run 37138710037 is indexed at head SHA 10687883fa84d3c2d19de0e326ba08c875457554. Supersedes the merge-SHA poll and the product `no_evidence` sentence in ADR-0008.

## Context

`actions/checkout` on `pull_request` leaves `GITHUB_SHA` and `git rev-parse HEAD` on the merge commit. `workflow_runs` for `build-speedup-bench` is indexed by `github.event.pull_request.head.sha`. Polling the merge SHA cannot find the run.

## Decision

bench-delta queries `build-speedup-bench` with `github.event.pull_request.head.sha`, and with `github.sha` when the event is not a pull request. The action passes that value as `RUBRIC_BENCH_SHA`. It does not fall back to `GITHUB_SHA`. If the diff matches no `pull_request` path in `.github/workflows/build-speedup-bench.yml`, perf is `not_applicable` and the client does not call the API. If the filter matches, the client polls at most 13 times and sleeps 20 seconds only between attempts. A success whose `head_sha` differs from `RUBRIC_BENCH_SHA` is `no_evidence` and does not score 3. When the bound ends without a matching success, perf is `no_evidence` and the evidence is the last reason. The artifact zip redirect is fetched without the bearer token, because the blob host rejects that header.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | keep polling `GITHUB_SHA` for 30 attempts | 1 | run 37138710060 waited 609 seconds and still had no measurement |
| B | head SHA, no poll on a path-filter miss, bounded wait, reject a mismatched `head_sha` | 3 | the dogfood run is found by the SHA GitHub indexes; a miss returns in one response; a stuck run stops inside four minutes |
| C | fail the check when the bench run is absent | 1 | the gate is report-only, and a path-filter miss is not a failed measurement |

## Trade-off

A product diff no longer marks perf `no_evidence`. Correctness, compat, clarity, and tests still escalate that diff when Maven did not run. A bench-source diff whose run is still going after the bound is `no_evidence` instead of a ten-minute wait.

## Revisit when

`build-speedup-bench` regularly takes longer than the poll bound, or GitHub indexes pull request workflow runs by the merge SHA.
