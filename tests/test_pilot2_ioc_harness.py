from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from pulsar_pilot import pilot2_ioc_harness as ioc
from pulsar_pilot import pilot2_release_contract as release


def _git(repository: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@dataclass
class FakeScienceModule:
    module_id: str = release.IOC_MODULE_ID
    release_id: str = release.IOC_MODULE_RELEASE_ID
    behavior: str = "success"
    nonzero_counter: str | None = None
    gate_calls: int = 0
    preflight_calls: int = 0
    run_calls: int = 0
    published_status: dict[str, Any] | None = None
    verified_binding: dict[str, Any] | None = None
    gate4_result: dict[str, Any] | None = None
    gate4_authority: dict[str, Any] | None = None

    def verify_gate(
        self,
        project_root: Path,
        science_execution: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        self.gate_calls += 1
        self.verified_binding = dict(science_execution)
        return {"status": "PASS", "project_root": str(project_root)}

    def preflight(
        self,
        project_root: Path,
        qualification: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        self.preflight_calls += 1
        if qualification is not None:
            self.gate4_authority = dict(qualification)
            if self.gate4_result is None:
                raise AssertionError("Gate 4 result fixture is absent")
            return self.gate4_result
        counters = dict.fromkeys(ioc.ZERO_SCIENCE_COUNTERS, 0)
        if self.nonzero_counter is not None:
            counters[self.nonzero_counter] = 1
        return {
            "zero_science_counters": counters,
            "run_root_created": False,
            "science_executed": False,
        }

    def run(
        self,
        run_root: Path,
        manifest: Mapping[str, Any],
        publish_status: Any,
    ) -> Mapping[str, Any]:
        self.run_calls += 1
        self.published_status = dict(
            publish_status(
                stage="run",
                completed=1,
                total=release.IOC_EXPECTED_ACCOUNTING["cases"],
                checkpoint=1,
                message="forbidden scientific message from adapter",
            )
        )
        manifest_sha256 = hashlib.sha256((run_root / "manifest.json").read_bytes()).hexdigest()
        binding = manifest["science_execution"]

        def write_receipt(
            *,
            completed: int,
            checkpoint: int,
            artifacts: list[dict[str, Any]],
            execution_binding_sha256: str | None,
            manifest_binding: str = manifest_sha256,
        ) -> None:
            receipt = {
                "schema": ioc.SCIENCE_EVIDENCE_SCHEMA,
                "ioc_run_id": manifest["run_id"],
                "science_run_id": binding["science_run_id"],
                "ioc_manifest_sha256": manifest_binding,
                "execution_freeze_sha256": binding["execution_freeze_sha256"],
                "inventory_sha256": binding["inventory_sha256"],
                "data_root_id": binding["science_data_root"]["data_root_id"],
                "marker_sha256": binding["science_data_root"]["marker_sha256"],
                "execution_binding_sha256": execution_binding_sha256,
                "accounting": {
                    "completed": completed,
                    "total": release.IOC_EXPECTED_ACCOUNTING["cases"],
                    "checkpoint": checkpoint,
                    "primary_fits": release.IOC_EXPECTED_ACCOUNTING["primary_fits"],
                    "solver_audits": release.IOC_EXPECTED_ACCOUNTING["solver_audits"],
                },
                "artifacts": artifacts,
                "hard_stop_present": self.behavior in {"interrupt", "error"},
                "scientific_outcomes_visible": False,
            }
            (run_root / "science-evidence-binding.json").write_text(
                json.dumps(receipt), encoding="utf-8"
            )

        if self.behavior == "interrupt":
            write_receipt(
                completed=1,
                checkpoint=1,
                artifacts=[],
                execution_binding_sha256=None,
            )
            raise KeyboardInterrupt
        if self.behavior == "error":
            write_receipt(
                completed=1,
                checkpoint=1,
                artifacts=[],
                execution_binding_sha256=None,
            )
            raise RuntimeError("injected operational fault")
        if self.behavior == "error_missing_receipt":
            raise RuntimeError("injected missing-receipt fault")
        if self.behavior == "error_tampered_receipt":
            write_receipt(
                completed=1,
                checkpoint=1,
                artifacts=[],
                execution_binding_sha256=None,
                manifest_binding="0" * 64,
            )
            raise RuntimeError("injected tampered-receipt fault")
        if self.behavior == "incomplete":
            return {
                "completed": 1,
                "total": release.IOC_EXPECTED_ACCOUNTING["cases"],
                "checkpoint": 1,
            }
        sealed = run_root / "sealed-science"
        sealed.mkdir()
        (sealed / "opaque-result.bin").write_bytes(b"sealed-test-evidence")
        write_receipt(
            completed=release.IOC_EXPECTED_ACCOUNTING["cases"],
            checkpoint=release.IOC_EXPECTED_ACCOUNTING["cases"],
            execution_binding_sha256="d" * 64,
            artifacts=[
                {
                    "name": name,
                    "logical_path": (
                        "run_records/pilot2/wrong-ledger.json"
                        if self.behavior == "success_bad_path" and name == "ledger"
                        else ioc.SCIENCE_EVIDENCE_ARTIFACT_PATHS[name]
                    ),
                    "size_bytes": 1,
                    "sha256": character * 64,
                }
                for name, character in zip(
                    ("ledger", "terminal_result", "annual_mask", "health"),
                    "4567",
                    strict=True,
                )
            ],
        )
        total = release.IOC_EXPECTED_ACCOUNTING["cases"]
        return {"completed": total, "total": total, "checkpoint": total}


@pytest.fixture
def bounded_context(tmp_path: Path) -> dict[str, Any]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    (repository / "README.md").write_text("bounded IOC fixture\n", encoding="utf-8")
    _git(repository, "add", "README.md")
    _git(
        repository,
        "-c",
        "user.name=Pilot 2 Test",
        "-c",
        "user.email=pilot2-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "bounded fixture",
    )
    module = FakeScienceModule()
    identity = ioc.repository_identity(repository)
    runs_root = tmp_path / "runs"
    authority = {
        "schema": ioc.AUTHORITY_SCHEMA,
        "authority_id": "authority-pilot2-ioc-test-001",
        "run_id": "pilot2-ioc-test-001",
        "created_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
        "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        "project_root": str(repository.resolve()),
        "runs_root": str(runs_root.resolve()),
        "attempt": 1,
        "one_shot": True,
        "release": {
            "commit": identity["commit"],
            "tree": identity["tree"],
            "tracked_manifest_sha256": identity["tracked_manifest_sha256"],
        },
        "science_module": {
            "module_id": module.module_id,
            "release_id": module.release_id,
        },
        "science_execution": {
            "schema": release.IOC_SCIENCE_BINDING_SCHEMA,
            "ioc_run_id": "pilot2-ioc-test-001",
            "module_release_id": release.IOC_MODULE_RELEASE_ID,
            "science_run_id": release.IOC_SCIENCE_RUN_ID,
            "execution_freeze_sha256": "a" * 64,
            "inventory_sha256": release.INVENTORY_SHA256,
            "expected_accounting": dict(release.IOC_EXPECTED_ACCOUNTING),
            "science_data_root": {
                "canonical_path": str((tmp_path / "science-root").resolve()),
                "data_root_id": "pilot2-test-data-root",
                "marker_sha256": "b" * 64,
            },
            "fresh_only": True,
            "resume_authorized": False,
        },
    }
    authority_path = tmp_path / "authority.json"
    authority_path.write_text(json.dumps(authority), encoding="utf-8")
    return {
        "repository": repository,
        "runs_root": runs_root,
        "authority_path": authority_path,
        "evidence_root": tmp_path / "preflight-evidence",
        "module": module,
    }


@pytest.fixture
def gate4_context(tmp_path: Path) -> dict[str, Any]:
    repository = tmp_path / "repository"
    (repository / "docs").mkdir(parents=True)
    _git(repository, "init", "-q")
    (repository / "README.md").write_text("bounded Gate 4 fixture\n", encoding="utf-8")
    receipts: dict[str, dict[str, str]] = {}
    for name in ("gate2", "gate3"):
        relative = f"docs/{name}.json"
        path = repository / relative
        path.write_text(json.dumps({"gate": name, "status": "PASS"}), encoding="utf-8")
        receipts[name] = {
            "relative_path": relative,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    _git(repository, "add", ".")
    _git(
        repository,
        "-c",
        "user.name=Pilot 2 Test",
        "-c",
        "user.email=pilot2-test@example.invalid",
        "commit",
        "-q",
        "-m",
        "bounded Gate 4 fixture",
    )
    module = FakeScienceModule()
    identity = ioc.repository_identity(repository)
    restore_receipt = tmp_path / "restore-boundary.json"
    restore_receipt.write_text(
        json.dumps(
            {
                "schema": "pilot2-ioc-gate4-restore-boundary-v1",
                "status": "PASS",
                "source_data_root_id": "pilot2-test-data-root",
                "restored_data_root_id": "pilot2-test-restored-root",
                "source_manifest_sha256": "8" * 64,
                "restored_manifest_sha256": "8" * 64,
                "science_executed": False,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    evidence_root = tmp_path / "gate4-evidence"
    sandbox = Path("/usr/bin/sandbox-exec")
    authority = {
        "schema": ioc.GATE4_AUTHORITY_SCHEMA,
        "authority_id": "authority-pilot2-gate4-test-001",
        "qualification_id": "pilot2-gate4-test-001",
        "created_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
        "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        "project_root": str(repository.resolve()),
        "evidence_root": str(evidence_root.resolve()),
        "attempt": 1,
        "one_shot": True,
        "release": {
            "commit": identity["commit"],
            "tree": identity["tree"],
            "tracked_manifest_sha256": identity["tracked_manifest_sha256"],
        },
        "science_module": {
            "module_id": module.module_id,
            "release_id": module.release_id,
        },
        "science_data_root": {
            "canonical_path": str((tmp_path / "science-root").resolve()),
            "data_root_id": "pilot2-test-data-root",
            "marker_sha256": "b" * 64,
        },
        "manifest_paths": {
            "resource": "protocol/PILOT2_RUNTIME_RESOURCE_MANIFEST_v0.2.8.json",
            "environment": "protocol/PILOT2_RUNTIME_ENVIRONMENT_MANIFEST_v0.2.8.json",
        },
        "setup_log_paths": [
            "run_records/pilot2/gate4-context-pass-1.log",
            "run_records/pilot2/gate4-context-pass-2.log",
        ],
        "resource_manifest": {
            "manifest_id": "gate4-test-resource",
            "local_repository_relative_path": "controlled/offline-resources",
            "clock_override_relative_path": "controlled/clock-overrides",
            "entries": [],
            "required_resource_classes": [],
        },
        "environment_manifest": {
            "manifest_id": "gate4-test-environment",
            "critical_modules": ["pint"],
            "allowed_environment": [],
        },
        "network_denial": {
            "executable": str(sandbox),
            "executable_sha256": hashlib.sha256(sandbox.read_bytes()).hexdigest(),
            "profile": ioc.GATE4_NETWORK_PROFILE,
        },
        "qualification_receipts": receipts,
        "restore_boundary": {
            "receipt_path": str(restore_receipt.resolve()),
            "receipt_sha256": hashlib.sha256(restore_receipt.read_bytes()).hexdigest(),
        },
        "host": {
            "python_version": "3.11.15",
            "python_executable_sha256": "c" * 64,
            "macos": "test",
            "kernel_machine": "arm64",
            "process_machine": "x86_64",
            "pointer_bits": 64,
            "minimum_free_bytes": 0,
        },
        "expected_zero_counters": dict.fromkeys(ioc.GATE4_ZERO_SCIENCE_COUNTERS, 0),
        "execution_authorized": False,
    }
    resource_manifest = {"schema_version": 1, "fixture": "resource"}
    environment_manifest = {"schema_version": 1, "fixture": "environment"}
    input_binding = {
        "target": "B1937+21",
        "active_toas": 660,
        "network_attempt_count": 0,
        "trace": "d" * 64,
    }
    root_marker = {
        "schema_version": 2,
        "project": ioc.MARKER_PROJECT,
        "data_root_id": authority["science_data_root"]["data_root_id"],
        "generation": "gate4-test",
    }
    restore_record = json.loads(restore_receipt.read_text(encoding="utf-8"))
    module.gate4_result = {
        "schema": ioc.GATE4_RESULT_SCHEMA,
        "status": "PASS",
        "disposable_validations": [
            {
                "attempt": attempt,
                "status": "PASS",
                "criteria": {f"criterion_{index:02d}": True for index in range(1, 14)},
                "candidate_implementation_sha256": "1" * 64,
                "candidate_science_control_sha256": "2" * 64,
                "science_cases_executed": 0,
                "random_draws_generated": 0,
                "model_fits_executed": 0,
                "periodic_scans_executed": 0,
                "observed_residual_accessed": False,
            }
            for attempt in (1, 2)
        ],
        "data_root_identity": {
            "status": "pass",
            "failures": [],
            "marker": root_marker,
        },
        "host_storage": {
            "host": {
                key: authority["host"][key]
                for key in (
                    "python_version",
                    "macos",
                    "kernel_machine",
                    "process_machine",
                    "pointer_bits",
                )
            },
            "storage": {"block_size": 4096, "total_bytes": 1024, "free_bytes": 512},
        },
        "resource_manifest": resource_manifest,
        "resource_manifest_sha256": hashlib.sha256(ioc._canonical(resource_manifest)).hexdigest(),
        "environment_manifest": environment_manifest,
        "environment_manifest_sha256": hashlib.sha256(
            ioc._canonical(environment_manifest)
        ).hexdigest(),
        "context_passes": [
            {
                "pass": number,
                "setup_log_relative": authority["setup_log_paths"][number - 1],
                "setup_log_sha256": str(number) * 64,
                "input_binding": dict(input_binding),
            }
            for number in (1, 2)
        ],
        "restore_boundary": restore_record,
        "zero_science_counters": dict.fromkeys(ioc.GATE4_ZERO_SCIENCE_COUNTERS, 0),
        "run_root_created": False,
        "science_executed": False,
    }
    authority_path = tmp_path / "gate4-authority.json"
    authority_path.write_text(json.dumps(authority), encoding="utf-8")
    return {
        "repository": repository,
        "authority": authority,
        "authority_path": authority_path,
        "evidence_root": evidence_root,
        "runs_root": tmp_path / "runs",
        "module": module,
        "restore_receipt": restore_receipt,
    }


def _prepare(context: Mapping[str, Any]) -> Path:
    ioc.preflight(
        context["repository"],
        context["authority_path"],
        module=context["module"],
        evidence_root=context["evidence_root"],
    )
    return ioc.prepare(
        context["repository"],
        context["evidence_root"],
        module=context["module"],
    )


def _events(run_root: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in (run_root / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def test_verify_gate_is_read_only_and_exact(bounded_context: dict[str, Any]) -> None:
    context = bounded_context
    before = ioc.repository_identity(context["repository"])

    gate = ioc.verify_gate(
        context["repository"],
        context["authority_path"],
        module=context["module"],
    )

    assert gate["status"] == "PASS"
    assert context["module"].gate_calls == 1
    assert context["module"].verified_binding == gate["authority"]["science_execution"]
    assert ioc.repository_identity(context["repository"]) == before
    assert not context["evidence_root"].exists()
    assert not context["runs_root"].exists()


def test_preflight_is_zero_science_and_precedes_run_root(
    bounded_context: dict[str, Any],
) -> None:
    context = bounded_context

    record = ioc.preflight(
        context["repository"],
        context["authority_path"],
        module=context["module"],
        evidence_root=context["evidence_root"],
    )

    assert record["status"] == "PASS"
    assert record["zero_science_counters"] == dict.fromkeys(ioc.ZERO_SCIENCE_COUNTERS, 0)
    assert context["module"].run_calls == 0
    assert not context["runs_root"].exists()
    assert {path.name for path in context["evidence_root"].iterdir()} == {
        "authority.json",
        "gate.json",
        "preflight.json",
    }


def test_prepare_creates_one_identity_and_refuses_reuse(
    bounded_context: dict[str, Any],
) -> None:
    context = bounded_context
    manifest_path = _prepare(context)
    run_root = manifest_path.parent

    assert manifest_path.is_file()
    assert (run_root / "run.lock").is_file()
    assert (run_root / "events.jsonl").is_file()
    assert ioc.observe_status(run_root)["state"] == "prepared"
    assert context["module"].run_calls == 0
    with pytest.raises(ioc.IocError, match="already been used"):
        ioc.prepare(
            context["repository"],
            context["evidence_root"],
            module=context["module"],
        )


def test_foreground_success_seals_metadata_and_refuses_second_run(
    bounded_context: dict[str, Any],
) -> None:
    context = bounded_context
    manifest_path = _prepare(context)

    inventory = ioc.run_foreground(manifest_path, module=context["module"])
    status = ioc.observe_status(manifest_path.parent)

    assert inventory["terminal_state"] == "complete"
    assert context["module"].run_calls == 1
    assert context["module"].published_status["message"] == "Foreground checkpoint updated"
    assert status["state"] == "complete"
    assert status["terminal"] is True
    assert status["checkpoint"] == release.IOC_EXPECTED_ACCOUNTING["cases"]
    assert status["science_outcomes_visible"] is False
    assert "result" not in status and "score" not in status
    assert (manifest_path.parent / "run.active").is_file()
    assert any(
        item["path"] == "sealed-science/opaque-result.bin" for item in inventory["artifacts"]
    )
    with pytest.raises(ioc.IocError, match="already terminal|already been started"):
        ioc.run_foreground(manifest_path, module=context["module"])


@pytest.mark.parametrize(
    ("behavior", "expected_exception", "terminal_state"),
    [
        ("interrupt", ioc.ControlledStop, "controlled_stop"),
        ("error", RuntimeError, "operational_failure"),
    ],
)
def test_operator_stop_and_fault_consume_the_run_identity(
    bounded_context: dict[str, Any],
    behavior: str,
    expected_exception: type[BaseException],
    terminal_state: str,
) -> None:
    context = bounded_context
    context["module"].behavior = behavior
    manifest_path = _prepare(context)

    with pytest.raises(expected_exception):
        ioc.run_foreground(manifest_path, module=context["module"])

    status = ioc.observe_status(manifest_path.parent)
    inventory = json.loads(
        (manifest_path.parent / "terminal-inventory.json").read_text(encoding="utf-8")
    )
    assert status["state"] == terminal_state
    assert status["terminal"] is True
    assert inventory["terminal_state"] == terminal_state
    assert (manifest_path.parent / "run.active").is_file()
    terminal_event = _events(manifest_path.parent)[-1]
    assert terminal_event["science_evidence_receipt_present"] is True
    assert terminal_event["science_evidence_receipt_valid"] is True
    assert terminal_event["science_evidence_receipt_incident"] is False


@pytest.mark.parametrize("behavior", ["error_missing_receipt", "error_tampered_receipt"])
def test_failure_receipt_incident_never_masks_original_failure(
    bounded_context: dict[str, Any], behavior: str
) -> None:
    context = bounded_context
    context["module"].behavior = behavior
    manifest_path = _prepare(context)

    with pytest.raises(RuntimeError, match=behavior.removeprefix("error_").replace("_", "-")):
        ioc.run_foreground(manifest_path, module=context["module"])

    terminal_event = _events(manifest_path.parent)[-1]
    assert terminal_event["science_evidence_receipt_valid"] is False
    assert terminal_event["science_evidence_receipt_incident"] is True
    assert terminal_event["science_evidence_receipt_present"] is (
        behavior == "error_tampered_receipt"
    )


def test_success_receipt_requires_exact_inner_artifact_paths(
    bounded_context: dict[str, Any],
) -> None:
    context = bounded_context
    context["module"].behavior = "success_bad_path"
    manifest_path = _prepare(context)

    with pytest.raises(ioc.IocError, match="artifact path differs"):
        ioc.run_foreground(manifest_path, module=context["module"])

    assert ioc.observe_status(manifest_path.parent)["state"] == "operational_failure"


def test_nonzero_preflight_fails_before_run_root(bounded_context: dict[str, Any]) -> None:
    context = bounded_context
    context["module"].nonzero_counter = "network_requests"

    with pytest.raises(ioc.IocError, match="zero-science boundary is nonzero"):
        ioc.preflight(
            context["repository"],
            context["authority_path"],
            module=context["module"],
            evidence_root=context["evidence_root"],
        )

    assert context["module"].run_calls == 0
    assert not context["runs_root"].exists()


def test_incomplete_accounting_is_terminal_operational_failure(
    bounded_context: dict[str, Any],
) -> None:
    context = bounded_context
    context["module"].behavior = "incomplete"
    manifest_path = _prepare(context)

    with pytest.raises(ioc.IocError, match="did not complete the exact workload"):
        ioc.run_foreground(manifest_path, module=context["module"])

    status = ioc.observe_status(manifest_path.parent)
    assert status["state"] == "operational_failure"
    assert status["checkpoint"] == 1
    assert (manifest_path.parent / "terminal-inventory.json").is_file()


def test_post_lock_evidence_failure_is_terminalized(
    bounded_context: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    context = bounded_context
    manifest_path = _prepare(context)
    write_event = ioc._write_event

    def fail_run_started(path: Path, event: Mapping[str, Any]) -> None:
        if event.get("event") == "run_started":
            raise ioc.IocError("injected event failure")
        write_event(path, event)

    monkeypatch.setattr(ioc, "_write_event", fail_run_started)

    with pytest.raises(ioc.IocError, match="injected event failure"):
        ioc.run_foreground(manifest_path, module=context["module"])

    status = ioc.observe_status(manifest_path.parent)
    assert status["state"] == "operational_failure"
    assert status["terminal"] is True
    assert (manifest_path.parent / "terminal-inventory.json").is_file()


def test_status_rejects_any_extra_science_field(bounded_context: dict[str, Any]) -> None:
    manifest_path = _prepare(bounded_context)
    status_path = manifest_path.parent / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["scientific_result"] = "forbidden"
    status_path.write_text(json.dumps(status), encoding="utf-8")

    with pytest.raises(ioc.IocError, match="status contract is not exact"):
        ioc.observe_status(manifest_path.parent)


def test_cli_fails_closed_while_successor_execution_is_locked(
    bounded_context: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    context = bounded_context

    result = ioc.main(
        [
            "verify-gate",
            "--project-root",
            str(context["repository"]),
            "--authority",
            str(context["authority_path"]),
        ]
    )

    assert result == 2
    assert "science gate did not pass" in capsys.readouterr().err
    assert not context["runs_root"].exists()
    assert not context["evidence_root"].exists()


def test_gate4_preflight_is_inspection_only_and_create_once(
    gate4_context: dict[str, Any],
) -> None:
    context = gate4_context

    receipt = ioc.preflight(
        context["repository"],
        context["authority_path"],
        context["evidence_root"],
        module=context["module"],
    )

    assert receipt["schema"] == ioc.GATE4_PREFLIGHT_SCHEMA
    assert receipt["status"] == "PASS"
    assert receipt["execution_authorized"] is False
    assert receipt["run_root_created"] is False
    assert receipt["science_executed"] is False
    assert receipt["zero_science_counters"] == dict.fromkeys(ioc.GATE4_ZERO_SCIENCE_COUNTERS, 0)
    assert context["module"].preflight_calls == 1
    assert context["module"].run_calls == 0
    assert context["module"].gate_calls == 0
    assert context["module"].gate4_authority["execution_authorized"] is False
    assert not context["runs_root"].exists()
    assert {
        path.relative_to(context["evidence_root"]).as_posix()
        for path in context["evidence_root"].iterdir()
    } == {
        "authority.json",
        "context-pass-1.json",
        "context-pass-2.json",
        "gate4-preflight.json",
    }
    for relative in context["authority"]["manifest_paths"].values():
        assert (context["repository"] / relative).is_file()
    assert not (context["repository"] / release.IOC_EXECUTION_FREEZE_PATH).exists()

    with pytest.raises(ioc.IocError, match="authority schema is not exact"):
        ioc.prepare(
            context["repository"],
            context["evidence_root"],
            module=context["module"],
        )
    with pytest.raises(ioc.IocError, match="manifest is not exact"):
        ioc.run_foreground(
            context["evidence_root"] / "gate4-preflight.json",
            module=context["module"],
        )
    with pytest.raises(ioc.IocError, match="authority schema is not exact"):
        ioc.verify_gate(
            context["repository"],
            context["authority_path"],
            module=context["module"],
        )
    preserved = {
        f"repository:{relative}": (context["repository"] / relative).read_bytes()
        for relative in context["authority"]["manifest_paths"].values()
    }
    preserved.update(
        {
            f"evidence:{name}": (context["evidence_root"] / name).read_bytes()
            for name in (
                "authority.json",
                "context-pass-1.json",
                "context-pass-2.json",
                "gate4-preflight.json",
            )
        }
    )
    with pytest.raises(ioc.IocError, match="repository is dirty|already exists"):
        ioc.preflight(
            context["repository"],
            context["authority_path"],
            context["evidence_root"],
            module=context["module"],
        )
    observed = {
        f"repository:{relative}": (context["repository"] / relative).read_bytes()
        for relative in context["authority"]["manifest_paths"].values()
    }
    observed.update(
        {
            f"evidence:{name}": (context["evidence_root"] / name).read_bytes()
            for name in (
                "authority.json",
                "context-pass-1.json",
                "context-pass-2.json",
                "gate4-preflight.json",
            )
        }
    )
    assert preserved == observed
    assert context["module"].preflight_calls == 1
    assert context["module"].run_calls == 0


@pytest.mark.parametrize(
    "mutation",
    [
        *[f"counter:{name}" for name in ioc.GATE4_ZERO_SCIENCE_COUNTERS],
        "context",
        "context_type",
        "resource_manifest",
        "resource_hash",
        "setup_path",
        "host",
        "data_root",
        "extra",
        "restore",
    ],
)
def test_gate4_preflight_fails_closed_on_result_drift(
    gate4_context: dict[str, Any],
    mutation: str,
) -> None:
    context = gate4_context
    result = copy.deepcopy(context["module"].gate4_result)
    if mutation.startswith("counter:"):
        result["zero_science_counters"][mutation.removeprefix("counter:")] = 1
    elif mutation == "context":
        result["context_passes"][1]["input_binding"]["active_toas"] = 659
    elif mutation == "context_type":
        result["context_passes"][1]["input_binding"]["network_attempt_count"] = False
    elif mutation == "resource_manifest":
        result["resource_manifest"]["fixture"] = "changed"
    elif mutation == "resource_hash":
        result["resource_manifest_sha256"] = "0" * 64
    elif mutation == "setup_path":
        result["context_passes"][1]["setup_log_relative"] = "unauthorized.log"
    elif mutation == "host":
        result["host_storage"]["host"]["process_machine"] = "changed"
    elif mutation == "data_root":
        result["data_root_identity"]["marker"]["data_root_id"] = "changed"
    elif mutation == "extra":
        result["unexpected"] = True
    else:
        result["restore_boundary"]["status"] = "FAIL"
    context["module"].gate4_result = result

    with pytest.raises(ioc.IocError):
        ioc.preflight(
            context["repository"],
            context["authority_path"],
            context["evidence_root"],
            module=context["module"],
        )

    assert (context["evidence_root"] / "gate4-failure.json").is_file()
    assert context["module"].run_calls == 0
    assert not context["runs_root"].exists()
    assert not any(
        (context["repository"] / relative).exists()
        for relative in context["authority"]["manifest_paths"].values()
    )


def test_gate4_operator_surface_remains_exact(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as stopped:
        ioc._main(["--help"])

    assert stopped.value.code == 0
    help_text = capsys.readouterr().out
    assert "{verify-gate,preflight,prepare,run,status,develop}" in help_text


def test_gate4_authority_cannot_grant_execution(gate4_context: dict[str, Any]) -> None:
    context = gate4_context
    authority = copy.deepcopy(context["authority"])
    authority["execution_authorized"] = True
    context["authority_path"].write_text(json.dumps(authority), encoding="utf-8")

    with pytest.raises(ioc.IocError, match="grants execution"):
        ioc.preflight(
            context["repository"],
            context["authority_path"],
            context["evidence_root"],
            module=context["module"],
        )

    assert context["module"].preflight_calls == 0
    assert context["module"].run_calls == 0
    assert not context["evidence_root"].exists()
    assert not context["runs_root"].exists()


def test_gate4_rejects_any_unapproved_repository_output(
    gate4_context: dict[str, Any],
) -> None:
    context = gate4_context
    original = context["module"].preflight

    def contaminated(
        project_root: Path,
        qualification: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        value = original(project_root, qualification)
        (project_root / "unexpected.txt").write_text("unexpected\n", encoding="utf-8")
        return value

    context["module"].preflight = contaminated
    with pytest.raises(ioc.IocError, match="exact manifest pair"):
        ioc.preflight(
            context["repository"],
            context["authority_path"],
            context["evidence_root"],
            module=context["module"],
        )

    assert (context["evidence_root"] / "gate4-failure.json").is_file()
    assert context["module"].run_calls == 0
    assert not context["runs_root"].exists()
