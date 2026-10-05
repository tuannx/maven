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

# ADR-0025 Check out the base gate into an empty directory

- status: accepted
- date: 2026-10-12
- decided-by: gate-tighten job [111845512967](https://github.com/tuannx/maven/actions/runs/37334167250/job/111845512967) printed `perf-claim.json: AUTO_MERGE_OK is looser than ESCALATE`. The same command failed locally once `clear_results` marked bench-delta `ok`.

## Context

`git checkout "$BASE_SHA" -- .github/actions/rubric-gate` updates files that exist on the base and leaves files that exist only on the pull request. The job then ran that leftover `tighten.py`. `clear_results` set every scorer status to `ok`, so `perf-claim` passed and the verdict was `AUTO_MERGE_OK` while the fixture expects `ESCALATE`. A local run that scored the fixture the way the unit tests do did not.

## Decision

Delete `.github/actions/rubric-gate` before the base checkout. The tighten job exits 1 when the base tree has no `tighten.py`. `tighten.py` scores fixtures with the same scorer calls as the unit tests, so a skipped bench stays `skipped`.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | keep the overlay checkout and the `ok` status | 0 | job 111845512967 compared a mixed tree and a fake bench status |
| B | empty the directory, fail closed without `tighten.py`, and score like the unit tests | 3 | the base file is the one that runs, and a missing checker is not a pass |
| C | run the pull request's `tighten.py` | 1 | the pull request can delete the check |

## Trade-off

A base that has not yet received `tighten.py` fails the job instead of skipping it. The first pull request that adds the file fails until that file is on the base.

## Revisit when

The base branch of this pull request contains `tighten.py` and the job is green on that SHA.
