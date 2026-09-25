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
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

# Wall-clock the api/ reactor. Exit 0 when every timed build exits 0.
# A smaller speedup than a developer laptop is reported, not failed.
set -euo pipefail

export LC_ALL=C

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

LOG_DIR="${ROOT}/bench-logs"
mkdir -p "$LOG_DIR"

SOURCE_FILE="api/maven-api-annotations/src/main/java/org/apache/maven/api/annotations/Experimental.java"
INSTALLED_CACHE=0

COMMON=(
  -f api/pom.xml
  --batch-mode
  -q
  -DskipTests
  -Drat.skip=true
  -Dcheckstyle.skip=true
  -Denforcer.skip=true
  -T 1C
)

on_exit() {
  local rc=$?
  trap - EXIT
  restore_workspace || rc=1
  write_summary || true
  emit_soft_warning || true
  exit "$rc"
}
trap on_exit EXIT

restore_workspace() {
  local rc=0
  if [[ -f "$SOURCE_FILE" ]]; then
    git checkout -- "$SOURCE_FILE" || rc=1
  fi
  if [[ "$INSTALLED_CACHE" == 1 ]]; then
    rm -f .mvn/extensions.xml .mvn/maven-build-cache-config.xml || rc=1
  fi
  if [[ -n "$(git status --porcelain -- "$SOURCE_FILE" .mvn/extensions.xml .mvn/maven-build-cache-config.xml)" ]]; then
    echo "::error::Bench left the source edit or .mvn cache files in the worktree"
    git status --porcelain -- "$SOURCE_FILE" .mvn/extensions.xml .mvn/maven-build-cache-config.xml
    rc=1
  fi
  return "$rc"
}

note() {
  echo "$1" | tee -a "$LOG_DIR/notes.txt"
}

stop_daemon() {
  mvnd --stop >/dev/null 2>&1 || true
}

