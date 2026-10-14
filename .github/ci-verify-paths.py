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

"""Decide whether Java CI must run ./mvnw verify. ADR-0014. Stdlib only."""

import os
import re
import subprocess

EXACT = frozenset(
    {
        "AGENTS.md",
        "llms.txt",
        "SECURITY.md",
        "docs/adr/boundaries.yml",
    }
)
MARKDOWN_PREFIXES = ("docs/", ".cursor/skills/")
BASE_REF = re.compile(r"[A-Za-z0-9._/-]{1,200}")


def allowed(path):
    if path in EXACT:
        return True
    if not path.endswith(".md"):
        return False
    if ".." in path.split("/"):
        return False
    return path.startswith(MARKDOWN_PREFIXES)


def verify_required(event_name, paths):
    if event_name != "pull_request" or paths is None or not paths:
        return True
    return not all(allowed(path) for path in paths)


def pull_request_paths():
    base = os.environ.get("GITHUB_BASE_REF", "")
    if BASE_REF.fullmatch(base) is None or base.startswith("/") or ".." in base.split("/"):
        return None
    completed = subprocess.run(
        [
            "git",
            "-c",
            "core.quotepath=false",
            "diff",
            "--name-only",
            "-z",
            f"origin/{base}...HEAD",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return [path for path in completed.stdout.split("\0") if path]


def main():
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    paths = pull_request_paths() if event_name == "pull_request" else None
    value = "true" if verify_required(event_name, paths) else "false"
    line = f"verify={value}\n"
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(line)
    else:
        print(line, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
