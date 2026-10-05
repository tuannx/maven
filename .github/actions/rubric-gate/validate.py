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

"""Validate verdict.json against schema.json. Stdlib only."""

import json
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.json")


def load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def validate(instance, schema=None):
    document = schema if schema is not None else load_schema()
    defs = document.get("$defs", {})
    errors = _check(instance, document, defs, "$")
    errors.extend(_state_errors(instance))
    return errors


def _state_errors(instance):
    if not isinstance(instance, dict):
        return []
    dimensions = instance.get("dimensions")
    if not isinstance(dimensions, dict):
        return []
    errors = []
    for name, item in dimensions.items():
        if not isinstance(item, dict):
            continue
        state = item.get("state")
        path = f"$.dimensions.{name}"
        if state == "not_applicable" and "score" in item:
            errors.append(f"{path} not_applicable has score")
        elif state in ("scored", "no_evidence") and "score" not in item:
            errors.append(f"{path} missing score")
        elif state == "no_evidence" and isinstance(item.get("score"), int) and not isinstance(item.get("score"), bool):
            if item["score"] > 2:
                errors.append(f"{path} no_evidence maximum")
    return errors


def _check(instance, schema, defs, path):
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        return _check(instance, defs[name], defs, path)
    errors = []
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path} const {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path} enum")
    declared = schema.get("type")
    if declared == "integer":
        if isinstance(instance, bool) or not isinstance(instance, int):
            errors.append(f"{path} integer")
            return errors
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path} minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path} maximum")
    elif declared == "string":
        if not isinstance(instance, str):
            errors.append(f"{path} string")
    elif declared == "boolean":
        if not isinstance(instance, bool):
            errors.append(f"{path} boolean")
    elif declared == "array":
        if not isinstance(instance, list):
            errors.append(f"{path} array")
            return errors
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path} minItems")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path} maxItems")
        prefix = schema.get("prefixItems") or []
        for index, sub in enumerate(prefix):
            if index < len(instance):
                errors.extend(_check(instance[index], sub, defs, f"{path}[{index}]"))
        item_schema = schema.get("items")
        if item_schema is not None:
            start = len(prefix)
            for index, item in enumerate(instance[start:], start):
                errors.extend(_check(item, item_schema, defs, f"{path}[{index}]"))
    elif declared == "object":
        if not isinstance(instance, dict):
            errors.append(f"{path} object")
            return errors
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path} missing {key}")
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in properties:
                    errors.append(f"{path} extra {key}")
        for key, sub in properties.items():
            if key in instance:
                errors.extend(_check(instance[key], sub, defs, f"{path}.{key}"))
    return errors
