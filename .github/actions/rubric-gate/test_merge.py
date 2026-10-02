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


GOLDEN = Path(__file__).with_name("testdata")


ROOT = Path(__file__).resolve().parents[3]
SCOPE = "scope: agent-contract, ci, product\n"


def _gate_verdict(paths, patch, runner, head_sha, base_sha, pr_body):
    modules = ["api/maven-api-core"]
    results = [
        score.score_affected(paths, modules, runner)[0],
        score.score_japicmp(paths, patch, modules, runner)[0],
        score.score_spotless(paths, patch, modules, runner)[0],
        score.score_comments(patch)[0],
        score.score_bench(paths, None, None)[0],
    ]
    return merge.build_verdict(
        results,
        patch,
        paths,
        "name: rubric-gate\n",
        0,
        head_sha,
        base_sha,
        False,
        "",
        0,
        ROOT,
        pr_body,
    )


def _docs_only_verdict():
    paths = ["docs/adr/0001-bench-is-composite-action.md", "AGENTS.md"]
    patch = (
        "+++ b/docs/adr/0001-bench-is-composite-action.md\n"
        "+# title\n"
        "+++ b/AGENTS.md\n"
        "+# contract\n"
    )
    return _gate_verdict(
        paths,
        patch,
        lambda _commands: (0, "unused"),
        "docs-head",
        "docs-base",
        "scope: agent-contract\n",
    )


