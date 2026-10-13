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

# ADR-0024 Score a stacked pull request from its base SHA

- status: accepted
- date: 2026-10-12
- decided-by: rubric-gate run [37334083354](https://github.com/tuannx/maven/actions/runs/37334083354). The verdict `base_sha` was `19266313127cb010e49dc4c467bbb35b8ce5c6c8` while PR #4 targets `cursor/hermetic-golden-1127`.

## Context

The workflow passed `origin/${{ github.base_ref || 'master' }}`. On that run `github.base_ref` was `master`, so the three-dot diff included the hermetic commits. `tests-weakened` then reported the assertion line those commits had rewritten. A pull request whose base is another branch must not be scored as if its base were master.

## Decision

The diff base and the recorded `base_sha` are `github.event.pull_request.base.sha` when that SHA is present. The action reads it from `RUBRIC_EVENT_BASE_SHA` and uses it instead of the `base` input. `workflow_dispatch` still uses the `base` input.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | keep `origin/master` when `base_ref` is empty or master | 0 | run 37334083354 scored PR #4 against master |
| B | prefer `pull_request.base.sha` for the diff | 3 | the SHA is the base GitHub stored for that event, including a stacked branch |
| C | refuse pull requests whose base is not master | 1 | stacked reviews are how this fork lands the gate |

## Trade-off

The job must have that SHA in the local git history. A `workflow_dispatch` run has no pull request base and still needs an explicit ref.

## Revisit when

GitHub stops populating `pull_request.base.sha` for a pull request whose base is not the default branch.
