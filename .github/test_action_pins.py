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

import re
import unittest
from pathlib import Path

USE = re.compile(r"uses:\s*['\"]?(\S+)")
SHA = re.compile(r"^[0-9a-f]{40}$")


def uses_value(line):
    match = USE.search(line)
    if not match:
        return ""
    return match.group(1).strip("'\"")


def pinned(value):
    if not value or value.startswith("./"):
        return True
    if "@" not in value:
        return False
    ref = value.rsplit("@", 1)[1].strip("'\"")
    return SHA.fullmatch(ref) is not None


def unpinned_uses(root):
    found = []
    workflow_dir = Path(root) / ".github" / "workflows"
    for path in sorted(workflow_dir.glob("*.yml")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            value = uses_value(line)
            if value and not pinned(value):
                found.append(f"{path.relative_to(root).as_posix()}:{number}:{value}")
    return found


class ActionPinTest(unittest.TestCase):
    def test_sha_is_pinned_and_a_branch_ref_is_not(self):
        self.assertTrue(pinned("actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"))
        self.assertTrue(pinned("./.github/actions/rubric-gate"))
        self.assertFalse(pinned("apache/maven-gh-actions-shared/.github/workflows/stale.yml@v5"))
        self.assertFalse(pinned("actions/checkout@v7"))

    def test_workflows_pin_every_third_party_and_github_action(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(unpinned_uses(root), [])


if __name__ == "__main__":
    unittest.main()
