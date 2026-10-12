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

# ADR-0027 Shard integration tests across runners

- status: accepted
- date: 2026-10-12
- decided-by: Java CI run 37261000352. The `Build Maven and ITs and run them` step on ubuntu-latest Java 21 was 805s, and `Maven Core ITs suite` inside it was 09:02. `its.forkCount` stays `0.75C` (ADR-0015). Open branches already use ADR-0016 through ADR-0026, so this record is ADR-0027.

## Context

Each integration-tests cell runs the reactor and then the core IT suite on one runner. The suite already forks at `0.75C`. Raising that count shares `target/test-classes` more widely. ADR-0015 copies only `mng-0095`. A second failsafe process in the same workspace would also share Jetty ports.

## Decision

The integration-tests matrix gains `shard` `0` and `1`. Both pass `-Dits.shard` and `-Dits.shardCount=2`. `IntegrationTestShardFilter` keeps a `MavenIT` class when `floorMod(className.hashCode(), count)` equals the shard. Unset properties run every class. One property without the other, or a shard outside `0..count-1`, throws. `its.forkCount` stays `0.75C`.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | leave one suite process per cell | 1 | ubuntu-latest Java 21 already spent 09:02 in the suite after a ~4 minute reactor |
| B | two runners, same fork count, hash shard | 3 | no shared fixture directory or port, and every class stays on exactly one runner |
| C | set `forkCount` to `1C` in the one cell | 0 | ADR-0015 already rejected more sharing of the fixture tree |

## Trade-off

Each shard repeats the reactor build. Eighteen integration-tests jobs can queue behind the hosted runner cap, so the workflow wall clock may fall by less than the cell median. A class moves shards when its name changes.

## Revisit when

A cell median is still above the pre-shard median after run, or a shard logs `shared fixture collision`.