run_timed() {
  local name="$1"
  shift
  local logfile="$LOG_DIR/${name}.log"
  echo "=== ${name}: $* ==="
  {
    echo "+ $*"
  } >"$logfile"
  local rc=0
  local start end
  start="$(date +%s%N)"
  "$@" >>"$logfile" 2>&1 || rc=$?
  end="$(date +%s%N)"
  local secs
  secs="$(awk -v start="$start" -v end="$end" 'BEGIN { printf "%.2f", (end - start) / 1000000000 }')"
  if [[ ! "$secs" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
    echo "::error::${name} did not record a wall-clock time (got '${secs}')"
    exit 1
  fi
  printf '%s\t%s\t%s\n' "$name" "$secs" "$rc" >>"$LOG_DIR/timings.tsv"
  echo "${name} ${secs}s (exit ${rc})"
  if [[ "$rc" -ne 0 ]]; then
    echo "::error::${name} failed (exit ${rc}). Tail of ${logfile}:"
    tail -n 80 "$logfile" || true
    exit "$rc"
  fi
}

install_cache_extension() {
  cp .github/bench/extensions.xml .mvn/extensions.xml
  cp .github/bench/maven-build-cache-config.xml .mvn/maven-build-cache-config.xml
  INSTALLED_CACHE=1
}

cache_file_count() {
  if [[ -d "${HOME}/.m2/build-cache" ]]; then
    find "${HOME}/.m2/build-cache" -type f | wc -l | tr -d ' '
  else
    echo 0
  fi
}

write_summary() {
  python3 - "$LOG_DIR" <<'PY'
import os
import sys
from pathlib import Path

log_dir = Path(sys.argv[1])
samples = {}
timings = log_dir / "timings.tsv"
if timings.exists():
    for line in timings.read_text(encoding="utf-8").splitlines()[1:]:
        if not line.strip():
            continue
        scenario, seconds, rc = line.split("\t")
        samples[scenario] = (float(seconds), int(rc))

def median(keys):
    values = [samples[key][0] for key in keys if key in samples and samples[key][1] == 0]
    if not values:
        return None
    values.sort()
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2.0

baseline = median(["mvn_clean_1", "mvn_clean_2"])
warm = median(["mvnd_warm_clean_1", "mvnd_warm_clean_2"])

def fmt_seconds(value):
    if value is None:
        return "n/a"
    return f"{value:.2f}"

def fmt_ratio(seconds):
    if seconds is None or baseline is None or seconds <= 0:
        return "n/a"
    return f"{baseline / seconds:.2f}x"

# (label, seconds or None, ratio_ok)
rows = []

def add_sample(label, key):
    if key not in samples:
        rows.append((label, None, False))
        return
    seconds, rc = samples[key]
    shown = label if rc == 0 else f"{label} (exit {rc})"
    rows.append((shown, seconds, rc == 0))

def add_value(label, value):
    rows.append((label, value, value is not None))

add_sample("Host `mvn` clean package, run 1", "mvn_clean_1")
add_sample("Host `mvn` clean package, run 2", "mvn_clean_2")
add_value("Host `mvn` median (baseline)", baseline)
add_sample("`mvnd` cold daemon, clean package", "mvnd_cold_clean")
add_sample("`mvnd` warm clean package, run 1", "mvnd_warm_clean_1")
add_sample("`mvnd` warm clean package, run 2", "mvnd_warm_clean_2")
add_value("`mvnd` warm median", warm)
add_sample("Build-cache seed (`mvnd` clean package)", "cache_seed_clean")
add_sample("Build-cache no-change rebuild", "cache_no_change")
add_sample("Build-cache touch-only (mtime)", "cache_touch_only")
add_sample("Build-cache restore after deleting `target/`", "cache_restore_wiped_targets")
add_sample("Build-cache after one-line source edit", "cache_content_edit")

lines = [
    "# Maven build speedup bench (`api/` reactor)",
    "",
    "Wall-clock seconds for `-f api/pom.xml` package on the api/ reactor. Tests, RAT, Checkstyle, and Enforcer are skipped.",
    "Speedup is `mvn median / seconds` (higher is faster). The job succeeds when the builds succeed; a smaller ratio than a laptop run is not a failure.",
    "",
]
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
for label, seconds, ratio_ok in rows:
    ratio = fmt_ratio(seconds) if ratio_ok else "n/a"
    lines.append(f"| {label} | {fmt_seconds(seconds)} | {ratio} |")
lines.append("")

if "seed_m2" in samples:
    seconds, rc = samples["seed_m2"]
    lines.append(
        f"Untimed `.m2` seed (`mvn clean package`, excluded from the table): {seconds:.2f}s, exit {rc}."
    )
    lines.append("")

notes = log_dir / "notes.txt"
if notes.exists():
    lines.extend(["## Notes", ""])
    lines.extend(f"- {note}" for note in notes.read_text(encoding="utf-8").splitlines() if note.strip())
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
print(text, end="")
summary = os.environ.get("GITHUB_STEP_SUMMARY")
if summary:
    with open(summary, "a", encoding="utf-8") as handle:
        handle.write(text)
PY
}

emit_soft_warning() {
  local warning_file="$LOG_DIR/soft-warning.txt"
  if [[ -s "$warning_file" ]]; then
    echo "::warning title=Build speedup bench::$(tr '\n' ' ' <"$warning_file")"
  fi
}

{
  echo "java:"
  java -version 2>&1
  echo "mvn:"
  mvn -version
  echo "mvnd:"
  mvnd --version
  echo "nproc: $(nproc)"
  echo "runner arch: $(uname -m)"
} | tee "$LOG_DIR/tool-versions.txt"

printf '%s\n' "mvn|mvnd ${COMMON[*]} [clean] package" >"$LOG_DIR/command.txt"
printf 'scenario\tseconds\texit_code\n' >"$LOG_DIR/timings.tsv"

if [[ -e .mvn/extensions.xml || -e .mvn/maven-build-cache-config.xml ]]; then
  echo "::error::Refusing to bench with a pre-existing .mvn cache extension; baseline would not be host Maven alone"
  exit 1
fi

note "Baseline runs leave .mvn/extensions.xml unset. Cache runs copy .github/bench templates into .mvn/ and remove them afterward."
note "CI adds --batch-mode so the runner never waits on a prompt. The other flags match the api/ package measurement."
note "Parallelism is -T 1C (one thread per core). This runner has $(nproc) cores."

stop_daemon
note "Seeding ~/.m2 with one untimed mvn clean package so later timings are not dominated by plugin downloads."
run_timed seed_m2 mvn "${COMMON[@]}" clean package

run_timed mvn_clean_1 mvn "${COMMON[@]}" clean package
run_timed mvn_clean_2 mvn "${COMMON[@]}" clean package

stop_daemon
run_timed mvnd_cold_clean mvnd "${COMMON[@]}" clean package
run_timed mvnd_warm_clean_1 mvnd "${COMMON[@]}" clean package
run_timed mvnd_warm_clean_2 mvnd "${COMMON[@]}" clean package

stop_daemon
install_cache_extension
note "Cache extension: maven-build-cache-extension 1.2.0, enabled only for the following runs."
run_timed cache_seed_clean mvnd "${COMMON[@]}" clean package
cache_files="$(cache_file_count)"
note "Files under ~/.m2/build-cache after the cache seed: ${cache_files}."
if [[ "$cache_files" -lt 1 ]]; then
  echo "::error::maven-build-cache-extension did not populate ~/.m2/build-cache"
  exit 1
fi

run_timed cache_no_change mvnd "${COMMON[@]}" package

touch "$SOURCE_FILE"
note "Touch-only changed the mtime of ${SOURCE_FILE} and left its bytes unchanged."
run_timed cache_touch_only mvnd "${COMMON[@]}" package

rm -rf api/target api/*/target
note "Deleted api/target and api/*/target before the restore run."
run_timed cache_restore_wiped_targets mvnd "${COMMON[@]}" package

printf '\n// bench-speedup-content-edit\n' >>"$SOURCE_FILE"
note "Content edit appended a one-line comment to ${SOURCE_FILE}; git checkout restores it before the job finishes."
run_timed cache_content_edit mvnd "${COMMON[@]}" package
