from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .pilot2_injection_executor import InjectionContext
from .pilot2_injection_executor_v023 import execute_injection_case as execute_v023_case

RECORD_SCHEMA_VERSION = 3
RECORD_RUN_ID = "pilot2-b1937-injection-remediation-v0.2.8"


def execute_injection_case(
    context: InjectionContext,
    case: dict[str, Any],
    threshold: float,
    audit_required: bool,
    config: dict[str, Any],
    execution_binding: str,
    on_operation: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Run the unchanged v0.2.3 science executor with a v0.2.8 record identity."""
    record = execute_v023_case(
        context,
        case,
        threshold,
        audit_required,
        config,
        execution_binding,
        on_operation=on_operation,
    )
    record["schema_version"] = RECORD_SCHEMA_VERSION
    record["run_id"] = RECORD_RUN_ID
    return record
