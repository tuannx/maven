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

# ADR-0010 Applicability is not a pass

- status: accepted
- date: 2026-10-02
- decided-by: meta-review of PR #2. Run 36997986388 returned `AUTO_MERGE_OK` because skipped scorers and path heuristics scored 3. Supersedes ADR-0007. Supersedes the unmeasured-product score in ADR-0008. Bench reuse in ADR-0008 stays.

## Decision

A dimension is `scored` (0-3), `not_applicable`, or `no_evidence`. `not_applicable` has no score and is left out of the threshold; its evidence is a path classification. `no_evidence` scores at most 2. On a risky path it fails hard rule `no-evidence-risky` and the verdict is `ESCALATE`. Risky paths are product trees (`api/`, `impl/`, `compat/`, `apache-maven/`), build config (`pom.xml`, `.mvn/`, any `pom.xml`), and a workflow whose added lines grant `contents`, `actions`, `pull-requests`, `checks`, `packages`, `security-events`, or `id-token` `write`. Spotless not run on changed Java or XML is `no_evidence`. Architecture and intent stay at most 2 until a structural check exists; the evidence says so. The LLM hook still cannot raise a score.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | three states; exclude `not_applicable`; cap `no_evidence` at 2; risky `no_evidence` escalates; cap weak heuristics at 2 | 3 | a skip is not a measurement; docs-only stays `AUTO_FIX`; an unrun tool on product code escalates |
| B | keep score 3 and record the skip in evidence | 1 | run 36997986388 treated that evidence as a pass |
| C | score 2 for every skip, including docs-only | 2 | docs-only and product diffs look the same, so the risky-path rule cannot fire |

## Trade-off

`AUTO_MERGE_OK` needs every applicable score at 3. Architecture and intent are always scored and capped, so that verdict waits on a structural check. A docs-only diff is `AUTO_FIX`. A product diff whose Maven, spotless, japicmp, or bench scorer did not run is `ESCALATE`.

## Revisit when

A structural check, or an LLM hook that is allowed to set scores, is tested against the docs-only and product-code golden verdicts.
