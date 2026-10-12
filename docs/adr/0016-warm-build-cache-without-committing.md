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

# ADR-0016 Warm the build cache without committing it

- status: accepted
- date: 2026-10-05
- decided-by: ADR-0002. Bench run 36996291340 on `api/pom.xml` measured an mvn median of 12.74s and a build-cache no-change rebuild of 0.43s. The extension files were copied for that segment and deleted before the action exited.

## Context

`maven-build-cache-extension` 1.2.0 speeds a no-change rebuild only while `.mvn/extensions.xml` and `.mvn/maven-build-cache-config.xml` are installed. ADR-0002 forbids committing either file, because a live extension changes the bench baseline and Java CI's copy of `.github/ci-extensions.xml`.

## Decision

`.github/warm-build-cache.py` copies the bench templates into `.mvn/` for one `api/maven-api-core` measurement and deletes those two files before it returns. It refuses to start when either file is already present. The job records cold seconds (no extension) and warm seconds (package after a cache seed). A warm run that is not faster does not fail the job. A run that leaves the files, or that does not populate `~/.m2/build-cache`, fails.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | commit `.mvn/extensions.xml` | 0 | ADR-0002: it contaminates the baseline and Java CI |
| B | copy the templates for the measured run, then delete them | 3 | same files as the bench, and the worktree does not keep them |
| C | skip a separate measurement and cite only run 36996291340 | 1 | the numbers exist, but this repository would not show that the files were removed |

## Trade-off

The job builds `maven-api-core` three times (cold, seed, warm). It does not change Java CI's verify. A project that already has those `.mvn` files cannot use this entry point until it moves them aside.

## Revisit when

Java CI and this job share one extension file that does not change the bench baseline.
