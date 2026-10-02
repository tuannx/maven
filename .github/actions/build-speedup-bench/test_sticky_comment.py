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

"""Stdlib checks that the sticky comment updates only its own marker."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sticky_comment

MARKER = sticky_comment.MARKER


class StickyCommentTest(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._saved)

    def test_own_comment_id_matches_marker_only(self):
        comments = [
            {"id": 1, "body": "prose that mentions build-speedup-bench"},
            {"id": 2, "body": f"{MARKER}\n# previous table"},
            {"id": 3, "body": f"{MARKER}\n# later copy"},
        ]
        self.assertEqual(sticky_comment.own_comment_id(comments), 2)
        self.assertIsNone(sticky_comment.own_comment_id([{"id": 9, "body": "build-speedup-bench"}]))
        self.assertIsNone(sticky_comment.own_comment_id([]))
        self.assertIsNone(sticky_comment.own_comment_id(None))

    def test_plan_update_posts_or_patches_that_id_only(self):
        method, url = sticky_comment.plan_update(None, "tuannx/maven", "7")
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://api.github.com/repos/tuannx/maven/issues/7/comments")
        method, url = sticky_comment.plan_update(22, "tuannx/maven", "7")
        self.assertEqual(method, "PATCH")
        self.assertEqual(url, "https://api.github.com/repos/tuannx/maven/issues/comments/22")
        self.assertNotIn("/comments/1", url)
        self.assertNotIn("/comments/33", url)

    def _enable(self, summary_path):
        os.environ["BENCH_STICKY_COMMENT"] = "true"
        os.environ["BENCH_PR_NUMBER"] = "7"
        os.environ["GITHUB_TOKEN"] = "test-token"
        os.environ["GITHUB_REPOSITORY"] = "tuannx/maven"
        os.environ["BENCH_SUMMARY_PATH"] = str(summary_path)

    def test_main_patches_only_the_marked_comment(self):
        calls = []

        def fake_request(token, method, url, payload=None):
            calls.append((method, url, payload))
            if method == "GET":
                return 200, [
                    {"id": 11, "body": "build-speedup-bench without the html marker"},
                    {"id": 22, "body": f"{MARKER}\nold table"},
                    {"id": 33, "body": "unrelated review note"},
                ]
            return 200, {"id": 22}

        with tempfile.TemporaryDirectory() as raw:
            summary = Path(raw) / "summary.md"
            summary.write_text("# build-speedup-bench\n", encoding="utf-8")
            self._enable(summary)
            with mock.patch.object(sticky_comment, "request", fake_request):
                sticky_comment.main()
        self.assertEqual([call[0] for call in calls], ["GET", "PATCH"])
        self.assertTrue(calls[1][1].endswith("/issues/comments/22"))
        self.assertNotIn("/comments/11", calls[1][1])
        self.assertNotIn("/comments/33", calls[1][1])
        self.assertIn(MARKER, calls[1][2]["body"])

    def test_main_posts_when_no_comment_has_the_marker(self):
        calls = []

        def fake_request(token, method, url, payload=None):
            calls.append((method, url, payload))
            if method == "GET":
                return 200, [{"id": 11, "body": "build-speedup-bench mentioned only in prose"}]
            return 201, {"id": 99}

        with tempfile.TemporaryDirectory() as raw:
            summary = Path(raw) / "summary.md"
            summary.write_text("# build-speedup-bench\n", encoding="utf-8")
            self._enable(summary)
            with mock.patch.object(sticky_comment, "request", fake_request):
                sticky_comment.main()
        self.assertEqual(calls[1][0], "POST")
        self.assertTrue(calls[1][1].endswith("/issues/7/comments"))
        self.assertFalse(any(call[0] == "PATCH" for call in calls))

    def test_main_does_not_call_the_api_when_disabled(self):
        os.environ["BENCH_STICKY_COMMENT"] = "false"
        os.environ["BENCH_PR_NUMBER"] = "7"
        os.environ["GITHUB_TOKEN"] = "test-token"
        os.environ["GITHUB_REPOSITORY"] = "tuannx/maven"
        with mock.patch.object(sticky_comment, "request") as request:
            sticky_comment.main()
        request.assert_not_called()
