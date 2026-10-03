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

# ADR-0006 Rubric gate v0 is report-only

- status: accepted
- date: 2026-10-02
- decided-by: this change. Java CI (`.github/workflows/maven.yml`) stays the blocking verify. The bench stays non-failing on ratio (ADR-0003).

## Context

Java CI already fails the build. A second failing check would duplicate it.

## Decision

`.github/actions/rubric-gate` writes `verdict.json` and a job summary. `blocking` is false. Scorer steps and the merge step exit 0 for `AUTO_FIX` and `ESCALATE`. An optional LLM hook is off unless `llm-hook` is true, and its notes cannot change scores.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | failing check on `AUTO_FIX` | 1 | blocks product PRs before the scorers have a baseline of false failures |
| B | report-only, hook cannot change scores | 3 | the verdict is reproducible; Java CI still blocks a broken build |
| C | LLM scores are the verdict | 0 | not deterministic |

## Trade-off

A bad verdict does not turn the GitHub check red. Readers use the job summary and `rubric-verdict` artifact. Unit-test failure is recorded as hard rule `gate-unit-tests` and still exits 0.

## Revisit when

Two merged PRs in a row shipped with verdict `ESCALATE` that Java CI did not catch.
