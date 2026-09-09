from __future__ import annotations

import builtins
import importlib.util
import io
import os
import platform
import socket
import sys
from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager
from pathlib import Path
from types import TracebackType
from typing import Any, ClassVar, Self

from .pilot2_trusted_data import (
    TrustedDataError,
    canonical_sha256,
    exact_typed_equal,
    load_json,
    require_exact_keys,
    require_nonempty_string,
    require_sha256,
    require_type,
)
from .precision import assert_precision
from .provenance import hash_file

RESOURCE_MANIFEST_KEYS = {
    "schema_version",
    "manifest_id",
    "status",
    "local_repository_relative_path",
    "clock_override_relative_path",
    "entries",
    "required_resource_classes",
}
RESOURCE_ENTRY_KEYS = {
    "logical_name",
    "controlled_relative_path",
    "source_url_or_publication",
    "license_or_redistribution_status",
    "bytes",
    "sha256",
    "consumer",
    "resolution_role",
}
RESOURCE_ENTRY_SPEC_KEYS = RESOURCE_ENTRY_KEYS - {"bytes", "sha256"}
ENVIRONMENT_MANIFEST_KEYS = {
    "schema_version",
    "manifest_id",
    "status",
    "repository_files",
    "python",
    "platform",
    "precision",
    "packages",
    "critical_modules",
    "environment_policy",
    "resource_manifest_sha256",
}

_MISSING = object()
_GATE4A_R3_REPOSITORY_RELATIVE_PATH = Path("derived/cache-v0.2.8")
_GATE4A_R3_CLOCK_RELATIVE_PATH = Path("controlled/clock-overrides")
_GATE4A_R3_CLOCK_FILENAMES = frozenset(
    {
        "time_ao.dat",
        "time_gbt.dat",
        "gps2utc.clk",
        "tai2tt_bipm2019.clk",
    }
)
_GATE4A_R3_RESOURCE_ROLES = {
    "controlled/clock-overrides/time_ao.dat": "observatory_clock",
    "controlled/clock-overrides/time_gbt.dat": "observatory_clock",
    "controlled/clock-overrides/gps2utc.clk": "gps_clock",
    "controlled/clock-overrides/tai2tt_bipm2019.clk": "bipm_clock",
    "derived/cache-v0.2.8/iers/finals2000A.all": "iers_a",
    "derived/cache-v0.2.8/iers/ReadMe.finals2000A": "iers_a",
    "derived/cache-v0.2.8/iers/eopc04.1962-now": "iers_b",
    "derived/cache-v0.2.8/iers/ReadMe.eopc04": "iers_b",
    "derived/cache-v0.2.8/iers/Leap_Second.dat": "leap_seconds",
    "derived/cache-v0.2.8/ephemerides/de440.bsp": "solar_system_ephemeris",
}
_GATE4A_R3_REQUIRED_RESOURCE_CLASSES = frozenset(_GATE4A_R3_RESOURCE_ROLES.values())


def _safe_relative_path(value: Any, label: str) -> Path:
    text = require_nonempty_string(value, label)
    path = Path(text)
    if path.is_absolute() or ".." in path.parts:
        raise TrustedDataError(f"{label} is not a confined relative path")
    return path


def validate_resource_manifest(
    value: Any,
    *,
    data_root: Path | None = None,
) -> dict[str, Any]:
    manifest = require_exact_keys(value, RESOURCE_MANIFEST_KEYS, "v0.2.8 resource manifest")
    if manifest["schema_version"] != 1 or type(manifest["schema_version"]) is not int:
        raise TrustedDataError("v0.2.8 resource manifest schema is invalid")
    require_nonempty_string(manifest["manifest_id"], "resource manifest ID")
    if manifest["status"] != "frozen_local_only":
        raise TrustedDataError("v0.2.8 resource manifest status is invalid")
    repository_relative = _safe_relative_path(
        manifest["local_repository_relative_path"], "local repository path"
    )
    clock_relative = _safe_relative_path(
        manifest["clock_override_relative_path"], "clock override path"
    )
    entries = require_type(manifest["entries"], list, "resource manifest entries")
    if not entries:
        raise TrustedDataError("v0.2.8 resource manifest is empty")
    logical_names: set[str] = set()
    controlled_paths: set[str] = set()
    roles: set[str] = set()
    for index, raw_entry in enumerate(entries):
        entry = require_exact_keys(raw_entry, RESOURCE_ENTRY_KEYS, f"resource entry[{index}]")
        logical_name = require_nonempty_string(
            entry["logical_name"], f"resource entry[{index}].logical_name"
        )
        relative = _safe_relative_path(
            entry["controlled_relative_path"],
            f"resource entry[{index}].controlled_relative_path",
        )
        require_nonempty_string(
            entry["source_url_or_publication"], f"resource entry[{index}].source"
        )
        require_nonempty_string(
            entry["license_or_redistribution_status"], f"resource entry[{index}].license"
        )
        require_type(entry["bytes"], int, f"resource entry[{index}].bytes")
        if entry["bytes"] < 0:
            raise TrustedDataError(f"resource entry[{index}].bytes is negative")
        require_sha256(entry["sha256"], f"resource entry[{index}].sha256")
        require_nonempty_string(entry["consumer"], f"resource entry[{index}].consumer")
        role = require_nonempty_string(
            entry["resolution_role"], f"resource entry[{index}].resolution_role"
        )
        if logical_name in logical_names or relative.as_posix() in controlled_paths:
            raise TrustedDataError("v0.2.8 resource manifest contains duplicate identity")
        logical_names.add(logical_name)
        controlled_paths.add(relative.as_posix())
        roles.add(role)
        if data_root is not None:
            path = data_root / relative
            resolved_root = data_root.resolve()
            if not path.is_file() or not path.resolve(strict=True).is_relative_to(resolved_root):
                raise TrustedDataError(f"resource is missing or escapes data root: {relative}")
            if (
                path.stat().st_size != entry["bytes"]
                or hash_file(path, "sha256") != entry["sha256"]
            ):
                raise TrustedDataError(f"resource identity mismatch: {relative}")
    required_classes = require_type(
        manifest["required_resource_classes"], list, "required resource classes"
    )
    if any(type(item) is not str or not item for item in required_classes):
        raise TrustedDataError("required resource class is invalid")
    if len(set(required_classes)) != len(required_classes):
        raise TrustedDataError("required resource classes contain duplicates")
    if not set(required_classes).issubset(roles):
        raise TrustedDataError("resource manifest does not cover every required class")
    allowed_roots = (repository_relative, clock_relative)
    if any(
        not any(Path(relative).is_relative_to(root) for root in allowed_roots)
        for relative in controlled_paths
    ):
        raise TrustedDataError("resource manifest entry is outside its controlled repositories")
    if data_root is not None:
        for relative, label in (
            (repository_relative, "local repository"),
            (clock_relative, "clock override"),
        ):
            path = data_root / relative
            if not path.is_dir() or not path.resolve(strict=True).is_relative_to(
                data_root.resolve()
            ):
                raise TrustedDataError(f"{label} directory is unavailable")
    return manifest


