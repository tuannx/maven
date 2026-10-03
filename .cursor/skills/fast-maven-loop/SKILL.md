---
name: fast-maven-loop
description: "Run one Maven module with mvnd from its aggregator POM. Use when iterating on api, impl, or compat without a full verify."
---

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

# fast-maven-loop

Iterate on one module. Do not run root `mvn verify` or `its/` for an edit loop. Java release is 17.

## Command

Use the aggregator POM, then `-pl` the artifact. `-am` from that aggregator builds its reactor dependencies.

```bash
mvnd -f api/pom.xml -pl maven-api-core -am test --batch-mode -T 1C -DskipITs -Drat.skip=true -Dcheckstyle.skip=true -Denforcer.skip=true
```

| tree | aggregator | example `-pl` |
|---|---|---|
| api | `api/pom.xml` | `maven-api-core` |
| impl | `impl/pom.xml` | `maven-core` |
| compat | `compat/pom.xml` | `maven-model` |

Do not run `mvn -pl api -am` from the root POM. If `mvnd` is absent, use the same arguments with `mvn`.

## Cache

Do not commit `.mvn/extensions.xml` or `.mvn/maven-build-cache-config.xml`. The bench refuses to start when either file exists (ADR-0002). Java CI replaces `.mvn/extensions.xml` from `.github/ci-extensions.xml`.

Warm `mvnd` is the edit loop. Build-cache no-change on `api/` was 0.43s against a 12.74s mvn median (run 36996291340). Measure with `build-speedup-bench`. Do not leave the extension installed.

## Wrong tool

Root `pom.xml` or `.mvn/maven.config`: Java CI, `.github/workflows/maven.yml`, `./mvnw verify`. Core ITs under `its/` are that workflow, not this loop.
