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

# ADR-0017 Integration tests run affected modules when the diff is inside them

- status: accepted
- date: 2026-10-05
- decided-by: Java CI run 37256530986. `integration-tests (ubuntu-latest, 21)` ran `mvn install -Prun-its,mimir` from 2026-10-05T03:10:45Z to 2026-10-05T03:30:24Z (19m39s). The workflow ran from 2026-10-05T02:43:49Z to 2026-10-05T03:47:25Z (63m36s).

## Context

A pull request that edits one product module still runs the core IT suite on nine matrix cells. The rubric gate already plans `mvn -f <aggregator> -pl <module> -am test` for that diff and does not run it in Java CI.

## Decision

On a pull request, the integration-tests job asks `.github/affected-modules.py` which mode to use. A diff that stays inside `api/`, `impl/`, or `compat/` modules runs those planned test commands with the Maven distribution this workflow just built. A diff that touches `its/`, `.github/`, `.mvn/`, `apache-maven/`, the root `pom.xml`, or no product module keeps `mvn install -Prun-its,mimir`. A push to master keeps the full command. An unreadable diff keeps the full command. The sample workflow times one `maven-api-core` command so this pull request has an after number while its own workflow change still takes the full path.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | always run the IT matrix | 1 | the ubuntu/21 cell is already 19m39s when the diff is one module |
| B | `-pl` only when every path is inside a product module; otherwise the full IT command | 3 | module edits skip the suite; workflow, IT, and root edits still run it |
| C | skip the IT job for every pull request | 0 | a change under `its/` would never run |

## Trade-off

A product change that the selector accepts does not run the core IT suite on that pull request. The full-build matrix is unchanged. This pull request changes `.github/workflows/maven.yml`, so its own integration-tests job stays on the full command.

## Revisit when

An affected-module pull request fails a core IT that the selector skipped, or the sample `maven-api-core` command is not shorter than the 19m39s cell.