def load_resource_manifest(path: Path, *, data_root: Path | None = None) -> dict[str, Any]:
    return validate_resource_manifest(
        load_json(path, "v0.2.8 resource manifest"), data_root=data_root
    )


def build_resource_manifest(
    data_root: Path,
    *,
    manifest_id: str,
    local_repository_relative_path: str,
    clock_override_relative_path: str,
    entries: Sequence[Mapping[str, Any]],
    required_resource_classes: Sequence[str],
) -> dict[str, Any]:
    """Build one exact local-only manifest from an authority-bound inventory."""

    root = Path(data_root).resolve(strict=True)
    repository_relative = _safe_relative_path(
        local_repository_relative_path, "local repository path"
    )
    clock_relative = _safe_relative_path(clock_override_relative_path, "clock override path")
    controlled_roots = (repository_relative, clock_relative)
    specified: list[dict[str, Any]] = []
    specified_paths: set[str] = set()
    for index, raw in enumerate(entries):
        spec = require_exact_keys(
            dict(raw), RESOURCE_ENTRY_SPEC_KEYS, f"resource entry specification[{index}]"
        )
        relative = _safe_relative_path(
            spec["controlled_relative_path"],
            f"resource entry specification[{index}].controlled_relative_path",
        )
        if not any(relative.is_relative_to(parent) for parent in controlled_roots):
            raise TrustedDataError("resource entry specification is outside controlled roots")
        logical = relative.as_posix()
        if logical in specified_paths:
            raise TrustedDataError("resource entry specification contains duplicate paths")
        specified_paths.add(logical)
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise TrustedDataError(f"resource is not a regular file: {logical}")
        if not path.resolve(strict=True).is_relative_to(root):
            raise TrustedDataError(f"resource escapes data root: {logical}")
        specified.append(
            {
                **spec,
                "controlled_relative_path": logical,
                "bytes": path.stat().st_size,
                "sha256": hash_file(path, "sha256"),
            }
        )
    observed_paths: set[str] = set()
    for relative_root in controlled_roots:
        current = root
        for part in relative_root.parts:
            current = current / part
            if current.is_symlink():
                raise TrustedDataError(
                    f"controlled resource path contains a symlink: {relative_root}"
                )
        directory = root / relative_root
        if directory.is_symlink() or not directory.is_dir():
            raise TrustedDataError(f"controlled resource directory is unavailable: {relative_root}")
        for item in directory.rglob("*"):
            if item.is_symlink():
                raise TrustedDataError(f"controlled resource tree contains a symlink: {item}")
            if item.is_file():
                observed_paths.add(item.relative_to(root).as_posix())
    if observed_paths != specified_paths:
        raise TrustedDataError(
            "authority-bound resource inventory differs: "
            f"missing={sorted(specified_paths - observed_paths)}, "
            f"extra={sorted(observed_paths - specified_paths)}"
        )
    manifest = {
        "schema_version": 1,
        "manifest_id": require_nonempty_string(manifest_id, "resource manifest ID"),
        "status": "frozen_local_only",
        "local_repository_relative_path": repository_relative.as_posix(),
        "clock_override_relative_path": clock_relative.as_posix(),
        "entries": sorted(specified, key=lambda item: item["controlled_relative_path"]),
        "required_resource_classes": list(required_resource_classes),
    }
    return validate_resource_manifest(manifest, data_root=root)


