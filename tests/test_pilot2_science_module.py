from __future__ import annotations

import copy
import hashlib
import json
import os
import socket
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from pulsar_pilot import pilot2_offline_resources as offline
from pulsar_pilot import pilot2_release_contract as release
from pulsar_pilot import pilot2_runtime_core as runtime
from pulsar_pilot import pilot2_science_module as science
from pulsar_pilot.pilot2_durable_ledger import V028Ledger
from pulsar_pilot.pilot2_trusted_data import TrustedDataError


def _binding(data_root: Path, run_id: str = "pilot2-ioc-test-001") -> dict[str, Any]:
    return {
        "schema": release.IOC_SCIENCE_BINDING_SCHEMA,
        "ioc_run_id": run_id,
        "module_release_id": release.IOC_MODULE_RELEASE_ID,
        "science_run_id": release.IOC_SCIENCE_RUN_ID,
        "execution_freeze_sha256": "a" * 64,
        "inventory_sha256": release.INVENTORY_SHA256,
        "expected_accounting": dict(release.IOC_EXPECTED_ACCOUNTING),
        "science_data_root": {
            "canonical_path": str(data_root.resolve()),
            "data_root_id": "pilot2-test-data-root",
            "marker_sha256": "b" * 64,
        },
        "fresh_only": True,
        "resume_authorized": False,
    }


