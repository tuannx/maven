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

# build-speedup-bench

Composite action that wall-clocks a Maven reactor and writes a markdown table to the job summary.

Measured goal is `package` on the POM you pass (`mvn -f`), with `--batch-mode -q`. Default skips are tests, RAT, Checkstyle, and Enforcer. Scenarios:

- `mvn`: N timed `clean package` runs (default 2). Median is the baseline.
- `mvnd`: one cold daemon `clean package`, then N warm runs (default 2).
- `build-cache`: opt-in `maven-build-cache-extension` 1.2.0 on `mvnd`. Templates are copied into `.mvn/` only for this segment and deleted before the action exits. Seed, no-change rebuild, mtime touch, restore after deleting `target/`, one-line source edit restored afterward.

An untimed `mvn clean package` seeds `~/.m2` first and is excluded from the ratio table.

The action does not fail when warm `mvnd` is slower than `mvn`. That case is a warning annotation. It does not change the Maven sources under test.

Agent contract: [llms.txt](llms.txt).

## Copy

`v1` is a moving tag cut on `master` after this action is merged. Until that tag exists, pin a commit SHA instead of `@v1`.

```yaml
permissions:
  contents: read
  actions: write

steps:
  - uses: actions/checkout@v7
  - uses: tuannx/maven/.github/actions/build-speedup-bench@v1
    with:
      pom: pom.xml
```

Same-repo dogfood uses `uses: ./.github/actions/build-speedup-bench` with `pom: api/pom.xml`.

Give the job at least 45 minutes. The check name is whatever `name:` you set on the job; this repo's dogfood job is `build-speedup-bench`.

## Inputs

| Input | Default | Role |
|---|---|---|
| `pom` | `pom.xml` | `-f` reactor POM |
| `scenarios` | `mvn,mvnd,build-cache` | Comma-separated subset |
| `maven-version` | `3.9.11` | Host Maven. Central `.sha512` is checked |
| `mvnd-version` | `1.0.6` | Daemon. Cache scenario uses it |
| `mvnd-sha256` | empty | Required for versions other than 1.0.6/linux-amd64 when the release has no `.sha256` |
| `mvn-runs` | `2` | Timed host `mvn` runs |
| `mvnd-warm-runs` | `2` | Timed warm `mvnd` runs after one cold run |
| `threads` | `1C` | `-T` |
| `extra-maven-args` | `-DskipTests -Drat.skip=true -Dcheckstyle.skip=true -Denforcer.skip=true` | Whitespace-separated. No spaces inside one argument |
| `java-version` | `21` | Used when `setup-java` is true |
| `java-distribution` | `temurin` | `actions/setup-java` distribution |
| `setup-java` | `true` | Set `false` if the job already has a JDK |
| `touch-file` | empty | File for mtime touch and one-line edit. Empty picks the first `src/main/java` file under the POM |
| `upload-logs` | `true` | Artifact of `bench-logs/` (14 days) |
| `artifact-name` | `build-speedup-bench-logs` | Artifact name |
| `sticky-comment` | `false` | One PR comment, updated in place. Needs `pull-requests: write` |

## Outputs

| Output | Example | Empty when |
|---|---|---|
| `mvn-median-seconds` | `12.98` | `mvn` not run |
| `warm-mvnd-seconds` | `4.26` | `mvnd` not run |
| `warm-mvnd-speedup` | `3.04` | Baseline or warm median missing. Number only, no `x` |
| `cache-no-change-seconds` | `0.44` | Cache scenario not run |
| `summary-path` | `bench-logs/summary.md` | Never, after the measure step |

## Permissions

| Permission | When |
|---|---|
| `contents: read` | Checkout of the project under test |
| `actions: write` | `upload-logs` true (the default) |
| `pull-requests: write` | `sticky-comment` true only |

## Not in scope

- Failing the job because the speedup is small
- Enabling the build-cache extension outside the cache scenario
- Changing Apache Maven product source, or opening PRs on `apache/maven`
- Running tests or the core IT suite (default skips tests)
- Creating the `v1` tag
