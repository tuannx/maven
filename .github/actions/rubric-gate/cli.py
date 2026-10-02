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

"""Plan, score, or merge the report-only rubric gate. Exit 0 is the caller's choice."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import merge
import score


def git_rev(root, ref):
    completed = subprocess.run(
        ["git", "rev-parse", ref],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def load_context(root, base):
    return score.git_paths(root, base), score.git_patch(root, base)


def write_output(name, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def maven_runner_for(root):
    return score.default_maven_runner(root)


def bench_inputs(paths, root):
    mode = os.environ.get("RUBRIC_GATE_FETCH_BENCH", "auto")
    if mode == "never" or not score.intersects_bench(paths):
        return None, None
    token = os.environ.get("GITHUB_TOKEN", "")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    sha = os.environ.get("GITHUB_SHA", "") or git_rev(root, "HEAD")
    if not token or not repository or not sha:
        return None, "bench sources changed and GITHUB_TOKEN, GITHUB_REPOSITORY, or SHA is missing"
    try:
        speedup, error = score.fetch_bench_speedup(repository, sha, token)
    except Exception as error:
        return None, f"bench fetch failed: {error}"
    return speedup, error


def run_one(scorer_name, paths, patch, modules, root):
    runner = maven_runner_for(root)
    if scorer_name == "affected-build":
        return score.score_affected(paths, modules, runner)
    if scorer_name == "japicmp":
        return score.score_japicmp(paths, patch, modules, runner)
    if scorer_name == "spotless":
        return score.score_spotless(paths, patch, modules, runner)
    if scorer_name == "comment-density":
        return score.score_comments(patch)
    if scorer_name == "bench-delta":
        speedup, error = bench_inputs(paths, root)
        return score.score_bench(paths, speedup, error)
    raise SystemExit(f"unknown scorer {scorer_name}")


def write_result(out_dir, body):
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{body['scorer']}.json"
    target.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def command_plan(args, paths, modules):
    if args.scorer == "affected-build":
        plan = score.plan_affected(paths, modules)
    elif args.scorer == "japicmp":
        plan = score.plan_japicmp(paths, modules)
    elif args.scorer == "spotless":
        plan = score.plan_spotless(paths, modules)
    else:
        plan = {"needs_maven": False}
    needs = "true" if plan.get("needs_maven") else "false"
    write_output("needs_maven", needs)
    print(f"needs_maven={needs}")
    return 0


def command_score(args, paths, patch, modules):
    body, plan = run_one(args.scorer, paths, patch, modules, Path(args.root))
    write_result(Path(args.out), body)
    write_output("needs_maven", "true" if plan.get("needs_maven") else "false")
    return 0


def load_results(out_dir):
    bodies = []
    for name in score.SCORERS:
        matches = sorted(out_dir.rglob(f"{name}.json"), key=lambda item: len(item.as_posix()))
        if matches:
            bodies.append(json.loads(matches[0].read_text(encoding="utf-8")))
    return bodies


def command_merge(args, paths, patch):
    root = Path(args.root)
    out_dir = Path(args.out)
    workflow = root / ".github/workflows/rubric-gate.yml"
    workflow_text = workflow.read_text(encoding="utf-8") if workflow.is_file() else None
    enabled = args.llm_hook.lower() == "true"
    document = merge.build_verdict(
        load_results(out_dir),
        patch,
        paths,
        workflow_text,
        args.loop,
        git_rev(root, "HEAD"),
        git_rev(root, args.base) if args.base else "",
        enabled,
        args.llm_hook_command,
        args.unit_test_rc,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    verdict_path = out_dir / "verdict.json"
    verdict_path.write_text(merge.dumps(document), encoding="utf-8")
    text = merge.summary_markdown(document)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as handle:
            handle.write(text)
    sys.stdout.write(text)
    write_output("verdict", document["verdict"])
    write_output("verdict-path", verdict_path.as_posix())
    return 0


def main(argv):
    parser = argparse.ArgumentParser(description="rubric-gate v0")
    parser.add_argument("command", choices=("plan", "score", "merge", "all"))
    parser.add_argument("--scorer", default="")
    parser.add_argument("--base", default="")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", default="rubric-gate-results")
    parser.add_argument("--loop", type=int, default=0)
    parser.add_argument("--llm-hook", default="false")
    parser.add_argument("--llm-hook-command", default="")
    parser.add_argument("--unit-test-rc", type=int, default=0)
    args = parser.parse_args(argv)
    root = Path(args.root)
    if not args.base:
        args.base = os.environ.get("RUBRIC_GATE_BASE", "")
    if args.command != "merge" and not args.base:
        raise SystemExit("rubric-gate needs --base or RUBRIC_GATE_BASE")
    paths, patch = load_context(root, args.base) if args.base else ([], "")
    modules = score.discover_modules(root)
    if args.command == "plan":
        return command_plan(args, paths, modules)
    if args.command == "score":
        return command_score(args, paths, patch, modules)
    if args.command == "all":
        for name in score.SCORERS:
            args.scorer = name
            command_score(args, paths, patch, modules)
        return command_merge(args, paths, patch)
    return command_merge(args, paths, patch)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
