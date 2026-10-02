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

"""Deterministic rubric scorers. Maven runs only when the diff selects modules."""

import io
import json
import os
import re
import shutil
import subprocess
import time
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

SCORERS = ("affected-build", "japicmp", "spotless", "comment-density", "bench-delta")

PRODUCT_TOPS = ("api", "impl", "compat", "apache-maven")

# japicmp is bound on these modules only. maven-api-* has no 3.9.8 baseline.
JAPICMP_MODULES = (
    "compat/maven-model",
    "compat/maven-model-builder",
    "compat/maven-plugin-api",
    "compat/maven-settings",
    "compat/maven-settings-builder",
    "compat/maven-toolchain-builder",
    "compat/maven-toolchain-model",
    "impl/maven-core",
)

# ADR-0008. Dogfood run 36996291340 warm-mvnd-speedup was 3.11; the prior run was 3.16.
BASELINE_SPEEDUP = 3.11
SPEEDUP_REGRESSION = 0.15
BENCH_SOURCE_PREFIX = ".github/actions/build-speedup-bench/"
BENCH_WORKFLOW = ".github/workflows/build-speedup-bench.yml"

SOURCE_SUFFIXES = (".py", ".java", ".sh", ".yml", ".yaml")
FORMAT_SUFFIXES = SOURCE_SUFFIXES + (".xml",)
REDUNDANT_PHRASES = (
    "this " + "function",
    "this " + "method",
    "note " + "that",
    "it is " + "important",
    "please " + "note",
)
PUBLIC_SIGNATURE = re.compile(r"^[+-]\s*(public|protected)\b")
SKIP_ARGS = ("-DskipITs", "-Drat.skip=true", "-Dcheckstyle.skip=true", "-Denforcer.skip=true")


def dim(score, evidence):
    text = evidence if isinstance(evidence, list) else [evidence]
    return {"score": score, "evidence": text}


def discover_modules(root):
    found = []
    root = Path(root)
    for top in PRODUCT_TOPS:
        base = root / top
        if not base.is_dir():
            continue
        for pom in base.rglob("pom.xml"):
            parts = pom.relative_to(base).parts
            if "src" in parts or "target" in parts:
                continue
            found.append(pom.parent.relative_to(root).as_posix())
    found.sort(key=len, reverse=True)
    return found


def module_for_path(path, modules):
    for module in modules:
        prefix = module + "/"
        if path.startswith(prefix):
            return module
    return None


def select_modules(paths, modules):
    ordered = sorted(modules, key=len, reverse=True)
    selected = []
    for path in paths:
        module = module_for_path(path, ordered)
        if module and module not in selected:
            selected.append(module)
    return selected


def maven_commands(modules, goal):
    grouped = {}
    for module in modules:
        parts = module.split("/")
        slot = grouped.setdefault(parts[0], {"all": False, "pl": []})
        if len(parts) == 1:
            slot["all"] = True
        elif not slot["all"]:
            slot["pl"].append(parts[-1])
    commands = []
    for aggregator, slot in sorted(grouped.items()):
        command = ["mvn", "-f", f"{aggregator}/pom.xml", "--batch-mode", "-T", "1C", *SKIP_ARGS]
        if goal != "test":
            command.append("-DskipTests")
        if not slot["all"] and slot["pl"]:
            command.extend(["-pl", ",".join(sorted(set(slot["pl"]))), "-am"])
        command.append(goal)
        commands.append(command)
    return commands


def root_build_changed(paths):
    return "pom.xml" in paths or ".mvn/maven.config" in paths


def plan_affected(paths, modules):
    if root_build_changed(paths):
        return {"needs_maven": False, "commands": [], "reason": "root-build-file"}
    selected = [module for module in select_modules(paths, modules) if module.count("/") >= 1]
    if not selected:
        return {"needs_maven": False, "commands": [], "reason": "no-product-modules"}
    return {"needs_maven": True, "commands": maven_commands(selected, "test"), "reason": "modules", "modules": selected}


