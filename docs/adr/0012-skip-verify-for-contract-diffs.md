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

# ADR-0012 Skip verify for contract diffs

- status: accepted
- date: 2026-10-03
- decided-by: Java CI run 37021463700 on master (push of c9f9f2d576, 2026-10-02T14:40:07Z to 2026-10-02T15:24:53Z, 44m46s, success). That workflow has no path filter, so a docs-only pull request pays the same `./mvnw verify`.

## Context

`.github/workflows/maven.yml` runs `./mvnw verify` on every pull request to master. A change that touches only the agent contract or an ADR does not change the reactor. The rubric gate is a separate workflow and must keep running.

## Decision

A `path-filter` job runs `.github/ci-verify-paths.py`. `initial-build` runs only when that job sets `verify=true`. The allowlist is `AGENTS.md`, `llms.txt`, `SECURITY.md`, `docs/adr/boundaries.yml`, and `*.md` under `docs/` or `.cursor/skills/`. A push, an empty diff, or a diff git cannot read still verifies. The script reads `GITHUB_BASE_REF` from the environment and rejects a ref that is not a branch name. Code under `docs/` does not match the allowlist, so verify still runs.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | stdlib suffix allowlist in the workflow, fail closed | 3 | no third-party action; a `.java` file under `docs/` still builds; reversible by deleting the job |
| B | a third-party paths filter action | 0 | this fork does not take workflow steps from another repository |
| C | skip verify for every path under `docs/` | 1 | `docs/adr/Hidden.java` would skip the build |

## Trade-off

`docs/adr/boundaries.yml` skips verify. It is data for the gate, not a reactor input. A pull request that also changes `.github/workflows/maven.yml` still verifies, so this change does not skip its own build. `rubric-gate.yml` is not on this branch yet; when it merges it keeps its own trigger.

## Revisit when

A contract path outside the allowlist shows up on more than one pull request, or the docs-only proof run no longer skips `initial-build`.
