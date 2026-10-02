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

# Wall-clock a Maven reactor. Exit 0 when every timed build exits 0.
# A smaller speedup than a developer laptop is reported, not failed.
set -euo pipefail

export LC_ALL=C

ACTION_DIR="${BENCH_ACTION_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
if [[ -n "${GITHUB_WORKSPACE:-}" ]]; then
  cd "$GITHUB_WORKSPACE"
else
  cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
fi

BENCH_POM="${BENCH_POM:-pom.xml}"
BENCH_SCENARIOS="${BENCH_SCENARIOS:-mvn,mvnd,build-cache}"
BENCH_MVN_RUNS="${BENCH_MVN_RUNS:-2}"
BENCH_MVND_WARM_RUNS="${BENCH_MVND_WARM_RUNS:-2}"
BENCH_THREADS="${BENCH_THREADS:-1C}"
BENCH_EXTRA_ARGS="${BENCH_EXTRA_ARGS:--DskipTests -Drat.skip=true -Dcheckstyle.skip=true -Denforcer.skip=true}"
BENCH_TOUCH_FILE="${BENCH_TOUCH_FILE:-}"

LOG_DIR="${PWD}/bench-logs"
SOURCE_FILE=""
SOURCE_BACKUP=""
INSTALLED_CACHE=0
CREATED_MVN_DIR=0

trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

want() {
  local needle="$1"
  local item
  local -a items
  IFS=',' read -ra items <<<"$BENCH_SCENARIOS"
  for item in "${items[@]}"; do
    if [[ "$(trim "$item")" == "$needle" ]]; then
      return 0
    fi
  done
  return 1
}

validate_scenarios() {
  local item
  local -a items
  local any=0
  IFS=',' read -ra items <<<"$BENCH_SCENARIOS"
  for item in "${items[@]}"; do
    item="$(trim "$item")"
    [[ -z "$item" ]] && continue
    any=1
    case "$item" in
      mvn | mvnd | build-cache) ;;
      *)
        echo "::error::Unknown scenario '${item}'. Use mvn, mvnd, build-cache."
        exit 1
        ;;
    esac
  done
  if [[ "$any" -eq 0 ]]; then
    echo "::error::scenarios is empty"
    exit 1
  fi
}

require_count() {
  local label="$1"
  local value="$2"
  if [[ ! "$value" =~ ^[1-9][0-9]*$ ]]; then
    echo "::error::${label} must be a positive integer (got '${value}')"
    exit 1
  fi
}

on_exit() {
  local rc=$?
  trap - EXIT
  restore_workspace || rc=1
  write_summary || true
  emit_soft_warning || true
  if [[ -n "${GITHUB_OUTPUT:-}" && -f "${LOG_DIR}/github_output.txt" ]]; then
    cat "${LOG_DIR}/github_output.txt" >> "$GITHUB_OUTPUT"
  fi
  exit "$rc"
}
trap on_exit EXIT

restore_workspace() {
  local rc=0
  if [[ -n "$SOURCE_BACKUP" && -n "$SOURCE_FILE" ]]; then
    cp "$SOURCE_BACKUP" "$SOURCE_FILE" || rc=1
    if ! cmp -s "$SOURCE_BACKUP" "$SOURCE_FILE"; then
      echo "::error::Failed to restore ${SOURCE_FILE}"
      rc=1
    fi
  fi
  if [[ "$INSTALLED_CACHE" == 1 ]]; then
    rm -f .mvn/extensions.xml .mvn/maven-build-cache-config.xml || rc=1
    if [[ "$CREATED_MVN_DIR" == 1 ]]; then
      rmdir .mvn 2>/dev/null || true
    fi
  fi
  if [[ -e .mvn/extensions.xml || -e .mvn/maven-build-cache-config.xml ]]; then
    if [[ "$INSTALLED_CACHE" == 1 ]]; then
      echo "::error::Bench left .mvn cache files in the worktree"
      rc=1
    fi
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
  local start end secs
  start="$(date +%s%N)"
  "$@" >>"$logfile" 2>&1 || rc=$?
  end="$(date +%s%N)"
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
  if [[ ! -d .mvn ]]; then
    CREATED_MVN_DIR=1
  fi
  mkdir -p .mvn
  cp "${ACTION_DIR}/extensions.xml" .mvn/extensions.xml
  cp "${ACTION_DIR}/maven-build-cache-config.xml" .mvn/maven-build-cache-config.xml
  INSTALLED_CACHE=1
}

cache_file_count() {
  if [[ -d "${HOME}/.m2/build-cache" ]]; then
    find "${HOME}/.m2/build-cache" -type f | wc -l | tr -d ' '
  else
    echo 0
  fi
}

discover_java() {
  local pom_dir="$1"
  find "$pom_dir" \
    \( -type d \( -name target -o -name .git \) -prune \) -o \
    \( -type f -name '*.java' -path '*/src/main/java/*' -print -quit \)
}

