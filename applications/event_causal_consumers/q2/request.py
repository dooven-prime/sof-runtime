"""Prepare a local JSON request; this is not a canonical SOF wire schema."""

from dataclasses import dataclass

from .common import Budget, LANGUAGE, digest, fields, require
from .model import parse_block, parse_environment
from .syntax import compile_expr, same
from .values import BOOL


@dataclass(frozen=True)
class Command:
    label: str
    letter: str
    guard: object


@dataclass
class Request:
    env: object
    selected: frozenset
    reports: tuple
    commands: tuple
    q: object
    budget: Budget
    sha256: str


def label(raw):
    require(type(raw) is str and bool(raw), "labels must be nonempty strings")
    return raw


def prepare(raw):
    identity = digest(raw)
    fields(raw, ("language", "environment", "selected", "program"), ("resources",))
    require(raw["language"] == LANGUAGE, "unsupported local query language")
    resources = raw.get("resources", {})
    fields(resources, (), ("max_states", "max_steps", "max_ast_nodes", "max_seconds"))
    budget = Budget(**resources)
    env = parse_environment(raw["environment"])
    selected = parse_block(raw["selected"], env, nonempty=True)
    program = raw["program"]
    fields(program, ("reports", "commands", "q"))
    require(type(program["reports"]) is list and type(program["commands"]) is list,
            "reports and commands must be arrays")
    reports, commands = [], []
    for item in program["reports"]:
        fields(item, ("label", "expr"))
        reports.append((label(item["label"]), compile_expr(item["expr"], env, budget)))
    for item in program["commands"]:
        fields(item, ("label", "letter", "guard"))
        require(type(item["letter"]) is str and item["letter"] in ("p", "d"), "unknown command letter")
        guard = compile_expr(item["guard"], env, budget)
        same(guard.sort, BOOL)
        commands.append(Command(label(item["label"]), item["letter"], guard))
    require(len({name for name, _ in reports}) == len(reports), "duplicate report label")
    require(len({c.label for c in commands}) == len(commands), "duplicate command label")
    q = compile_expr(program["q"], env, budget)
    return Request(env, selected, tuple(reports), tuple(commands), q, budget, identity)
