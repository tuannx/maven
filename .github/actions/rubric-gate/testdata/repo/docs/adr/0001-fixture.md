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

# ADR-0001 Fixture

- status: accepted
- date: 2026-10-05
- decided-by: hermetic golden fixture

## Context

The golden verdict must not count ADR files in the live checkout.

## Decision

This tree holds exactly one ADR besides the template.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | live repo | 0 | an unrelated ADR changes the golden |
| B | frozen tree | 3 | the count stays at one |

## Trade-off

The fixture is a second copy of the template headings.

## Revisit when

The architecture check stops counting ADR files.