def build_environment_manifest(
    repository_root: Path,
    *,
    manifest_id: str,
    resource_manifest_sha256: str,
    critical_modules: Sequence[str],
    allowed_environment: Sequence[str],
) -> dict[str, Any]:
    """Build the exact live environment record used by Gate 4 qualification."""

    root = Path(repository_root).resolve(strict=True)
    require_sha256(resource_manifest_sha256, "resource manifest SHA-256")
    modules = list(critical_modules)
    allowed = list(allowed_environment)
    if (
        not modules
        or any(type(item) is not str or not item for item in modules)
        or len(set(modules)) != len(modules)
    ):
        raise TrustedDataError("critical-module specification is invalid")
    if any(type(item) is not str or not item for item in allowed) or len(set(allowed)) != len(
        allowed
    ):
        raise TrustedDataError("environment-variable allowlist is invalid")
    module_hashes: dict[str, str] = {}
    for name in sorted(modules):
        spec = importlib.util.find_spec(name)
        if spec is None or spec.origin is None or spec.origin in {"built-in", "frozen"}:
            raise TrustedDataError(f"critical module is not file-backed: {name}")
        path = Path(spec.origin)
        if path.is_symlink() or not path.is_file():
            raise TrustedDataError(f"critical module is not a regular file: {name}")
        module_hashes[name] = hash_file(path, "sha256")
    observed = current_platform_observation()
    precision = observed["precision"]
    manifest = {
        "schema_version": 1,
        "manifest_id": require_nonempty_string(manifest_id, "environment manifest ID"),
        "status": "frozen_exact_environment",
        "repository_files": {
            name: hash_file(root / name, "sha256")
            for name in ("pixi.lock", "pixi.toml", "pyproject.toml")
        },
        "python": {
            "version": observed["python_version"],
            "executable_sha256": hash_file(Path(sys.executable).resolve(), "sha256"),
        },
        "platform": {
            "macos": observed["macos"],
            "kernel_machine": observed["kernel_machine"],
            "process_machine": observed["process_machine"],
            "pointer_bits": observed["pointer_bits"],
        },
        "precision": {
            "gate_g1_precision": precision["gate_g1_precision"],
            "extended_precision": precision["extended_precision"],
            "float64_mantissa_bits": precision["float64_mantissa_bits"],
            "longdouble_mantissa_bits": precision["longdouble_mantissa_bits"],
        },
        "packages": _installed_conda_packages(),
        "critical_modules": module_hashes,
        "environment_policy": {
            "allowed": sorted(allowed),
            "values_sha256": canonical_sha256(
                {name: os.environ.get(name) for name in sorted(allowed)}
            ),
        },
        "resource_manifest_sha256": resource_manifest_sha256,
    }
    return validate_environment_manifest(
        manifest,
        repository_root=root,
        resource_manifest_sha256=resource_manifest_sha256,
    )


def validate_environment_manifest(
    value: Any,
    *,
    repository_root: Path,
    resource_manifest_sha256: str,
    verify_live: bool = True,
) -> dict[str, Any]:
    manifest = require_exact_keys(value, ENVIRONMENT_MANIFEST_KEYS, "v0.2.8 environment manifest")
    if manifest["schema_version"] != 1 or type(manifest["schema_version"]) is not int:
        raise TrustedDataError("v0.2.8 environment schema is invalid")
    require_nonempty_string(manifest["manifest_id"], "environment manifest ID")
    if manifest["status"] != "frozen_exact_environment":
        raise TrustedDataError("v0.2.8 environment status is invalid")
    repository_files = require_type(
        manifest["repository_files"], dict, "environment repository files"
    )
    if set(repository_files) != {"pixi.lock", "pixi.toml", "pyproject.toml"}:
        raise TrustedDataError("environment repository file set is not exact")
    for relative, digest in repository_files.items():
        require_sha256(digest, f"environment repository file {relative}")
        path = repository_root / relative
        if not path.is_file() or hash_file(path, "sha256") != digest:
            raise TrustedDataError(f"environment repository file mismatch: {relative}")
    python = require_exact_keys(
        manifest["python"], {"version", "executable_sha256"}, "environment Python"
    )
    require_nonempty_string(python["version"], "environment Python version")
    require_sha256(python["executable_sha256"], "environment Python executable hash")
    platform_record = require_exact_keys(
        manifest["platform"],
        {"macos", "kernel_machine", "process_machine", "pointer_bits"},
        "environment platform",
    )
    for key in ("macos", "kernel_machine", "process_machine"):
        require_nonempty_string(platform_record[key], f"environment platform.{key}")
    require_type(platform_record["pointer_bits"], int, "environment pointer bits")
    precision = require_exact_keys(
        manifest["precision"],
        {
            "gate_g1_precision",
            "extended_precision",
            "float64_mantissa_bits",
            "longdouble_mantissa_bits",
        },
        "environment precision",
    )
    if precision["gate_g1_precision"] != "pass" or precision["extended_precision"] is not True:
        raise TrustedDataError("environment precision gate is not PASS")
    for key in ("float64_mantissa_bits", "longdouble_mantissa_bits"):
        require_type(precision[key], int, f"environment precision.{key}")
    packages = require_type(manifest["packages"], list, "environment packages")
    package_names: set[str] = set()
    for index, package in enumerate(packages):
        item = require_exact_keys(
            package,
            {"name", "version", "build", "channel", "sha256"},
            f"environment package[{index}]",
        )
        name = require_nonempty_string(item["name"], f"environment package[{index}].name")
        if name in package_names:
            raise TrustedDataError("environment package names are not unique")
        package_names.add(name)
        for key in ("version", "build", "channel"):
            require_nonempty_string(item[key], f"environment package[{index}].{key}")
        require_sha256(item["sha256"], f"environment package[{index}].sha256")
    for required in ("python", "pint-pulsar", "astropy-base", "numpy", "scipy"):
        if required not in package_names:
            raise TrustedDataError(f"environment package closure omits {required}")
    critical_modules = require_type(
        manifest["critical_modules"], dict, "environment critical modules"
    )
    if not critical_modules:
        raise TrustedDataError("environment critical-module map is empty")
    for module, digest in critical_modules.items():
        require_nonempty_string(module, "environment critical-module key")
        require_sha256(digest, f"environment critical module {module}")
    policy = require_exact_keys(
        manifest["environment_policy"],
        {"allowed", "values_sha256"},
        "environment-variable policy",
    )
    allowed = require_type(policy["allowed"], list, "allowed environment variables")
    if any(type(item) is not str or not item for item in allowed) or len(set(allowed)) != len(
        allowed
    ):
        raise TrustedDataError("environment-variable allowlist is invalid")
    require_sha256(policy["values_sha256"], "environment-variable values hash")
    if manifest["resource_manifest_sha256"] != resource_manifest_sha256:
        raise TrustedDataError("environment resource-manifest binding mismatch")
    if verify_live:
        verify_live_environment(manifest)
    return manifest


