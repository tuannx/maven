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

# ADR-0020 The gate executes from the base ref

- status: accepted
- date: 2026-10-05
- decided-by: rubric-gate run [37261949361](https://github.com/tuannx/maven/actions/runs/37261949361) on PR #4 returned AUTO_MERGE_OK from that pull request's own `merge.py`.

## Context

`rubric-gate.yml` used `uses: ./.github/actions/rubric-gate` after checking out the pull request. A change to `merge.py`, a scorer, or the workflow could emit its own `AUTO_MERGE_OK`. The same shape applies to `.github/ci-verify-paths.py`: the pull request's copy decided whether Java CI runs verify.

## Decision

The job checks out the pull request head, then `git checkout` of the base SHA restores `.github/actions/rubric-gate`, `.github/workflows/rubric-gate.yml`, and `.github/ci-verify-paths.py` when that blob exists. The diff that is scored is still the pull request head. `pull_request_target` loads this workflow file from the base branch once it is on master; `pull_request` runs the same checkout on this pull request. Decision code from the pull request is never imported. The `gate-self-edit` fixture changes `merge.py` so that running it would write `gate-self-edit-marker` and return `AUTO_MERGE_OK`. After the base checkout, that marker is absent and the verdict is the one the base gate computes from the diff. The base SHA is passed through `env`, not interpolated inside `run:`.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | keep running the pull request's action | 0 | run 37261949361 already returned AUTO_MERGE_OK from the pull request's own gate |
| B | execute decision code from the base SHA | 3 | the pull request's merge.py is replaced before it is imported |
| C | turn the gate check red when the verdict is ESCALATE | 1 | the gate stays report-only; the tighten job is the check that fails |

## Trade-off

`pull_request_target` is the event that selects the base workflow file. Permissions stay `contents: read`. The pull request tree is still checked out so the diff and the product files are the ones under review.

## Revisit when

GitHub grows a pull_request mode that always loads workflow files from the base ref.