def _product_code_verdict():
    path = "api/maven-api-core/src/main/java/org/apache/maven/api/Foo.java"
    patch = "+++ b/" + path + "\n+    public void next() {\n+        return;\n+    }\n"
    return _gate_verdict(
        [path],
        patch,
        lambda _commands: (None, "mvn not on PATH"),
        "product-head",
        "product-base",
        "scope: product\n",
    )


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
    def verdict(self, results=None, patch="", paths=None, loop=0, workflow="name: rubric-gate\n", unit_test_rc=0, llm=False, command="", pr_body=SCOPE):
        chosen = ["docs/adr/template.md"] if paths is None else paths
        return merge.build_verdict(
            results if results is not None else all_clear_results(),
            patch,
            chosen,
            workflow,
            loop,
            "head",
            "base",
            llm,
            command,
            unit_test_rc,
            ROOT,
            pr_body,
        )

    def test_measured_threes_merge_ok(self):
        dimensions = {name: score.dim(3, "measured") for name in merge.DIMENSIONS}
        rules = [merge.hard_rule("secrets", True, "ok")]
        self.assertEqual(merge.decide(dimensions, rules, 0), "AUTO_MERGE_OK")
        self.assertEqual(merge.decide(dimensions, rules, 0, risky=True), "AUTO_MERGE_OK")
        document = self.verdict(paths=["docs/adr/0001.md", "llms.txt"])
        self.assertEqual(document["schema_version"], 2)
        self.assertFalse(document["blocking"])
        self.assertEqual(validate.validate(document), [])
        self.assertEqual(document["dimensions"]["architecture"]["score"], 3)
        self.assertEqual(document["dimensions"]["intent"]["score"], 3)
        self.assertEqual(document["verdict"], "AUTO_MERGE_OK")

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
        document["blocking"] = False
        document["dimensions"]["perf"] = score.not_applicable("no bench sources in the diff")
        document["dimensions"]["perf"]["score"] = 3
        self.assertTrue(any("not_applicable has score" in error for error in validate.validate(document)))
        del document["dimensions"]["perf"]["score"]
        self.assertEqual(validate.validate(document), [])
        document["dimensions"]["perf"] = {
            "state": "no_evidence",
            "score": 3,
            "evidence": ["bench did not run"],
        }
        self.assertTrue(any("no_evidence maximum" in error for error in validate.validate(document)))

    def test_missing_scorer_caps_unless_risky(self):
        quiet = self.verdict(results=[])
        self.assertEqual(quiet["verdict"], "AUTO_FIX")
        self.assertEqual(quiet["scorers"]["affected-build"]["status"], "missing")
        self.assertEqual(quiet["dimensions"]["correctness"]["state"], "no_evidence")
        self.assertLessEqual(quiet["dimensions"]["correctness"]["score"], 2)
        loud = self.verdict(results=[], paths=["pom.xml"])
        self.assertEqual(loud["verdict"], "ESCALATE")
        rule = next(item for item in loud["hard_rules"] if item["id"] == "no-evidence-risky")
        self.assertFalse(rule["passed"])

    def test_determinism_allows_sleep(self):
        call = "time" + ".time()"
        patch = "+++ b/tool.py\n+import time\n+time.sleep(1)\n+" + call + "\n"
        self.assertEqual(merge.score_determinism(patch)["score"], 1)
        patch = "+++ b/tool.py\n+import time\n+time.sleep(1)\n"
        self.assertEqual(merge.score_determinism(patch)["score"], 3)
        absent = merge.score_determinism("+++ b/docs/a.md\n+# a\n")
        self.assertEqual(absent["state"], "not_applicable")
        self.assertNotIn("score", absent)

    def test_unmeasured_intent_escalates(self):
        document = self.verdict(paths=["docs/adr/template.md"], pr_body=None)
        self.assertEqual(document["dimensions"]["intent"]["state"], "no_evidence")
        self.assertEqual(document["verdict"], "ESCALATE")
        rule = next(item for item in document["hard_rules"] if item["id"] == "structure-measured")
        self.assertFalse(rule["passed"])
        placed = merge.score_architecture(ROOT, ["notes.txt"])
        self.assertEqual(placed["state"], "no_evidence")
        self.assertEqual(self.verdict(paths=["notes.txt"])["verdict"], "ESCALATE")

    def test_not_applicable_is_excluded_and_risky_no_evidence_escalates(self):
        dimensions = {name: score.dim(3, "measured") for name in merge.DIMENSIONS}
        dimensions["perf"] = score.not_applicable("no bench sources in the diff")
        rules = [merge.hard_rule("secrets", True, "ok")]
        self.assertEqual(merge.decide(dimensions, rules, 0), "AUTO_MERGE_OK")
        dimensions["clarity"] = score.no_evidence("spotless not run")
        self.assertEqual(merge.decide(dimensions, rules, 0, risky=False), "AUTO_FIX")
        self.assertEqual(merge.decide(dimensions, rules, 0, risky=True), "ESCALATE")
        empty = {name: score.not_applicable("n/a") for name in merge.DIMENSIONS}
        self.assertEqual(merge.decide(empty, rules, 0), "ESCALATE")
        self.assertEqual(merge.decide(empty, rules, 2), "ESCALATE")

    def test_no_evidence_on_risky_path_escalates(self):
        results = all_clear_results()
        results[0]["dimensions"]["correctness"] = score.no_evidence("maven did not run")
        results[0]["dimensions"]["tests"] = score.no_evidence("maven did not run")
        quiet = self.verdict(results, paths=["docs/adr/0001.md"])
        self.assertEqual(quiet["verdict"], "AUTO_FIX")
        self.assertTrue(next(item["passed"] for item in quiet["hard_rules"] if item["id"] == "no-evidence-risky"))
        loud = self.verdict(results, paths=["api/maven-api-core/src/A.java"])
        self.assertEqual(loud["verdict"], "ESCALATE")
        permission = "actions:" + " write"
        patch = "+++ b/.github/workflows/extra.yml\n+" + permission + "\n"
        workflow = self.verdict(results, patch=patch, paths=[".github/workflows/extra.yml"])
        self.assertEqual(workflow["verdict"], "ESCALATE")

    def test_golden_docs_only_and_product_code(self):
        docs = _docs_only_verdict()
        self.assertEqual(docs["verdict"], "AUTO_MERGE_OK")
        self.assertEqual(docs["dimensions"]["correctness"]["state"], "not_applicable")
        self.assertNotIn("score", docs["dimensions"]["correctness"])
        self.assertEqual(docs["dimensions"]["intent"]["score"], 3)
        self.assertEqual(docs["dimensions"]["architecture"]["score"], 3)
        self.assertIn("docs/adr/template.md", " ".join(docs["dimensions"]["architecture"]["evidence"]))
        self.assertTrue(next(item["passed"] for item in docs["hard_rules"] if item["id"] == "no-evidence-risky"))
        product = _product_code_verdict()
        self.assertEqual(product["verdict"], "ESCALATE")
        self.assertEqual(product["dimensions"]["architecture"]["score"], 3)
        self.assertEqual(product["dimensions"]["intent"]["score"], 3)
        self.assertEqual(product["dimensions"]["correctness"]["state"], "no_evidence")
        self.assertLessEqual(product["dimensions"]["correctness"]["score"], 2)
        self.assertEqual(product["dimensions"]["compat"]["state"], "no_evidence")
        self.assertEqual(product["dimensions"]["perf"]["state"], "no_evidence")
        self.assertFalse(next(item["passed"] for item in product["hard_rules"] if item["id"] == "no-evidence-risky"))
        for name, document in (("docs-only-verdict.json", docs), ("product-code-verdict.json", product)):
            expected = json.loads((GOLDEN / name).read_text(encoding="utf-8"))
            self.assertIn("Licensed to the Apache Software Foundation", expected.pop("$comment"))
            self.assertEqual(document, expected)
            self.assertEqual(validate.validate(document), [])

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