def _installed_conda_packages() -> list[dict[str, str]]:
    conda_meta = Path(sys.prefix) / "conda-meta"
    if not conda_meta.is_dir():
        raise TrustedDataError("live environment has no conda-meta closure")
    packages: list[dict[str, str]] = []
    for record_path in sorted(conda_meta.glob("*.json")):
        record = load_json(record_path, f"installed package {record_path.name}")
        require_type(record, dict, f"installed package {record_path.name}")
        item = {
            "name": record.get("name"),
            "version": record.get("version"),
            "build": record.get("build"),
            "channel": record.get("channel"),
            "sha256": record.get("sha256"),
        }
        for key in ("name", "version", "build", "channel"):
            require_nonempty_string(item[key], f"installed package {record_path.name}.{key}")
        require_sha256(item["sha256"], f"installed package {record_path.name}.sha256")
        packages.append(item)
    packages.sort(key=lambda item: item["name"])
    return packages


def verify_live_environment(manifest: dict[str, Any]) -> None:
    observed = current_platform_observation()
    python = manifest["python"]
    if python["version"] != observed["python_version"]:
        raise TrustedDataError("live Python version differs from environment manifest")
    if hash_file(Path(sys.executable).resolve(), "sha256") != python["executable_sha256"]:
        raise TrustedDataError("live Python executable differs from environment manifest")
    expected_platform = {
        "macos": observed["macos"],
        "kernel_machine": observed["kernel_machine"],
        "process_machine": observed["process_machine"],
        "pointer_bits": observed["pointer_bits"],
    }
    if not exact_typed_equal(manifest["platform"], expected_platform):
        raise TrustedDataError("live platform differs from environment manifest")
    observed_precision = observed["precision"]
    expected_precision = {
        "gate_g1_precision": observed_precision["gate_g1_precision"],
        "extended_precision": observed_precision["extended_precision"],
        "float64_mantissa_bits": observed_precision["float64_mantissa_bits"],
        "longdouble_mantissa_bits": observed_precision["longdouble_mantissa_bits"],
    }
    if not exact_typed_equal(manifest["precision"], expected_precision):
        raise TrustedDataError("live precision differs from environment manifest")
    if not exact_typed_equal(
        sorted(manifest["packages"], key=lambda item: item["name"]),
        _installed_conda_packages(),
    ):
        raise TrustedDataError("live package closure differs from environment manifest")
    for module_name, expected_hash in manifest["critical_modules"].items():
        spec = importlib.util.find_spec(module_name)
        if spec is None or spec.origin is None or spec.origin in {"built-in", "frozen"}:
            raise TrustedDataError(f"critical module is not file-backed: {module_name}")
        module_path = Path(spec.origin)
        if not module_path.is_file() or hash_file(module_path, "sha256") != expected_hash:
            raise TrustedDataError(f"critical module differs from manifest: {module_name}")
    allowed = manifest["environment_policy"]["allowed"]
    allowed_values = {name: os.environ.get(name) for name in sorted(allowed)}
    if canonical_sha256(allowed_values) != manifest["environment_policy"]["values_sha256"]:
        raise TrustedDataError("live environment-variable values differ from manifest")


class NetworkDeniedError(RuntimeError):
    pass


class NetworkDeny(AbstractContextManager["NetworkDeny"]):
    """Deny and count DNS/socket connection attempts within one process."""

    def __init__(self) -> None:
        self.attempts: list[str] = []
        self._originals: dict[str, Any] = {}

    def _deny(self, operation: str) -> Callable[..., Any]:
        def denied(*args: Any, **kwargs: Any) -> Any:
            self.attempts.append(operation)
            raise NetworkDeniedError(f"network operation denied: {operation}")

        return denied

    def __enter__(self) -> Self:
        self._originals = {
            "create_connection": socket.create_connection,
            "getaddrinfo": socket.getaddrinfo,
            "socket_connect": socket.socket.connect,
            "socket_connect_ex": socket.socket.connect_ex,
        }
        socket.create_connection = self._deny("socket.create_connection")
        socket.getaddrinfo = self._deny("socket.getaddrinfo")
        socket.socket.connect = self._deny("socket.socket.connect")
        socket.socket.connect_ex = self._deny("socket.socket.connect_ex")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        socket.create_connection = self._originals["create_connection"]
        socket.getaddrinfo = self._originals["getaddrinfo"]
        socket.socket.connect = self._originals["socket_connect"]
        socket.socket.connect_ex = self._originals["socket_connect_ex"]


