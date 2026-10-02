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

"""Scorer plans, density, format, and bench delta."""

import tempfile
import unittest
from pathlib import Path

import score


class ScoreTest(unittest.TestCase):
    def test_discover_skips_its_and_finds_api_module(self):
        root = Path(__file__).resolve().parents[3]
        modules = score.discover_modules(root)
        self.assertIn("api/maven-api-core", modules)
        self.assertNotIn("its", modules)
        self.assertTrue(all(not module.startswith("its/") for module in modules))

    def test_affected_command_uses_aggregator_pom(self):
        modules = ["api", "api/maven-api-core", "impl/maven-core"]
        selected = score.select_modules(
            ["api/maven-api-core/src/main/java/A.java", "impl/maven-core/src/main/java/B.java"],
            modules,
        )
        self.assertEqual(selected, ["api/maven-api-core", "impl/maven-core"])
        commands = score.maven_commands(selected, "test")
        rendered = [" ".join(command) for command in commands]
        self.assertIn("mvn -f api/pom.xml --batch-mode -T 1C", rendered[0])
        self.assertIn("-pl maven-api-core -am test", rendered[0])
        self.assertNotIn("-f pom.xml", rendered[0])
        self.assertNotIn("-pl api ", rendered[0])

    def test_no_product_diff_skips_maven(self):
        body, plan = score.score_affected(["docs/adr/0001.md"], ["api/maven-api-core"], lambda _commands: (0, ""))
        self.assertFalse(plan["needs_maven"])
        self.assertEqual(body["status"], "skipped")
        self.assertEqual(body["dimensions"]["correctness"]["state"], "not_applicable")
        self.assertNotIn("score", body["dimensions"]["correctness"])
        self.assertEqual(body["dimensions"]["tests"]["state"], "not_applicable")

    def test_root_pom_does_not_rebuild_here(self):
        body, plan = score.score_affected(["pom.xml"], ["api/maven-api-core"], lambda _commands: (0, ""))
        self.assertFalse(plan["needs_maven"])
        item = body["dimensions"]["correctness"]
        self.assertEqual(item["state"], "no_evidence")
        self.assertEqual(item["score"], 2)

    def test_api_signature_without_japicmp_scores_two(self):
        patch = (
            "+++ b/api/maven-api-core/src/main/java/org/apache/maven/api/Foo.java\n"
            "+    public void next() {\n"
        )
        body, plan = score.score_japicmp(
            ["api/maven-api-core/src/main/java/org/apache/maven/api/Foo.java"],
            patch,
            ["api/maven-api-core"],
            lambda _commands: (0, ""),
        )
        self.assertFalse(plan["needs_maven"])
        item = body["dimensions"]["compat"]
        self.assertEqual(item["state"], "no_evidence")
        self.assertLessEqual(item["score"], 2)
        self.assertIn("japicmp is not bound", item["evidence"][0])

    def test_clean_density_and_redundant_phrase(self):
        clean = "+++ b/Example.java\n+class Example {\n+    void run() {}\n+}\n"
        phrase = "this " + "method"
        noisy = "+++ b/Example.java\n+class Example {\n+    // " + phrase + " wraps run\n+    void run() {}\n+}\n"
        self.assertEqual(score.score_comment_density(clean)["score"], 3)
        self.assertEqual(score.score_comment_density(noisy)["score"], 1)

    def test_comment_ratio_bands(self):
        two = "+++ b/Example.java\n+int a;\n+// one\n+int b;\n+int c;\n"
        high = "+++ b/Example.java\n+int a;\n+// a\n+// b\n+// c;\n"
        self.assertEqual(score.score_comment_density(two)["score"], 2)
        self.assertEqual(score.score_comment_density(high)["score"], 1)

    def test_license_header_is_not_density(self):
        patch = "+++ b/Example.py\n+# Licensed header\n+# still header\n+\n+value = 1\n"
        self.assertEqual(score.score_comment_density(patch)["score"], 3)

    def test_trailing_whitespace(self):
        patch = "+++ b/Example.java\n+int a; \n"
        self.assertEqual(score.score_format(patch)["score"], 1)
        self.assertEqual(score.score_format("+++ b/Example.java\n+int a;\n")["score"], 3)

    def test_speedup_band(self):
        self.assertEqual(score.score_speedup(3.11)["score"], 3)
        self.assertEqual(score.score_speedup(2.65)["score"], 3)
        self.assertEqual(score.score_speedup(2.50)["score"], 1)

    def test_product_diff_does_not_wait_for_bench(self):
        scored, status = score.evaluate_bench(["api/maven-api-core/src/main/java/A.java"], None, None)
        self.assertEqual(status, "skipped")
        self.assertEqual(scored["state"], "no_evidence")
        self.assertLessEqual(scored["score"], 2)
        self.assertIn("did not run", scored["evidence"][0])

    def test_docs_diff_bench_is_not_applicable(self):
        scored, status = score.evaluate_bench(["docs/adr/0001.md"], None, None)
        self.assertEqual(status, "skipped")
        self.assertEqual(scored["state"], "not_applicable")
        self.assertNotIn("score", scored)

    def test_bench_source_uses_fetched_speedup(self):
        path = ".github/actions/build-speedup-bench/run-bench.sh"
        scored, status = score.evaluate_bench([path], 3.11, None)
        self.assertEqual(status, "ok")
        self.assertEqual(scored["score"], 3)
        scored, status = score.evaluate_bench([path], None, "bench run not found")
        self.assertEqual(scored["state"], "no_evidence")
        self.assertEqual(scored["score"], 2)
        self.assertEqual(status, "failed")

    def test_parse_speedup_and_newest_run(self):
        self.assertEqual(score.parse_speedup("warm-mvnd-speedup=3.11\n"), 3.11)
        self.assertIsNone(score.parse_speedup("warm-mvnd-speedup=\n"))
        run = score.choose_run({"workflow_runs": [{"id": 2, "conclusion": "success"}, {"id": 1}]})
        self.assertEqual(run["id"], 2)

    def test_poll_stops_on_success_without_extra_sleep(self):
        calls = {"n": 0}

        def get_json():
            calls["n"] += 1
            return {"workflow_runs": [{"id": 9, "conclusion": "success", "status": "completed"}]}

        def get_zip(_run_id):
            return _zip_with_output("warm-mvnd-speedup=3.20\n")

        speedup, error = score.poll_speedup(get_json, get_zip, attempts=3, pause=lambda: calls.__setitem__("slept", True))
        self.assertEqual(speedup, 3.20)
        self.assertIsNone(error)
        self.assertNotIn("slept", calls)


