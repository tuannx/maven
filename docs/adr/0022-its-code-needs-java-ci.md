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

# ADR-0022 Code under its/ needs Java CI evidence

- status: accepted
- date: 2026-10-05
- decided-by: PR #8 changes Java under `its/core-it-support/maven-it-helper/src/main/java` and the gate reported `no product modules in the diff` with correctness `not_applicable`.

## Context

`plan_affected` treats only `api/`, `impl/`, `compat/`, and `apache-maven/` as product modules. A Java change under `its/` skipped Maven, so correctness and tests were `not_applicable` and the missing run was not risky.

## Decision

Code under `its/` (`.java`, `.kt`, `.groovy`, `.scala`, `.py`, `.js`, `.ts`, `.sh`) plans `mvn -f its/pom.xml test`. If that run is missing, correctness and tests are `no_evidence`. Those paths are risky, so the verdict is `ESCALATE`. A markdown file under `its/` stays `not_applicable`.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | leave `its/` as no product module | 0 | PR #8 changed helper Java and correctness did not apply |
| B | require a Java CI result for code under `its/` | 3 | the same no-evidence rule as a product module, without treating a README as code |
| C | add `its/` to the product module list | 1 | the IT tree is not a reactor module the affected-build `-pl` list already knows |

## Trade-off

The gate job runs `mvn -f its/pom.xml test` when the diff contains that code. A missing Maven binary is `no_evidence`, not a skip.

## Revisit when

Java CI publishes a check that the gate can read without starting another Maven run.
