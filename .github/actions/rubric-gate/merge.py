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
import structure
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
HARD_RULES = (
    "secrets",
    "contents-write",
    "third-party-push",
    "report-only",
    "gate-unit-tests",
    "hidden-code",
    "forged-verdict",
    "tests-weakened",
    "perf-claim",
)
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


# Code dropped under a docs or skill prefix still classifies as agent-contract.
# ADR-0013. Suffixes only: a markdown ADR stays allowed.
HIDDEN_CODE_PREFIXES = ("docs/", ".cursor/")
HIDDEN_CODE_SUFFIXES = (".java", ".xml", ".py", ".class", ".jar", ".sh")
TEST_PATH = re.compile(r"(^|/)(test_.+\.py|.+Tests?\.java)$|src/test/")
ASSERTION = re.compile(
    r"(self\.assert[A-Za-z0-9_]+|assertEquals|assertNotEquals|assertTrue|assertFalse|"
    r"assertNull|assertNotNull|assertSame|assertNotSame|assertThat|@Test\b)"
)
PERF_CLAIM = re.compile(r"warm-mvnd-speedup|\bspeedup\s*[:=]?\s*\d", re.IGNORECASE)


def hidden_code_path(path):
    if not path.startswith(HIDDEN_CODE_PREFIXES):
        return False
    if path.endswith(HIDDEN_CODE_SUFFIXES):
        return True
    name = path.rsplit("/", 1)[-1]
    return name == "pom.xml"


def scan_hidden_code(paths):
    hidden = [path for path in paths if hidden_code_path(path)]
    if hidden:
        shown = ", ".join(hidden[:8])
        return hard_rule("hidden-code", False, f"code path under docs or .cursor: {shown}")
    return hard_rule("hidden-code", True, "no code path under docs or .cursor")


def verdict_json_path(path):
    return path == "verdict.json" or path.endswith("/verdict.json")


def scan_forged_verdict(paths, patch, head_sha, base_sha):
    forged = [path for path in paths if verdict_json_path(path)]
    if not forged:
        return hard_rule("forged-verdict", True, "no verdict.json in the diff")
    reasons = []
    added = added_by_file(patch)
    for path in forged[:4]:
        reasons.append(f"{path} is in the diff")
        blob = "\n".join(added.get(path, [])).strip()
        if not blob:
            continue
        try:
            document = json.loads(blob)
        except json.JSONDecodeError:
            reasons.append(f"{path} is not a single JSON document")
            continue
        if not isinstance(document, dict):
            reasons.append(f"{path} is not a JSON object")
            continue
        if document.get("verdict") == "AUTO_MERGE_OK":
            reasons.append(f"{path} claims AUTO_MERGE_OK")
        if str(document.get("head_sha")) != str(head_sha):
            reasons.append(f"{path} head_sha {document.get('head_sha')} != {head_sha}")
        if str(document.get("base_sha")) != str(base_sha):
            reasons.append(f"{path} base_sha {document.get('base_sha')} != {base_sha}")
    return hard_rule("forged-verdict", False, "; ".join(reasons))


def test_path(path):
    return bool(TEST_PATH.search(path))


def scan_tests_weakened(patch):
    old = None
    new = None
    removed = {}
    added = {}
    deleted = []
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            old = None
            new = None
            continue
        if line.startswith("--- "):
            old = line[4:]
            if old.startswith("a/"):
                old = old[2:]
            continue
        if line.startswith("+++ "):
            new = line[4:]
            if new.startswith("b/"):
                new = new[2:]
            if new == "/dev/null" and old and test_path(old):
                deleted.append(old)
            continue
        path = new if new and new != "/dev/null" else old
        if not path or path == "/dev/null" or not test_path(path):
            continue
        if line.startswith("+") and not line.startswith("+++"):
            text = line[1:].strip()
            if ASSERTION.search(text):
                added[text] = added.get(text, 0) + 1
        elif line.startswith("-") and not line.startswith("---"):
            text = line[1:].strip()
            if ASSERTION.search(text):
                removed[text] = removed.get(text, 0) + 1
    missing = []
    for text, count in removed.items():
        gap = count - added.get(text, 0)
        if gap > 0:
            missing.append(text)
    if not deleted and not missing:
        return hard_rule("tests-weakened", True, "no deleted test file and no removed assertion")
    parts = []
    if deleted:
        parts.append("deleted test file: " + ", ".join(deleted[:4]))
    if missing:
        parts.append("removed assertion not re-added: " + missing[0])
    return hard_rule("tests-weakened", False, "; ".join(parts))


def scan_perf_claim(pr_body, bench_status):
    if not pr_body or PERF_CLAIM.search(pr_body) is None:
        return hard_rule("perf-claim", True, "no speedup claim in the pull request body")
    if bench_status == "ok":
        return hard_rule("perf-claim", True, "bench-delta status ok")
    return hard_rule("perf-claim", False, f"speedup claim while bench-delta status is {bench_status}")


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


WRITE_PERMISSION = re.compile(
    r"(?i)(contents|actions|pull-requests|checks|packages|security-events|id-token):\s*write"
)


def score_intent(paths, pr_body, root):
    loaded = structure.load_boundaries(root)
    if isinstance(loaded, str):
        return score.no_evidence(loaded)
    return structure.score_intent(paths, pr_body, loaded["path_groups"])


def score_architecture(root, paths):
    return structure.score_architecture(root, paths)