class ResourceOpenTracer(AbstractContextManager["ResourceOpenTracer"]):
    """Record file opens confined to the controlled resource tree."""

    _active: ClassVar[set[Any]] = set()
    _audit_installed = False

    @staticmethod
    def _audit(event: str, arguments: tuple[Any, ...]) -> None:
        # Astropy also opens via io.FileIO, bypassing builtins.open/io.open.
        if event == "open" and arguments:
            for tracer in tuple(ResourceOpenTracer._active):
                tracer._record(arguments[0])

    def __init__(self, resource_root: Path, included_roots: tuple[Path, ...] | None = None):
        self.resource_root = resource_root.resolve()
        self.included_roots = tuple(
            path.resolve() for path in (included_roots or (self.resource_root,))
        )
        self.opened: set[str] = set()
        self._builtins_open: Any | None = None
        self._io_open: Any | None = None

    def _record(self, file: Any) -> None:
        if not isinstance(file, (str, bytes, os.PathLike)):
            return
        try:
            path = Path(file).expanduser().resolve()
        except (OSError, TypeError, ValueError):
            return
        if path.is_relative_to(self.resource_root) and any(
            path.is_relative_to(root) for root in self.included_roots
        ):
            self.opened.add(path.relative_to(self.resource_root).as_posix())

    def __enter__(self) -> Self:
        if not ResourceOpenTracer._audit_installed:
            sys.addaudithook(ResourceOpenTracer._audit)
            ResourceOpenTracer._audit_installed = True
        ResourceOpenTracer._active.add(self)
        self._builtins_open = builtins.open
        self._io_open = io.open

        def traced_builtin(file: Any, *args: Any, **kwargs: Any) -> Any:
            self._record(file)
            return self._builtins_open(file, *args, **kwargs)

        def traced_io(file: Any, *args: Any, **kwargs: Any) -> Any:
            self._record(file)
            return self._io_open(file, *args, **kwargs)

        builtins.open = traced_builtin
        io.open = traced_io
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        ResourceOpenTracer._active.discard(self)
        builtins.open = self._builtins_open
        io.open = self._io_open


