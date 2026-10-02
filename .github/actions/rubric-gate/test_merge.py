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

"""Verdict thresholds, hard rules, schema, and the disabled score hook."""

import json
import unittest
from pathlib import Path

import merge
import score
import validate


def passed(name, evidence="ok"):
    return {"scorer": name, "status": "ok", "dimensions": {}, "evidence": [evidence]}


def all_clear_results():
    bodies = []
    for name in score.SCORERS:
        body = passed(name)
        if name == "affected-build":
            body["dimensions"] = {
                "correctness": score.dim(3, "no product modules in the diff"),
                "tests": score.dim(3, "no product modules in the diff"),
            }
        elif name == "japicmp":
            body["dimensions"] = {"compat": score.dim(3, "no japicmp module")}
        elif name == "spotless":
            body["dimensions"] = {"clarity": score.dim(3, "no trailing whitespace")}
        elif name == "comment-density":
            body["dimensions"] = {"clarity": score.dim(3, "comment ratio 0.00")}
        elif name == "bench-delta":
            body["dimensions"] = {"perf": score.dim(3, "no bench sources in the diff")}
        bodies.append(body)
    return bodies


class MergeTest(unittest.TestCase):
    def verdict(self, results=None, patch="", paths=None, loop=0, workflow="name: rubric-gate\n", unit_test_rc=0, llm=False, command=""):
        return merge.build_verdict(
            results if results is not None else all_clear_results(),
            patch,
            [] if paths is None else paths,
            workflow,
            loop,
            "head",
            "base",
            llm,
            command,
            unit_test_rc,
        )

    def test_all_threes_merge_ok(self):
        document = self.verdict(paths=["docs/adr/0001.md", "llms.txt"])
        self.assertEqual(document["verdict"], "AUTO_MERGE_OK")
        self.assertFalse(document["blocking"])
        self.assertEqual(validate.validate(document), [])

    def test_score_two_is_auto_fix_until_loop_two(self):
        results = all_clear_results()
        results[0]["dimensions"]["tests"] = score.dim(2, "gap")
        self.assertEqual(self.verdict(results, loop=0)["verdict"], "AUTO_FIX")
        self.assertEqual(self.verdict(results, loop=1)["verdict"], "AUTO_FIX")
        self.assertEqual(self.verdict(results, loop=2)["verdict"], "ESCALATE")

    def test_zero_and_hard_rule_escalate(self):
        results = all_clear_results()
        results[0]["dimensions"]["correctness"] = score.dim(0, "compile failed")
        self.assertEqual(self.verdict(results)["verdict"], "ESCALATE")
        secret = "ghp_" + ("a" * 20)
        patch = "+++ b/notes.txt\n+" + secret + "\n"
        document = self.verdict(patch=patch, paths=["notes.txt"])
        self.assertEqual(document["verdict"], "ESCALATE")
        self.assertFalse(next(rule["passed"] for rule in document["hard_rules"] if rule["id"] == "secrets"))

    def test_contents_write_and_third_party_push(self):
        permission = "contents:" + " write"
        patch = "+++ b/.github/workflows/extra.yml\n+" + permission + "\n"
        document = self.verdict(patch=patch, paths=[".github/workflows/extra.yml"])
        self.assertFalse(next(rule["passed"] for rule in document["hard_rules"] if rule["id"] == "contents-write"))
        push = "git " + "push"
        url = "https://github.com/" + "apache/maven.git"
        patch = "+++ b/bad.sh\n+" + push + " " + url + "\n"
        document = self.verdict(patch=patch, paths=["bad.sh"])
        self.assertFalse(next(rule["passed"] for rule in document["hard_rules"] if rule["id"] == "third-party-push"))

    def test_report_only_rejects_exit(self):
        document = self.verdict(workflow="name: rubric-gate\nexit 1\n")
        self.assertFalse(next(rule["passed"] for rule in document["hard_rules"] if rule["id"] == "report-only"))
        self.assertFalse(document["blocking"])

    def test_unit_test_failure_escalates(self):
        document = self.verdict(unit_test_rc=1)
        self.assertEqual(document["dimensions"]["tests"]["score"], 0)
        self.assertEqual(document["verdict"], "ESCALATE")

    def test_hook_notes_do_not_change_scores(self):
        command = (
            "python3 -c 'import json,sys; json.load(sys.stdin); "
            "print(json.dumps({\"notes\":[\"seen\"],\"dimensions\":{\"perf\":{\"score\":0,\"evidence\":[\"no\"]}}}))'"
        )
        before = self.verdict(paths=["llms.txt"])
        after = self.verdict(paths=["llms.txt"], llm=True, command=command)
        self.assertEqual(after["dimensions"], before["dimensions"])
        self.assertEqual(after["llm_hook"]["status"], "ok")
        self.assertIn("v0 hook cannot change scores", after["llm_hook"]["notes"])
        self.assertEqual(after["verdict"], "AUTO_MERGE_OK")

    def test_hook_disabled_by_default(self):
        document = self.verdict()
        self.assertFalse(document["llm_hook"]["enabled"])
        self.assertEqual(document["llm_hook"]["status"], "disabled")

    def test_schema_rejects_extra_and_bad_score(self):
        document = self.verdict(paths=["llms.txt"])
        document["extra"] = 1
        self.assertTrue(validate.validate(document))
        del document["extra"]
        document["dimensions"]["perf"]["score"] = 4
        self.assertTrue(validate.validate(document))
        document["blocking"] = True
        document["dimensions"]["perf"]["score"] = 3
        self.assertTrue(any("blocking" in error for error in validate.validate(document)))

    def test_missing_scorer_escalates(self):
        document = self.verdict(results=[])
        self.assertEqual(document["verdict"], "ESCALATE")
        self.assertEqual(document["scorers"]["affected-build"]["status"], "missing")

    def test_determinism_allows_sleep(self):
        call = "time" + ".time()"
        patch = "+++ b/tool.py\n+import time\n+time.sleep(1)\n+" + call + "\n"
        self.assertEqual(merge.score_determinism(patch)["score"], 1)
        patch = "+++ b/tool.py\n+import time\n+time.sleep(1)\n"
        self.assertEqual(merge.score_determinism(patch)["score"], 3)

    def test_new_action_requires_index(self):
        paths = [".github/actions/rubric-gate/action.yml"]
        self.assertEqual(merge.score_intent(paths, "")["score"], 1)
        paths.append("llms.txt")
        self.assertEqual(merge.score_intent(paths, "")["score"], 3)

    def test_skill_mirrors(self):
        root = Path(__file__).resolve().parents[3]
        for name in ("rubric-gate", "write-adr", "fast-maven-loop"):
            skill = (root / ".cursor" / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            doc = (root / "docs" / "agents" / f"{name}.md").read_text(encoding="utf-8")
            self.assertTrue(skill.startswith("---\n"))
            body = skill.split("---\n", 2)[2].strip() + "\n"
            self.assertEqual(body, doc.strip() + "\n")


if __name__ == "__main__":
    unittest.main()
