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

"""Doctrine advisory hard rule. ADR-0028."""


def scan_doctrine_advisory(paths, patch):
    text = patch or ""
    path_hit = any("redteam" in path or "pinned-doctrine" in path for path in paths)
    text_hit = "name: redteam-advisory" in text
    if not path_hit and not text_hit:
        return {
            "id": "doctrine-advisory",
            "passed": True,
            "evidence": "diff is not a doctrine advisory",
        }
    return {
        "id": "doctrine-advisory",
        "passed": False,
        "evidence": "doctrine advisory cannot score AUTO_MERGE_OK",
    }
