"""The host binding may replace only the Python executable hash and macOS version."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import recherche_operator as operator

OLD = {"python_executable_sha256": "a" * 64, "macos": "old-os"}
NEW = {"python_executable_sha256": "b" * 64, "macos": "new-os"}


def manifest(executable=OLD["python_executable_sha256"], macos=OLD["macos"]):
    return {
        "python": {"version": "3.11.15", "executable_sha256": executable},
        "platform": {"macos": macos, "kernel_machine": "x86_64"},
        "packages": [{"name": "numpy"}],
    }


@pytest.fixture
def calls(monkeypatch, tmp_path):
    seen = []

    def validate(value, *, repository_root, resource_manifest_sha256, verify_live=True):
        seen.append((json.loads(json.dumps(value)), verify_live))

    monkeypatch.setattr(operator, "validate_environment_manifest", validate)
    monkeypatch.setattr(operator, "BINDING", tmp_path / "binding.json")
    return seen


def bind(checkout=None, supersedes=OLD):
    operator.BINDING.write_text(
        json.dumps(
            {
                "binding_id": "test-binding",
                "checkout": str(operator.REPO) if checkout is None else checkout,
                "supersedes": supersedes,
                "bound": NEW,
            }
        )
    )


def test_without_binding_the_manifest_is_verified_live(calls):
    assert operator.validate_bound_environment(manifest(), "c" * 64) == "native"
    assert calls == [(manifest(), False), (manifest(), True)]


def test_binding_replaces_only_executable_hash_and_macos(calls):
    bind()
    original = manifest()
    assert operator.validate_bound_environment(original, "c" * 64) == "test-binding"
    assert original == manifest()
    assert calls[0] == (manifest(), False)
    rebound, live = calls[1]
    assert live is True
    assert rebound == manifest(NEW["python_executable_sha256"], NEW["macos"])


def test_binding_for_another_checkout_is_refused(calls):
    bind(checkout="/somewhere/else")
    with pytest.raises(RuntimeError, match="another location needs a new binding"):
        operator.validate_bound_environment(manifest(), "c" * 64)
    assert all(live is False for _, live in calls)


@pytest.mark.parametrize("changed", [{"executable": "d" * 64}, {"macos": "third-os"}])
def test_a_manifest_without_the_superseded_values_is_verified_live_unchanged(calls, changed):
    bind(checkout="/somewhere/else")
    native = manifest(**changed)
    assert operator.validate_bound_environment(native, "c" * 64) == "native"
    assert calls == [(native, False), (native, True)]


def test_committed_binding_matches_the_frozen_manifest():
    binding = json.loads(
        (operator.REPO / "protocol/RUNTIME_ENVIRONMENT_BINDING_20261116.json").read_text()
    )
    frozen_path = operator.REPO / binding["supersedes"]["environment_manifest"]
    frozen = json.loads(frozen_path.read_text())
    assert operator.sha(frozen_path) == binding["supersedes"]["environment_manifest_sha256"]
    assert frozen["python"]["executable_sha256"] == binding["supersedes"]["python_executable_sha256"]
    assert frozen["platform"]["macos"] == binding["supersedes"]["macos"]
    evidence = operator.REPO / binding["evidence"]["path"]
    assert operator.sha(evidence) == binding["evidence"]["sha256"]
    assert binding["historical_host_qualification_transferred"] is False
