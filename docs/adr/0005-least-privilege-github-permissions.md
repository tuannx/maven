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

# ADR-0005 Least-privilege GitHub permissions

- status: accepted
- date: 2026-10-02
- decided-by: PR #1 review. Public bench snippet is `contents: read`. Dogfood adds `actions: write` only for step `Upload timing logs`.

## Context

The bench uploads logs. A workflow token that can push is wider than that step.

## Decision

Default token scope is `contents: read`. `actions: write` is granted only on jobs that upload an artifact, and the job comment names that step. `pull-requests: write` is granted only when `sticky-comment` is true, for step `Update sticky pull request comment`. `contents: write` is not used.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | write-all on the workflow | 0 | the token can push and change other workflows |
| B | `contents: read`, plus `actions: write` only on upload jobs | 3 | matches the step that calls `actions/upload-artifact` |
| C | no artifact upload | 2 | the verdict and bench logs leave with the job log only |

## Trade-off

GitHub permissions are job-scoped, so a job that uploads cannot drop `actions: write` for its other steps. The comment names the upload step.

## Revisit when

A step needs `contents: write` or `pull-requests: write` for a reason other than the sticky bench comment.
