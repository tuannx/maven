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

# ADR-0034 its/ Java is covered without a spotless run

- status: accepted
- date: 2026-10-14
- decided-by: PR #8 scored clarity `no_evidence` because `plan_spotless` selects no module for `its/` Java. ADR-0026 already keeps non-reactor fixture XML off that plan and uses the format score.

## Context

`discover_modules` lists only `api/`, `impl/`, `compat/`, and `apache-maven/`. Java under `its/` therefore takes the `no-module` plan, and clarity becomes `no_evidence`. The its reactor parent is `org.apache:apache`, so it does not inherit the Maven parent's spotless execution. `its/core-it-suite` stores a spotless configuration under `pluginManagement` and does not bind the goal. Invoking `spotless:check` there exits non-zero without a format result.

## Decision

Java and XML only under `its/` are covered. The spotless plan does not call Maven. Clarity uses the same-diff format score and records `its/ covered`. A product `.java` or `.xml` path in the same diff still requires `spotless:check`.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | keep `no_evidence` for every `its/` Java path | 0 | the fixture pull request cannot raise clarity without editing the scorer |
| B | run `mvn -f its/pom.xml spotless:check` | 1 | the goal is not bound, so the exit is not a format result |
| C | cover `its/` with the same-diff format check | 3 | matches ADR-0026, leaves product Java fail-closed, and does not format fixture sources |

## Trade-off

Palantir format and license headers on `its/` Java are not checked. Trailing whitespace is. A product path beside an `its/` path still cannot score 3 without `spotless:check`.

## Revisit when

The its reactor binds `spotless-maven-plugin`, or a second non-product tree needs the same coverage.
