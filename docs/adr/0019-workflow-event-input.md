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

# ADR-0019 Flag pull_request_target and untrusted run input

- status: accepted
- date: 2026-10-05
- decided-by: `.github/workflows/pr-automation.yml` is the one `pull_request_target` workflow. It calls a reusable workflow and has no `run:` step and no `actions/checkout`. A scan of `run:` blocks found no `${{ github.event.* }}` or `${{ github.head_ref }}` interpolated into the script. `rubric-gate.yml` passes the pull request body through `env` and `toJson`.

## Context

`pull_request_target` runs with the base repository's token. A `run:` script that interpolates `${{ github.head_ref }}` or pull request text executes that text as shell. Passing the same value through `env` does not.

## Decision

`.github/workflow_security.py` fails the workflow when a file uses `pull_request_target` unless it contains `workflow-security: reusable-workflow-only`, has no `run:` script, and does not checkout the repository. It also fails when a `run:` script's `${{ }}` expression contains pull request, issue, comment, review, or head ref data. `pr-automation.yml` keeps the event and carries the marker. Before this check the unmarked `pull_request_target` count is 1 and the untrusted `run:` count is 0. After it, both counts are 0.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | leave the event unexamined | 1 | one workflow already runs as `pull_request_target` with a write token in the called workflow |
| B | fail the scan on an unmarked `pull_request_target` or untrusted `run:` interpolation, and mark the reusable-only caller | 3 | the existing caller does not run pull request code; a new `run:` interpolation fails |
| C | delete `pr-automation.yml` | 1 | drops milestone and label automation to avoid a scan |

## Trade-off

The marker is an exception for one reusable caller. A later edit that adds `run:` or `actions/checkout` to that file fails the scan until the event is removed.

## Revisit when

The reusable workflow starts checking out the pull request head, or a workflow needs event text in a `run:` script.
