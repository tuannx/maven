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

# ADR-0032 Pull requests skip the Maven site

- status: accepted
- date: 2026-10-13
- decided-by: Java CI run [37329433772](https://github.com/tuannx/maven/actions/runs/37329433772), job steps on the same `ubuntu-latest` and `windows-latest` runners.

## Context

`full-build` runs `mvn verify -Papache-release` and then `mvn site -Preporting` on nine runners. Graphviz is installed only for the site. On that run the site step was 582s of the 1132s `ubuntu-latest` Java 21 job and 759s of the 1719s `windows-latest` Java 25 job. The integration-tests cell was still longer on the unsharded matrix (windows-latest Java 21, 2013s). On the sharded run [38273056619](https://github.com/tuannx/maven/actions/runs/38273056619) the slowest full-build job was 1667s and the slowest integration-tests job was 1613s, so the site sat on the critical path once the suite was split.

## Decision

`mvn site -Preporting` and the Graphviz install run only when `github.event_name == 'push'`. A pull request still runs `mvn verify -Papache-release`.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | keep the site on every full-build cell | 1 | nine runners each spend about ten minutes on a report the pull request does not read |
| B | run the site only on push to master | 3 | the verify cell stays; pull-request full-build drops the measured site step |
| C | drop the site from push as well | 1 | master would no longer fail on a broken reporting render |

## Trade-off

A site-only breakage is invisible until the push to master. Pull-request full-build keeps the verify step. Same runner class, run [37329433772](https://github.com/tuannx/maven/actions/runs/37329433772) versus this pull request's run [38422998169](https://github.com/tuannx/maven/actions/runs/38422998169). The site step and Graphviz install were skipped.

| cell | before verify | before site | before job | after verify | after site | after job |
|---|---:|---:|---:|---:|---:|---:|
| ubuntu-latest, Java 21 | 510s | 582s | 1132s | 304s | skipped | 328s |
| windows-latest, Java 25 | 878s | 759s | 1719s | 882s | skipped | 939s |

The windows-25 job fell 780s with verify flat (878s to 882s), in line with the 759s site step. The ubuntu-21 job fell 804s; verify on that cell also moved from 510s to 304s, so that drop is not the site step alone. On this unsharded run the slowest integration-tests job was 1912s (windows-latest, Java 21) and the slowest full-build job was 939s, so the integration-tests cell stayed the critical path.

## Revisit when

A pull request merges a broken site and the master push is the first failure, or the verify step grows longer than the old verify-plus-site cell.
