"""Domain-facing adapter protocol for runtime-owned SOF compilation."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol

from sof_runtime.contracts import ContractError, load_json, validate_contract
from sof_runtime.paths import RUNTIME_CONTRACT_ROOT


CANONICAL_CANDIDATE_SCHEMA = RUNTIME_CONTRACT_ROOT / "expert-realization-candidate.schema.json"
EXTENSION_CANDIDATE_SCHEMA = RUNTIME_CONTRACT_ROOT / "expert-extension-realization-candidate.schema.json"


class ExpertAdapter(Protocol):
    """The only object an external domain adapter must implement.

    Adapter methods exchange JSON-compatible dictionaries. The adapter never
    returns canonical SOF IR; the runtime builds that internal representation.
    """

    def describe(self) -> dict[str, Any]: ...

    def inspect_source(self, source: dict[str, Any]) -> dict[str, Any]: ...

    def realize(
        self, source: dict[str, Any], request: dict[str, Any]
    ) -> dict[str, Any]: ...

    def evidence(self) -> dict[str, Any]: ...


def load_expert_adapter(path: str | Path) -> ExpertAdapter:
    module_path = Path(path).resolve()
    if not module_path.is_file() or module_path.suffix != ".py":
        raise ContractError(f"expert adapter must be a Python file: {module_path}")
    spec = importlib.util.spec_from_file_location("sof_external_adapter", module_path)
    if spec is None or spec.loader is None:
        raise ContractError(f"cannot load expert adapter: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    factory = getattr(module, "get_adapter", None)
    adapter = factory() if callable(factory) else getattr(module, "ADAPTER", None)
    if adapter is None:
        raise ContractError("adapter module must expose get_adapter() or ADAPTER")
    missing = [
        name
        for name in ("describe", "inspect_source", "realize", "evidence")
        if not callable(getattr(adapter, name, None))
    ]
    if missing:
        raise ContractError("expert adapter is missing methods: " + ", ".join(missing))
    return adapter


def validate_declaration(declaration: dict[str, Any]) -> None:
    validate_contract(
        declaration,
        RUNTIME_CONTRACT_ROOT / "expert-adapter-declaration.schema.json",
        label="Expert Adapter Declaration",
    )


def validate_candidate(candidate: dict[str, Any]) -> str:
    """Validate and return runtime-derived compilation eligibility."""
    if candidate.get("candidate_kind") == "extension_only":
        validate_contract(
            candidate,
            EXTENSION_CANDIDATE_SCHEMA,
            label="Expert Extension Realization Candidate",
        )
        return "extension_only"
    validate_contract(
        candidate,
        CANONICAL_CANDIDATE_SCHEMA,
        label="Canonical-compilable Expert Realization Candidate",
    )
    return "canonical_compilable"


def load_case_json(case_directory: str | Path) -> dict[str, Any]:
    directory = Path(case_directory).resolve()
    case_path = directory / "case.json"
    case = load_json(case_path)
    if not isinstance(case, dict):
        raise ContractError("external adapter case must be an object")
    for key in ("case_id", "source", "adapter"):
        if key not in case:
            raise ContractError(f"external adapter case lacks {key}")
    return case
