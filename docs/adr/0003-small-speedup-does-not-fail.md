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

# ADR-0003 A small speedup does not fail the bench

- status: accepted
- date: 2026-10-02
- decided-by: ADR-0001. Run 36996291340 exited 0 with warm speedup 3.11. The bench emits `::warning::` when warm mvnd is not faster than mvn.

## Decision

The bench job exits 0 when the builds exit 0. A ratio below a laptop run is a warning, not a failure.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | fail under a fixed ratio | 1 | runner noise (2-run median was the average of a pair) fails unrelated commits |
| B | warn, exit 0 | 3 | the published table is the proof; the build result stays the failure signal |
| C | silent exit 0 | 2 | hides a warm run that got slower than mvn |

## Trade-off

A real warmup regression is visible in the table and in rubric-gate perf (ADR-0008), not as a red bench check.

## Revisit when

Two consecutive dogfood runs show warm mvnd slower than host mvn on `ubuntu-latest`.
