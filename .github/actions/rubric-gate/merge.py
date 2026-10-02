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

"""Merge scorer JSON into a schema-valid verdict. v0 never sets blocking true."""

import json
import re
import shlex
import subprocess

import score
import validate

DIMENSIONS = (
    "correctness",
    "intent",
    "compat",
    "security",
    "perf",
    "architecture",
    "clarity",
    "determinism",
    "tests",
)
TIE_BREAK = (
    "adr",
    "stated_priorities",
    "existing_code_pattern",
    "prior_verdict",
    "simpler_reversible",
)
HARD_RULES = ("secrets", "contents-write", "third-party-push", "report-only", "gate-unit-tests")
ACTION_DIRS = ("build-speedup-bench", "rubric-gate")
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
)
NONDETERMINISTIC = re.compile(r"\brandom\.|datetime\.now\(|time\.time\(")


def added_by_file(patch):
    return score.added_lines_by_file(patch)


def hard_rule(rule_id, passed, evidence):
    return {"id": rule_id, "passed": passed, "evidence": evidence}


def scan_secrets(patch):
    for path, lines in added_by_file(patch).items():
        for line in lines:
            for pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    return hard_rule("secrets", False, f"secret pattern in {path}")
    return hard_rule("secrets", True, "no secret pattern on added lines")


def scan_contents_write(patch):
    for path, lines in added_by_file(patch).items():
        if not path.endswith((".yml", ".yaml")):
            continue
        for line in lines:
            if re.search(r"(?i)contents:\s*write", line):
                return hard_rule("contents-write", False, f"contents: write added in {path}")
    return hard_rule("contents-write", True, "no added contents: write")


def scan_third_party(patch):
    push = "git " + "push"
    create = "gh " + "pr create"
    pattern = re.compile(r"\b" + re.escape(push) + r"\b|\b" + re.escape(create) + r"\b")
    for path, lines in added_by_file(patch).items():
        for line in lines:
            if "apache/maven" in line and pattern.search(line):
                return hard_rule("third-party-push", False, f"push or pr create toward apache/maven in {path}")
    return hard_rule("third-party-push", True, "no push or pr create toward apache/maven")


def scan_report_only(workflow_text):
    if workflow_text is None:
        return hard_rule("report-only", True, "workflow text not supplied")
    if re.search(r"(?i)contents:\s*write", workflow_text):
        return hard_rule("report-only", False, "rubric-gate workflow grants contents: write")
    if re.search(r"(?m)^\s*exit 1\s*$", workflow_text):
        return hard_rule("report-only", False, "rubric-gate workflow exits 1")
    return hard_rule("report-only", True, "workflow has no contents: write and no exit 1")


def score_security(rules):
    failed = [rule for rule in rules if rule["id"] in {"secrets", "contents-write", "third-party-push"} and not rule["passed"]]
    if failed:
        return score.dim(0, failed[0]["evidence"])
    return score.dim(3, "secret, contents: write, and third-party push rules passed")


def score_intent(paths, patch):
    new_action = any(path.startswith(".github/actions/") and path.endswith("/action.yml") for path in paths)
    indexed = any(path == "llms.txt" or path.endswith("/llms.txt") for path in paths)
    if new_action and not indexed:
        return score.dim(1, "action.yml added and no llms.txt in the diff")
    fix_marker = "FIX" + "ME"
    triple = "XX" + "X"
    for path, lines in added_by_file(patch).items():
        for line in lines:
            if fix_marker in line or triple in line:
                return score.dim(1, f"banned marker added in {path}")
    return score.dim(3, "new actions are indexed; no banned marker added")


def score_architecture(paths):
    outliers = []
    for path in paths:
        if path.startswith(".github/actions/"):
            parts = path.split("/")
            name = parts[2] if len(parts) > 2 else ""
            if name not in ACTION_DIRS:
                outliers.append(path)
        elif path in {"AGENTS.md", "llms.txt", "pom.xml"}:
            continue
        elif path.startswith(("docs/", ".cursor/", ".github/", ".mvn/", "api/", "impl/", "compat/", "apache-maven/", "its/")):
            continue
        else:
            outliers.append(path)
    if outliers:
        return score.dim(2, "paths outside the agent and product trees: " + ", ".join(sorted(outliers)[:8]))
    return score.dim(3, "diff stays in the agent contract paths or the product tree")


def score_determinism(patch):
    hits = []
    for path, lines in added_by_file(patch).items():
        if not path.endswith(".py"):
            continue
        for line in score.strip_leading_comments(lines):
            if NONDETERMINISTIC.search(line):
                hits.append(path)
                break
    if hits:
        return score.dim(1, "nondeterministic call in " + ", ".join(hits))
    return score.dim(3, "no random, datetime.now, or time.time on added Python lines")


def combine(parts):
    score_value = min(part["score"] for part in parts)
    evidence = []
    for part in parts:
        evidence.extend(part["evidence"])
    return score.dim(score_value, evidence)


def decide(dimensions, rules, loop):
    if any(not rule["passed"] for rule in rules):
        return "ESCALATE"
    scores = [dimensions[name]["score"] for name in DIMENSIONS]
    if any(value == 0 for value in scores):
        return "ESCALATE"
    if all(value == 3 for value in scores):
        return "AUTO_MERGE_OK"
    if loop >= 2:
        return "ESCALATE"
    return "AUTO_FIX"