class LocalPintRepository(AbstractContextManager["LocalPintRepository"]):
    """Install exact direct bindings without modifying PINT or Astropy source."""

    def __init__(self, data_root: Path, manifest: dict[str, Any]):
        self.data_root = Path(data_root).resolve(strict=True)
        self.manifest = validate_resource_manifest(manifest, data_root=self.data_root)
        repository_relative = Path(self.manifest["local_repository_relative_path"])
        clock_relative = Path(self.manifest["clock_override_relative_path"])
        if repository_relative != _GATE4A_R3_REPOSITORY_RELATIVE_PATH:
            raise TrustedDataError("Gate 4A-R3 local repository path is not exact")
        if clock_relative != _GATE4A_R3_CLOCK_RELATIVE_PATH:
            raise TrustedDataError("Gate 4A-R3 clock override path is not exact")
        entries_by_path = {
            entry["controlled_relative_path"]: entry for entry in self.manifest["entries"]
        }
        if set(entries_by_path) != set(_GATE4A_R3_RESOURCE_ROLES):
            raise TrustedDataError("Gate 4A-R3 direct resource set is not exact")
        if set(self.manifest["required_resource_classes"]) != set(
            _GATE4A_R3_REQUIRED_RESOURCE_CLASSES
        ):
            raise TrustedDataError("Gate 4A-R3 required resource classes are not exact")
        for relative, expected_role in _GATE4A_R3_RESOURCE_ROLES.items():
            if entries_by_path[relative]["resolution_role"] != expected_role:
                raise TrustedDataError(f"Gate 4A-R3 resource role is invalid: {relative}")
            path = self.data_root / relative
            if path.is_symlink() or not path.is_file():
                raise TrustedDataError(f"Gate 4A-R3 resource is not a regular file: {relative}")

        self.repository = self.data_root / repository_relative
        self.clock_override = self.data_root / clock_relative
        self.iers_a = self.data_root / "derived/cache-v0.2.8/iers/finals2000A.all"
        self.iers_a_readme = self.data_root / "derived/cache-v0.2.8/iers/ReadMe.finals2000A"
        self.iers_b = self.data_root / "derived/cache-v0.2.8/iers/eopc04.1962-now"
        self.iers_b_readme = self.data_root / "derived/cache-v0.2.8/iers/ReadMe.eopc04"
        self.leap_seconds = self.data_root / "derived/cache-v0.2.8/iers/Leap_Second.dat"
        self.de440 = self.data_root / "derived/cache-v0.2.8/ephemerides/de440.bsp"

        self._old_env: dict[str, str | None] = {}
        self._old_get_toas_array: Any | None = None
        self._pint_observatory: Any | None = None
        self._pint_global_clocks: Any | None = None
        self._pint_ephemerides: Any | None = None
        self._topo_obs_was_loaded = False
        self._old_find_clock_file: Any | None = None
        self._old_topo_find_clock_file: Any = _MISSING
        self._old_index: Any | None = None
        self._clock_adapter = self._bound_find_clock_file
        self._old_gps_clock: Any = _MISSING
        self._old_bipm_clock_object: Any | None = None
        self._old_bipm_clock_values: dict[str, Any] = {}
        self._old_observatory_clocks: list[tuple[Any, Any]] = []
        self._iers: Any | None = None
        self._old_iers_auto_download: Any = _MISSING
        self._old_iers_b_table: Any = _MISSING
        self._old_iers_auto_table: Any = _MISSING
        self._old_earth_orientation_value: Any = _MISSING
        self._erfa: Any | None = None
        self._time_core: Any | None = None
        self._old_erfa_leaps: Any = _MISSING
        self._old_leap_seconds_check: Any = _MISSING
        self._solar_system_ephemeris: Any | None = None
        self._old_loaded_ephems_object: Any | None = None
        self._old_loaded_ephems_values: dict[str, Any] = {}
        self._state_snapshotted = False
        self._state_installed = False
        self._resources_binding_started = False
        self._resources_bound = False

    @staticmethod
    def _unique_registry_observatories(observatory: Any) -> list[Any]:
        result: list[Any] = []
        seen: set[int] = set()
        for item in observatory.Observatory._registry.values():
            identity = id(item)
            if identity not in seen:
                seen.add(identity)
                result.append(item)
        return result

    @staticmethod
    def _forbidden_pint_index(*args: Any, **kwargs: Any) -> Any:
        raise TrustedDataError("PINT global Index construction is forbidden")

    def _bound_find_clock_file(
        self,
        name: Any,
        format: Any,
        bogus_last_correction: bool = False,
        url_base: Any = None,
        clock_dir: Any = None,
        valid_beyond_ends: bool = False,
    ) -> Any:
        if type(name) is not str or name not in _GATE4A_R3_CLOCK_FILENAMES:
            raise TrustedDataError("PINT clock file is outside the Gate 4A-R3 allowlist")
        if url_base is not None:
            raise TrustedDataError("PINT clock URL resolution is forbidden")
        controlled = self.clock_override.resolve(strict=True)
        if clock_dir is not None and str(clock_dir).upper() != "PINT":
            try:
                requested = Path(clock_dir).resolve(strict=True)
            except (OSError, TypeError, ValueError) as error:
                raise TrustedDataError("PINT clock directory is invalid") from error
            if requested != controlled:
                raise TrustedDataError("PINT clock directory is outside the controlled root")
        if self._old_find_clock_file is None:
            raise TrustedDataError("PINT clock adapter has no bound original callable")
        return self._old_find_clock_file(
            name=name,
            format=format,
            bogus_last_correction=bogus_last_correction,
            url_base=None,
            clock_dir=controlled,
            valid_beyond_ends=valid_beyond_ends,
        )

    def __enter__(self) -> Self:
        if self._state_snapshotted or self._state_installed:
            raise RuntimeError("Gate 4A-R3 local resource boundary cannot be re-entered")

        import erfa
        import pint.observatory.global_clock_corrections as global_clocks
        import pint.solar_system_ephemerides as pint_ephemerides
        from astropy.coordinates import solar_system_ephemeris
        from astropy.time import core as time_core
        from astropy.utils import iers
        from pint import observatory

        if not isinstance(observatory._bipm_clock_versions, dict):
            raise TrustedDataError("PINT BIPM clock cache shape is invalid")
        earth_value = getattr(iers.earth_orientation_table, "_value", _MISSING)
        if earth_value is _MISSING or (
            earth_value is not None and not isinstance(earth_value, iers.IERS)
        ):
            raise TrustedDataError("Astropy Earth-orientation entry state is invalid")
        leap_check = getattr(time_core, "_LEAP_SECONDS_CHECK", _MISSING)
        if leap_check is _MISSING or not hasattr(leap_check.__class__, "DONE"):
            raise TrustedDataError("Astropy leap-second compatibility state is invalid")
        if not isinstance(pint_ephemerides.loaded_ephems, dict):
            raise TrustedDataError("PINT ephemeris cache shape is invalid")
        if "de440" in pint_ephemerides.loaded_ephems:
            raise TrustedDataError("PINT DE440 cache must be empty at boundary entry")
        if (
            getattr(solar_system_ephemeris, "_value", _MISSING) != "builtin"
            or getattr(solar_system_ephemeris, "_kernel", _MISSING) is not None
        ):
            raise TrustedDataError("Astropy ephemeris entry state is not builtin")

        self._pint_observatory = observatory
        self._pint_global_clocks = global_clocks
        self._pint_ephemerides = pint_ephemerides
        self._iers = iers
        self._erfa = erfa
        self._time_core = time_core
        self._solar_system_ephemeris = solar_system_ephemeris
        self._old_find_clock_file = observatory.find_clock_file
        self._topo_obs_was_loaded = "pint.observatory.topo_obs" in sys.modules
        if self._topo_obs_was_loaded:
            self._old_topo_find_clock_file = sys.modules[
                "pint.observatory.topo_obs"
            ].find_clock_file
        self._old_index = global_clocks.Index
        self._old_gps_clock = observatory._gps_clock
        self._old_bipm_clock_object = observatory._bipm_clock_versions
        self._old_bipm_clock_values = dict(observatory._bipm_clock_versions)
        self._old_observatory_clocks = [
            (item, getattr(item, "_clock", _MISSING))
            for item in self._unique_registry_observatories(observatory)
        ]
        self._old_env = {
            "PINT_CLOCK_OVERRIDE": os.environ.get("PINT_CLOCK_OVERRIDE"),
        }
        self._old_iers_auto_download = iers.conf.auto_download
        self._old_iers_b_table = iers.IERS_B.iers_table
        self._old_iers_auto_table = iers.IERS_Auto.iers_table
        self._old_earth_orientation_value = earth_value
        self._old_erfa_leaps = iers.LeapSeconds.from_erfa()
        self._old_leap_seconds_check = leap_check
        self._old_loaded_ephems_object = pint_ephemerides.loaded_ephems
        self._old_loaded_ephems_values = dict(pint_ephemerides.loaded_ephems)
        self._state_snapshotted = True

        self._state_installed = True
        try:
            from pint import toa

            self._old_get_toas_array = toa.get_TOAs_array

            def bound_toas_array(*args: Any, **kwargs: Any) -> Any:
                # PINT 1.1.5 AbsPhase omits bipm_version for its TZR TOA.
                # Preserve the release's TT(BIPM2019), including that reference.
                kwargs.setdefault("bipm_version", "BIPM2019")
                return self._old_get_toas_array(*args, **kwargs)

            toa.get_TOAs_array = bound_toas_array
            observatory.find_clock_file = self._clock_adapter
            if self._topo_obs_was_loaded:
                sys.modules["pint.observatory.topo_obs"].find_clock_file = self._clock_adapter
            global_clocks.Index = self._forbidden_pint_index
            os.environ["PINT_CLOCK_OVERRIDE"] = str(self.clock_override.resolve(strict=True))
            iers.conf.auto_download = False
        except BaseException:
            self._restore_process_state()
            raise
        return self

    def bind_science_resources(self) -> None:
        if not self._state_installed or self._resources_binding_started:
            raise RuntimeError("Gate 4A-R3 science resources cannot be rebound")
        if any(
            value is None
            for value in (
                self._iers,
                self._erfa,
                self._time_core,
                self._pint_ephemerides,
                self._solar_system_ephemeris,
            )
        ):
            raise RuntimeError("Gate 4A-R3 process bindings are incomplete")
        self._resources_binding_started = True

        controlled_b = self._iers.IERS_B.read(file=str(self.iers_b), readme=str(self.iers_b_readme))
        if not isinstance(controlled_b, self._iers.IERS):
            raise TrustedDataError("controlled IERS-B parser returned an invalid table")
        self._iers.IERS_B.iers_table = controlled_b
        controlled_a = self._iers.IERS_Auto.read(
            file=str(self.iers_a), readme=str(self.iers_a_readme)
        )
        if not isinstance(controlled_a, self._iers.IERS):
            raise TrustedDataError("controlled IERS-A parser returned an invalid table")
        self._iers.IERS_Auto.iers_table = controlled_a
        self._iers.earth_orientation_table.set(controlled_a)

        controlled_leaps = self._iers.LeapSeconds.from_iers_leap_seconds(str(self.leap_seconds))
        self._erfa.leap_seconds.set(None)
        controlled_leaps.update_erfa_leap_seconds()
        self._time_core._LEAP_SECONDS_CHECK = self._old_leap_seconds_check.__class__.DONE

        loaded = self._pint_ephemerides.load_kernel("DE440", path=str(self.de440))
        try:
            loaded_path = Path(loaded).resolve(strict=True)
        except (OSError, TypeError, ValueError) as error:
            raise TrustedDataError("PINT DE440 loader returned an invalid local path") from error
        if loaded_path != self.de440.resolve(strict=True):
            raise TrustedDataError("PINT DE440 loader did not bind the controlled kernel")
        if self._pint_ephemerides.loaded_ephems.get("de440") != loaded:
            raise TrustedDataError("PINT DE440 cache does not bind the controlled kernel")
        self._resources_bound = True

    def _restore_observatory_clocks(self) -> None:
        if self._pint_observatory is None:
            return
        saved_ids = {id(item) for item, _ in self._old_observatory_clocks}
        for item in self._unique_registry_observatories(self._pint_observatory):
            if id(item) not in saved_ids and hasattr(item, "_clock"):
                item._clock = None
        for item, old_value in self._old_observatory_clocks:
            if old_value is _MISSING:
                if hasattr(item, "_clock"):
                    delattr(item, "_clock")
            else:
                item._clock = old_value

    def _restore_process_state(self) -> None:
        if not self._state_snapshotted:
            return
        errors: list[tuple[str, BaseException]] = []

        def attempt(label: str, operation: Callable[[], None]) -> None:
            try:
                operation()
            except BaseException as error:  # noqa: BLE001 - restore every global on operator stop
                errors.append((label, error))

        def restore_solar_state() -> None:
            if self._solar_system_ephemeris is None:
                return
            if (
                self._solar_system_ephemeris._value != "builtin"
                or self._solar_system_ephemeris._kernel is not None
            ):
                self._solar_system_ephemeris.set("builtin")
            if (
                self._solar_system_ephemeris._value != "builtin"
                or self._solar_system_ephemeris._kernel is not None
            ):
                raise RuntimeError("Astropy ephemeris state did not restore to builtin")

        def restore_loaded_ephems() -> None:
            if self._pint_ephemerides is None or self._old_loaded_ephems_object is None:
                return
            self._pint_ephemerides.loaded_ephems = self._old_loaded_ephems_object
            self._old_loaded_ephems_object.clear()
            self._old_loaded_ephems_object.update(self._old_loaded_ephems_values)

        def restore_erfa_leaps() -> None:
            if self._erfa is not None and self._old_erfa_leaps is not _MISSING:
                self._erfa.leap_seconds.set(self._old_erfa_leaps)

        def restore_leap_check() -> None:
            if self._time_core is not None and self._old_leap_seconds_check is not _MISSING:
                self._time_core._LEAP_SECONDS_CHECK = self._old_leap_seconds_check

        def restore_iers_state() -> None:
            if self._iers is None:
                return
            self._iers.earth_orientation_table._value = self._old_earth_orientation_value
            self._iers.IERS_Auto.iers_table = self._old_iers_auto_table
            self._iers.IERS_B.iers_table = self._old_iers_b_table
            self._iers.conf.auto_download = self._old_iers_auto_download

        def restore_pint_clocks() -> None:
            if self._pint_observatory is None:
                return
            self._pint_observatory._gps_clock = self._old_gps_clock
            if self._old_bipm_clock_object is not None:
                self._pint_observatory._bipm_clock_versions = self._old_bipm_clock_object
                self._old_bipm_clock_object.clear()
                self._old_bipm_clock_object.update(self._old_bipm_clock_values)
            self._restore_observatory_clocks()

        def restore_clock_callables() -> None:
            if self._old_get_toas_array is not None:
                from pint import toa

                toa.get_TOAs_array = self._old_get_toas_array
            if self._pint_observatory is None or self._old_find_clock_file is None:
                return
            topo_obs = sys.modules.get("pint.observatory.topo_obs")
            if topo_obs is not None:
                topo_obs.find_clock_file = (
                    self._old_topo_find_clock_file
                    if self._topo_obs_was_loaded
                    else self._old_find_clock_file
                )
            self._pint_observatory.find_clock_file = self._old_find_clock_file
            if self._pint_global_clocks is not None and self._old_index is not None:
                self._pint_global_clocks.Index = self._old_index

        def restore_environment() -> None:
            for key, value in self._old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        attempt("solar_system_ephemeris", restore_solar_state)
        attempt("pint_loaded_ephems", restore_loaded_ephems)
        attempt("erfa_leap_seconds", restore_erfa_leaps)
        attempt("astropy_leap_check", restore_leap_check)
        attempt("iers_state", restore_iers_state)
        attempt("pint_clock_caches", restore_pint_clocks)
        attempt("pint_clock_callables", restore_clock_callables)
        attempt("environment", restore_environment)
        self._state_installed = False
        self._state_snapshotted = False
        self._resources_binding_started = False
        self._resources_bound = False
        if errors:
            labels = ",".join(label for label, _ in errors)
            raise RuntimeError(
                f"Gate 4A-R3 process-state restoration failed: {labels}"
            ) from errors[0][1]

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._restore_process_state()


