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

# Install Apache Maven or Maven Daemon onto PATH for later action steps.
set -euo pipefail

tool="${1:-}"
dest="${HOME}/build-speedup-bench-tools"
mkdir -p "$dest"

require_version() {
  local label="$1"
  local version="$2"
  if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "::error::${label} must look like 3.9.11 (got '${version}')"
    exit 1
  fi
}

install_maven() {
  local version="${MAVEN_VERSION:-3.9.11}"
  require_version "maven-version" "$version"
  local url="https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/${version}/apache-maven-${version}-bin.tar.gz"
  local archive dest_root sha_file hash top
  archive="$(mktemp)"
  sha_file="$(mktemp)"
  curl -fsSL "$url" -o "$archive"
  curl -fsSL "${url}.sha512" -o "$sha_file"
  hash="$(awk 'NF { print $1; exit }' "$sha_file" | tr -d '\r')"
  echo "${hash}  ${archive}" | sha512sum -c -
  tar -tzf "$archive" > "${archive}.list"
  top="$(awk -F/ 'NR==1 { print $1; exit }' "${archive}.list")"
  tar -xzf "$archive" -C "$dest"
  dest_root="${dest}/${top}"
  if [[ ! -x "${dest_root}/bin/mvn" ]]; then
    echo "::error::Maven archive did not contain bin/mvn"
    exit 1
  fi
  echo "${dest_root}/bin" >> "$GITHUB_PATH"
  echo "Installed Apache Maven ${version} at ${dest_root}"
}

install_mvnd() {
  local version="${MVND_VERSION:-1.0.6}"
  local arch archive url expected sha_file top dest_root
  require_version "mvnd-version" "$version"
  case "$(uname -m)" in
    x86_64) arch="linux-amd64" ;;
    aarch64 | arm64) arch="linux-aarch64" ;;
    *)
      echo "::error::mvnd install supports linux-amd64 and linux-aarch64; this runner is $(uname -m)"
      exit 1
      ;;
  esac
  url="https://github.com/apache/maven-mvnd/releases/download/${version}/maven-mvnd-${version}-${arch}.tar.gz"
  archive="$(mktemp)"
  curl -fsSL "$url" -o "$archive"
  if [[ -n "${MVND_SHA256:-}" ]]; then
    if [[ ! "${MVND_SHA256}" =~ ^[a-fA-F0-9]{64}$ ]]; then
      echo "::error::mvnd-sha256 must be 64 hex characters"
      exit 1
    fi
    expected="${MVND_SHA256}"
  elif [[ "$version" == "1.0.6" && "$arch" == "linux-amd64" ]]; then
    expected="88fd474fd3f21b33ec1e6a75950f6abbe493d63a5e2b429475f5230b3ee6cb24"
  else
    sha_file="$(mktemp)"
    if curl -fsSL "${url}.sha256" -o "$sha_file"; then
      expected="$(awk 'NF { print $1; exit }' "$sha_file" | tr -d '\r')"
    else
      echo "::error::No published checksum for mvnd ${version} ${arch}. Set the mvnd-sha256 input."
      exit 1
    fi
  fi
  echo "${expected}  ${archive}" | sha256sum -c -
  tar -tzf "$archive" > "${archive}.list"
  top="$(awk -F/ 'NR==1 { print $1; exit }' "${archive}.list")"
  tar -xzf "$archive" -C "$dest"
  dest_root="${dest}/${top}"
  if [[ ! -x "${dest_root}/bin/mvnd" ]]; then
    echo "::error::mvnd archive did not contain bin/mvnd"
    exit 1
  fi
  echo "${dest_root}/bin" >> "$GITHUB_PATH"
  echo "Installed Maven Daemon ${version} (${arch}) at ${dest_root}"
}

case "$tool" in
  maven) install_maven ;;
  mvnd) install_mvnd ;;
  *)
    echo "::error::install-tools.sh expects maven or mvnd"
    exit 1
    ;;
esac
