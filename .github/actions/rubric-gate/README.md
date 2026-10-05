<!--
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
-->

# rubric-gate

Report-only v0. The GitHub check stays green. The verdict is the job summary and the `rubric-verdict` artifact.

Contract: [llms.txt](llms.txt). Procedure: [docs/agents/rubric-gate.md](../../../docs/agents/rubric-gate.md).

Dogfood: `.github/workflows/rubric-gate.yml`. Java CI remains the blocking verify.

Local:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s .github/actions/rubric-gate -p 'test_*.py'
python3 .github/actions/rubric-gate/cli.py all --base origin/master --out rubric-gate-results
```
