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

# ADR-0004 Agent contracts live in llms.txt and AGENTS.md

- status: accepted
- date: 2026-10-02
- decided-by: root `llms.txt` indexes this fork. Action contracts stay next to each action. `AGENTS.md` is the coding-agent entry point.

## Context

Agents need one index and one contract, and each action needs its own contract beside the code.

## Decision

Machines read `AGENTS.md` first, then root `llms.txt` for the index, then the action `llms.txt` for inputs and outputs. Human notes stay in each action `README.md`.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | README only | 1 | agents that load `llms.txt` or `AGENTS.md` miss the contract |
| B | `llms.txt` per action plus a root index and `AGENTS.md` | 3 | one adopt snippet, one coding contract, no second copy of the input tables |
| C | paste the full contract into every file | 0 | the copies drift |

## Trade-off

A new action is invisible until root `llms.txt` gains a line. Rubric-gate intent scores that gap as 1.

## Revisit when

A third action is added and the root index no longer fits on one screen.
