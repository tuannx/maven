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

"""Stdlib checks for summarize.py table rows and action outputs."""

import os
import tempfile
import unittest
from pathlib import Path

import summarize

HEADER = "scenario\tseconds\trc\n"


class SummarizeTest(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.copy()
        os.environ.pop("GITHUB_STEP_SUMMARY", None)
        os.environ.pop("BENCH_REVISION", None)
        os.environ["BENCH_POM"] = "api/pom.xml"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._saved)

    def write_timings(self, log_dir, body):
        (log_dir / "timings.tsv").write_text(HEADER + body, encoding="utf-8")

    def outputs(self, log_dir):
        text = (log_dir / "github_output.txt").read_text(encoding="utf-8")
        return dict(line.split("=", 1) for line in text.splitlines() if line)

    def test_sample_logs_produce_table_and_outputs(self):
        with tempfile.TemporaryDirectory() as raw:
            log_dir = Path(raw)
            step_summary = log_dir / "step-summary.md"
            os.environ["GITHUB_STEP_SUMMARY"] = str(step_summary)
            self.write_timings(
                log_dir,
                "mvn_clean_1\t8.00\t0\n"
                "mvn_clean_2\t7.50\t0\n"
                "mvn_clean_3\t99.00\t1\n"
                "mvnd_cold_clean\t5.00\t0\n"
                "mvnd_warm_clean_1\t2.50\t0\n"
                "mvnd_warm_clean_2\t2.40\t0\n"
                "cache_no_change\t0.20\t0\n",
            )
            summarize.main(log_dir)
            summary = (log_dir / "summary.md").read_text(encoding="utf-8")
            self.assertIn("| Scenario | Seconds | Speedup vs mvn median |", summary)
            self.assertIn("| Host `mvn` median (baseline) | 7.75 | 1.00x |", summary)
            self.assertIn("| `mvnd` warm median | 2.45 | 3.16x |", summary)
            self.assertIn("| Build-cache no-change rebuild | 0.20 | 38.75x |", summary)
            self.assertNotIn("99.00", summary)
            values = self.outputs(log_dir)
            self.assertEqual(values["mvn-median-seconds"], "7.75")
            self.assertEqual(values["warm-mvnd-seconds"], "2.45")
            self.assertEqual(values["warm-mvnd-speedup"], "3.16")
            self.assertEqual(values["cache-no-change-seconds"], "0.20")
            self.assertEqual(values["summary-path"], "bench-logs/summary.md")
            self.assertEqual(step_summary.read_text(encoding="utf-8"), summary)

    def test_missing_scenarios_leave_outputs_empty(self):
        with tempfile.TemporaryDirectory() as raw:
            log_dir = Path(raw)
            self.write_timings(log_dir, "mvn_clean_1\t8.00\t0\nmvn_clean_2\t7.50\t0\n")
            summarize.main(log_dir)
            summary = (log_dir / "summary.md").read_text(encoding="utf-8")
            self.assertNotIn("`mvnd`", summary)
            self.assertNotIn("Build-cache", summary)
            values = self.outputs(log_dir)
            self.assertEqual(values["mvn-median-seconds"], "7.75")
            self.assertEqual(values["warm-mvnd-seconds"], "")
            self.assertEqual(values["warm-mvnd-speedup"], "")
            self.assertEqual(values["cache-no-change-seconds"], "")
            self.assertEqual(values["summary-path"], "bench-logs/summary.md")

    def test_empty_or_missing_timings_leave_timing_outputs_empty(self):
        with tempfile.TemporaryDirectory() as raw:
            empty_dir = Path(raw) / "empty"
            missing_dir = Path(raw) / "missing"
            empty_dir.mkdir()
            missing_dir.mkdir()
            self.write_timings(empty_dir, "")
            for log_dir in (empty_dir, missing_dir):
                summarize.main(log_dir)
                summary = (log_dir / "summary.md").read_text(encoding="utf-8")
                self.assertIn("| (no successful timed runs) | n/a | n/a |", summary)
                values = self.outputs(log_dir)
                self.assertEqual(values["mvn-median-seconds"], "")
                self.assertEqual(values["warm-mvnd-seconds"], "")
                self.assertEqual(values["warm-mvnd-speedup"], "")
                self.assertEqual(values["cache-no-change-seconds"], "")
                self.assertEqual(values["summary-path"], "bench-logs/summary.md")

    def test_three_run_median_is_the_middle_sample(self):
        self.assertEqual(summarize.median([12.0, 8.0, 10.0]), 10.0)
        with tempfile.TemporaryDirectory() as raw:
            log_dir = Path(raw)
            self.write_timings(
                log_dir,
                "mvn_clean_1\t8.00\t0\n"
                "mvn_clean_2\t10.00\t0\n"
                "mvn_clean_3\t12.00\t0\n"
                "mvnd_warm_clean_1\t3.00\t0\n",
            )
            summarize.main(log_dir)
            values = self.outputs(log_dir)
            self.assertEqual(values["mvn-median-seconds"], "10.00")
            self.assertEqual(values["warm-mvnd-seconds"], "3.00")
            self.assertEqual(values["warm-mvnd-speedup"], "3.33")

    def test_equal_warm_and_baseline_writes_soft_warning(self):
        with tempfile.TemporaryDirectory() as raw:
            log_dir = Path(raw)
            self.write_timings(
                log_dir,
                "mvn_clean_1\t4.00\t0\nmvnd_warm_clean_1\t4.00\t0\n",
            )
            summarize.main(log_dir)
            warning = (log_dir / "soft-warning.txt").read_text(encoding="utf-8")
            self.assertIn("4.00s", warning)
            self.assertIn("not faster", warning)
