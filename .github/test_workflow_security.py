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

_SCRIPT = Path(__file__).resolve().parent / "workflow_security.py"
_SPEC = importlib.util.spec_from_file_location("workflow_security", _SCRIPT)
workflow_security = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(workflow_security)


class WorkflowSecurityTest(unittest.TestCase):
    def test_pull_request_target_without_the_marker_is_a_finding(self):
        text = "on:\n  pull_request_target:\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n"
        self.assertIn("wf.yml: pull_request_target", workflow_security.scan_text("wf.yml", text))

    def test_reusable_workflow_only_is_allowed(self):
        text = (
            "on:\n  # workflow-security: reusable-workflow-only\n"
            "  pull_request_target:\n    types: [closed]\n"
            "jobs:\n  call:\n    uses: example/repo/.github/workflows/pr.yml@0123456789abcdef0123456789abcdef01234567\n"
        )
        self.assertEqual(workflow_security.scan_text("wf.yml", text), [])

    def test_untrusted_event_data_inside_run_is_a_finding(self):
        text = "jobs:\n  a:\n    steps:\n      - run: echo ${{ github.head_ref }}\n"
        findings = workflow_security.scan_text("wf.yml", text)
        self.assertEqual(len(findings), 1)
        self.assertIn("github.head_ref", findings[0])

    def test_gate_from_base_may_use_pull_request_target(self):
        text = (
            "on:\n  # workflow-security: gate-from-base\n  pull_request_target:\n"
            "jobs:\n  a:\n    steps:\n"
            "      - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567\n"
            "        with:\n          ref: ${{ github.event.pull_request.head.sha }}\n"
            "      - env:\n          BASE_SHA: ${{ github.event.pull_request.base.sha }}\n"
            "        run: git checkout \"$BASE_SHA\" -- .github/actions/rubric-gate\n"
        )
        self.assertEqual(workflow_security.scan_text("rubric-gate.yml", text), [])
        tainted = text.replace(
            'run: git checkout \"$BASE_SHA\"',
            "run: echo ${{ github.event.pull_request.head.sha }}",
        )
        self.assertTrue(workflow_security.scan_text("rubric-gate.yml", tainted))

    def test_event_data_passed_through_env_is_not_a_finding(self):
        text = "jobs:\n  a:\n    steps:\n      - env:\n          HEAD: ${{ github.head_ref }}\n        run: echo \"$HEAD\"\n"
        self.assertEqual(workflow_security.scan_text("wf.yml", text), [])

    def test_this_repository_has_no_findings(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(workflow_security.scan_workflows(root), [])


if __name__ == "__main__":
    unittest.main()
