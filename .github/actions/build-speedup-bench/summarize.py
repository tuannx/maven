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

"""Write the bench markdown table, soft warning, and GitHub Action outputs."""

import os
import re
import sys
from pathlib import Path


def median(values):
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def load_samples(log_dir):
    samples = {}
    timings = log_dir / "timings.tsv"
    if not timings.exists():
        return samples
    for line in timings.read_text(encoding="utf-8").splitlines()[1:]:
        if not line.strip():
            continue
        scenario, seconds, rc = line.split("\t")
        samples[scenario] = (float(seconds), int(rc))
    return samples


def numbered(samples, prefix):
    found = []
    pattern = re.compile(rf"{prefix}(\d+)$")
    for key, (seconds, rc) in samples.items():
        match = pattern.fullmatch(key)
        if match and rc == 0:
            found.append((int(match.group(1)), key, seconds))
    found.sort()
    return found


def fmt_seconds(value):
    if value is None:
        return "n/a"
    return f"{value:.2f}"


def main(log_dir):
    samples = load_samples(log_dir)
    pom = os.environ.get("BENCH_POM", "pom.xml")
    mvn_runs = numbered(samples, "mvn_clean_")
    warm_runs = numbered(samples, "mvnd_warm_clean_")
    baseline = median([seconds for _, _, seconds in mvn_runs])
    warm = median([seconds for _, _, seconds in warm_runs])

    def ratio(seconds, ok):
        if not ok or seconds is None or baseline is None or seconds <= 0:
            return "n/a"
        return f"{baseline / seconds:.2f}x"

    rows = []

    def add(label, seconds, ok):
        rows.append((label, seconds, ok))

    for number, _key, seconds in mvn_runs:
        add(f"Host `mvn` clean package, run {number}", seconds, True)
    if mvn_runs:
        add("Host `mvn` median (baseline)", baseline, baseline is not None)
    if "mvnd_cold_clean" in samples and samples["mvnd_cold_clean"][1] == 0:
        add("`mvnd` cold daemon, clean package", samples["mvnd_cold_clean"][0], True)
    for number, _key, seconds in warm_runs:
        add(f"`mvnd` warm clean package, run {number}", seconds, True)
    if warm_runs:
        add("`mvnd` warm median", warm, warm is not None)

    cache_rows = (
        ("cache_seed_clean", "Build-cache seed (`mvnd` clean package)"),
        ("cache_no_change", "Build-cache no-change rebuild"),
        ("cache_touch_only", "Build-cache touch-only (mtime)"),
        ("cache_restore_wiped_targets", "Build-cache restore after deleting `target/`"),
        ("cache_content_edit", "Build-cache after one-line source edit"),
    )
    for key, label in cache_rows:
        if key in samples and samples[key][1] == 0:
            add(label, samples[key][0], True)

    lines = [
        "# build-speedup-bench",
        "",
        f"Wall-clock seconds for `-f {pom}` package. Tests, RAT, Checkstyle, and Enforcer follow `extra-maven-args` (skipped by default).",
        "Speedup is `mvn median / seconds` (higher is faster). The action succeeds when the builds succeed. A smaller ratio than a laptop run is a warning, not a failure.",
        "",
        "Action: `tuannx/maven/.github/actions/build-speedup-bench`",
        "",
    ]
    revision = os.environ.get("BENCH_REVISION", "").strip()
    if revision:
        lines.append(f"Revision: `{revision}`")
        lines.append("")
    versions = log_dir / "tool-versions.txt"
    if versions.exists():
        lines.extend(["## Tools", "", "```", versions.read_text(encoding="utf-8").rstrip(), "```", ""])
    command = log_dir / "command.txt"
    if command.exists():
        lines.extend(["## Timed command", "", "```", command.read_text(encoding="utf-8").rstrip(), "```", ""])

    lines.extend(
        [
            "## Timings",
            "",
            "| Scenario | Seconds | Speedup vs mvn median |",
            "|---|---:|---:|",
        ]
    )
    if rows:
        for label, seconds, ok in rows:
            lines.append(f"| {label} | {fmt_seconds(seconds)} | {ratio(seconds, ok)} |")
    else:
        lines.append("| (no successful timed runs) | n/a | n/a |")
    lines.append("")

    if "seed_m2" in samples:
        seconds, rc = samples["seed_m2"]
        lines.append(
            f"Untimed `.m2` seed (`mvn clean package`, excluded from the table): {seconds:.2f}s, exit {rc}."
        )
        lines.append("")

    speedup = ""
    if baseline is not None and warm is not None and warm > 0:
        speedup = f"{baseline / warm:.2f}"
    cache_no_change = ""
    if "cache_no_change" in samples and samples["cache_no_change"][1] == 0:
        cache_no_change = f"{samples['cache_no_change'][0]:.2f}"
    output_values = {
        "mvn-median-seconds": fmt_seconds(baseline) if baseline is not None else "",
        "warm-mvnd-seconds": fmt_seconds(warm) if warm is not None else "",
        "warm-mvnd-speedup": speedup,
        "cache-no-change-seconds": cache_no_change,
        "summary-path": "bench-logs/summary.md",
    }
    lines.extend(
        [
            "## Outputs",
            "",
            "| Name | Value |",
            "|---|---|",
        ]
    )
    for name, value in output_values.items():
        lines.append(f"| `{name}` | {value or 'n/a'} |")
    lines.append("")

    notes = log_dir / "notes.txt"
    if notes.exists():
        note_lines = [note for note in notes.read_text(encoding="utf-8").splitlines() if note.strip()]
        if note_lines:
            lines.extend(["## Notes", ""])
            lines.extend(f"- {note}" for note in note_lines)
            lines.append("")

    warning_path = log_dir / "soft-warning.txt"
    if warning_path.exists():
        warning_path.unlink()
    if warm is not None and baseline is not None and warm >= baseline:
        warning = (
            f"Warm mvnd median ({warm:.2f}s) was not faster than mvn median ({baseline:.2f}s) on this runner."
        )
        warning_path.write_text(warning + "\n", encoding="utf-8")
        lines.extend([f"> **Warning:** {warning}", ""])

    text = "\n".join(lines).rstrip() + "\n"
    (log_dir / "summary.md").write_text(text, encoding="utf-8")
    (log_dir / "github_output.txt").write_text(
        "".join(f"{name}={value}\n" for name, value in output_values.items()),
        encoding="utf-8",
    )
    sys.stdout.write(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(text)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: summarize.py LOG_DIR")
    main(Path(sys.argv[1]))
