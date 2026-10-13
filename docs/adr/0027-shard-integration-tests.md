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

Two samples, same `ubuntu-latest` / `macos-latest` / `windows-latest` runners. PR #8 run [37329433772](https://github.com/tuannx/maven/actions/runs/37329433772) versus this branch runs [38273056619](https://github.com/tuannx/maven/actions/runs/38273056619) and [38422198790](https://github.com/tuannx/maven/actions/runs/38422198790). Job duration is `completed_at` minus `started_at`. The IT span is the first integration-tests `started_at` through the last `completed_at`.

| | #8, 9 jobs | sample 1, 18 jobs | sample 2, 18 jobs |
|---|---:|---:|---:|
| slowest integration-tests job | 2013s (windows-latest, 21) | 1613s (windows-latest, 21, shard 0) | 1575s (windows-latest, 21, shard 0) |
| sum of integration-tests job durations | 12149s | 19098s | 19895s |
| integration-tests span | 6013s | 13005s | 5893s |
| Java CI run wall clock | 6525s | 15357s | 7382s |

The slowest job fell 400s (20%) then 438s (22%). Runner time rose 6949s (57%) then 7746s (64%) because each shard repeats the reactor. Sample 1 wall clock rose because eighteen jobs queued (span 13005s). Sample 2 span was 5893s, under the unsharded span, and wall clock was 7382s, 857s (13%) above the unsharded run. On sample 2 the slowest full-build job was 1724s, above the slowest integration-tests job, because full-build still runs the site.

## Revisit when

A later sample's slowest integration-tests job is above 2013s, the sum of integration-tests durations falls under 12149s, or a shard logs `shared fixture collision`.
