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

# ADR-0014 Replay gate fixtures on a gate-touching diff

- status: accepted
- date: 2026-10-12
- decided-by: rubric-gate run [37334083354](https://github.com/tuannx/maven/actions/runs/37334083354) on PR #4. `gate-self-edit` expected `AUTO_MERGE_OK`. ADR-0013.

## Context

`gate-self-edit` changes `merge.py` so that executing the patch would return `AUTO_MERGE_OK`. The fixture recorded that verdict. A later edit of the gate can keep that result while the diff is the code that produces it. Cache writes without `hashFiles(` and `uses:` refs that are not a commit SHA scored the same way when every dimension was 3.

## Decision

A diff that touches `.github/actions/rubric-gate/` or `.github/workflows/rubric-gate.yml` replays the gaming fixtures inside the verdict. Replay that returns `AUTO_MERGE_OK` fails hard rule `fixture-replay`. `gate-self-edit` expects `ESCALATE`. An added cache use without `hashFiles(`, or a committed `.mvn` cache extension, fails `cache-poisoning`. An added `uses:` ref that is not 40 hex characters, or a pom dependency block with no version, fails `unpinned-dependency`.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | leave `gate-self-edit` at `AUTO_MERGE_OK` | 0 | the fixture is the diff a gate edit can hide behind |
| B | replay fixtures as a hard rule and fail the two supply-chain diffs | 3 | the verdict cannot be `AUTO_MERGE_OK` for those cases; the check stays report-only |
| C | fail the GitHub check when the gate directory changes | 1 | ADR-0006 keeps the rubric report-only |

## Trade-off

Every gate-touching diff is `ESCALATE` while any fixture replays to `AUTO_MERGE_OK`. A real test fix under `.github/actions/rubric-gate/` takes the same verdict. The owner can still merge.

## Revisit when

Fixture replay no longer finds an `AUTO_MERGE_OK`, or the gate stops executing decision code from the tree under review.
