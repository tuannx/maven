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

# ADR-0026 Spotless ignores gate fixture XML

- status: accepted
- date: 2026-10-12
- decided-by: rubric-gate run 37334083354 scored PR #4 clarity `no_evidence` / `spotless not run` because the diff contained `.github/actions/rubric-gate/testdata/repo/api/maven-api-core/pom.xml`. Open branches already use ADR-0013 through ADR-0025, so this record is ADR-0026.

## Context

`plan_spotless` treats every `.java` and `.xml` path as a spotless target. A path under the gate fixture tree is not a reactor module, so the plan reason is `no-module` and clarity becomes `no_evidence` even when the same diff's format check already scored the added lines. That `no_evidence` is on a risky `pom.xml` suffix, so the verdict is `ESCALATE`.

## Decision

Paths under `.github/actions/rubric-gate/testdata/` are not spotless targets. Clarity for those lines is the format score from the same diff. A product `.java` or `.xml` path in the same diff still requires `spotless:check`.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | keep every XML path as a spotless target | 0 | the fixture pom made clarity `no_evidence` on the gate pull request that added it |
| B | ignore gate fixture XML and keep the same-diff format score | 3 | deterministic, reversible, and a real module pom still fails closed |
| C | mark all `no-module` XML `not_applicable` | 1 | a hand-written pom outside a module would skip the spotless gap |

## Trade-off

A format break inside the fixture tree is scored by the whitespace check, not by `spotless:check`. Product Java and XML still cannot score 3 without a spotless run.

## Revisit when

The fixture repository no longer contains `.xml` files, or spotless learns a module for that tree.
