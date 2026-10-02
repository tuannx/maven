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

# ADR-0007 Verdict thresholds

- status: accepted
- date: 2026-10-02
- decided-by: prior verdict on PR #1 was `AUTO_FIX` with tests at 1 and other dimensions at 2 or 3. Tie-break order is stated in `AGENTS.md`.

## Decision

Hard-rule failure or any dimension at 0 yields `ESCALATE`. All nine dimensions at 3 yields `AUTO_MERGE_OK`. Any 1 or 2 yields `AUTO_FIX` while `loop` is 0 or 1, and `ESCALATE` when `loop` is 2 or more.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | all 3s to merge; 0 escalates; else fix for two loops | 3 | matches the prior verdict's treatment of a 1, and stops the fix loop |
| B | minimum 2 merges | 2 | a 2 would have merged the bench before tests existed |
| C | any score under 3 escalates immediately | 1 | no fix loop; every gap pages a human |

## Trade-off

A single 2 blocks `AUTO_MERGE_OK` until the loop count runs out. v0 does not block the GitHub check either way (ADR-0006).

## Revisit when

A dimension stays at 2 on every PR because a scorer cannot reach 3. Change that scorer, not this table.
