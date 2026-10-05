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

import importlib.util
import unittest
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent / "affected-modules.py"
_SPEC = importlib.util.spec_from_file_location("affected_modules", _SCRIPT)
affected_modules = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(affected_modules)

MODULES = ["api/maven-api-core", "impl/maven-core", "compat/maven-model"]


class AffectedModulesTest(unittest.TestCase):
    def test_one_module_uses_pl_and_am(self):
        decision = affected_modules.decide(
            ["api/maven-api-core/src/main/java/org/apache/maven/api/Session.java"],
            MODULES,
        )
        self.assertEqual(decision["mode"], "affected")
        self.assertEqual(len(decision["commands"]), 1)
        command = decision["commands"][0]
        self.assertIn("-pl", command)
        self.assertIn("maven-api-core", command)
        self.assertIn("-am", command)
        self.assertEqual(command[-1], "test")

    def test_its_or_workflow_or_root_pom_stays_full(self):
        for path in (
            "its/core-it-suite/pom.xml",
            ".github/workflows/maven.yml",
            "pom.xml",
            ".mvn/maven.config",
            "apache-maven/pom.xml",
        ):
            decision = affected_modules.decide([path, "api/maven-api-core/pom.xml"], MODULES)
            self.assertEqual(decision["mode"], "full", path)

    def test_empty_diff_stays_full(self):
        self.assertEqual(affected_modules.decide([], MODULES)["mode"], "full")

    def test_docs_only_stays_full(self):
        decision = affected_modules.decide(["docs/adr/template.md"], MODULES)
        self.assertEqual(decision["mode"], "full")

    def test_maven_override_replaces_only_the_executable(self):
        command = ["mvn", "-f", "api/pom.xml", "test"]
        self.assertEqual(
            affected_modules.with_maven(command, "./mvnw"),
            ["./mvnw", "-f", "api/pom.xml", "test"],
        )


if __name__ == "__main__":
    unittest.main()
