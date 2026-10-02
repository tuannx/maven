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

"""Boundaries file, contract checks, reactor direction, and scope."""

import tempfile
import textwrap
import unittest
from pathlib import Path

import structure


TEMPLATE = textwrap.dedent(
    """\
    # ADR-0001 Sample

    - status: accepted
    - date: 2026-10-02
    - decided-by: test

    ## Context

    A constraint.

    ## Decision

    One sentence.

    ## Options

    | id | option | score | why |
    |---|---|---:|---|
    | A | keep | 3 | fits |

    ## Trade-off

    Cost.

    ## Revisit when

    A trigger.
    """
)

BOUNDARIES = textwrap.dedent(
    """\
    path_groups:
      agent-contract:
        - AGENTS.md
        - llms.txt
        - docs/adr/
        - docs/agents/
      ci:
        - .github/
      product:
        - api/
    dependency_direction:
      api:
        - api
    least_privilege:
      actions:
        - actions/upload-artifact
    absent_on_purpose:
      - .mvn/extensions.xml
    """
)

DOC = "<!--\nlicense\n-->\n\n# demo\n\nBody.\n"


def write(root, path, text):
    target = Path(root) / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def tiny_repo(root):
    write(root, "docs/adr/boundaries.yml", BOUNDARIES)
    write(root, "docs/adr/template.md", TEMPLATE)
    write(root, "docs/adr/0001-sample.md", TEMPLATE)
    write(root, "docs/agents/demo.md", DOC)
    write(root, ".cursor/skills/demo/SKILL.md", "---\nname: demo\n---\n\n" + DOC)
    write(root, "AGENTS.md", "See [template](docs/adr/template.md) and `.mvn/extensions.xml`.\n")
    write(root, "llms.txt", "See [contract](AGENTS.md).\n")


