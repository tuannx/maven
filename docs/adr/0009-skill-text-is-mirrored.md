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

# ADR-0009 Skill text is mirrored and checked

- status: accepted
- date: 2026-10-02
- decided-by: ADR-0004. Cursor loads `.cursor/skills/*/SKILL.md` only when frontmatter is the first bytes. Other agents read `docs/agents/`.

## Context

Cursor reads frontmatter skills. Other agents read plain markdown. The two copies can drift.

## Decision

`docs/agents/<name>.md` is the body. `.cursor/skills/<name>/SKILL.md` is YAML frontmatter plus that body. `test_skill_mirrors` fails when they differ.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | one file, linked from both places | 2 | Cursor does not load `docs/agents` as a skill |
| B | two bodies, test-locked | 3 | both loaders see the procedure; drift fails CI |
| C | two bodies, untested | 0 | redundant text that will diverge |

## Trade-off

A procedure edit touches two paths. The test is the check. The frontmatter is the only extra text.

## Revisit when

Cursor loads a skill from an arbitrary markdown path. Delete the `.cursor/skills` copy.
