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

# ADR-0029 Same-head spotless for Java or XML

- status: accepted
- date: 2026-10-12
- decided-by: base-ref re-score of PR #4, clarity `no_evidence` when the diff touches Java or XML

## Context

Clarity is `no_evidence` when Java or XML changes and `spotless:check` does not run. A path under `.github/actions/rubric-gate/testdata/repo/` does not start with a product module, so the planner skipped Maven. The same skip hits Java outside `api/`, `impl/`, `compat/`, and `apache-maven/`.

## Decision

A path that contains `testdata/repo/` is selected as the suffix after that marker. When no leaf module matches, `spotless:check` runs on `api/maven-api-core` on that same head. Exit 0 is scored evidence. A missing Maven runner stays `no_evidence`.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | ignore fixture XML and leave an unmatched path as `no_evidence` | 1 | the fixture pom disappears, and other Java still has no spotless run |
| B | map `testdata/repo/` and fall back to `api/maven-api-core` | 3 | every Java or XML diff gets a same-head `spotless:check` result |
| C | add `its/` to the product module list | 1 | ADR-0022 keeps that list to the four reactor tops |

## Trade-off

Fixture XML and Java outside the four tops still run `spotless:check` for `api/maven-api-core`. That is the head's formatter, not a format check of the changed file. The spotless job pays for a Maven run.

## Revisit when

Spotless can check the changed file without a reactor module.
