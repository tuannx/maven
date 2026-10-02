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

"""Create or update one pull request comment marked for this bench."""

import json
import os
import sys
import urllib.error
import urllib.request

MARKER = "<!-- build-speedup-bench -->"
API = "https://api.github.com"


def fail(message):
    print(f"::error::{message}", file=sys.stderr)
    sys.exit(1)


def request(token, method, url, payload=None):
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "build-speedup-bench",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        fail(f"GitHub API {method} {url} returned {error.code}: {detail[:500]}")


def own_comment_id(comments):
    """Return the id of the first comment that contains MARKER, else None."""
    for comment in comments or []:
        if MARKER in (comment.get("body") or ""):
            return comment.get("id")
    return None


def plan_update(existing_id, repo, pr):
    """POST a new issue comment, or PATCH only the comment id that holds MARKER."""
    if existing_id is None:
        return "POST", f"{API}/repos/{repo}/issues/{pr}/comments"
    return "PATCH", f"{API}/repos/{repo}/issues/comments/{existing_id}"


def find_comment(token, repo, pr):
    page = 1
    while page <= 5:
        status, comments = request(
            token,
            "GET",
            f"{API}/repos/{repo}/issues/{pr}/comments?per_page=100&page={page}",
        )
        if status != 200 or not comments:
            return None
        found = own_comment_id(comments)
        if found is not None:
            return found
        if len(comments) < 100:
            return None
        page += 1
    return None


def main():
    if os.environ.get("BENCH_STICKY_COMMENT", "").lower() != "true":
        print("sticky comment skipped (input is off)")
        return
    pr = os.environ.get("BENCH_PR_NUMBER", "").strip()
    if not pr:
        print("sticky comment skipped (this run is not a pull request)")
        return
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        fail("sticky comment needs GITHUB_TOKEN and GITHUB_REPOSITORY")
    summary_path = os.environ.get("BENCH_SUMMARY_PATH", "bench-logs/summary.md")
    if not os.path.isfile(summary_path):
        print(f"sticky comment skipped (missing {summary_path})")
        return
    with open(summary_path, encoding="utf-8") as handle:
        summary = handle.read().strip()
    body = f"{MARKER}\n{summary}\n"
    existing = find_comment(token, repo, pr)
    method, url = plan_update(existing, repo, pr)
    request(token, method, url, {"body": body})
    if existing is None:
        print(f"Created sticky bench comment on PR {pr}")
        return
    print(f"Updated sticky bench comment {existing} on PR {pr}")


if __name__ == "__main__":
    main()
