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

"""Path filter for Java CI. ADR-0012."""

import importlib.util
import unittest
from pathlib import Path


def load_filter():
    path = Path(__file__).with_name("ci-verify-paths.py")
    spec = importlib.util.spec_from_file_location("ci_verify_paths", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class VerifyPathsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_filter()

    def test_contract_markdown_skips_verify(self):
        paths = [
            "AGENTS.md",
            "llms.txt",
            "SECURITY.md",
            "docs/adr/0012-skip-verify-for-contract-diffs.md",
            "docs/agents/rubric-gate.md",
            ".cursor/skills/rubric-gate/SKILL.md",
            "docs/adr/boundaries.yml",
        ]
        self.assertFalse(self.mod.verify_required("pull_request", paths))

    def test_code_under_docs_still_verifies(self):
        for path in (
            "docs/adr/Hidden.java",
            "docs/agents/evil.py",
            "docs/adr/Payload.class",
            ".cursor/skills/rubric-gate/payload.jar",
            "docs/agents/run.sh",
            "docs/adr/pom.xml",
            "docs/exploit/Foo.java",
        ):
            self.assertTrue(self.mod.verify_required("pull_request", ["docs/adr/0001.md", path]), path)

    def test_workflow_and_product_verify(self):
        self.assertTrue(self.mod.verify_required("pull_request", [".github/workflows/maven.yml"]))
        self.assertTrue(self.mod.verify_required("pull_request", ["api/maven-api-core/pom.xml"]))
        self.assertTrue(self.mod.verify_required("pull_request", ["docs/adr/other.yml"]))

    def test_push_empty_and_unreadable_diff_verify(self):
        self.assertTrue(self.mod.verify_required("push", ["docs/adr/0001.md"]))
        self.assertTrue(self.mod.verify_required("pull_request", []))
        self.assertTrue(self.mod.verify_required("pull_request", None))

    def test_base_ref_is_not_a_shell_string(self):
        import os

        self.assertIsNone(self.mod.BASE_REF.fullmatch("master;touch x"))
        self.assertIsNotNone(self.mod.BASE_REF.fullmatch("cursor/maven-ci-path-filter-1127"))
        previous = os.environ.get("GITHUB_BASE_REF")
        try:
            os.environ["GITHUB_BASE_REF"] = "../master"
            self.assertIsNone(self.mod.pull_request_paths())
            os.environ["GITHUB_BASE_REF"] = "master;touch x"
            self.assertIsNone(self.mod.pull_request_paths())
        finally:
            if previous is None:
                os.environ.pop("GITHUB_BASE_REF", None)
            else:
                os.environ["GITHUB_BASE_REF"] = previous


if __name__ == "__main__":
    unittest.main()
