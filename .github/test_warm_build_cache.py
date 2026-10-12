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
import tempfile
import unittest
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent / "warm-build-cache.py"
_SPEC = importlib.util.spec_from_file_location("warm_build_cache", _SCRIPT)
warm_build_cache = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(warm_build_cache)


class WarmBuildCacheTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.templates = tempfile.TemporaryDirectory()
        self.root_path = Path(self.root.name)
        self.template_path = Path(self.templates.name)
        (self.root_path / ".mvn").mkdir()
        (self.root_path / ".mvn" / "maven.config").write_text("keep\n", encoding="utf-8")
        for name in warm_build_cache.TEMPLATE_NAMES:
            (self.template_path / name).write_text(f"<template>{name}</template>\n", encoding="utf-8")

    def tearDown(self):
        self.root.cleanup()
        self.templates.cleanup()

    def test_install_then_remove_leaves_the_existing_mvn_dir(self):
        copied = warm_build_cache.install(self.root_path, self.template_path)
        self.assertEqual(len(copied), 2)
        self.assertTrue((self.root_path / ".mvn" / "extensions.xml").is_file())
        self.assertEqual((self.root_path / ".mvn" / "maven.config").read_text(encoding="utf-8"), "keep\n")
        warm_build_cache.remove(self.root_path)
        self.assertFalse((self.root_path / ".mvn" / "extensions.xml").exists())
        self.assertFalse((self.root_path / ".mvn" / "maven-build-cache-config.xml").exists())
        self.assertTrue((self.root_path / ".mvn" / "maven.config").is_file())

    def test_install_refuses_to_replace_a_live_extension_file(self):
        warm_build_cache.install(self.root_path, self.template_path)
        with self.assertRaises(SystemExit):
            warm_build_cache.install(self.root_path, self.template_path)
        self.assertTrue((self.root_path / ".mvn" / "maven.config").is_file())

    def test_module_command_targets_one_module_without_a_clean_on_the_warm_run(self):
        cold = warm_build_cache.module_command("mvn", ["clean", "package"])
        warm = warm_build_cache.module_command("mvn", ["package"])
        self.assertEqual(cold[0], "mvn")
        self.assertIn("maven-api-core", cold)
        self.assertIn("-am", cold)
        self.assertEqual(cold[-2:], ["clean", "package"])
        self.assertEqual(warm[-1], "package")
        self.assertNotIn("clean", warm)


if __name__ == "__main__":
    unittest.main()
