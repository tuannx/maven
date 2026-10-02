#!/usr/bin/env bash

#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

# Exits 0 on AUTO_FIX and ESCALATE. ADR-0006: v0 is report-only.

set -uo pipefail
cd "${GITHUB_WORKSPACE:-.}"
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1

args=("${RUBRIC_COMMAND}")
if [ -n "${RUBRIC_SCORER}" ]; then
  args+=(--scorer "${RUBRIC_SCORER}")
fi
if [ -n "${RUBRIC_BASE}" ]; then
  args+=(--base "${RUBRIC_BASE}")
fi
args+=(--out "${RUBRIC_OUT}" --loop "${RUBRIC_LOOP}" --llm-hook "${RUBRIC_LLM_HOOK}")
if [ -n "${RUBRIC_LLM_HOOK_COMMAND}" ]; then
  args+=(--llm-hook-command "${RUBRIC_LLM_HOOK_COMMAND}")
fi
args+=(--unit-test-rc "${RUBRIC_UNIT_TEST_RC}")

python3 "$GITHUB_ACTION_PATH/cli.py" "${args[@]}" || echo "::warning::rubric-gate cli exit $?"
exit 0
