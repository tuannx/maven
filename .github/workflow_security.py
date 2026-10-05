#!/usr/bin/env python3

#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

"""Flag pull_request_target and untrusted ${{ }} inside run: scripts. ADR-0019."""

import re
import sys
from pathlib import Path

MARKER = "workflow-security: reusable-workflow-only"
GATE_FROM_BASE = "workflow-security: gate-from-base"
EXPRESSION = re.compile(r"\$\{\{(.+?)\}\}")
UNTRUSTED = (
    "github.head_ref",
    "github.event.pull_request",
    "github.event.issue",
    "github.event.comment",
    "github.event.review",
    "github.event.commits",
    "github.event.head_commit",
    "github.event.inputs",
    "github.event.client_payload",
    "github.event.discussion",
    "github.event.workflow_run",
)


def run_scripts(text):
    scripts = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        body = stripped[2:].strip() if stripped.startswith("- ") else stripped
        if not body.startswith("run:"):
            index += 1
            continue
        rest = body[4:].strip()
        if rest in ("|", ">", "|-", ">-", "|+", ">+"):
            base = len(line) - len(line.lstrip(" "))
            block = []
            index += 1
            while index < len(lines):
                nxt = lines[index]
                if nxt.strip() == "":
                    block.append("")
                    index += 1
                    continue
                indent = len(nxt) - len(nxt.lstrip(" "))
                if indent <= base:
                    break
                block.append(nxt)
                index += 1
            scripts.append("\n".join(block))
            continue
        scripts.append(rest)
        index += 1
    return scripts


def untrusted_expressions(script):
    found = []
    for expression in EXPRESSION.findall(script):
        if any(token in expression for token in UNTRUSTED):
            found.append(expression.strip())
    return found


def scan_text(path, text):
    findings = []
    if "pull_request_target" in text:
        reusable_only = (
            MARKER in text
            and not run_scripts(text)
            and "actions/checkout" not in text
        )
        gate_from_base = GATE_FROM_BASE in text and not any(
            untrusted_expressions(script) for script in run_scripts(text)
        )
        if not reusable_only and not gate_from_base:
            findings.append(f"{path}: pull_request_target")
    for script in run_scripts(text):
        for expression in untrusted_expressions(script):
            findings.append(f"{path}: untrusted run expression: {expression}")
    return findings


def scan_workflows(root):
    findings = []
    workflow_dir = Path(root) / ".github" / "workflows"
    for path in sorted(workflow_dir.glob("*.yml")):
        relative = path.relative_to(root).as_posix()
        findings.extend(scan_text(relative, path.read_text(encoding="utf-8")))
    return findings


def main(argv):
    root = Path(argv[0]) if argv else Path(".")
    findings = scan_workflows(root)
    print(f"pull_request_target={sum(1 for item in findings if item.endswith('pull_request_target'))}")
    print(f"untrusted_run={sum(1 for item in findings if 'untrusted run expression' in item)}")
    for item in findings:
        print(item)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
