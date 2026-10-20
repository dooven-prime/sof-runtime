"""Local Q2 errors, cooperative resource bounds, and input identity."""

from dataclasses import dataclass
import hashlib
import json
import time

IMPLEMENTATION_STATUS = "SYNTAX_WIDE_Q2_IMPLEMENTED"
LANGUAGE = "ECC_SYN_V1"


class InputError(ValueError):
    pass


class ResourceLimit(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise InputError(message)


def fields(value, required, optional=()):
    require(type(value) is dict, "expected a JSON object")
    require(set(required) <= value.keys(), f"missing fields: {set(required) - value.keys()}")
    require(value.keys() <= set(required) | set(optional), "undeclared object fields")


@dataclass
class Budget:
    max_states: int = 100000
    max_steps: int = 10000000
    max_ast_nodes: int = 100000
    max_seconds: float | None = None
    steps: int = 0
    ast_nodes: int = 0

    def __post_init__(self):
        for name in ("max_states", "max_steps", "max_ast_nodes"):
            value = getattr(self, name)
            require(type(value) is int and value > 0, f"invalid {name}")
        require(self.max_seconds is None or
                (type(self.max_seconds) in (int, float) and self.max_seconds > 0),
                "invalid max_seconds")
        self.started = time.monotonic()

    def tick(self, count=1):
        self.steps += count
        if self.steps > self.max_steps:
            raise ResourceLimit("evaluation/exploration step limit")
        if self.max_seconds is not None and time.monotonic() - self.started >= self.max_seconds:
            raise ResourceLimit("cooperative wall-time limit")

    def node(self):
        self.ast_nodes += 1
        if self.ast_nodes > self.max_ast_nodes:
            raise ResourceLimit("AST/type node limit")
        self.tick()


def digest(request):
    try:
        data = json.dumps(request, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        if "integer string conversion" in str(exc):
            raise ResourceLimit("integer serialization resource limit") from exc
        raise InputError("request must contain only finite JSON data") from exc
    return hashlib.sha256(data).hexdigest()