def plan_japicmp(paths, modules):
    selected = [module for module in select_modules(paths, modules) if module in JAPICMP_MODULES]
    if not selected:
        return {"needs_maven": False, "commands": [], "reason": "no-japicmp-modules"}
    return {"needs_maven": True, "commands": maven_commands(selected, "verify"), "reason": "modules", "modules": selected}


def plan_spotless(paths, modules):
    java = [path for path in paths if path.endswith(".java")]
    if not java:
        return {"needs_maven": False, "commands": [], "reason": "no-java"}
    selected = select_modules(java, modules)
    leaves = [module for module in selected if module.count("/") >= 1]
    if not leaves:
        return {"needs_maven": False, "commands": [], "reason": "no-module"}
    return {"needs_maven": True, "commands": maven_commands(leaves, "spotless:check"), "reason": "java", "modules": leaves}


def public_signature_files(paths_or_patch):
    if isinstance(paths_or_patch, str):
        files = set()
        current = None
        for line in paths_or_patch.splitlines():
            if line.startswith("+++ b/"):
                current = line[6:]
            elif line.startswith("+") or line.startswith("-"):
                if current and "/src/main/java/" in current and current.endswith(".java") and current.startswith("api/"):
                    if PUBLIC_SIGNATURE.match(line):
                        files.add(current)
        return sorted(files)
    return []


def added_lines_by_file(patch):
    files = {}
    current = None
    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            files.setdefault(current, [])
        elif line.startswith("+") and not line.startswith("+++") and current:
            files[current].append(line[1:])
    return files


def strip_leading_comments(lines):
    kept = []
    started = False
    for line in lines:
        if not started:
            stripped = line.strip()
            header = (
                stripped == ""
                or stripped.startswith("#")
                or stripped.startswith("//")
                or stripped.startswith("/*")
                or stripped.startswith("*")
                or stripped.startswith("<!--")
                or stripped.startswith("-->")
            )
            if header:
                continue
            started = True
        kept.append(line)
    return kept


def comment_line(path, line):
    stripped = line.strip()
    if path.endswith(".java"):
        return stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*")
    return stripped.startswith("#")


def score_comment_density(patch):
    code = 0
    comments = 0
    redundant = []
    for path, lines in sorted(added_lines_by_file(patch).items()):
        if not path.endswith(SOURCE_SUFFIXES):
            continue
        for line in strip_leading_comments(lines):
            if not line.strip():
                continue
            lowered = line.lower()
            for phrase in REDUNDANT_PHRASES:
                if phrase in lowered:
                    redundant.append(f"{path}: {phrase}")
            if comment_line(path, line):
                comments += 1
            else:
                code += 1
    if code == 0 and comments == 0:
        return dim(3, "no added source lines")
    ratio = comments / max(code, 1)
    if redundant:
        return dim(1, f"redundant phrases: {', '.join(redundant[:5])}")
    if ratio > 0.45:
        return dim(1, f"comment ratio {ratio:.2f}")
    if ratio > 0.25:
        return dim(2, f"comment ratio {ratio:.2f}")
    return dim(3, f"comment ratio {ratio:.2f}")


def score_format(patch):
    hits = []
    for path, lines in sorted(added_lines_by_file(patch).items()):
        if not path.endswith(FORMAT_SUFFIXES):
            continue
        for line in lines:
            if line.rstrip("\n").endswith((" ", "\t")):
                hits.append(path)
                break
    if hits:
        return dim(1, "trailing whitespace in " + ", ".join(hits[:8]))
    return dim(3, "no trailing whitespace on added source lines")


def apply_spotless_result(heuristic, returncode, log):
    if returncode is None:
        return heuristic, "spotless not run"
    if returncode == 0:
        return heuristic, "spotless:check exit 0"
    lowered = log.lower()
    if "format violation" in lowered or "would be reformatted" in lowered:
        score = min(heuristic["score"], 1)
        return dim(score, heuristic["evidence"] + ["spotless reported format violations"]), "spotless violations"
    score = min(heuristic["score"], 2)
    return dim(score, heuristic["evidence"] + [f"spotless:check exit {returncode}"]), "spotless exit"