def _run_root(tmp_path: Path, binding: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    run_root = tmp_path / binding["ioc_run_id"]
    run_root.mkdir()
    manifest = {
        "run_id": binding["ioc_run_id"],
        "science_execution": binding,
    }
    (run_root / "manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
    return run_root, manifest


def _write_inner_artifacts(
    data_root: Path,
    *,
    complete: bool = True,
    hard_stop: bool = False,
) -> None:
    paths = science.ARTIFACT_PATHS
    ledger_path = data_root / paths["ledger"]
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text(
        json.dumps(
            {
                "execution_binding_sha256": "c" * 64,
                "hard_stop": {"reason": "test"} if hard_stop else None,
            }
        ),
        encoding="utf-8",
    )
    (data_root / paths["health"]).write_text('{"outcomes":false}\n', encoding="utf-8")
    if complete:
        (data_root / paths["terminal_result"]).write_text('{"sealed":"result"}\n', encoding="utf-8")
        (data_root / paths["annual_mask"]).write_text('{"sealed":"mask"}\n', encoding="utf-8")


def test_module_identity_and_preflight_are_zero_science(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = {"gate": 0, "execute": 0}
    gate_arguments: list[dict[str, Any]] = []

    def passed_gate(*args: Any, **kwargs: Any) -> dict[str, Any]:
        calls["gate"] += 1
        gate_arguments.append(dict(kwargs))
        return {"status": "pass", "failures": [], "predecessors_loaded": False}

    def forbidden_execute(*args: Any, **kwargs: Any) -> dict[str, Any]:
        calls["execute"] += 1
        raise AssertionError("science execution is forbidden in preflight")

    monkeypatch.setattr(science, "verify_ioc_science_execution_authorization", passed_gate)
    monkeypatch.setattr(science, "execute", forbidden_execute)

    assert science.SCIENCE_MODULE.module_id == release.IOC_MODULE_ID
    assert science.SCIENCE_MODULE.release_id == release.IOC_MODULE_RELEASE_ID
    binding = _binding(tmp_path / "absent-science-root")
    assert science.SCIENCE_MODULE.verify_gate(tmp_path, binding)["status"] == "PASS"
    preflight = science.SCIENCE_MODULE.preflight(tmp_path)
    assert preflight["zero_science_counters"] == dict.fromkeys(science.ZERO_SCIENCE_COUNTERS, 0)
    assert preflight["run_root_created"] is False
    assert preflight["science_executed"] is False
    assert calls == {"gate": 2, "execute": 0}
    assert gate_arguments[0] == {"binding": binding, "root": tmp_path}
    assert gate_arguments[1] == {"root": tmp_path}


def test_binding_validation_is_exact_and_does_not_open_root(tmp_path: Path) -> None:
    absent_root = tmp_path / "absent-science-root"
    binding = _binding(absent_root)

    normalized = release.validate_ioc_science_execution_binding(
        binding, ioc_run_id=binding["ioc_run_id"]
    )

    assert normalized == binding
    assert not absent_root.exists()

    mutations: list[dict[str, Any]] = []
    extra = copy.deepcopy(binding)
    extra["extra"] = True
    mutations.append(extra)
    wrong_run = copy.deepcopy(binding)
    wrong_run["ioc_run_id"] = "pilot2-ioc-other"
    mutations.append(wrong_run)
    wrong_inventory = copy.deepcopy(binding)
    wrong_inventory["inventory_sha256"] = "0" * 64
    mutations.append(wrong_inventory)
    relative_root = copy.deepcopy(binding)
    relative_root["science_data_root"]["canonical_path"] = "relative/root"
    mutations.append(relative_root)
    resumable = copy.deepcopy(binding)
    resumable["resume_authorized"] = True
    mutations.append(resumable)

    for candidate in mutations:
        with pytest.raises(TrustedDataError):
            release.validate_ioc_science_execution_binding(
                candidate, ioc_run_id=binding["ioc_run_id"]
            )
    assert not absent_root.exists()


@pytest.mark.parametrize("science_status", ["pass", "fail"])
def test_adapter_uses_only_bound_root_and_seals_outcome_free_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    science_status: str,
) -> None:
    data_root = tmp_path / "science-root"
    data_root.mkdir()
    binding = _binding(data_root)
    run_root, manifest = _run_root(tmp_path, binding)
    decoy = tmp_path / "environment-decoy"
    monkeypatch.setenv("RECHERCHE_DATA_ROOT", str(decoy))
    observed: dict[str, Any] = {}

    def fake_execute(path: Path, **kwargs: Any) -> dict[str, Any]:
        observed["path"] = path
        observed["binding"] = kwargs["ioc_binding"]
        observed["manifest_sha256"] = kwargs["ioc_manifest_sha256"]
        kwargs["publish_status"](stage="run", completed=25, total=344, checkpoint=25)
        _write_inner_artifacts(path)
        return {
            "status": science_status,
            "completed_injection_cases": 344,
            "execution_binding_sha256": "c" * 64,
        }

    published: list[dict[str, Any]] = []

    def publish_status(**fields: Any) -> dict[str, Any]:
        published.append(dict(fields))
        return dict(fields)

    monkeypatch.setattr(science, "execute", fake_execute)
    result = science.SCIENCE_MODULE.run(run_root, manifest, publish_status)

    assert result == {"completed": 344, "total": 344, "checkpoint": 344}
    assert observed["path"] == data_root.resolve()
    assert observed["binding"] == binding
    assert (
        observed["manifest_sha256"]
        == hashlib.sha256((run_root / "manifest.json").read_bytes()).hexdigest()
    )
    assert published == [{"stage": "run", "completed": 25, "total": 344, "checkpoint": 25}]
    assert not decoy.exists()

    receipt = json.loads((run_root / science.EVIDENCE_FILENAME).read_text(encoding="utf-8"))
    assert receipt["scientific_outcomes_visible"] is False
    assert "status" not in receipt and "payload" not in receipt
    assert receipt["execution_binding_sha256"] == "c" * 64
    assert receipt["accounting"] == {
        "completed": 344,
        "total": 344,
        "checkpoint": 344,
        "primary_fits": 688,
        "solver_audits": 35,
    }
    assert {item["name"] for item in receipt["artifacts"]} == set(science.ARTIFACT_PATHS)
    for item in receipt["artifacts"]:
        path = data_root / item["logical_path"]
        assert item["size_bytes"] == path.stat().st_size
        assert item["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("error", [RuntimeError("fault"), KeyboardInterrupt()])
def test_adapter_preserves_failure_and_writes_partial_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
) -> None:
    data_root = tmp_path / "science-root"
    data_root.mkdir()
    binding = _binding(data_root)
    run_root, manifest = _run_root(tmp_path, binding)

    def fake_execute(path: Path, **kwargs: Any) -> dict[str, Any]:
        kwargs["publish_status"](stage="run", completed=10, total=344, checkpoint=0)
        _write_inner_artifacts(path, complete=False, hard_stop=True)
        raise error

    monkeypatch.setattr(science, "execute", fake_execute)
    with pytest.raises(type(error)):
        science.SCIENCE_MODULE.run(run_root, manifest, lambda **fields: fields)

    receipt = json.loads((run_root / science.EVIDENCE_FILENAME).read_text(encoding="utf-8"))
    assert receipt["accounting"]["completed"] == 10
    assert receipt["accounting"]["checkpoint"] == 0
    assert receipt["hard_stop_present"] is True
    assert {item["name"] for item in receipt["artifacts"]} == {"ledger", "health"}


def test_receipt_failure_does_not_reclassify_operator_interrupt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_root = tmp_path / "science-root"
    data_root.mkdir()
    binding = _binding(data_root)
    run_root, manifest = _run_root(tmp_path, binding)

    def interrupted_execute(path: Path, **kwargs: Any) -> dict[str, Any]:
        _write_inner_artifacts(path, complete=False, hard_stop=True)
        raise KeyboardInterrupt

    def failed_receipt(*args: Any, **kwargs: Any) -> None:
        raise science.ScienceAdapterError("injected receipt failure")

    monkeypatch.setattr(science, "execute", interrupted_execute)
    monkeypatch.setattr(science, "_write_once", failed_receipt)

    with pytest.raises(KeyboardInterrupt) as raised:
        science.SCIENCE_MODULE.run(run_root, manifest, lambda **fields: fields)

    assert isinstance(raised.value.__cause__, science.ScienceAdapterError)


def test_adapter_rejects_runtime_ledger_binding_disagreement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_root = tmp_path / "science-root"
    data_root.mkdir()
    binding = _binding(data_root)
    run_root, manifest = _run_root(tmp_path, binding)

    def mismatched_execute(path: Path, **kwargs: Any) -> dict[str, Any]:
        _write_inner_artifacts(path)
        return {
            "status": "pass",
            "completed_injection_cases": 344,
            "execution_binding_sha256": "e" * 64,
        }

    monkeypatch.setattr(science, "execute", mismatched_execute)
    with pytest.raises(science.ScienceAdapterError, match="bindings differ"):
        science.SCIENCE_MODULE.run(run_root, manifest, lambda **fields: fields)

    receipt = json.loads((run_root / science.EVIDENCE_FILENAME).read_text(encoding="utf-8"))
    assert receipt["execution_binding_sha256"] == "c" * 64


def test_adapter_rejects_success_without_execution_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_root = tmp_path / "science-root"
    data_root.mkdir()
    binding = _binding(data_root)
    run_root, manifest = _run_root(tmp_path, binding)

    def unbound_execute(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"status": "pass", "completed_injection_cases": 344}

    monkeypatch.setattr(science, "execute", unbound_execute)
    with pytest.raises(science.ScienceAdapterError, match="runtime execution binding"):
        science.SCIENCE_MODULE.run(run_root, manifest, lambda **fields: fields)

    receipt = json.loads((run_root / science.EVIDENCE_FILENAME).read_text(encoding="utf-8"))
    assert receipt["execution_binding_sha256"] is None


def test_adapter_refuses_broken_artifact_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_root = tmp_path / "science-root"
    data_root.mkdir()
    binding = _binding(data_root)
    run_root, manifest = _run_root(tmp_path, binding)

    def symlinked_execute(path: Path, **kwargs: Any) -> dict[str, Any]:
        ledger = path / science.ARTIFACT_PATHS["ledger"]
        ledger.parent.mkdir(parents=True)
        ledger.symlink_to(path / "absent-ledger.json")
        return {
            "status": "pass",
            "completed_injection_cases": 344,
            "execution_binding_sha256": "c" * 64,
        }

    monkeypatch.setattr(science, "execute", symlinked_execute)
    with pytest.raises(science.ScienceAdapterError, match="ledger is not a regular file"):
        science.SCIENCE_MODULE.run(run_root, manifest, lambda **fields: fields)
    assert not (run_root / science.EVIDENCE_FILENAME).exists()


def test_adapter_rejects_symlink_root_before_runtime_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_root = tmp_path / "real-science-root"
    real_root.mkdir()
    alias_root = tmp_path / "science-root-alias"
    alias_root.symlink_to(real_root, target_is_directory=True)
    binding = _binding(real_root)
    binding["science_data_root"]["canonical_path"] = str(alias_root)
    run_root, manifest = _run_root(tmp_path, binding)
    calls = 0

    def forbidden_execute(*args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise AssertionError("runtime must not be called through a root alias")

    monkeypatch.setattr(science, "execute", forbidden_execute)
    with pytest.raises(science.ScienceAdapterError, match="not canonical"):
        science.SCIENCE_MODULE.run(run_root, manifest, lambda **fields: fields)
    assert calls == 0
    assert not (run_root / science.EVIDENCE_FILENAME).exists()


def _empty_ledger(data_root: Path) -> dict[str, Any]:
    return V028Ledger(
        data_root,
        inventory_sha256=release.INVENTORY_SHA256,
        implementation_sha256="1" * 64,
        science_control_sha256="2" * 64,
        environment_manifest_sha256="3" * 64,
        resource_manifest_sha256="4" * 64,
    ).empty()


def test_runtime_freshness_is_pure_and_refuses_state_or_artifact_reuse(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "science-root"
    data_root.mkdir()
    paths = {
        "result": science.ARTIFACT_PATHS["terminal_result"],
        "annual_mask": science.ARTIFACT_PATHS["annual_mask"],
        "health": science.ARTIFACT_PATHS["health"],
        "case_root": "derived/pilot2/calibration-v0.2.8/injections",
    }
    empty = _empty_ledger(data_root)

    assert runtime.verify_ioc_fresh_state(empty, data_root, paths) == {
        "status": "pass",
        "completed": 0,
        "total": 344,
        "checkpoint": 0,
    }

    nonfresh = copy.deepcopy(empty)
    nonfresh["checkpoints"] = [{"completed_cases": 1, "recorded_utc": "test"}]
    with pytest.raises(RuntimeError, match="not fresh"):
        runtime.verify_ioc_fresh_state(nonfresh, data_root, paths)

    result_path = data_root / paths["result"]
    result_path.parent.mkdir(parents=True)
    result_path.write_text("sealed", encoding="utf-8")
    with pytest.raises(RuntimeError, match="physical_artifact:result"):
        runtime.verify_ioc_fresh_state(empty, data_root, paths)


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (KeyboardInterrupt(), "operator_controlled_stop"),
        (RuntimeError("fault"), "operational_failure"),
    ],
)
def test_runtime_terminalizes_successor_stop_without_resume(
    tmp_path: Path, error: BaseException, reason: str
) -> None:
    data_root = tmp_path / reason
    data_root.mkdir()
    ledger = V028Ledger(
        data_root,
        inventory_sha256=release.INVENTORY_SHA256,
        implementation_sha256="1" * 64,
        science_control_sha256="2" * 64,
        environment_manifest_sha256="3" * 64,
        resource_manifest_sha256="4" * 64,
    )

    runtime._terminalize_ioc_failure(ledger, error, None)

    state = ledger.load()
    assert state["stage_status"][runtime.STAGE] == "fail"
    assert state["hard_stop"]["reason"] == reason
    assert state["active_attempt"] is None
    assert state["runtime_active"] is False


def test_successor_and_legacy_routes_are_both_unauthorized_without_freeze(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    (root / "protocol").mkdir(parents=True)

    successor = release.verify_ioc_science_execution_authorization(root=root)
    legacy = release.verify_repository_execution_authorization(root=root)

    assert successor["status"] == "locked"
    assert legacy["status"] == "fail"
    assert legacy["status"] != "pass"
    assert successor["predecessors_loaded"] is False
    assert legacy["predecessors_loaded"] is False

    legacy_freeze = root / release.EXECUTION_FREEZE_PATH
    legacy_freeze.write_text("{}\n", encoding="utf-8")
    refused = release.verify_ioc_science_execution_authorization(root=root)
    assert refused["status"] == "fail"
    assert "legacy v0.2.8 execution freeze must remain absent" in refused["failures"]


def test_repository_authority_compares_external_binding_before_root_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "repository"
    freeze_path = root / release.IOC_EXECUTION_FREEZE_PATH
    freeze_path.parent.mkdir(parents=True)
    freeze_path.write_text("{}\n", encoding="utf-8")
    binding = _binding(tmp_path / "absent-science-root")
    freeze = {
        "ioc_run_id": binding["ioc_run_id"],
        "module_release_id": binding["module_release_id"],
        "science_run_id": binding["science_run_id"],
        "inventory_sha256": binding["inventory_sha256"],
        "expected_accounting": binding["expected_accounting"],
        "science_data_root": {
            "data_root_id": binding["science_data_root"]["data_root_id"],
            "marker_sha256": binding["science_data_root"]["marker_sha256"],
        },
        "fresh_only": True,
        "resume_authorized": False,
    }
    monkeypatch.setattr(release, "hash_file", lambda *args, **kwargs: "a" * 64)
    monkeypatch.setattr(release, "load_json", lambda *args, **kwargs: freeze)
    monkeypatch.setattr(release, "_validate_ioc_execution_freeze", lambda *args, **kwargs: [])

    accepted = release.verify_ioc_science_execution_authorization(binding, root)
    assert accepted["status"] == "pass"
    assert not Path(binding["science_data_root"]["canonical_path"]).exists()

    mismatch = copy.deepcopy(binding)
    mismatch["execution_freeze_sha256"] = "c" * 64
    mismatch["science_data_root"]["marker_sha256"] = "d" * 64
    refused = release.verify_ioc_science_execution_authorization(mismatch, root)
    assert refused["status"] == "fail"
    assert "IOC science binding execution-freeze hash differs" in refused["failures"]
    assert "IOC science binding data-root identity differs from freeze" in refused["failures"]
    assert not Path(binding["science_data_root"]["canonical_path"]).exists()


def test_ioc_execution_binding_hash_binds_outer_manifest_and_run() -> None:
    values = {
        "implementation_hash": "1" * 64,
        "execution_freeze_sha256": "2" * 64,
        "threshold_lock_sha256": "3" * 64,
        "inventory_sha256": release.INVENTORY_SHA256,
        "science_control_hash": "4" * 64,
        "environment_manifest_sha256": "5" * 64,
        "resource_manifest_sha256": "6" * 64,
        "input_binding_sha256": "7" * 64,
        "ioc_manifest_sha256": "8" * 64,
        "ioc_run_id": "pilot2-ioc-test-001",
    }

    first = release.ioc_execution_binding_sha256(**values)
    changed_manifest = release.ioc_execution_binding_sha256(
        **{**values, "ioc_manifest_sha256": "9" * 64}
    )
    changed_run = release.ioc_execution_binding_sha256(
        **{**values, "ioc_run_id": "pilot2-ioc-test-002"}
    )

    assert len(first) == 64
    assert len({first, changed_manifest, changed_run}) == 3


def test_gate4_manifest_builders_are_exact_and_live_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    for name in ("pixi.lock", "pixi.toml", "pyproject.toml"):
        (repository / name).write_text(f"{name}\n", encoding="utf-8")
    data_root = tmp_path / "data-root"
    local = data_root / "controlled/offline-resources"
    clocks = data_root / "controlled/clock-overrides"
    local.mkdir(parents=True)
    clocks.mkdir(parents=True)
    (local / "index.txt").write_text("index\n", encoding="utf-8")
    (clocks / "time_ao.dat").write_text("clock\n", encoding="utf-8")
    entries = [
        {
            "logical_name": "global-clock-index",
            "controlled_relative_path": "controlled/offline-resources/index.txt",
            "source_url_or_publication": "test source",
            "license_or_redistribution_status": "test-only",
            "consumer": "PINT",
            "resolution_role": "global_clock_index",
        },
        {
            "logical_name": "arecibo-clock",
            "controlled_relative_path": "controlled/clock-overrides/time_ao.dat",
            "source_url_or_publication": "test source",
            "license_or_redistribution_status": "test-only",
            "consumer": "PINT",
            "resolution_role": "observatory_clock",
        },
    ]
    resource = offline.build_resource_manifest(
        data_root,
        manifest_id="gate4-resource-test",
        local_repository_relative_path="controlled/offline-resources",
        clock_override_relative_path="controlled/clock-overrides",
        entries=entries,
        required_resource_classes=["global_clock_index", "observatory_clock"],
    )
    assert {item["controlled_relative_path"] for item in resource["entries"]} == {
        "controlled/offline-resources/index.txt",
        "controlled/clock-overrides/time_ao.dat",
    }
    module_file = tmp_path / "critical.py"
    module_file.write_text("VALUE = 1\n", encoding="utf-8")
    observed = {
        "python_version": sys.version.split()[0],
        "python_executable": str(Path(sys.executable).resolve()),
        "macos": "test-macos",
        "kernel_machine": "arm64",
        "process_machine": "x86_64",
        "pointer_bits": 64,
        "precision": {
            "gate_g1_precision": "pass",
            "extended_precision": True,
            "float64_mantissa_bits": 52,
            "longdouble_mantissa_bits": 63,
        },
    }
    packages = [
        {
            "name": name,
            "version": "1",
            "build": "test",
            "channel": "test",
            "sha256": "a" * 64,
        }
        for name in sorted(("python", "pint-pulsar", "astropy-base", "numpy", "scipy"))
    ]
    monkeypatch.setattr(offline, "current_platform_observation", lambda: observed)
    monkeypatch.setattr(offline, "_installed_conda_packages", lambda: packages)
    monkeypatch.setattr(
        offline.importlib.util,
        "find_spec",
        lambda name: SimpleNamespace(origin=str(module_file)),
    )
    monkeypatch.setenv("PILOT2_GATE4_TEST_ALLOWED", "fixed")
    resource_sha = science._manifest_sha256(resource)
    environment = offline.build_environment_manifest(
        repository,
        manifest_id="gate4-environment-test",
        resource_manifest_sha256=resource_sha,
        critical_modules=["critical"],
        allowed_environment=["PILOT2_GATE4_TEST_ALLOWED"],
    )
    assert environment["resource_manifest_sha256"] == resource_sha
    assert environment["platform"]["process_machine"] == "x86_64"

    (local / "unexpected.txt").write_text("unexpected\n", encoding="utf-8")
    with pytest.raises(TrustedDataError, match="inventory differs"):
        offline.build_resource_manifest(
            data_root,
            manifest_id="gate4-resource-test",
            local_repository_relative_path="controlled/offline-resources",
            clock_override_relative_path="controlled/clock-overrides",
            entries=entries,
            required_resource_classes=["global_clock_index", "observatory_clock"],
        )


_GATE4_R3_TEST_RESOURCE_ROLES = {
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
_GATE4_R3_TEST_REQUIRED_CLASSES = {
    "observatory_clock",
    "gps_clock",
    "bipm_clock",
    "iers_a",
    "iers_b",
    "leap_seconds",
    "solar_system_ephemeris",
}
_GATE4_R3_TEST_CLOCKS = (
    "time_ao.dat",
    "time_gbt.dat",
    "gps2utc.clk",
    "tai2tt_bipm2019.clk",
)


def _gate4_r3_resource_fixture(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    data_root = tmp_path / "gate4-r3-data-root"
    entries: list[dict[str, str]] = []
    for index, (relative, role) in enumerate(_GATE4_R3_TEST_RESOURCE_ROLES.items()):
        path = data_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"gate4-r3-fixture-{index}\n".encode())
        entries.append(
            {
                "logical_name": relative.replace("/", "-"),
                "controlled_relative_path": relative,
                "source_url_or_publication": "Gate 4A-R3 disposable fixture",
                "license_or_redistribution_status": "test-only",
                "consumer": "PINT" if role.endswith("clock") else "Astropy/PINT",
                "resolution_role": role,
            }
        )
    manifest = offline.build_resource_manifest(
        data_root,
        manifest_id="gate4-r3-resource-test",
        local_repository_relative_path="derived/cache-v0.2.8",
        clock_override_relative_path="controlled/clock-overrides",
        entries=entries,
        required_resource_classes=sorted(_GATE4_R3_TEST_REQUIRED_CLASSES),
    )
    return data_root, manifest


def _install_gate4_r3_library_fakes(
    monkeypatch: pytest.MonkeyPatch,
    data_root: Path,
) -> SimpleNamespace:
    import erfa
    import pint.observatory.global_clock_corrections as global_clocks
    import pint.solar_system_ephemerides as pint_ephemerides
    from astropy.coordinates import solar_system_ephemeris
    from astropy.time import core as time_core
    from astropy.utils import iers
    from pint import observatory
    from pint.observatory import topo_obs

    observatory.Observatory.names()
    resource_reads: list[str] = []
    clock_calls: list[dict[str, Any]] = []
    kernel_closes: list[str] = []
    leap_events: list[Any] = []

    def read_resource(value: str | Path) -> str:
        path = Path(value).resolve(strict=True)
        path.read_bytes()
        relative = path.relative_to(data_root).as_posix()
        resource_reads.append(relative)
        return relative

    def primary_find_clock_file(
        name: str,
        format: str,
        bogus_last_correction: bool = False,
        url_base: Any = None,
        clock_dir: Any = None,
        valid_beyond_ends: bool = False,
    ) -> str:
        relative = read_resource(Path(clock_dir) / name)
        clock_calls.append(
            {
                "name": name,
                "format": format,
                "bogus_last_correction": bogus_last_correction,
                "url_base": url_base,
                "clock_dir": str(Path(clock_dir).resolve(strict=True)),
                "valid_beyond_ends": valid_beyond_ends,
            }
        )
        return relative

    def topo_find_clock_file(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("the pre-boundary topo alias must be restored, not called")

    def original_index(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("the PINT global Index must never be constructed")

    monkeypatch.setattr(observatory, "find_clock_file", primary_find_clock_file)
    monkeypatch.setattr(topo_obs, "find_clock_file", topo_find_clock_file)
    monkeypatch.setattr(global_clocks, "Index", original_index)

    prior_gps_clock = object()
    prior_bipm_value = object()
    prior_bipm_clocks = {"prior": prior_bipm_value}
    monkeypatch.setattr(observatory, "_gps_clock", prior_gps_clock)
    monkeypatch.setattr(observatory, "_bipm_clock_versions", prior_bipm_clocks)
    clock_observatory = next(
        item for item in observatory.Observatory._registry.values() if hasattr(item, "_clock")
    )
    prior_observatory_clock = object()
    monkeypatch.setattr(clock_observatory, "_clock", prior_observatory_clock)

    prior_iers_b = iers.IERS_B()
    prior_iers_auto = iers.IERS_Auto()
    prior_earth_orientation = iers.IERS_B()
    controlled_iers_b = iers.IERS_B()
    controlled_iers_a = iers.IERS_Auto()
    monkeypatch.setattr(iers.IERS_B, "iers_table", prior_iers_b)
    monkeypatch.setattr(iers.IERS_Auto, "iers_table", prior_iers_auto)
    monkeypatch.setattr(iers.earth_orientation_table, "_value", prior_earth_orientation)
    monkeypatch.setattr(iers.conf, "auto_download", True)

    def read_iers_b(cls: Any, *, file: str, readme: str, **kwargs: Any) -> Any:
        read_resource(file)
        read_resource(readme)
        return controlled_iers_b

    def read_iers_a(cls: Any, *, file: str, readme: str, **kwargs: Any) -> Any:
        assert iers.IERS_B.iers_table is controlled_iers_b
        read_resource(file)
        read_resource(readme)
        return controlled_iers_a

    monkeypatch.setattr(iers.IERS_B, "read", classmethod(read_iers_b))
    monkeypatch.setattr(iers.IERS_Auto, "read", classmethod(read_iers_a))

    prior_erfa_leaps = object()
    leap_state = {"value": prior_erfa_leaps}

    class ControlledLeapSeconds:
        def update_erfa_leap_seconds(self) -> None:
            leap_state["value"] = "controlled"
            leap_events.append("controlled_update")

    def from_erfa(cls: Any) -> Any:
        return prior_erfa_leaps

    def from_iers_leap_seconds(cls: Any, file: str) -> Any:
        read_resource(file)
        return ControlledLeapSeconds()

    def set_erfa_leaps(cls: Any, table: Any = None) -> None:
        leap_state["value"] = "builtin" if table is None else table
        leap_events.append(table)

    monkeypatch.setattr(iers.LeapSeconds, "from_erfa", classmethod(from_erfa))
    monkeypatch.setattr(
        iers.LeapSeconds,
        "from_iers_leap_seconds",
        classmethod(from_iers_leap_seconds),
    )
    monkeypatch.setattr(erfa.leap_seconds, "set", classmethod(set_erfa_leaps))
    leap_check_type = time_core._LEAP_SECONDS_CHECK.__class__
    prior_leap_check = leap_check_type.NOT_STARTED
    monkeypatch.setattr(time_core, "_LEAP_SECONDS_CHECK", prior_leap_check)

    prior_loaded_ephems = {"de421": "prior-kernel"}
    monkeypatch.setattr(pint_ephemerides, "loaded_ephems", prior_loaded_ephems)
    monkeypatch.setattr(solar_system_ephemeris, "_value", "builtin")
    monkeypatch.setattr(solar_system_ephemeris, "_kernel", None)

    class KernelFile:
        def close(self) -> None:
            kernel_closes.append("closed")

    def load_kernel(ephem: str, path: str | None = None, link: str | None = None) -> str:
        assert ephem == "DE440"
        assert path is not None
        read_resource(path)
        resolved = str(Path(path).resolve(strict=True))
        solar_system_ephemeris._value = resolved
        solar_system_ephemeris._kernel = SimpleNamespace(
            origin=resolved,
            daf=SimpleNamespace(file=KernelFile()),
        )
        pint_ephemerides.loaded_ephems["de440"] = resolved
        return resolved

    monkeypatch.setattr(pint_ephemerides, "load_kernel", load_kernel)
    monkeypatch.setenv("PINT_CLOCK_OVERRIDE", "prior-clock-root")
    monkeypatch.setenv("XDG_CACHE_HOME", "unchanged-cache-root")

    return SimpleNamespace(
        observatory=observatory,
        topo_obs=topo_obs,
        global_clocks=global_clocks,
        pint_ephemerides=pint_ephemerides,
        solar_system_ephemeris=solar_system_ephemeris,
        time_core=time_core,
        iers=iers,
        primary_find_clock_file=primary_find_clock_file,
        topo_find_clock_file=topo_find_clock_file,
        original_index=original_index,
        prior_gps_clock=prior_gps_clock,
        prior_bipm_clocks=prior_bipm_clocks,
        prior_bipm_value=prior_bipm_value,
        clock_observatory=clock_observatory,
        prior_observatory_clock=prior_observatory_clock,
        prior_iers_b=prior_iers_b,
        prior_iers_auto=prior_iers_auto,
        prior_earth_orientation=prior_earth_orientation,
        controlled_iers_b=controlled_iers_b,
        controlled_iers_a=controlled_iers_a,
        prior_erfa_leaps=prior_erfa_leaps,
        prior_leap_check=prior_leap_check,
        prior_loaded_ephems=prior_loaded_ephems,
        leap_state=leap_state,
        leap_events=leap_events,
        resource_reads=resource_reads,
        clock_calls=clock_calls,
        kernel_closes=kernel_closes,
        old_global_base=global_clocks.global_clock_correction_url_base,
        old_global_mirrors=list(global_clocks.global_clock_correction_url_mirrors),
    )


def _assert_gate4_r3_state_restored(state: SimpleNamespace) -> None:
    assert state.observatory.find_clock_file is state.primary_find_clock_file
    assert state.topo_obs.find_clock_file is state.topo_find_clock_file
    assert state.global_clocks.Index is state.original_index
    assert state.global_clocks.global_clock_correction_url_base == state.old_global_base
    assert state.global_clocks.global_clock_correction_url_mirrors == state.old_global_mirrors
    assert os.environ["PINT_CLOCK_OVERRIDE"] == "prior-clock-root"
    assert os.environ["XDG_CACHE_HOME"] == "unchanged-cache-root"
    assert state.observatory._gps_clock is state.prior_gps_clock
    assert state.observatory._bipm_clock_versions is state.prior_bipm_clocks
    assert state.observatory._bipm_clock_versions == {"prior": state.prior_bipm_value}
    assert state.clock_observatory._clock is state.prior_observatory_clock
    assert state.iers.IERS_B.iers_table is state.prior_iers_b
    assert state.iers.IERS_Auto.iers_table is state.prior_iers_auto
    assert state.iers.earth_orientation_table._value is state.prior_earth_orientation
    assert state.iers.conf.auto_download is True
    assert state.leap_state["value"] is state.prior_erfa_leaps
    assert state.time_core._LEAP_SECONDS_CHECK is state.prior_leap_check
    assert state.pint_ephemerides.loaded_ephems is state.prior_loaded_ephems
    assert state.pint_ephemerides.loaded_ephems == {"de421": "prior-kernel"}
    assert state.solar_system_ephemeris._value == "builtin"
    assert state.solar_system_ephemeris._kernel is None


def test_gate4_r3_manifest_closure_has_only_ten_direct_resources(tmp_path: Path) -> None:
    data_root, manifest = _gate4_r3_resource_fixture(tmp_path)

    assert {entry["controlled_relative_path"] for entry in manifest["entries"]} == set(
        _GATE4_R3_TEST_RESOURCE_ROLES
    )
    assert {entry["resolution_role"] for entry in manifest["entries"]} == (
        _GATE4_R3_TEST_REQUIRED_CLASSES
    )
    assert set(manifest["required_resource_classes"]) == _GATE4_R3_TEST_REQUIRED_CLASSES
    assert not any(path.name in {"index.txt", "url"} for path in data_root.rglob("*"))
    assert len([path for path in data_root.rglob("*") if path.is_file()]) == 10


def test_gate4_r3_direct_boundary_is_deterministic_and_restores_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root, manifest = _gate4_r3_resource_fixture(tmp_path)
    state = _install_gate4_r3_library_fakes(monkeypatch, data_root)
    expected_resources = sorted(_GATE4_R3_TEST_RESOURCE_ROLES)
    traces: list[dict[str, Any]] = []
    synthetic_bindings: list[dict[str, Any]] = []
    science_calls = 0

    def forbidden_science(*args: Any, **kwargs: Any) -> Any:
        nonlocal science_calls
        science_calls += 1
        raise AssertionError("Gate 4A-R4 must not execute science")

    monkeypatch.setattr(science, "execute", forbidden_science)
    for _ in range(2):
        with offline.OfflineRuntimeBoundary(data_root, manifest) as boundary:
            assert state.observatory.find_clock_file is not state.primary_find_clock_file
            assert state.topo_obs.find_clock_file is state.observatory.find_clock_file
            assert state.global_clocks.Index is not state.original_index
            assert os.environ["PINT_CLOCK_OVERRIDE"] == str(
                (data_root / "controlled/clock-overrides").resolve()
            )
            assert os.environ["XDG_CACHE_HOME"] == "unchanged-cache-root"
            for index, name in enumerate(_GATE4_R3_TEST_CLOCKS):
                resolver = (
                    state.observatory.find_clock_file
                    if index % 2 == 0
                    else state.topo_obs.find_clock_file
                )
                resolver(
                    name,
                    "tempo2",
                    bogus_last_correction=bool(index % 2),
                    valid_beyond_ends=bool((index + 1) % 2),
                )
            trace = boundary.verify_trace()
            assert trace == {
                "status": "pass",
                "network_attempt_count": 0,
                "opened_resources": expected_resources,
                "expected_resources": expected_resources,
                "failures": [],
            }
            assert state.iers.IERS_B.iers_table is state.controlled_iers_b
            assert state.iers.IERS_Auto.iers_table is state.controlled_iers_a
            assert state.iers.earth_orientation_table._value is state.controlled_iers_a
            assert state.iers.conf.auto_download is False
            assert state.leap_state["value"] == "controlled"
            assert state.time_core._LEAP_SECONDS_CHECK == (state.prior_leap_check.__class__.DONE)
            assert state.pint_ephemerides.loaded_ephems["de440"] == str(
                (data_root / "derived/cache-v0.2.8/ephemerides/de440.bsp").resolve()
            )
            state.observatory._gps_clock = "changed"
            state.observatory._bipm_clock_versions = {"changed": "changed"}
            state.clock_observatory._clock = "changed"
            synthetic_bindings.append(
                {
                    "opened_resources": trace["opened_resources"],
                    "network_attempt_count": trace["network_attempt_count"],
                }
            )
        final_trace = boundary.verify_trace()
        traces.append(final_trace)
        _assert_gate4_r3_state_restored(state)
        with pytest.raises(RuntimeError, match="cannot be re-entered"), boundary:
            pass

    assert traces[0] == traces[1]
    assert synthetic_bindings[0] == synthetic_bindings[1]
    assert len(state.clock_calls) == 8
    assert all(call["url_base"] is None for call in state.clock_calls)
    assert {call["name"] for call in state.clock_calls} == set(_GATE4_R3_TEST_CLOCKS)
    assert state.kernel_closes == ["closed", "closed"]
    assert science_calls == 0


def test_gate4_r3_boundary_rejects_clock_fallback_and_restores_after_body_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root, manifest = _gate4_r3_resource_fixture(tmp_path)
    state = _install_gate4_r3_library_fakes(monkeypatch, data_root)
    alternate = tmp_path / "alternate-clock-root"
    alternate.mkdir()

    with (
        pytest.raises(RuntimeError, match="injected body failure") as caught,
        offline.OfflineRuntimeBoundary(data_root, manifest),
    ):
        with pytest.raises(TrustedDataError, match="allowlist"):
            state.observatory.find_clock_file("../time_ao.dat", "tempo")
        with pytest.raises(TrustedDataError, match="URL resolution"):
            state.observatory.find_clock_file(
                "time_ao.dat", "tempo", url_base="https://invalid.example/"
            )
        with pytest.raises(TrustedDataError, match="outside the controlled root"):
            state.observatory.find_clock_file("time_ao.dat", "tempo", clock_dir=alternate)
        assert state.clock_calls == []
        for name in _GATE4_R3_TEST_CLOCKS:
            state.observatory.find_clock_file(name, "tempo2")
        with pytest.raises(offline.NetworkDeniedError):
            socket.getaddrinfo("example.invalid", 443)
        state.observatory._gps_clock = "changed"
        state.observatory._bipm_clock_versions = {"changed": "changed"}
        state.clock_observatory._clock = "changed"
        raise RuntimeError("injected body failure")

    _assert_gate4_r3_state_restored(state)
    assert state.kernel_closes == ["closed"]
    assert any("network_attempts_recorded" in note for note in caught.value.__notes__)


def test_gate4_r3_boundary_restores_after_partial_iers_binding_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root, manifest = _gate4_r3_resource_fixture(tmp_path)
    state = _install_gate4_r3_library_fakes(monkeypatch, data_root)

    def fail_iers_a(cls: Any, *, file: str, readme: str, **kwargs: Any) -> Any:
        Path(file).read_bytes()
        Path(readme).read_bytes()
        raise RuntimeError("injected IERS-A failure")

    monkeypatch.setattr(state.iers.IERS_Auto, "read", classmethod(fail_iers_a))
    with (
        pytest.raises(RuntimeError, match="injected IERS-A failure"),
        offline.OfflineRuntimeBoundary(data_root, manifest),
    ):
        raise AssertionError("boundary body must not begin")

    _assert_gate4_r3_state_restored(state)
    assert state.clock_calls == []
    assert state.kernel_closes == []


@pytest.mark.parametrize(
    ("invalid_state", "message"),
    [
        ("iers", "Earth-orientation entry state"),
        ("pint_de440", "PINT DE440 cache"),
        ("astropy_ephemeris", "Astropy ephemeris entry state"),
    ],
)
def test_gate4_r3_boundary_rejects_uncontrolled_entry_state_before_resource_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_state: str,
    message: str,
) -> None:
    data_root, manifest = _gate4_r3_resource_fixture(tmp_path)
    state = _install_gate4_r3_library_fakes(monkeypatch, data_root)
    if invalid_state == "iers":
        state.iers.earth_orientation_table._value = "default"
    elif invalid_state == "pint_de440":
        state.pint_ephemerides.loaded_ephems["de440"] = "stale"
    else:
        state.solar_system_ephemeris._value = "de430"

    with (
        pytest.raises(TrustedDataError, match=message),
        offline.OfflineRuntimeBoundary(data_root, manifest),
    ):
        raise AssertionError("boundary body must not begin")

    assert state.resource_reads == []
    assert state.clock_calls == []
    assert state.observatory.find_clock_file is state.primary_find_clock_file
    assert state.topo_obs.find_clock_file is state.topo_find_clock_file
    assert state.global_clocks.Index is state.original_index
    assert os.environ["PINT_CLOCK_OVERRIDE"] == "prior-clock-root"
    assert os.environ["XDG_CACHE_HOME"] == "unchanged-cache-root"


def _gate4_adapter_authority(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    data_root = tmp_path / "science-root"
    data_root.mkdir()
    authority = {
        "manifest_paths": {
            "resource": "protocol/PILOT2_RUNTIME_RESOURCE_MANIFEST_v0.2.8.json",
            "environment": "protocol/PILOT2_RUNTIME_ENVIRONMENT_MANIFEST_v0.2.8.json",
        },
        "restore_boundary": {
            "receipt_path": str(tmp_path / "restore.json"),
            "receipt_sha256": "1" * 64,
        },
        "science_data_root": {
            "canonical_path": str(data_root.resolve()),
            "data_root_id": "pilot2-test-data-root",
            "marker_sha256": "2" * 64,
        },
        "host": {
            "python_version": "3.11.15",
            "python_executable_sha256": science._sha256_file(Path(sys.executable).resolve()),
            "macos": "test",
            "kernel_machine": "arm64",
            "process_machine": "x86_64",
            "pointer_bits": 64,
            "minimum_free_bytes": 0,
        },
        "setup_log_paths": [
            "run_records/pilot2/gate4-context-pass-1.log",
            "run_records/pilot2/gate4-context-pass-2.log",
        ],
        "resource_manifest": {
            "manifest_id": "resource",
            "local_repository_relative_path": "controlled/offline-resources",
            "clock_override_relative_path": "controlled/clock-overrides",
            "entries": [],
            "required_resource_classes": [],
        },
        "environment_manifest": {
            "manifest_id": "environment",
            "critical_modules": ["pint"],
            "allowed_environment": [],
        },
    }
    return data_root, authority


def test_gate4_setup_log_refuses_symlink_ancestor(tmp_path: Path) -> None:
    data_root = tmp_path / "science-root"
    outside = tmp_path / "outside"
    data_root.mkdir()
    outside.mkdir()
    (data_root / "run_records").symlink_to(outside, target_is_directory=True)

    with pytest.raises(science.ScienceAdapterError, match="parent is a symlink"):
        science._validate_unused_output_path(
            data_root,
            "run_records/pilot2/gate4-context-pass-1.log",
        )

    assert list(outside.iterdir()) == []


def test_gate4_host_drift_fails_before_data_root_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_root, authority = _gate4_adapter_authority(tmp_path)
    data_root.rmdir()
    root_accesses = 0

    monkeypatch.setattr(
        science,
        "load_science_controls",
        lambda root: ({}, {}, {"manifests": authority["manifest_paths"]}),
    )
    monkeypatch.setattr(science, "_gate4_disposable_validation", list)
    monkeypatch.setattr(science, "_gate4_restore_boundary", lambda value: {})
    monkeypatch.setattr(
        science,
        "current_platform_observation",
        lambda: {
            "python_version": "changed",
            "macos": authority["host"]["macos"],
            "kernel_machine": authority["host"]["kernel_machine"],
            "process_machine": authority["host"]["process_machine"],
            "pointer_bits": authority["host"]["pointer_bits"],
            "precision": {},
        },
    )

    def forbidden_root_access(*args: Any, **kwargs: Any) -> Any:
        nonlocal root_accesses
        root_accesses += 1
        raise AssertionError("host drift must fail before data-root access")

    monkeypatch.setattr(science, "verify_data_root_identity", forbidden_root_access)

    with pytest.raises(science.ScienceAdapterError, match="host identity differs"):
        science.SCIENCE_MODULE.preflight(tmp_path, authority)

    assert root_accesses == 0
    assert not data_root.exists()


@pytest.mark.parametrize("mismatch", [False, True])
def test_gate4_adapter_uses_exact_context_twice_without_science(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mismatch: bool,
) -> None:
    data_root, authority = _gate4_adapter_authority(tmp_path)
    resource = {"schema_version": 1, "fixture": "resource"}
    resource_sha = science._manifest_sha256(resource)
    environment = {
        "schema_version": 1,
        "fixture": "environment",
        "resource_manifest_sha256": resource_sha,
    }
    observed_host = {
        "python_version": authority["host"]["python_version"],
        "python_executable": str(Path(sys.executable).resolve()),
        "macos": authority["host"]["macos"],
        "kernel_machine": authority["host"]["kernel_machine"],
        "process_machine": authority["host"]["process_machine"],
        "pointer_bits": authority["host"]["pointer_bits"],
        "precision": {},
    }
    monkeypatch.setattr(
        science,
        "load_science_controls",
        lambda root: (
            {},
            {},
            {
                "manifests": authority["manifest_paths"],
                "paths": {"case_root": "derived/pilot2/calibration-v0.2.8/injections"},
            },
        ),
    )
    monkeypatch.setattr(
        science,
        "_gate4_disposable_validation",
        lambda: [{"attempt": 1, "status": "PASS"}, {"attempt": 2, "status": "PASS"}],
    )
    monkeypatch.setattr(
        science,
        "_gate4_restore_boundary",
        lambda value: {"status": "PASS", "science_executed": False},
    )
    monkeypatch.setattr(
        science,
        "verify_data_root_identity",
        lambda root, binding: {"status": "pass", "failures": [], "marker": {}},
    )
    monkeypatch.setattr(science, "current_platform_observation", lambda: observed_host)
    monkeypatch.setattr(science, "build_resource_manifest", lambda *args, **kwargs: resource)
    monkeypatch.setattr(science, "build_environment_manifest", lambda *args, **kwargs: environment)
    monkeypatch.setattr(
        science,
        "build_v023_inventory",
        lambda: {
            "inventory_sha256": release.INVENTORY_SHA256,
            "cases": [{"case_id": "fixture-case", "period_days": 30.0}],
        },
    )
    context_calls: list[dict[str, Any]] = []

    def fake_prepare_context(root: Path, cases: list[dict[str, Any]], **kwargs: Any) -> Any:
        context_calls.append({"root": root, "cases": cases, **kwargs})
        log = root / kwargs["setup_log_relative"]
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("context setup\n", encoding="utf-8")
        active_toas = 659 if mismatch and len(context_calls) == 2 else 660
        return SimpleNamespace(
            input_binding={
                "target": "B1937+21",
                "active_toas": active_toas,
                "resource_manifest_sha256": kwargs["resource_manifest_sha256"],
                "environment_manifest_sha256": kwargs["environment_manifest_sha256"],
            }
        )

    execute_calls = 0

    def forbidden_execute(*args: Any, **kwargs: Any) -> Any:
        nonlocal execute_calls
        execute_calls += 1
        raise AssertionError("Gate 4 must not execute science")

    monkeypatch.setattr(science, "prepare_context", fake_prepare_context)
    monkeypatch.setattr(science, "execute", forbidden_execute)

    if mismatch:
        with pytest.raises(science.ScienceAdapterError, match="context bindings differ"):
            science.SCIENCE_MODULE.preflight(tmp_path, authority)
    else:
        result = science.SCIENCE_MODULE.preflight(tmp_path, authority)
        assert result["status"] == "PASS"
        assert result["zero_science_counters"] == dict.fromkeys(
            science.GATE4_ZERO_SCIENCE_COUNTERS, 0
        )
        assert result["run_root_created"] is False
        assert result["science_executed"] is False
    assert len(context_calls) == 2
    assert all(call["root"] == data_root.resolve() for call in context_calls)
    assert context_calls[0]["cases"] == context_calls[1]["cases"]
    assert context_calls[0]["resource_manifest"] == context_calls[1]["resource_manifest"]
    assert execute_calls == 0
