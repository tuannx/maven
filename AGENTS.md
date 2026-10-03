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

# AGENTS.md

Fork: `tuannx/maven`. Do not open pull requests, issues, or comments on apache/maven. Do not open them on any other third-party repository. Do not create tags or GitHub releases.

Index: `llms.txt`.

## Principles

Binding on every added file:

- No redundant text.
- Deterministic behavior.
- Names carry meaning.
- Comments only for a non-obvious why.
- Architecture holds at each step.
- Non-trivial decisions go to `docs/adr/` with context, options, decision, decided-by, trade-off, and revisit-when.
- Near-tie order: ADR, stated priorities, existing code pattern, prior verdict, simpler or reversible.

## Build

Product modules: `api/`, `impl/`, `compat/`, `apache-maven/`. Java release 17.

```bash
mvnd -f <aggregator>/pom.xml -pl <artifactId> -am test --batch-mode -T 1C -DskipITs -Drat.skip=true -Dcheckstyle.skip=true -Denforcer.skip=true
```

Aggregator is `api/pom.xml`, `impl/pom.xml`, or `compat/pom.xml`. Do not `-pl api -am` from the root POM. Do not commit `.mvn/extensions.xml` or `.mvn/maven-build-cache-config.xml`.

Procedure: `docs/agents/fast-maven-loop.md`.

Full verify is `.github/workflows/maven.yml` (`./mvnw verify`), not the edit loop. Core ITs are `its/`.

## Layout

| path | role |
|---|---|
| `AGENTS.md` | this contract |
| `llms.txt` | index |
| `docs/adr/` | decisions |
| `docs/agents/` | skills for any agent |
| `.cursor/skills/` | same skills, Cursor frontmatter |
| `.github/actions/build-speedup-bench/` | wall-clock bench |
| `.github/actions/rubric-gate/` | report-only rubric v0 |
| `.github/workflows/maven.yml` | blocking verify |

## Rubric

Report-only. Dimensions: correctness, intent, compat, security, perf, architecture, clarity, determinism, tests. Each is `scored` (0-3), `not_applicable` (excluded), or `no_evidence` (at most 2). `no_evidence` on a risky path is `ESCALATE`. Unmeasured architecture or intent is `ESCALATE`. `AUTO_MERGE_OK` when every applicable score is 3. `AUTO_FIX` when an applicable score is 1 or 2 and `loop` is under 2. Otherwise `ESCALATE`. Architecture and intent are measured from `docs/adr/boundaries.yml` (ADR-0011). Code under `docs/` or `.cursor/`, a committed `verdict.json`, a deleted or edited test assertion, or a speedup claim without a bench run is `ESCALATE` (ADR-0013). A `scope:` line that leaves a path out scores intent 1. `blocking` is false.

Procedure: `docs/agents/rubric-gate.md`.

## ADR

The next ADR goes in `docs/adr/` and copies `docs/adr/template.md`, before the code that depends on it. Procedure: `docs/agents/write-adr.md`.

## Security

Read `SECURITY.md` and the threat model it links before reporting a vulnerability.