def _zip_with_output(text):
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("build-speedup-bench-logs/github_output.txt", text)
    return buffer.getvalue()


class ApplicabilityTest(unittest.TestCase):
    def test_empty_density_and_format_are_not_applicable(self):
        patch = "+++ b/README.md\n+# title\n"
        density = score.score_comment_density(patch)
        self.assertEqual(density["state"], "not_applicable")
        self.assertNotIn("score", density)
        formatted = score.score_format(patch)
        self.assertEqual(formatted["state"], "not_applicable")
        self.assertNotIn("score", formatted)

    def test_japicmp_without_signature_is_not_applicable(self):
        body, plan = score.score_japicmp(["docs/a.md"], "", ["api/maven-api-core"], lambda _commands: (0, ""))
        self.assertFalse(plan["needs_maven"])
        self.assertEqual(body["dimensions"]["compat"]["state"], "not_applicable")
        self.assertNotIn("score", body["dimensions"]["compat"])

    def test_maven_missing_on_product_is_no_evidence(self):
        path = "api/maven-api-core/src/main/java/A.java"
        body, plan = score.score_affected([path], ["api/maven-api-core"], lambda _commands: (None, "mvn not on PATH"))
        self.assertTrue(plan["needs_maven"])
        item = body["dimensions"]["correctness"]
        self.assertEqual(body["status"], "maven_missing")
        self.assertEqual(item["state"], "no_evidence")
        self.assertLessEqual(item["score"], 2)

    def test_spotless_skipped_on_java_is_no_evidence(self):
        path = "api/maven-api-core/src/main/java/A.java"
        patch = "+++ b/" + path + "\n+int a; \n"
        body, _plan = score.score_spotless([path], patch, ["api/maven-api-core"], lambda _commands: (None, "mvn not on PATH"))
        item = body["dimensions"]["clarity"]
        self.assertEqual(item["state"], "no_evidence")
        self.assertEqual(item["score"], 1)
        self.assertIn("spotless not run", item["evidence"])

    def test_no_java_xml_without_source_is_not_applicable(self):
        body, plan = score.score_spotless(["docs/a.md"], "+++ b/docs/a.md\n+# a\n", [], lambda _commands: (0, ""))
        self.assertEqual(plan["reason"], "no-java-xml")
        item = body["dimensions"]["clarity"]
        self.assertEqual(item["state"], "not_applicable")
        self.assertNotIn("score", item)

    def test_python_whitespace_stays_scored_without_java(self):
        body, _plan = score.score_spotless(["tool.py"], "+++ b/tool.py\n+value = 1\n", [], lambda _commands: (0, ""))
        item = body["dimensions"]["clarity"]
        self.assertEqual(item["state"], "scored")
        self.assertEqual(item["score"], 3)


class DiscoverTmpTest(unittest.TestCase):
    def test_tmp_tree(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "api" / "maven-api-core").mkdir(parents=True)
            (root / "api" / "pom.xml").write_text("<project/>", encoding="utf-8")
            (root / "api" / "maven-api-core" / "pom.xml").write_text("<project/>", encoding="utf-8")
            (root / "its" / "core-it-suite").mkdir(parents=True)
            (root / "its" / "pom.xml").write_text("<project/>", encoding="utf-8")
            (root / "api" / "maven-api-core" / "src" / "it").mkdir(parents=True)
            (root / "api" / "maven-api-core" / "src" / "it" / "pom.xml").write_text("<project/>", encoding="utf-8")
            modules = score.discover_modules(root)
            self.assertEqual(modules, ["api/maven-api-core", "api"])


if __name__ == "__main__":
    unittest.main()
