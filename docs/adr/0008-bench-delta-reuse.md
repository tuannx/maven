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

# ADR-0008 Bench delta is reused, not re-run

- status: accepted
- date: 2026-10-02
- decided-by: ADR-0001 and ADR-0003. Baseline warm speedup 3.11 is dogfood run 36996291340. The earlier run on the same reactor was 3.16.

## Context

The bench workflow already times the reactor when its own sources change.

## Decision

The bench-delta scorer polls `build-speedup-bench` for the same SHA only when the diff touches `.github/actions/build-speedup-bench/` or `.github/workflows/build-speedup-bench.yml`. Perf is 1 when warm speedup drops more than 15% under 3.11 (floor 2.64). Otherwise a measured run is 3. A product diff that the bench workflow does not build is `no_evidence` (ADR-0010). The poll still runs only when bench sources change.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | invoke the bench action again inside rubric-gate | 1 | adds about two minutes to every PR; duplicates the dogfood |
| B | reuse the dogfood artifact when bench sources change; 15% band | 3 | same numbers, no second timer; 3.11 versus 3.16 sits inside the band |
| C | score 2 on every unmeasured product diff | 1 | `AUTO_FIX` becomes permanent for Java changes and stops meaning a gap |

## Trade-off

A Java change can slow the reactor while this scorer has no measurement. ADR-0010 turns that gap into `no_evidence` on a risky path, which escalates. Java CI still builds.

## Revisit when

The bench workflow runs on product-file PRs without pushing the dogfood job past 10 minutes.