write_summary() {
  BENCH_POM="$BENCH_POM" python3 "${ACTION_DIR}/summarize.py" "$LOG_DIR"
}

emit_soft_warning() {
  local warning_file="$LOG_DIR/soft-warning.txt"
  if [[ -s "$warning_file" ]]; then
    echo "::warning title=build-speedup-bench::$(tr '\n' ' ' <"$warning_file")"
  fi
}

validate_scenarios
require_count "mvn-runs" "$BENCH_MVN_RUNS"
require_count "mvnd-warm-runs" "$BENCH_MVND_WARM_RUNS"

if [[ ! -f "$BENCH_POM" ]]; then
  echo "::error::pom not found: ${BENCH_POM}"
  exit 1
fi

if [[ "$LOG_DIR" == "/" || "$LOG_DIR" == "$HOME" ]]; then
  echo "::error::refusing to use ${LOG_DIR} as the log directory"
  exit 1
fi
rm -rf "$LOG_DIR"
mkdir -p "$LOG_DIR"

EXTRA=()
if [[ -n "$BENCH_EXTRA_ARGS" ]]; then
  read -r -a EXTRA <<<"$BENCH_EXTRA_ARGS"
fi
COMMON=(
  -f "$BENCH_POM"
  --batch-mode
  -q
  "${EXTRA[@]}"
  -T "$BENCH_THREADS"
)

{
  echo "java:"
  java -version 2>&1
  echo "mvn:"
  mvn -version
  if want mvnd || want build-cache; then
    echo "mvnd:"
    mvnd --version
  fi
  echo "nproc: $(nproc)"
  echo "runner arch: $(uname -m)"
} | tee "$LOG_DIR/tool-versions.txt"

printf '%s\n' "mvn|mvnd -f ${BENCH_POM} --batch-mode -q ${BENCH_EXTRA_ARGS} -T ${BENCH_THREADS} [clean] package" >"$LOG_DIR/command.txt"
printf 'scenario\tseconds\texit_code\n' >"$LOG_DIR/timings.tsv"

if [[ -e .mvn/extensions.xml || -e .mvn/maven-build-cache-config.xml ]]; then
  echo "::error::Refusing to bench with a pre-existing .mvn cache extension; baseline would not be host Maven alone"
  exit 1
fi

note "Scenarios: ${BENCH_SCENARIOS}."
note "Baseline runs leave .mvn/extensions.xml unset. Cache runs copy action templates into .mvn/ and remove them afterward."
note "Every invocation adds --batch-mode and -q. Extra arguments: ${BENCH_EXTRA_ARGS:-<none>}."
note "Parallelism is -T ${BENCH_THREADS}. This runner has $(nproc) cores."

if want mvnd || want build-cache; then
  stop_daemon
fi
note "Seeding ~/.m2 with one untimed mvn clean package so later timings are not dominated by plugin downloads."
run_timed seed_m2 mvn "${COMMON[@]}" clean package

if want mvn; then
  for ((run = 1; run <= BENCH_MVN_RUNS; run++)); do
    run_timed "mvn_clean_${run}" mvn "${COMMON[@]}" clean package
  done
fi

if want mvnd; then
  stop_daemon
  run_timed mvnd_cold_clean mvnd "${COMMON[@]}" clean package
  for ((run = 1; run <= BENCH_MVND_WARM_RUNS; run++)); do
    run_timed "mvnd_warm_clean_${run}" mvnd "${COMMON[@]}" clean package
  done
fi

if want build-cache; then
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

  pom_dir="$(cd "$(dirname "$BENCH_POM")" && pwd)"
  if [[ -n "$BENCH_TOUCH_FILE" ]]; then
    SOURCE_FILE="$BENCH_TOUCH_FILE"
    if [[ ! -f "$SOURCE_FILE" ]]; then
      echo "::error::touch-file not found: ${SOURCE_FILE}"
      exit 1
    fi
  else
    SOURCE_FILE="$(discover_java "$pom_dir")"
  fi

  if [[ -n "$SOURCE_FILE" ]]; then
    SOURCE_BACKUP="$(mktemp)"
    cp "$SOURCE_FILE" "$SOURCE_BACKUP"
    touch "$SOURCE_FILE"
    note "Touch-only changed the mtime of ${SOURCE_FILE} and left its bytes unchanged."
    run_timed cache_touch_only mvnd "${COMMON[@]}" package
  else
    note "No src/main/java file under ${pom_dir}; skipped touch-only and content edit."
  fi

  find "$pom_dir" -type d -name target -print0 | xargs -0 -r rm -rf
  note "Deleted target/ directories under ${pom_dir} before the restore run."
  run_timed cache_restore_wiped_targets mvnd "${COMMON[@]}" package

  if [[ -n "$SOURCE_FILE" ]]; then
    printf '\n// bench-speedup-content-edit\n' >>"$SOURCE_FILE"
    note "Content edit appended a one-line comment to ${SOURCE_FILE}; the action restores the bytes before it finishes."
    run_timed cache_content_edit mvnd "${COMMON[@]}" package
  fi
fi