class OfflineRuntimeBoundary(AbstractContextManager["OfflineRuntimeBoundary"]):
    def __init__(self, data_root: Path, manifest: dict[str, Any]):
        self.local_repository = LocalPintRepository(data_root, manifest)
        self.network = NetworkDeny()
        self.tracer = ResourceOpenTracer(
            data_root,
            (self.local_repository.repository, self.local_repository.clock_override),
        )
        self._local_active = False
        self._network_active = False
        self._tracer_active = False
        self._final_trace: dict[str, Any] | None = None
        self._used = False

    def __enter__(self) -> Self:
        if self._used:
            raise RuntimeError("Gate 4A-R3 offline boundary cannot be re-entered")
        self._used = True
        try:
            self.local_repository.__enter__()
            self._local_active = True
            self.network.__enter__()
            self._network_active = True
            self.tracer.__enter__()
            self._tracer_active = True
            self.local_repository.bind_science_resources()
            return self
        except BaseException:
            self.__exit__(*sys.exc_info())
            raise

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        errors: list[tuple[str, BaseException]] = []
        if self._local_active:
            try:
                self.local_repository.__exit__(exc_type, exc_value, traceback)
            except BaseException as error:  # noqa: BLE001 - continue boundary restoration
                errors.append(("resource_state_restore", error))
            self._local_active = False
        if self._tracer_active and self._network_active:
            self._final_trace = self._observe_trace()
            if self._final_trace["status"] != "pass":
                trace_error = RuntimeError(
                    f"v0.2.8 offline resource trace failed: {self._final_trace['failures']}"
                )
                if exc_value is None:
                    errors.append(("final_resource_trace", trace_error))
                else:
                    exc_value.add_note(str(trace_error))
        if self._tracer_active:
            try:
                self.tracer.__exit__(exc_type, exc_value, traceback)
            except BaseException as error:  # noqa: BLE001 - continue boundary restoration
                errors.append(("resource_tracer_restore", error))
            self._tracer_active = False
        if self._network_active:
            try:
                self.network.__exit__(exc_type, exc_value, traceback)
            except BaseException as error:  # noqa: BLE001 - continue boundary restoration
                errors.append(("network_guard_restore", error))
            self._network_active = False
        if errors:
            labels = ",".join(label for label, _ in errors)
            raise RuntimeError(f"Gate 4A-R3 boundary exit failed: {labels}") from errors[0][1]

    def _observe_trace(self) -> dict[str, Any]:
        expected = {
            Path(entry["controlled_relative_path"]).as_posix()
            for entry in self.local_repository.manifest["entries"]
        }
        failures: list[str] = []
        if self.network.attempts:
            failures.append("network_attempts_recorded")
        unexpected = sorted(self.tracer.opened - expected)
        missing = sorted(expected - self.tracer.opened)
        if unexpected:
            failures.append(f"unexpected_resource_opens:{unexpected}")
        if missing:
            failures.append(f"manifested_resources_not_opened:{missing}")
        return {
            "status": "pass" if not failures else "fail",
            "network_attempt_count": len(self.network.attempts),
            "opened_resources": sorted(self.tracer.opened),
            "expected_resources": sorted(expected),
            "failures": failures,
        }

    def verify_trace(self) -> dict[str, Any]:
        return self._final_trace if self._final_trace is not None else self._observe_trace()


def current_platform_observation() -> dict[str, Any]:
    precision = assert_precision()
    return {
        "python_version": sys.version.split()[0],
        "python_executable": str(Path(sys.executable).resolve()),
        "macos": platform.mac_ver()[0],
        "kernel_machine": os.uname().machine,
        "process_machine": platform.machine(),
        "pointer_bits": 64 if sys.maxsize > 2**32 else 32,
        "precision": precision,
    }