def interpret_maven(returncode, log, goal):
    lowered = log.lower()
    if returncode == 0:
        if goal == "test":
            return 3, 3, "maven test exit 0"
        return 3, None, f"maven {goal} exit 0"
    if "compilation error" in lowered or "could not resolve dependencies" in lowered:
        return 0, 1, "maven compilation or resolution failed"
    if "there are test failures" in lowered or "there are failures" in lowered:
        return 2, 0, "maven reported test failures"
    return 0, 1, f"maven {goal} exit {returncode}"


def intersects_bench(paths):
    for path in paths:
        if path == BENCH_WORKFLOW or path.startswith(BENCH_SOURCE_PREFIX):
            return True
    return False


def product_paths(paths):
    return [path for path in paths if path.split("/", 1)[0] in PRODUCT_TOPS]


def score_speedup(current, baseline=BASELINE_SPEEDUP, regression=SPEEDUP_REGRESSION):
    floor = baseline * (1.0 - regression)
    if current + 1e-9 < floor:
        return dim(1, f"warm-mvnd-speedup {current:.2f} below {floor:.2f}")
    return dim(3, f"warm-mvnd-speedup {current:.2f} within band of {baseline:.2f}")


def evaluate_bench(paths, speedup, fetch_error):
    if not intersects_bench(paths):
        if product_paths(paths):
            return dim(3, "product diff; build-speedup-bench did not run; not measured"), "skipped"
        return dim(3, "no bench sources in the diff"), "skipped"
    if fetch_error:
        return dim(2, fetch_error), "failed"
    if speedup is None:
        return dim(2, "bench artifact has no warm-mvnd-speedup"), "failed"
    scored = score_speedup(speedup)
    return scored, "ok"


def parse_speedup(text):
    for line in text.splitlines():
        if line.startswith("warm-mvnd-speedup="):
            value = line.split("=", 1)[1].strip()
            if not value:
                return None
            return float(value)
    return None


def speedup_from_zip(payload):
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if name.endswith("github_output.txt")]
        if not names:
            return None
        return parse_speedup(archive.read(names[0]).decode("utf-8"))


def choose_run(payload):
    # GitHub lists workflow_runs newest first. Score that run only.
    runs = payload.get("workflow_runs") or []
    return runs[0] if runs else None


def poll_speedup(get_json, get_zip, attempts, pause):
    last = "bench run not found"
    for _ in range(attempts):
        payload = get_json()
        run = choose_run(payload)
        if run is None:
            last = "bench run not found"
        elif run.get("conclusion") == "success":
            speedup = speedup_from_zip(get_zip(run["id"]))
            return speedup, None
        elif run.get("conclusion") in ("failure", "cancelled"):
            return None, f"bench run {run.get('conclusion')}"
        else:
            last = "bench run still in progress"
        if pause:
            pause()
    return None, last


def run_maven(commands, cwd):
    binary = shutil.which("mvn")
    if binary is None:
        return None, "mvn not on PATH"
    logs = []
    worst = 0
    for command in commands:
        command = [binary, *command[1:]]
        completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
        worst = worst or completed.returncode
        if completed.returncode != 0:
            worst = completed.returncode
        logs.append("$ " + " ".join(command))
        logs.append((completed.stdout + completed.stderr)[-2000:])
        if completed.returncode != 0:
            break
    return worst, "\n".join(logs)


