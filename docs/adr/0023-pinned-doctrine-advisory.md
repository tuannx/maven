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

# ADR-0023 Pinned doctrine advisory measurements

- status: proposed
- date: 2026-10-05
- decided-by: owner request to update personal forks and measure each improvement; doctrine fork validation at 0ee5a2e48f16c5e3274fceb1f6c390a10aaaedb2

## Context

The fork's rubric is report-only. The doctrine's combined staging commit includes proposed fixes for package installation, stale verdicts and lesson lifecycle, but has no owner-signed release or attestation. The existing rubric and Java CI remain the fork's native checks. Open fork PRs reserve ADR-0013 through ADR-0022; this proposal avoids their numbers and files.

## Decision

Add a separate read-only advisory workflow that uses the exact staging SHA with comments disabled, runs the same base/head pair twice, verifies both schemas and SHA bindings, and publishes hashes, counters, applicability and measured adapter durations.

## Options

| id | option | score | why |
|---|---|---:|---|
| A | replace the rubric with a blocking unsigned gate | 0 | contradicts the accepted report-only contract and missing signed release |
| B | separate pinned advisory workflow | 3 | reuses existing CI, read-only permissions and artifact publication; reversible |
| C | moving doctrine branch and a single run | 1 | cannot bind changes to one tool revision or observe repeatability |

These option scores describe contract fit, not measured runtime or improvement scores.

## Trade-off

Two adapter invocations include setup and package installation overhead. A source BLOCK is recorded without authorizing enforcement; missing, invalid or mismatched evidence still fails the measurement job. Python F821 is the only wired symbol checker. Java, red/green tests, architecture and owner identity verification remain unsupported or notRun in the doctrine verdict. The pinned Action currently calls setup-python at v5 internally; the workflow records the installed environment rather than claiming a fully locked dependency graph.

## Revisit when

The owner merges the doctrine fixes and publishes a signed release with consuming policy and attestation, or hosted measurements expose a reproducible compatibility or determinism failure.
