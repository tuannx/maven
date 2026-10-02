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

# ADR-0002 Build cache is opt-in and isolated

- status: accepted
- date: 2026-10-02
- decided-by: ADR-0001. Cache templates live in the action directory and are copied into `.mvn/` only for the `build-cache` scenario, then deleted.

## Decision

`maven-build-cache-extension` 1.2.0 is not committed as a live `.mvn` extension. The bench enables it after the mvn and mvnd baselines and removes it before exit.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | commit `.mvn/extensions.xml` | 0 | contaminates the mvn baseline and Java CI, which copies `.github/ci-extensions.xml` |
| B | copy templates for the cache scenario only | 3 | baselines stay extension-free; the action restores the tree |
| C | skip the cache scenario | 1 | drops the no-change signal (0.43s on run 36996291340) |

## Trade-off

A project that already has those `.mvn` files cannot run the cache scenario until it moves them aside. Agents must not commit either file. See `docs/agents/fast-maven-loop.md`.

## Revisit when

Java CI and the bench agree on one extension file that does not change baseline timings.