def scorer_view(body):
    return {"status": body["status"], "evidence": body["evidence"]}


def missing_scorer(name):
    return {"scorer": name, "status": "missing", "dimensions": {}, "evidence": [f"{name} result missing"]}


def run_llm_hook(enabled, command, dimensions):
    if not enabled:
        return {"enabled": False, "status": "disabled", "notes": []}
    if not command.strip():
        return {"enabled": True, "status": "missing_command", "notes": []}
    try:
        completed = subprocess.run(
            shlex.split(command),
            input=json.dumps({"dimensions": dimensions}, sort_keys=True),
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"enabled": True, "status": "failed", "notes": [str(error)[:200]]}
    if completed.returncode != 0:
        return {"enabled": True, "status": "failed", "notes": [completed.stderr[-200:] or "hook exit"]}
    try:
        payload = json.loads(completed.stdout or "{}")
    except json.JSONDecodeError:
        return {"enabled": True, "status": "failed", "notes": ["hook stdout is not JSON"]}
    notes = payload.get("notes") if isinstance(payload, dict) else []
    if not isinstance(notes, list):
        notes = []
    cleaned = [str(note) for note in notes[:20]]
    cleaned.append("v0 hook cannot change scores")
    return {"enabled": True, "status": "ok", "notes": cleaned}


def build_verdict(results, patch, paths, workflow_text, loop, head_sha, base_sha, llm_enabled, llm_command, unit_test_rc):
    by_name = {body["scorer"]: body for body in results}
    for name in score.SCORERS:
        by_name.setdefault(name, missing_scorer(name))
    rules = [
        scan_secrets(patch),
        scan_contents_write(patch),
        scan_third_party(patch),
        scan_report_only(workflow_text),
    ]
    if unit_test_rc == 0:
        rules.append(hard_rule("gate-unit-tests", True, "rubric-gate unit tests exit 0"))
    else:
        rules.append(hard_rule("gate-unit-tests", False, f"rubric-gate unit tests exit {unit_test_rc}"))

    clarity_parts = []
    for name in ("spotless", "comment-density"):
        part = by_name[name]["dimensions"].get("clarity")
        if part:
            clarity_parts.append(part)
    if not clarity_parts:
        clarity_parts.append(score.dim(0, "clarity scorers missing"))

    dimensions = {
        "correctness": by_name["affected-build"]["dimensions"].get("correctness") or score.dim(0, "affected-build missing"),
        "tests": by_name["affected-build"]["dimensions"].get("tests") or score.dim(0, "affected-build missing"),
        "compat": by_name["japicmp"]["dimensions"].get("compat") or score.dim(0, "japicmp missing"),
        "perf": by_name["bench-delta"]["dimensions"].get("perf") or score.dim(0, "bench-delta missing"),
        "clarity": combine(clarity_parts),
        "security": score_security(rules),
        "intent": score_intent(paths, patch),
        "architecture": score_architecture(paths),
        "determinism": score_determinism(patch),
    }
    if unit_test_rc != 0:
        dimensions["tests"] = score.dim(0, dimensions["tests"]["evidence"] + [f"unit tests exit {unit_test_rc}"])

    hook = run_llm_hook(llm_enabled, llm_command, dimensions)
    document = {
        "schema_version": 1,
        "verdict": decide(dimensions, rules, loop),
        "blocking": False,
        "loop": loop,
        "head_sha": head_sha,
        "base_sha": base_sha,
        "tie_break": list(TIE_BREAK),
        "dimensions": dimensions,
        "hard_rules": rules,
        "scorers": {name: scorer_view(by_name[name]) for name in score.SCORERS},
        "llm_hook": hook,
    }
    errors = validate.validate(document)
    if errors:
        document = fallback(errors, head_sha, base_sha, loop)
    return document


def fallback(errors, head_sha, base_sha, loop):
    evidence = "verdict failed schema: " + "; ".join(errors[:8])
    broken = score.dim(0, evidence)
    dimensions = {name: broken for name in DIMENSIONS}
    rules = [hard_rule("secrets", False, evidence)]
    return {
        "schema_version": 1,
        "verdict": "ESCALATE",
        "blocking": False,
        "loop": loop,
        "head_sha": head_sha,
        "base_sha": base_sha,
        "tie_break": list(TIE_BREAK),
        "dimensions": dimensions,
        "hard_rules": rules,
        "scorers": {name: {"status": "missing", "evidence": [evidence]} for name in score.SCORERS},
        "llm_hook": {"enabled": False, "status": "disabled", "notes": []},
    }


def summary_markdown(document):
    lines = [
        "# rubric-gate",
        "",
        f"Verdict: `{document['verdict']}` (blocking `{str(document['blocking']).lower()}`, loop {document['loop']}).",
        "",
        "| Dimension | Score | Evidence |",
        "|---|---:|---|",
    ]
    for name in DIMENSIONS:
        item = document["dimensions"][name]
        evidence = "; ".join(item["evidence"])
        lines.append(f"| {name} | {item['score']} | {evidence} |")
    lines.extend(["", "| Hard rule | Passed | Evidence |", "|---|---|---|"])
    for rule in document["hard_rules"]:
        lines.append(f"| {rule['id']} | {str(rule['passed']).lower()} | {rule['evidence']} |")
    lines.append("")
    return "\n".join(lines)


def dumps(document):
    return json.dumps(document, indent=2, sort_keys=True) + "\n"
