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

# ADR-0033 permissions write-all fails contents-write

- status: accepted
- date: 2026-10-13
- decided-by: `write-all.json` replay on `e6f2dbeac4` before this rule returned `AUTO_MERGE_OK`. Architecture score was 3. ADR-0014.

## Context

`scan_contents_write` fails an added workflow line that matches `contents: write`. `permissions: write-all` grants every scope, including contents write, and that pattern does not match. `check_least_privilege` reads the workflow file on disk, so a patch that adds `permissions: write-all` to an otherwise read-only workflow still scores architecture 3. The fixture path is outside the bench filter, so perf is `not_applicable`. Every applicable score was 3 and every hard rule passed.

## Decision

`contents-write` fails when an added `.yml` or `.yaml` line matches `permissions: write-all`. Evidence is `permissions: write-all added in {path}`. The existing `contents: write` failure string and the pass string `no added contents: write` stay. `write-all.json` expected verdict is `ESCALATE`.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | leave `permissions: write-all` as `AUTO_MERGE_OK` | 0 | a workflow grant wider than `contents: write` is a pass |
| B | fail `contents-write` on `permissions: write-all` | 3 | one pattern, same hard rule, report-only, reversible |
| C | fail the GitHub check on `permissions: write-all` | 1 | ADR-0006 keeps the rubric report-only |

## Trade-off

A workflow that names `write-all` only in a comment or a non-workflow file still passes. Other write aliases (`permissions: write`, per-scope writes already covered by `contents: write`) stay on their current rules. This pull request edits `merge.py` and `testdata/`, so `decision-edit` is `ESCALATE` (ADR-0030).

## Revisit when

GitHub adds a permissions token other than `write-all` that grants contents write without the substring `contents: write`.
