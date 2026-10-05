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

# ADR-0018 Pin third-party actions to a commit SHA

- status: accepted
- date: 2026-10-05
- decided-by: `.github/workflows/release-drafter.yml`, `pr-automation.yml`, and `stale.yml` used `apache/maven-gh-actions-shared` at `@v5`. That name is a branch. Its tip on 2026-10-05 is `12e8b4cf8a92af0af4f4e203cc9ff2c46fdb5fd3`. `actions/*` uses in this repository were already 40-hex SHAs.

## Context

A moving branch ref runs whatever commit the upstream branch points at the next time the workflow starts. This fork does not publish tags, and it does not open changes on `apache/maven-gh-actions-shared`.

## Decision

Those three `uses:` lines pin `@12e8b4cf8a92af0af4f4e203cc9ff2c46fdb5fd3` and keep a `# v5` comment. `.github/test_action_pins.py` fails when a workflow `uses:` ref is not a 40-hex SHA. A local `uses: ./...` action is not a remote ref.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | keep `@v5` | 1 | three workflow calls follow a branch that moved on 2026-10-04 |
| B | pin the three calls to the current branch tip and reject any new unpinned `uses:` | 3 | the ref stops moving, and the count of unpinned uses goes from 3 to 0 |
| C | vendor the shared workflows into this repository | 1 | copies three upstream files this fork does not maintain |

## Trade-off

The pin does not float forward when `v5` gains a fix. Updating it is a new commit in this repository. The comment records which branch tip was pinned.

## Revisit when

`v5` changes and this fork needs that commit, or a workflow adds a `uses:` ref that is not 40 hex characters.
