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

# ADR-0028 Doctrine advisory cannot auto-merge

- status: accepted
- date: 2026-10-12
- decided-by: base-ref score of PR #17 against the hermetic gate

## Context

PR #17 changes `.github/workflows/redteam-advisory.yml` and `docs/adr/0023-pinned-doctrine-advisory.md`. The base gate scored that diff `AUTO_MERGE_OK`. The diff is a redteam doctrine advisory. Its measurement job reads the owner secret `REDTEAM_DOCTRINE_TOKEN` and exits 1 when the secret is absent. The gate must not ask for that secret.

## Decision

Hard rule `doctrine-advisory` fails when a path contains `redteam` or `pinned-doctrine`, or the patch contains `name: redteam-advisory`. Failure forces `ESCALATE`. The measurement job stays red until the repository owner sets `REDTEAM_DOCTRINE_TOKEN` on an owner-controlled event.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | leave the advisory at `AUTO_MERGE_OK` | 0 | the base-ref score already hid the case |
| B | fail a hard rule on the path and the workflow name | 3 | deterministic, report-only, reversible, and the verdict never carries the secret |
| C | fail the GitHub check | 1 | ADR-0006 keeps the rubric report-only |

## Trade-off

Every redteam or pinned-doctrine diff is `ESCALATE` even when every dimension scores 3. The owner can still merge. Naming `REDTEAM_DOCTRINE_TOKEN` in an ADR does not fail the rule.

## Revisit when

A signed doctrine release replaces the advisory workflow.
