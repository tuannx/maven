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

# ADR-0001 Bench is a composite action

- status: accepted
- date: 2026-10-02
- decided-by: `.github/actions/build-speedup-bench` on PR #1. Dogfood run [36996291340](https://github.com/tuannx/maven/actions/runs/36996291340).

## Context

Callers need the same timing run the dogfood workflow already performs.

## Decision

Wall-clock measurement is a composite action callers invoke with `uses`, dogfooded by `.github/workflows/build-speedup-bench.yml` on `api/pom.xml`.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | steps inlined in one workflow | 1 | agents copy a long workflow; outputs stay local |
| B | composite action | 3 | one `uses` line; dogfood runs the same code; outputs are step outputs |
| C | reusable workflow | 2 | separate run; harder to append the table to the caller job summary |

## Trade-off

Callers must check out the repo first. The action refuses to start when `.mvn/extensions.xml` or `.mvn/maven-build-cache-config.xml` already exists.

## Revisit when

A caller needs a matrix of POMs in one job that composite steps cannot express.
