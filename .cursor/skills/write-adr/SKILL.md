---
name: write-adr
description: "Record a non-trivial decision as an ADR with options, scores, trade-off, and revisit-when. Use before code that depends on the choice."
---

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

# write-adr

Record a non-trivial decision before the code that depends on it.

1. Copy `docs/adr/template.md` to `docs/adr/NNNN-slug.md`. `NNNN` is one greater than the highest existing number.
2. Fill `status`, `date`, `decided-by`, `Decision`, `Options`, `Trade-off`, `Revisit when`.
3. Score each option 0-3 for fit to determinism, least privilege, reversibility, and agent speed.
4. Near-tie order: ADR, stated priorities, existing code pattern, prior verdict, simpler or reversible.
5. Point a code comment at the ADR only when the why is not obvious from the name. Do not restate the ADR in the comment.
