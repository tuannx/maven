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

"""Copy the build-cache templates for one measured run, then delete them. ADR-0016."""

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

TEMPLATE_NAMES = ("extensions.xml", "maven-build-cache-config.xml")


def template_dir(root):
    return Path(root) / ".github" / "actions" / "build-speedup-bench"


def live_paths(root):
    return [Path(root) / ".mvn" / name for name in TEMPLATE_NAMES]


def install(root, templates):
    root = Path(root)
    templates = Path(templates)
    for path in live_paths(root):
        if path.exists():
            raise SystemExit(f"refusing to replace {path}")
    dest_dir = root / ".mvn"
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    try:
        for name in TEMPLATE_NAMES:
            source = templates / name
            if not source.is_file():
                raise SystemExit(f"missing cache template {source}")
            target = dest_dir / name
            shutil.copyfile(source, target)
            copied.append(target)
    except BaseException:
        for path in copied:
            path.unlink(missing_ok=True)
        raise
    return copied


def remove(root):
    root = Path(root)
    for path in live_paths(root):
        if path.exists():
            path.unlink()
    leftover = [str(path) for path in live_paths(root) if path.exists()]
    if leftover:
        raise SystemExit("warm cache left " + ", ".join(leftover))


def cache_file_count():
    cache = Path.home() / ".m2" / "build-cache"
    if not cache.is_dir():
        return 0
    return sum(1 for path in cache.rglob("*") if path.is_file())


def module_command(maven, goal_args):
    return [
        maven,
        "-f",
        "api/pom.xml",
        "-pl",
        "maven-api-core",
        "-am",
        "--batch-mode",
        "-T",
        "1C",
        "-DskipTests",
        "-Drat.skip=true",
        "-Dcheckstyle.skip=true",
        "-Denforcer.skip=true",
        *goal_args,
    ]


def run_timed(name, command, root):
    start = time.perf_counter()
    completed = subprocess.run(command, cwd=root)
    seconds = time.perf_counter() - start
    if completed.returncode != 0:
        raise SystemExit(f"{name} failed (exit {completed.returncode})")
    return seconds


def write_output(name, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"{name}={value}\n")


def measure(root, maven):
    root = Path(root)
    cold = run_timed("cold", module_command(maven, ["clean", "package"]), root)
    install(root, template_dir(root))
    try:
        seed = run_timed("seed", module_command(maven, ["clean", "package"]), root)
        files = cache_file_count()
        if files < 1:
            raise SystemExit("maven-build-cache-extension did not populate ~/.m2/build-cache")
        warm = run_timed("warm", module_command(maven, ["package"]), root)
    finally:
        remove(root)
    leftover = [path for path in live_paths(root) if path.exists()]
    if leftover:
        raise SystemExit("warm cache left " + ", ".join(str(path) for path in leftover))
    print(f"cold_seconds={cold:.2f}")
    print(f"seed_seconds={seed:.2f}")
    print(f"warm_seconds={warm:.2f}")
    print(f"cache_files={files}")
    write_output("cold_seconds", f"{cold:.2f}")
    write_output("warm_seconds", f"{warm:.2f}")
    write_output("cache_files", str(files))
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write("\n| run | seconds |\n|---|---:|\n")
            handle.write(f"| cold mvn, no extension | {cold:.2f} |\n")
            handle.write(f"| cache seed | {seed:.2f} |\n")
            handle.write(f"| warm package | {warm:.2f} |\n")
            handle.write(f"\n`~/.m2/build-cache` files after the seed: {files}.\n")
    return cold, warm, files


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--maven", default="mvn")
    parser.add_argument("command", choices=("measure",))
    args = parser.parse_args(argv)
    measure(args.root, args.maven)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
