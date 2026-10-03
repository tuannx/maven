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

"""Deterministic architecture and intent checks. ADR-0011. Stdlib only."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import score

BOUNDARIES = Path("docs/adr/boundaries.yml")
TEMPLATE = Path("docs/adr/template.md")
INDEX_FILES = ("AGENTS.md", "llms.txt")
PATH_PREFIXES = (
    "docs/",
    ".github/",
    ".cursor/",
    ".mvn/",
    "api/",
    "impl/",
    "compat/",
    "apache-maven/",
    "its/",
)
EXACT_PATHS = {"AGENTS.md", "llms.txt", "SECURITY.md", "pom.xml"}
SCOPE_LINE = re.compile(r"(?m)^scope:\s*(\S.*?)\s*$")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
TICK = re.compile(r"`([^`\n]+)`")
WRITE_SCOPE = re.compile(r"(?m)^[ \t]*([A-Za-z0-9_-]+):[ \t]*write[ \t]*$")
HEADING = re.compile(r"^##\s+(\S+)")
META = re.compile(r"^-\s+([A-Za-z0-9-]+):")


def parse_yaml(text):
    lines = text.splitlines()

    def rec(index, indent):
        mapping = {}
        items = []
        mode = None
        while index < len(lines):
            raw = lines[index]
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                index += 1
                continue
            current = len(raw) - len(raw.lstrip(" "))
            if current < indent:
                break
            if current != indent:
                raise ValueError(f"indent at line {index + 1}")
            if stripped.startswith("- "):
                if mode == "map":
                    raise ValueError(f"list inside map at line {index + 1}")
                mode = "list"
                items.append(stripped[2:].strip())
                index += 1
                continue
            if mode == "list":
                raise ValueError(f"map inside list at line {index + 1}")
            mode = "map"
            key, sep, rest = stripped.partition(":")
            if not sep:
                raise ValueError(f"missing colon at line {index + 1}")
            rest = rest.strip()
            if rest:
                mapping[key.strip()] = rest
                index += 1
            else:
                index, child = rec(index + 1, indent + 2)
                mapping[key.strip()] = child
        return index, (items if mode == "list" else mapping)

    _index, value = rec(0, 0)
    if not isinstance(value, dict):
        raise ValueError("boundaries.yml root must be a map")
    return value


def load_boundaries(root):
    path = Path(root) / BOUNDARIES
    if not path.is_file():
        return "docs/adr/boundaries.yml is missing"
    try:
        data = parse_yaml(path.read_text(encoding="utf-8"))
        groups = data["path_groups"]
        direction = data["dependency_direction"]
        privilege = data["least_privilege"]
        absent = data["absent_on_purpose"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        return f"docs/adr/boundaries.yml is unreadable: {error}"
    if not isinstance(groups, dict) or not isinstance(direction, dict):
        return "docs/adr/boundaries.yml is missing path_groups or dependency_direction"
    return {
        "path_groups": groups,
        "dependency_direction": direction,
        "least_privilege": privilege if isinstance(privilege, dict) else {},
        "absent_on_purpose": absent if isinstance(absent, list) else [],
    }


def path_in_prefix(path, prefix):
    if prefix.endswith("/"):
        return path.startswith(prefix)
    return path == prefix or path.startswith(prefix + "/")


def groups_for(path, groups):
    found = []
    for name, prefixes in groups.items():
        if any(path_in_prefix(path, prefix) for prefix in prefixes):
            found.append(name)
    return found


def classify(paths, groups):
    unknown = []
    touched = set()
    for path in paths:
        names = groups_for(path, groups)
        if not names:
            unknown.append(path)
        touched.update(names)
    return touched, unknown


def referenced_paths(text):
    found = []
    for match in LINK.finditer(text):
        target = match.group(1)
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        found.append(target.split("#", 1)[0])
    for match in TICK.finditer(text):
        token = match.group(1).strip()
        if token in EXACT_PATHS or token.startswith(PATH_PREFIXES):
            if " " not in token and "<" not in token:
                found.append(token)
    return found


def check_references(root, absent):
    failures = []
    seen = []
    for name in INDEX_FILES:
        path = Path(root) / name
        if not path.is_file():
            failures.append(f"missing index file {name}")
            continue
        for ref in referenced_paths(path.read_text(encoding="utf-8")):
            if ref in seen:
                continue
            seen.append(ref)
            target = Path(root) / ref
            if ref in absent:
                if target.exists():
                    failures.append(f"{ref} is named as absent and is on disk")
                continue
            if not target.exists():
                failures.append(f"{name} references {ref} and that path does not resolve")
    if failures:
        return failures, []
    return [], [f"paths referenced from {INDEX_FILES[0]} and {INDEX_FILES[1]} resolve"]


def skill_body(text):
    if not text.startswith("---\n"):
        return None
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return None
    return parts[2].strip() + "\n"


def check_skill_mirrors(root):
    docs = sorted((Path(root) / "docs" / "agents").glob("*.md"))
    if not docs:
        return ["docs/agents has no skill text"], []
    failures = []
    for doc in docs:
        skill = Path(root) / ".cursor" / "skills" / doc.stem / "SKILL.md"
        if not skill.is_file():
            failures.append(f"missing .cursor/skills/{doc.stem}/SKILL.md")
            continue
        body = skill_body(skill.read_text(encoding="utf-8"))
        expected = doc.read_text(encoding="utf-8").strip() + "\n"
        if body != expected:
            failures.append(f"docs/agents/{doc.name} and .cursor/skills/{doc.stem}/SKILL.md differ")
    if failures:
        return failures, []
    names = ", ".join(doc.stem for doc in docs)
    return [], [f"skill mirrors match docs/agents ({names})"]


def template_requirements(text):
    headings = []
    keys = []
    for line in text.splitlines():
        stripped = line.strip()
        heading = HEADING.match(stripped)
        if heading:
            headings.append(heading.group(1))
            continue
        meta = META.match(stripped)
        if meta:
            keys.append(meta.group(1))
    return headings, keys


def check_adrs(root):
    template_path = Path(root) / TEMPLATE
    if not template_path.is_file():
        return ["docs/adr/template.md is missing"], []
    headings, keys = template_requirements(template_path.read_text(encoding="utf-8"))
    if not headings or not keys:
        return ["docs/adr/template.md has no sections to match"], []
    failures = []
    count = 0
    for path in sorted((Path(root) / "docs" / "adr").glob("*.md")):
        if path.name == "template.md":
            continue
        count += 1
        text_lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
        for heading in headings:
            if not any(line.startswith(f"## {heading}") for line in text_lines):
                failures.append(f"{path.relative_to(root).as_posix()} missing ## {heading}")
        for key in keys:
            if not any(line.startswith(f"- {key}:") for line in text_lines):
                failures.append(f"{path.relative_to(root).as_posix()} missing {key}")
    if count == 0:
        return ["docs/adr has no ADR besides the template"], []
    if failures:
        return failures, []
    return [], [f"{count} ADR files match docs/adr/template.md"]


def check_action_index(root, paths):
    actions = []
    for path in paths:
        if path.startswith(".github/actions/") and path.endswith("/action.yml"):
            parts = path.split("/")
            if len(parts) >= 3:
                actions.append(parts[2])
    if not actions:
        return [], ["no new action.yml"]
    indexes = []
    for name in INDEX_FILES:
        file = Path(root) / name
        if file.is_file():
            indexes.append(file.read_text(encoding="utf-8"))
    blob = "\n".join(indexes)
    failures = []
    for name in actions:
        needle = f".github/actions/{name}"
        if needle not in blob:
            failures.append(f"index {needle} from AGENTS.md or llms.txt")
    if failures:
        return failures, []
    return [], ["new actions are indexed: " + ", ".join(actions)]


def check_least_privilege(root, paths, privilege):
    workflows = [
        path
        for path in paths
        if path.startswith(".github/workflows/") and path.endswith((".yml", ".yaml"))
    ]
    if not workflows:
        return [], ["no workflow file in the diff"]
    failures = []
    for path in workflows:
        file = Path(root) / path
        if not file.is_file():
            failures.append(f"missing workflow {path}")
            continue
        text = file.read_text(encoding="utf-8")
        for match in WRITE_SCOPE.finditer(text):
            scope = match.group(1)
            markers = privilege.get(scope) or []
            if not markers:
                failures.append(f"{path} grants {scope}: write")
                continue
            if not any(marker in text for marker in markers):
                failures.append(f"{path} grants {scope}: write without a least-privilege marker")
    if failures:
        return failures, []
    return [], ["workflows grant write only with a marker from boundaries.yml"]


def reactor_artifacts(root):
    found = {}
    for top in score.PRODUCT_TOPS:
        base = Path(root) / top
        if not base.is_dir():
            continue
        for pom in base.rglob("pom.xml"):
            if "src" in pom.parts or "target" in pom.parts:
                continue
            artifact, _deps = pom_reactor_deps(pom)
            if artifact:
                found[artifact] = top
    return found


def pom_reactor_deps(path):
    text = Path(path).read_text(encoding="utf-8")
    text = re.sub(r'\sxmlns(?::\w+)?="[^"]*"', "", text)
    text = re.sub(r'\sxsi:\w+="[^"]*"', "", text)
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        return None, str(error)
    for tag in ("dependencyManagement", "build", "reporting"):
        for node in list(root.findall(tag)):
            root.remove(node)
    artifact = root.findtext("artifactId")
    deps = []
    parent = root.findtext("parent/artifactId")
    parent_group = root.findtext("parent/groupId") or ""
    if parent and _reactor_group(parent_group):
        deps.append(parent)
    for dependency in root.findall("dependencies/dependency"):
        deps.extend(_dep_artifact(dependency))
    for dependency in root.findall("profiles/profile/dependencies/dependency"):
        deps.extend(_dep_artifact(dependency))
    return artifact, deps


def _reactor_group(group):
    return group in ("", "org.apache.maven", "${project.groupId}")


def _dep_artifact(dependency):
    group = dependency.findtext("groupId") or ""
    artifact = dependency.findtext("artifactId")
    if artifact and _reactor_group(group):
        return [artifact]
    return []


def check_dependency_direction(root, paths, direction):
    modules = score.discover_modules(root)
    selected = score.select_modules(paths, modules)
    pom_paths = []
    for module in selected:
        pom = Path(root) / module / "pom.xml"
        if pom.is_file():
            pom_paths.append(pom)
    for path in paths:
        if path.endswith("pom.xml"):
            pom = Path(root) / path
            if pom.is_file() and pom not in pom_paths:
                pom_paths.append(pom)
    if not pom_paths:
        return [], ["no affected module pom"]
    artifacts = reactor_artifacts(root)
    failures = []
    checked = []
    for pom in pom_paths:
        rel = pom.relative_to(root).as_posix()
        artifact, deps = pom_reactor_deps(pom)
        if artifact is None:
            return [f"{rel} could not be parsed: {deps}"], []
        source = artifacts.get(artifact)
        if source is None:
            source = rel.split("/", 1)[0]
        if source not in direction:
            return [f"no dependency direction for {source}"], []
        allowed = set(direction[source])
        checked.append(rel)
        for dep in deps:
            dest = artifacts.get(dep)
            if dest is None or dest == source:
                continue
            if dest not in allowed:
                failures.append(f"{rel} depends on {dest}:{dep}")
    if failures:
        return failures, []
    return [], ["reactor dependencies stay inside dependency_direction (" + ", ".join(checked[:8]) + ")"]


def contract_checks(root, paths, boundaries):
    pieces = [
        check_references(root, boundaries["absent_on_purpose"]),
        check_skill_mirrors(root),
        check_adrs(root),
        check_action_index(root, paths),
        check_least_privilege(root, paths, boundaries["least_privilege"]),
    ]
    failures = []
    passed = []
    for found, ok in pieces:
        failures.extend(found)
        passed.extend(ok)
    return failures, passed


def score_architecture(root, paths):
    loaded = load_boundaries(root)
    if isinstance(loaded, str):
        return score.no_evidence(loaded)
    touched, unknown = classify(paths, loaded["path_groups"])
    if not paths:
        return score.no_evidence("diff has no paths")
    if unknown:
        shown = ", ".join(unknown[:8])
        return score.no_evidence(f"unclassified path: {shown}")
    failures = []
    passed = []
    if "agent-contract" in touched or "ci" in touched:
        found, ok = contract_checks(root, paths, loaded)
        failures.extend(found)
        passed.extend(ok)
    if "product" in touched:
        found, ok = check_dependency_direction(root, paths, loaded["dependency_direction"])
        if found and (found[0].startswith("no dependency") or "could not be parsed" in found[0]):
            return score.no_evidence(found[0])
        failures.extend(found)
        passed.extend(ok)
    if failures:
        return score.dim(1, failures[:8])
    if not passed:
        return score.no_evidence("no structural check ran")
    return score.dim(3, passed)


def score_intent(paths, pr_body, groups):
    if pr_body is None:
        return score.no_evidence("pull request body was not supplied")
    match = SCOPE_LINE.search(pr_body)
    if match is None:
        return score.dim(1, "declare a scope line naming path groups from docs/adr/boundaries.yml")
    names = [part.strip() for part in match.group(1).split(",") if part.strip()]
    unknown = [name for name in names if name not in groups]
    if unknown or not names:
        shown = ", ".join(unknown) if unknown else "(empty)"
        return score.dim(1, f"scope names an unknown path group: {shown}")
    outside = [path for path in paths if not any(groups_for(path, {name: groups[name]}) for name in names)]
    if outside:
        return score.dim(1, "outside declared scope: " + ", ".join(outside[:8]))
    joined = ", ".join(names)
    return score.dim(3, f"scope {joined} covers {len(paths)} paths")