def git_paths(root, base):
    completed = subprocess.run(
        ["git", "-c", "core.quotepath=false", "diff", "--name-only", "-z", f"{base}...HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    return [path for path in completed.stdout.split("\0") if path]


def git_patch(root, base):
    completed = subprocess.run(
        ["git", "-c", "core.quotepath=false", "diff", "--unified=0", f"{base}...HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    return completed.stdout


def result(scorer, status, dimensions, evidence):
    return {
        "scorer": scorer,
        "status": status,
        "dimensions": dimensions,
        "evidence": evidence if isinstance(evidence, list) else [evidence],
    }


def score_affected(paths, modules, maven_runner):
    plan = plan_affected(paths, modules)
    if plan["reason"] == "root-build-file":
        scored = dim(2, "root build file changed; Java CI runs verify; this gate does not rebuild the reactor")
        return result("affected-build", "skipped", {"correctness": scored, "tests": scored}, plan["reason"]), plan
    if plan["reason"] == "no-product-modules":
        scored = dim(3, "no product modules in the diff")
        return result("affected-build", "skipped", {"correctness": scored, "tests": scored}, plan["reason"]), plan
    returncode, log = maven_runner(plan["commands"])
    if returncode is None:
        scored = dim(2, log)
        body = result("affected-build", "maven_missing", {"correctness": scored, "tests": scored}, log)
        return body, plan
    correctness, tests, evidence = interpret_maven(returncode, log, "test")
    status = "ok" if returncode == 0 else "failed"
    body = result(
        "affected-build",
        status,
        {"correctness": dim(correctness, evidence), "tests": dim(tests, evidence)},
        evidence,
    )
    return body, plan


def score_japicmp(paths, patch, modules, maven_runner):
    plan = plan_japicmp(paths, modules)
    public = public_signature_files(patch)
    notes = []
    compat = 3
    if public:
        compat = 2
        notes.append("api public or protected signature lines changed; japicmp is not bound on maven-api")
    if plan["needs_maven"]:
        returncode, log = maven_runner(plan["commands"])
        if returncode is None:
            compat = min(compat, 2)
            notes.append(log)
            status = "maven_missing"
        else:
            score, _tests, evidence = interpret_maven(returncode, log, "verify")
            compat = min(compat, score)
            notes.append(evidence)
            status = "ok" if returncode == 0 else "failed"
    else:
        status = "skipped"
        if not notes:
            notes.append("no japicmp module and no api signature line in the diff")
    return result("japicmp", status, {"compat": dim(compat, notes)}, notes), plan


def score_spotless(paths, patch, modules, maven_runner):
    plan = plan_spotless(paths, modules)
    heuristic = score_format(patch)
    status = "skipped"
    note = "spotless not run"
    scored = heuristic
    if plan["needs_maven"]:
        returncode, log = maven_runner(plan["commands"])
        if returncode is None:
            status = "maven_missing"
            scored = dim(min(heuristic["score"], 2), heuristic["evidence"] + [log])
            note = log
        else:
            scored, note = apply_spotless_result(heuristic, returncode, log)
            status = "ok" if returncode == 0 else "failed"
    return result("spotless", status, {"clarity": scored}, note), plan


def score_comments(patch):
    scored = score_comment_density(patch)
    return result("comment-density", "ok", {"clarity": scored}, scored["evidence"]), {"needs_maven": False}


def score_bench(paths, speedup, fetch_error):
    scored, status = evaluate_bench(paths, speedup, fetch_error)
    return result("bench-delta", status, {"perf": scored}, scored["evidence"]), {"needs_maven": False}


def github_json(url, token):
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "rubric-gate",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def github_bytes(url, token):
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "rubric-gate",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=60) as response:
        return response.read()


def fetch_bench_speedup(repository, sha, token, attempts=30, pause_seconds=20):
    api = f"https://api.github.com/repos/{repository}"

    def get_json():
        return github_json(f"{api}/actions/workflows/build-speedup-bench.yml/runs?head_sha={sha}&per_page=5", token)

    def get_zip(run_id):
        listing = github_json(f"{api}/actions/runs/{run_id}/artifacts?per_page=20", token)
        artifact = next(item for item in listing.get("artifacts", []) if item.get("name") == "build-speedup-bench-logs")
        return github_bytes(artifact["archive_download_url"], token)

    return poll_speedup(get_json, get_zip, attempts, lambda: time.sleep(pause_seconds))


def default_maven_runner(cwd):
    def runner(commands):
        return run_maven(commands, cwd)

    return runner
