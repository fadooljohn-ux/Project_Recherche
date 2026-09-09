from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import yaml


class TrustedDataError(ValueError):
    """A control document is malformed, ambiguous, or outside its exact schema."""


def _reject_duplicate_json_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TrustedDataError(f"duplicate JSON member {key!r}")
        result[key] = value
    return result


def _reject_nonfinite_json(value: str) -> None:
    raise TrustedDataError(f"non-finite JSON number {value!r}")


def loads_json(payload: str, label: str = "trusted JSON") -> Any:
    try:
        return json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_json_members,
            parse_constant=_reject_nonfinite_json,
        )
    except TrustedDataError:
        raise
    except (TypeError, json.JSONDecodeError) as error:
        raise TrustedDataError(f"{label} is invalid: {error}") from error


def load_json(path: Path, label: str | None = None) -> Any:
    try:
        payload = path.read_text(encoding="utf-8")
    except OSError as error:
        raise TrustedDataError(f"{label or path.as_posix()} is unreadable: {error}") from error
    return loads_json(payload, label or path.as_posix())


class _DuplicateRejectingSafeLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: _DuplicateRejectingSafeLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[str, Any]:
    pairs = loader.construct_pairs(node, deep=deep)
    result: dict[str, Any] = {}
    for key, value in pairs:
        if type(key) is not str:
            raise TrustedDataError(f"YAML mapping member is not a string: {key!r}")
        if key in result:
            raise TrustedDataError(f"duplicate YAML member {key!r}")
        result[key] = value
    return result


_DuplicateRejectingSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _reject_nonfinite_values(value: Any, label: str) -> None:
    if type(value) is float and not math.isfinite(value):
        raise TrustedDataError(f"{label} contains a non-finite number")
    if type(value) is list:
        for index, item in enumerate(value):
            _reject_nonfinite_values(item, f"{label}[{index}]")
    elif type(value) is dict:
        for key, item in value.items():
            _reject_nonfinite_values(item, f"{label}.{key}")


def loads_yaml(payload: str, label: str = "trusted YAML") -> dict[str, Any]:
    try:
        value = yaml.load(payload, Loader=_DuplicateRejectingSafeLoader)
    except TrustedDataError:
        raise
    except yaml.YAMLError as error:
        raise TrustedDataError(f"{label} is invalid: {error}") from error
    if type(value) is not dict:
        raise TrustedDataError(f"{label} is not a mapping")
    _reject_nonfinite_values(value, label)
    return value


def load_yaml(path: Path, label: str | None = None) -> dict[str, Any]:
    try:
        payload = path.read_text(encoding="utf-8")
    except OSError as error:
        raise TrustedDataError(f"{label or path.as_posix()} is unreadable: {error}") from error
    return loads_yaml(payload, label or path.as_posix())


def require_exact_keys(value: Any, expected: Iterable[str], label: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise TrustedDataError(f"{label} is not an object")
    expected_set = set(expected)
    actual_set = set(value)
    if actual_set != expected_set:
        missing = sorted(expected_set - actual_set)
        extra = sorted(actual_set - expected_set)
        raise TrustedDataError(f"{label} member mismatch: missing={missing}, extra={extra}")
    return value


def require_type(value: Any, expected: type, label: str) -> Any:
    if type(value) is not expected:
        raise TrustedDataError(
            f"{label} has type {type(value).__name__}; expected {expected.__name__}"
        )
    return value


def require_sha256(value: Any, label: str) -> str:
    require_type(value, str, label)
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise TrustedDataError(f"{label} is not a lowercase SHA-256 digest")
    return value


def require_nonempty_string(value: Any, label: str) -> str:
    require_type(value, str, label)
    if not value.strip():
        raise TrustedDataError(f"{label} is empty")
    return value


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError) as error:
        raise TrustedDataError(f"value is not canonical JSON: {error}") from error


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def exact_typed_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        return False
    if type(actual) is dict:
        if set(actual) != set(expected):
            return False
        return all(exact_typed_equal(actual[key], expected[key]) for key in actual)
    if type(actual) is list:
        return len(actual) == len(expected) and all(
            exact_typed_equal(left, right) for left, right in zip(actual, expected, strict=True)
        )
    if type(actual) is float:
        return math.isfinite(actual) and math.isfinite(expected) and actual == expected
    return actual == expected


def validate_hash_map(value: Any, label: str) -> dict[str, str]:
    require_type(value, dict, label)
    result: dict[str, str] = {}
    for key, digest in value.items():
        require_nonempty_string(key, f"{label} key")
        result[key] = require_sha256(digest, f"{label}.{key}")
    return result


def sanitize_environment(values: Mapping[str, str], allowed: Iterable[str]) -> dict[str, str]:
    allowed_set = set(allowed)
    unexpected = sorted(set(values) - allowed_set)
    if unexpected:
        raise TrustedDataError(f"unexpected environment variables: {unexpected}")
    return {key: values[key] for key in sorted(values)}