def score_determinism(patch):
    hits = []
    saw_python = False
    for path, lines in added_by_file(patch).items():
        if not path.endswith(".py"):
            continue
        saw_python = True
        for line in score.strip_leading_comments(lines):
            if NONDETERMINISTIC.search(line):
                hits.append(path)
                break
    if not saw_python:
        return score.not_applicable("no added Python")
    if hits:
        return score.dim(1, "nondeterministic call in " + ", ".join(hits))
    return score.dim(3, "no random, datetime.now, or time.time on added Python lines")


def risky_paths(paths, patch):
    added = added_by_file(patch)
    risky = []
    for path in paths:
        top = path.split("/", 1)[0]
        build_file = path == "pom.xml" or path.startswith(".mvn/") or path.endswith("/pom.xml") or path.endswith("pom.xml")
        if top in score.PRODUCT_TOPS or build_file:
            risky.append(path)
            continue
        if path.startswith(".github/workflows/") and path.endswith((".yml", ".yaml")):
            if WRITE_PERMISSION.search("\n".join(added.get(path, []))):
                risky.append(path)
    return risky


def combine(parts):
    applicable = [part for part in parts if part.get("state") != "not_applicable"]
    if not applicable:
        return score.not_applicable("no applicable clarity signal")
    evidence = []
    for part in applicable:
        evidence.extend(part["evidence"])
    if any(part.get("state") == "no_evidence" for part in applicable):
        values = [part["score"] for part in applicable if "score" in part]
        return score.no_evidence(evidence, min(values) if values else 2)
    return score.dim(min(part["score"] for part in applicable), evidence)


def decide(dimensions, rules, loop, risky=False):
    if any(not rule["passed"] for rule in rules):
        return "ESCALATE"
    for name in ("architecture", "intent"):
        if dimensions[name]["state"] != "scored":
            return "ESCALATE"
    applicable = []
    for name in DIMENSIONS:
        item = dimensions[name]
        if item["state"] == "not_applicable":
            continue
        if item["state"] == "no_evidence" and risky:
            return "ESCALATE"
        applicable.append(item["score"])
    if any(value == 0 for value in applicable):
        return "ESCALATE"
    if applicable and all(value == 3 for value in applicable):
        return "AUTO_MERGE_OK"
    if loop >= 2:
        return "ESCALATE"
    return "AUTO_FIX"


def scorer_view(body):
    return {"status": body["status"], "evidence": body["evidence"]}


def missing_scorer(name):
    return {
        "scorer": name,
        "status": "missing",
        "dimensions": {},
        "evidence": [f"{name} result missing"],
    }


def no_evidence_rule(dimensions, risky):
    blind = [name for name in DIMENSIONS if dimensions[name]["state"] == "no_evidence"]
    if blind and risky:
        return hard_rule(
            "no-evidence-risky",
            False,
            "no_evidence on " + ", ".join(blind) + "; risky paths present",
        )
    if blind:
        return hard_rule("no-evidence-risky", True, "no_evidence capped at 2; paths are not risky")
    return hard_rule("no-evidence-risky", True, "no no_evidence dimension")


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


def structure_measured_rule(dimensions):
    blind = [name for name in ("architecture", "intent") if dimensions[name]["state"] != "scored"]
    if blind:
        return hard_rule("structure-measured", False, "cannot measure " + ", ".join(blind))
    return hard_rule("structure-measured", True, "architecture and intent are scored")


def build_verdict(
    results,
    patch,
    paths,
    workflow_text,
    loop,
    head_sha,
    base_sha,
    llm_enabled,
    llm_command,
    unit_test_rc,
    root=".",
    pr_body=None,
):
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
    rules.append(scan_hidden_code(paths))
    rules.append(scan_forged_verdict(paths, patch, head_sha, base_sha))
    rules.append(scan_tests_weakened(patch))
    rules.append(scan_perf_claim(pr_body, by_name.get("bench-delta", {}).get("status")))

    clarity_parts = []
    for name in ("spotless", "comment-density"):
        part = by_name[name]["dimensions"].get("clarity")
        if part:
            clarity_parts.append(part)
    if not clarity_parts:
        clarity_parts.append(score.no_evidence("clarity scorers missing"))

    def owned(scorer_name, dimension):
        found = by_name[scorer_name]["dimensions"].get(dimension)
        if found:
            return found
        return score.no_evidence(f"{scorer_name} result missing")

    dimensions = {
        "correctness": owned("affected-build", "correctness"),
        "tests": owned("affected-build", "tests"),
        "compat": owned("japicmp", "compat"),
        "perf": owned("bench-delta", "perf"),
        "clarity": combine(clarity_parts),
        "security": score_security(rules),
        "intent": score_intent(paths, pr_body, root),
        "architecture": score_architecture(root, paths),
        "determinism": score_determinism(patch),
    }
    if unit_test_rc != 0:
        dimensions["tests"] = score.dim(0, dimensions["tests"]["evidence"] + [f"unit tests exit {unit_test_rc}"])

    risky = risky_paths(paths, patch)
    rules.append(no_evidence_rule(dimensions, risky))
    rules.append(structure_measured_rule(dimensions))
    hook = run_llm_hook(llm_enabled, llm_command, dimensions)
    document = {
        "schema_version": 2,
        "verdict": decide(dimensions, rules, loop, bool(risky)),
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
        "schema_version": 2,
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
        shown = "n/a" if item["state"] == "not_applicable" else str(item["score"])
        lines.append(f"| {name} | {item['state']} {shown} | {evidence} |")
    lines.extend(["", "| Hard rule | Passed | Evidence |", "|---|---|---|"])
    for rule in document["hard_rules"]:
        lines.append(f"| {rule['id']} | {str(rule['passed']).lower()} | {rule['evidence']} |")
    lines.append("")
    return "\n".join(lines)


def dumps(document):
    return json.dumps(document, indent=2, sort_keys=True) + "\n"
