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

# ADR-0015 Isolate the mng-0095 fixture per test

- status: accepted
- date: 2026-10-05
- decided-by: Java CI run 37140931251 failed `MavenITmng3004ReactorFailureBehaviorMultithreadedTest.testitFailFastSingleThread` and `MavenITmng0095ReactorFailureBehaviorTest.testitFailAtEnd` because `its/core-it-suite/target/test-classes/mng-0095/target/touch.txt` was missing. Run 37138710025 failed `testitFailAtEnd` because `subproject3/target/touch.txt` was present. Master run 37021463700 and re-run 37256530986 passed the same jobs. `its.forkCount` is `0.75C` and both classes call `extractResources("mng-0095")`.

## Context

`extractResources` returns `maven.test.tmpdir` plus the resource path and does not copy files. The IT POM sets that directory to `target/test-classes`, which every failsafe fork shares. The two reactor-failure classes delete and rebuild `target/` inside that one tree.

## Decision

`mng-0095` is copied into `it-fixtures/<test class>.<test method>.<instance>/mng-0095` for each test instance. A second call from the same instance returns that copy. Every other resource path still returns the shared directory. The shared `target/test-classes/mng-0095` tree is not modified.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | leave the shared tree | 0 | the two tests already failed in opposite directions on runs 37140931251 and 37138710025 |
| B | copy `mng-0095` per test instance | 3 | the callers stay the same, repeats inside one test keep their edits, and other fixtures stay put |
| C | set `forkCount` to 1 for the whole IT suite | 1 | removes parallelism for every IT to protect one fixture |

## Trade-off

A new test that calls `extractResources("mng-0095")` pays for a copy and must not expect to see another test's `target/` files. Callers of every other fixture still share one directory.

## Revisit when

A second fixture fails the same way, or failsafe stops running these classes in parallel.