class StructureTest(unittest.TestCase):
    def test_yaml_parser_reads_groups(self):
        data = structure.parse_yaml(BOUNDARIES)
        self.assertEqual(data["path_groups"]["product"], ["api/"])
        self.assertEqual(data["dependency_direction"]["api"], ["api"])

    def test_each_contract_check(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            tiny_repo(root)
            loaded = structure.load_boundaries(root)
            self.assertEqual(structure.check_references(root, loaded["absent_on_purpose"])[0], [])
            self.assertEqual(structure.check_skill_mirrors(root)[0], [])
            self.assertEqual(structure.check_adrs(root)[0], [])
            self.assertEqual(
                structure.check_action_index(root, ["docs/adr/0001-sample.md"])[1],
                ["no new action.yml"],
            )
            self.assertEqual(
                structure.check_least_privilege(root, ["docs/adr/0001-sample.md"], loaded["least_privilege"])[1],
                ["no workflow file in the diff"],
            )

            write(root, "AGENTS.md", "See [missing](docs/missing.md).\n")
            failures, _ok = structure.check_references(root, loaded["absent_on_purpose"])
            self.assertIn("docs/missing.md", failures[0])

            write(root, "docs/agents/demo.md", DOC + "drift\n")
            failures, _ok = structure.check_skill_mirrors(root)
            self.assertIn("differ", failures[0])

            write(root, "docs/adr/0001-sample.md", TEMPLATE.replace("## Context\n", ""))
            failures, _ok = structure.check_adrs(root)
            self.assertIn("missing ## Context", failures[0])

            failures, _ok = structure.check_action_index(root, [".github/actions/demo/action.yml"])
            self.assertIn("index .github/actions/demo", failures[0])
            write(root, "llms.txt", "See `.github/actions/demo` and [contract](AGENTS.md).\n")
            self.assertEqual(structure.check_action_index(root, [".github/actions/demo/action.yml"])[0], [])

            workflow = ".github/workflows/demo.yml"
            write(root, workflow, "permissions:\n  contents: write\n")
            failures, _ok = structure.check_least_privilege(root, [workflow], loaded["least_privilege"])
            self.assertIn("contents: write", failures[0])
            write(root, workflow, "permissions:\n  actions: write\nsteps:\n  - uses: actions/upload-artifact@v7\n")
            self.assertEqual(structure.check_least_privilege(root, [workflow], loaded["least_privilege"])[0], [])

            write(root, ".mvn/extensions.xml", "<extensions/>\n")
            write(root, "AGENTS.md", "Do not commit `.mvn/extensions.xml`.\n")
            failures, _ok = structure.check_references(root, loaded["absent_on_purpose"])
            self.assertIn("on disk", failures[0])

    def test_dependency_direction(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            write(root, "docs/adr/boundaries.yml", BOUNDARIES)
            pom = textwrap.dedent(
                """\
                <project>
                  <artifactId>maven-api-core</artifactId>
                  <dependencies>
                    <dependency>
                      <groupId>org.apache.maven</groupId>
                      <artifactId>maven-core</artifactId>
                    </dependency>
                  </dependencies>
                </project>
                """
            )
            write(root, "api/maven-api-core/pom.xml", pom)
            write(
                root,
                "impl/maven-core/pom.xml",
                "<project><artifactId>maven-core</artifactId></project>\n",
            )
            loaded = structure.load_boundaries(root)
            failures, _ok = structure.check_dependency_direction(
                root,
                ["api/maven-api-core/src/main/java/A.java"],
                loaded["dependency_direction"],
            )
            self.assertIn("impl:maven-core", failures[0])
            write(
                root,
                "api/maven-api-core/pom.xml",
                "<project><artifactId>maven-api-core</artifactId></project>\n",
            )
            failures, ok = structure.check_dependency_direction(
                root,
                ["api/maven-api-core/src/main/java/A.java"],
                loaded["dependency_direction"],
            )
            self.assertEqual(failures, [])
            self.assertIn("api/maven-api-core/pom.xml", ok[0])

    def test_intent_scope(self):
        groups = structure.parse_yaml(BOUNDARIES)["path_groups"]
        paths = ["docs/adr/0001-sample.md"]
        missing = structure.score_intent(paths, "no scope here\n", groups)
        self.assertEqual(missing["score"], 1)
        self.assertIn("declare a scope line", missing["evidence"][0])
        unknown = structure.score_intent(paths, "scope: other\n", groups)
        self.assertEqual(unknown["score"], 1)
        self.assertIn("unknown path group", unknown["evidence"][0])
        outside = structure.score_intent(["api/maven-api-core/pom.xml"], "scope: agent-contract\n", groups)
        self.assertEqual(outside["score"], 1)
        self.assertIn("outside declared scope", outside["evidence"][0])
        covered = structure.score_intent(paths, "scope: agent-contract\n", groups)
        self.assertEqual(covered["score"], 3)
        absent = structure.score_intent(paths, None, groups)
        self.assertEqual(absent["state"], "no_evidence")
        self.assertLessEqual(absent["score"], 2)

    def test_unclassified_path_is_no_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            tiny_repo(root)
            item = structure.score_architecture(root, ["notes.txt"])
            self.assertEqual(item["state"], "no_evidence")
            self.assertIn("unclassified path", item["evidence"][0])

    def test_repo_contract_and_product_score_three(self):
        root = Path(__file__).resolve().parents[3]
        contract = structure.score_architecture(
            root,
            [
                "docs/adr/0011-structural-checks-score-three.md",
                ".github/workflows/rubric-gate.yml",
                ".github/actions/rubric-gate/action.yml",
            ],
        )
        self.assertEqual(contract["state"], "scored")
        self.assertEqual(contract["score"], 3, contract["evidence"])
        product = structure.score_architecture(
            root,
            ["api/maven-api-core/src/main/java/org/apache/maven/api/Session.java"],
        )
        self.assertEqual(product["score"], 3, product["evidence"])


if __name__ == "__main__":
    unittest.main()
