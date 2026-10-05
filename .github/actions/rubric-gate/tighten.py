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

"""Run the base gaming fixtures against a pull request's gate code.

A change may keep the expected verdict or move toward ESCALATE.
AUTO_MERGE_OK where the fixture expects ESCALATE is a failure.
"""

import importlib
import json
import sys
from pathlib import Path


RANK = {"AUTO_MERGE_OK": 0, "AUTO_FIX": 1, "ESCALATE": 2}
GAMING = Path(__file__).resolve().parent / "testdata" / "gaming"


def loosened(actual, expected):
    if actual not in RANK or expected not in RANK:
        return True
    return RANK[actual] < RANK[expected]


def is_verdict_sidecar(path):
    name = path.name
    marker = "-verdict.json"
    if not name.endswith(marker):
        return False
    case_name = name[: -len(marker)] + ".json"
    return path.with_name(case_name).is_file()


def fixtures():
    found = []
    for path in sorted(GAMING.glob("*.json")):
        if is_verdict_sidecar(path):
            continue
        case = json.loads(path.read_text(encoding="utf-8"))
        case.pop("$comment", None)
        verdict_path = path.with_name(path.stem + "-verdict.json")
        if "expected_verdict" in case:
            expected = case["expected_verdict"]
        elif verdict_path.is_file():
            expected = json.loads(verdict_path.read_text(encoding="utf-8"))["verdict"]
        else:
            raise SystemExit(f"{path.name} has no expected verdict")
        found.append((path.name, case, expected))
    if not found:
        raise SystemExit("no gaming fixtures on the base gate")
    return found


def load_gate(gate_dir):
    gate_dir = str(Path(gate_dir).resolve())
    sys.path.insert(0, gate_dir)
    for name in ("merge", "score", "structure", "validate"):
        sys.modules.pop(name, None)
    return importlib.import_module("merge"), importlib.import_module("score")


def clear_results(score_mod):
    bodies = []
    for name in score_mod.SCORERS:
        body = {
            "scorer": name,
            "status": "ok",
            "dimensions": {},
            "evidence": ["ok"],
        }
        if name == "affected-build":
            body["dimensions"] = {
                "correctness": score_mod.dim(3, "measured"),
                "tests": score_mod.dim(3, "measured"),
            }
        elif name == "japicmp":
            body["dimensions"] = {"compat": score_mod.dim(3, "measured")}
        elif name == "spotless":
            body["dimensions"] = {"clarity": score_mod.dim(3, "measured")}
        elif name == "comment-density":
            body["dimensions"] = {"clarity": score_mod.dim(3, "measured")}
        elif name == "bench-delta":
            body["dimensions"] = {"perf": score_mod.dim(3, "measured")}
        bodies.append(body)
    return bodies


def verdict_for(merge_mod, score_mod, case, root):
    document = merge_mod.build_verdict(
        clear_results(score_mod),
        case.get("patch", ""),
        case.get("paths", []),
        "name: rubric-gate\n",
        0,
        "pr-head",
        "base",
        False,
        "",
        0,
        root,
        case.get("pr_body"),
    )
    if not isinstance(document, dict) or "verdict" not in document:
        raise SystemExit("pull request gate returned no verdict")
    return document["verdict"]


def compare(gate_dir, root):
    merge_mod, score_mod = load_gate(gate_dir)
    failures = []
    for name, case, expected in fixtures():
        try:
            actual = verdict_for(merge_mod, score_mod, case, root)
        except Exception as error:
            failures.append(f"{name}: pull request gate failed closed: {error}")
            continue
        if loosened(actual, expected):
            failures.append(f"{name}: {actual} is looser than {expected}")
    return failures


def main(argv):
    if len(argv) != 1:
        raise SystemExit("usage: tighten.py <pull-request-gate-dir>")
    failures = compare(argv[0], Path(__file__).resolve().parents[3])
    for line in failures:
        print(line)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
