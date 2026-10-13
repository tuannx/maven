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

# ADR-0031 A missing tighten.py is verdict evidence

- status: accepted
- date: 2026-10-13
- decided-by: base-ref rule `report-only` on PR #14 at `226a1a8230` failed with `rubric-gate workflow exits 1`. ADR-0006. ADR-0025.

## Context

ADR-0025 exits 1 when the base tree has no `tighten.py`. `scan_report_only` treats a line that is `exit 1` in `.github/workflows/rubric-gate.yml` as a report-only failure. The missing file is a real signal. The workflow text fails the rule even on a base that has `tighten.py`, because the scanner reads the line, not the branch that ran.

## Decision

Hard rule `tighten-missing` fails when `RUBRIC_TIGHTEN_MISSING`, action input `tighten-missing`, or `rubric-gate-results/tighten-missing.txt` is non-empty. The evidence is that text. The workflow step exits 0. `tighten.py` still returns non-zero when a pull request gate loosens a fixture.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | keep `exit 1` in the workflow | 0 | ADR-0006: the line fails `report-only` even when `tighten.py` exists |
| B | carry the text on `tighten-missing` and exit 0 | 3 | a missing checker still escalates; the step stays report-only |
| C | skip the check when the file is absent | 1 | a base without `tighten.py` would score the pull request's own gate |

## Trade-off

An empty input is a pass, so a workflow that forgets to pass it looks the same as a base that has `tighten.py`. The loosen check remains a failed job, which is the check ADR-0020 left allowed to fail.

## Revisit when

Every open pull request's base contains `tighten.py` and the input stays empty.
