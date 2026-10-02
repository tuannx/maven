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

# ADR-0011 Structural checks can score 3

- status: accepted
- date: 2026-10-02
- decided-by: meta-review of PR #2 after ADR-0010. The cap at 2 made `AUTO_MERGE_OK` unreachable and left `AUTO_FIX` with nothing to change. Supersedes that cap. ADR-0010 still defines `not_applicable` and `no_evidence`.

## Context

ADR-0010 required every applicable score to be 3 and then capped architecture and intent at 2.

## Decision

`docs/adr/boundaries.yml` lists path groups (`agent-contract`, `ci`, `product`), the reactor dependency direction, and the workflow write markers. For an agent-contract or ci diff, architecture is 3 when index paths resolve, skill mirrors match, every ADR matches `docs/adr/template.md`, every new `action.yml` is indexed, and changed workflows grant `write` only with a marker from that file. For a product diff, architecture is 3 when each affected module pom stays inside `dependency_direction`. A failure is score 1 and the evidence is the fix. Intent is 3 when the pull request body has one `scope:` line and every changed path is in a named group. If architecture or intent is `not_applicable` or `no_evidence`, the verdict is `ESCALATE`.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | boundaries file plus the checks above; unmeasured architecture or intent escalates | 3 | a pass is a measurement; a gap names the file to change; an unknown path does not spin the fix loop |
| B | keep the ADR-0010 cap at 2 | 1 | `AUTO_MERGE_OK` cannot happen, and `AUTO_FIX` has no edit that raises the score |
| C | drop architecture and intent from the all-3s rule | 1 | that relaxes the threshold the review refused to relax |

## Trade-off

The write-scope marker is anywhere in the workflow file, because this check does not embed a YAML parser. A diff outside the three path groups escalates until `boundaries.yml` gains a group. `its/` is outside those groups.

## Revisit when

A fourth path group is required on more than one pull request, or a workflow grants `write` in a job that does not contain the marker.
