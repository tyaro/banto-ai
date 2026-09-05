"""JSON Schemaの小さな標準ライブラリ検証器とmanifest読込。"""

from __future__ import annotations

import json
import re
from math import isfinite
from pathlib import Path
from typing import Any


class ManifestValidationError(ValueError):
    """manifestがschemaに適合しない場合に発生する。"""


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ManifestValidationError(f"duplicate JSON property: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    def reject_constant(value: str) -> None:
        raise ManifestValidationError(f"{path}: non-finite JSON constant is not allowed: {value}")

    def parse_float(value: str) -> float:
        parsed = float(value)
        if not isfinite(parsed):
            raise ManifestValidationError(f"{path}: non-finite JSON number is not allowed: {value}")
        return parsed

    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle, object_pairs_hook=_reject_duplicate_pairs, parse_constant=reject_constant, parse_float=parse_float)
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestValidationError(f"{path}: invalid JSON: {exc}") from exc


def validate(instance: Any, schema: dict[str, Any], path: str = "$", root: dict[str, Any] | None = None) -> None:
    """Phase 0で使用するJSON Schema subsetを検証する。"""
    root = schema if root is None else root
    if "$ref" in schema:
        reference = schema["$ref"]
        if not reference.startswith("#/"):
            raise ManifestValidationError(f"{path}: unsupported $ref {reference}")
        target: Any = root
        for part in reference[2:].split("/"):
            target = target[part]
        validate(instance, target, path, root)
        return
    expected = schema.get("type")
    if expected and not _matches_type(instance, expected):
        raise ManifestValidationError(f"{path}: expected {expected}")
    if "enum" in schema and instance not in schema["enum"]:
        raise ManifestValidationError(f"{path}: value is not in enum")
    if "const" in schema and instance != schema["const"]:
        raise ManifestValidationError(f"{path}: value must equal const")
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            raise ManifestValidationError(f"{path}: string is too short")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            raise ManifestValidationError(f"{path}: string does not match pattern")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise ManifestValidationError(f"{path}: number is below minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            raise ManifestValidationError(f"{path}: number is above maximum")
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            raise ManifestValidationError(f"{path}: number is not above exclusive minimum")
        if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
            raise ManifestValidationError(f"{path}: number is not below exclusive maximum")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            raise ManifestValidationError(f"{path}: too few items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise ManifestValidationError(f"{path}: too many items")
        if "items" in schema:
            for index, item in enumerate(instance):
                validate(item, schema["items"], f"{path}[{index}]", root)
    if isinstance(instance, dict):
        if "minProperties" in schema and len(instance) < schema["minProperties"]:
            raise ManifestValidationError(f"{path}: too few properties")
        if "maxProperties" in schema and len(instance) > schema["maxProperties"]:
            raise ManifestValidationError(f"{path}: too many properties")
        for required in schema.get("required", []):
            if required not in instance:
                raise ManifestValidationError(f"{path}: missing required property {required}")
        properties = schema.get("properties", {})
        property_names = schema.get("propertyNames")
        if isinstance(property_names, dict):
            for key in instance:
                validate(key, property_names, f"{path}.<propertyName>", root)
        for key, value in instance.items():
            if key in properties:
                validate(value, properties[key], f"{path}.{key}", root)
            elif schema.get("additionalProperties") is False:
                raise ManifestValidationError(f"{path}: unexpected property {key}")
            elif isinstance(schema.get("additionalProperties"), dict):
                validate(value, schema["additionalProperties"], f"{path}.{key}", root)
    for alternative in schema.get("anyOf", []):
        try:
            validate(instance, alternative, path, root)
            break
        except ManifestValidationError:
            continue
    else:
        if schema.get("anyOf"):
            raise ManifestValidationError(f"{path}: no anyOf alternative matched")
    alternatives = schema.get("oneOf", [])
    if alternatives:
        matched = 0
        for alternative in alternatives:
            try:
                validate(instance, alternative, path, root)
            except ManifestValidationError:
                continue
            matched += 1
        if matched != 1:
            raise ManifestValidationError(f"{path}: expected exactly one oneOf alternative, matched {matched}")


def _matches_type(value: Any, expected: str | list[str]) -> bool:
    expected_types = [expected] if isinstance(expected, str) else expected
    for type_name in expected_types:
        if type_name == "object" and isinstance(value, dict):
            return True
        if type_name == "array" and isinstance(value, list):
            return True
        if type_name == "string" and isinstance(value, str):
            return True
        if type_name == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if (type_name == "number" and isinstance(value, (int, float)) and not isinstance(value, bool)
                and isfinite(value)):
            return True
        if type_name == "boolean" and isinstance(value, bool):
            return True
        if type_name == "null" and value is None:
            return True
    return False


def validate_manifest(path: Path, schema_path: Path) -> None:
    schema = load_json(schema_path)
    instance = load_json(path)
    validate(instance, schema)
