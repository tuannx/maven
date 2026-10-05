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

"""Choose a full IT run or one -pl test command. ADR-0017."""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "actions" / "rubric-gate"))

import score  # noqa: E402


def outside_module(path):
    if path in ("pom.xml", ".mvn"):
        return True
    return path.startswith(("its/", ".github/", ".mvn/", "apache-maven/"))


def decide(paths, modules):
    if not paths:
        return {"mode": "full", "reason": "empty-diff", "commands": []}
    outside = [path for path in paths if outside_module(path)]
    if outside:
        return {"mode": "full", "reason": "outside-module", "paths": outside, "commands": []}
    plan = score.plan_affected(paths, modules)
    if not plan.get("needs_maven"):
        return {"mode": "full", "reason": plan.get("reason") or "no-modules", "commands": []}
    return {
        "mode": "affected",
        "reason": "modules",
        "modules": plan.get("modules") or [],
        "commands": plan["commands"],
    }


def load_paths(root, base, explicit):
    if explicit:
        return explicit
    if not base:
        return []
    try:
        return score.git_paths(root, base)
    except subprocess.CalledProcessError:
        return []


def with_maven(command, maven):
    if not maven or maven == "mvn":
        return list(command)
    argv = list(command)
    argv[0] = maven
    return argv


def execute(commands, maven, root):
    start = time.perf_counter()
    for command in commands:
        argv = with_maven(command, maven)
        completed = subprocess.run(argv, cwd=root)
        if completed.returncode != 0:
            raise SystemExit(completed.returncode)
    return time.perf_counter() - start


def write_mode(path, mode):
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"mode={mode}\n")


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--base", default="")
    parser.add_argument("--paths", action="append", default=[])
    parser.add_argument("--maven", default="mvn")
    parser.add_argument("--github-output", default="")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root)
    paths = load_paths(root, args.base, args.paths)
    decision = decide(paths, score.discover_modules(root))
    print(f"mode={decision['mode']}")
    print(f"reason={decision['reason']}")
    output = args.github_output or os.environ.get("GITHUB_OUTPUT", "")
    if output:
        write_mode(output, decision["mode"])
    if args.execute:
        if decision["mode"] != "affected":
            raise SystemExit(f"refusing to execute mode {decision['mode']}")
        seconds = execute(decision["commands"], args.maven, root)
        print(f"affected_seconds={seconds:.2f}")
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as handle:
                handle.write(f"\nAffected module build: {seconds:.2f}s\n")
                for command in decision["commands"]:
                    handle.write("\n`" + " ".join(with_maven(command, args.maven)) + "`\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
