"""Log-only source model. No forest, UFE, or fixed-control imports."""

from collections import deque
from dataclasses import dataclass

from .common import InputError, ResourceLimit, fields, require


def atom_key(label):
    require(type(label) in (int, str), "atom labels must be integers or strings, not Bool")
    return type(label).__name__, label


@dataclass(frozen=True)
class Environment:
    defect: tuple
    seed: tuple
    atoms: tuple
    ports: tuple

    @property
    def n(self):
        return len(self.defect)

    @property
    def collision(self):
        return self.defect[self.ports[0]]

    def atom_index(self, label):
        key = atom_key(label)
        for i, candidate in enumerate(self.atoms):
            if atom_key(candidate) == key:
                return i
        raise ValueError("unknown atom label")

    def action(self, letter, position):
        return (position + 1) % self.n if letter == "p" else self.defect[position]


def parse_environment(data):
    fields(data, ("defect", "seed"), ("atoms", "kernel_ports"))
    defect, seed = data["defect"], data["seed"]
    require(type(defect) is list and len(defect) >= 2, "invalid defect carrier")
    n = len(defect)
    require(all(type(x) is int and 0 <= x < n for x in defect), "invalid defect entry")
    fibers = [tuple(i for i, x in enumerate(defect) if x == target) for target in range(n)]
    require(sorted(map(len, fibers)) == sorted([0, 2] + [1] * (n - 2)),
            "defect must have exactly one binary collision")
    kernel = next(f for f in fibers if len(f) == 2)
    ports = data.get("kernel_ports", list(kernel))
    require(type(ports) is list and len(ports) == 2 and
            all(type(x) is int for x in ports) and set(ports) == set(kernel), "invalid ordered ports")
    require(type(seed) is list and 2 <= len(seed) <= n and
            all(type(x) is int and 0 <= x < n for x in seed) and len(set(seed)) == len(seed),
            "invalid injective singleton seed")
    atoms = data.get("atoms", list(range(len(seed))))
    require(type(atoms) is list and len(atoms) == len(seed), "atom/seed length mismatch")
    require(len({atom_key(x) for x in atoms}) == len(atoms), "duplicate atom labels")
    return Environment(tuple(defect), tuple(seed), tuple(atoms), tuple(ports))


def parse_block(data, env, nonempty=False):
    require(type(data) is list, "block must be a list of declared atom labels")
    try:
        result = frozenset(env.atom_index(x) for x in data)
    except ValueError as exc:
        raise InputError("block uses an undeclared atom") from exc
    require(len(result) == len(data), "duplicate block atom")
    require(not nonempty or bool(result), "selected block must be nonempty")
    return result


@dataclass(frozen=True)
class Event:
    parents: tuple
    target: int
    label: str = "d"

    @property
    def fresh(self):
        return self.parents[0][1] | self.parents[1][1]


@dataclass(frozen=True)
class AbsRecord:
    carrier_at: int
    carrier: frozenset
    partner_at: int
    partner: frozenset
    target: int
    merged: frozenset
    label: str = "d"


@dataclass(frozen=True)
class Summary:
    partition: tuple
    selected: frozenset
    origin: Event
    absorptions: tuple


@dataclass(frozen=True)
class LogState:
    partition: tuple
    events: tuple = ()


def initial(env):
    return LogState(tuple(sorted((q, frozenset({i})) for i, q in enumerate(env.seed))))


def step(env, state, letter):
    require(letter in ("p", "d"), "unknown raw letter")
    incoming = {}
    for q, block in state.partition:
        incoming.setdefault(env.action(letter, q), []).append((q, block))
    events = state.events
    if letter == "d":
        packets = dict(state.partition)
        if all(q in packets for q in env.ports):
            events += (Event(tuple((q, packets[q]) for q in env.ports), env.collision),)
    partition = tuple((q, frozenset().union(*(block for _, block in entries)))
                      for q, entries in sorted(incoming.items()))
    return LogState(partition, events)


def decode(state, selected):
    origins = [i for i, event in enumerate(state.events) if event.fresh == selected]
    if not origins:
        return None
    if len(origins) != 1:
        raise RuntimeError("generated fresh event is not unique")
    index = origins[0]
    records = []
    for event in state.events[index + 1:]:
        for side, (q, carrier) in enumerate(event.parents):
            if selected <= carrier:
                s, partner = event.parents[1 - side]
                records.append(AbsRecord(q, carrier, s, partner, event.target, carrier | partner))
    return Summary(state.partition, selected, state.events[index], tuple(records))


@dataclass
class Domain:
    logs: list
    predecessors: list
    summaries: list
    representatives: list
    successors: dict

    def word(self, index):
        letters = []
        while self.predecessors[index] is not None:
            index, letter = self.predecessors[index]
            letters.append(letter)
        return "".join(reversed(letters))


def saturate(env, selected, budget):
    logs, predecessors = [initial(env)], [None]
    indices, edges, queue = {logs[0]: 0}, {}, deque([0])
    while queue:
        index = queue.popleft()
        for letter in ("p", "d"):
            budget.tick(1 + len(logs[index].partition))
            target = step(env, logs[index], letter)
            if target not in indices:
                if len(logs) >= budget.max_states:
                    raise ResourceLimit("log-state limit before saturation")
                indices[target] = len(logs)
                logs.append(target)
                predecessors.append((index, letter))
                queue.append(len(logs) - 1)
            edges[index, letter] = indices[target]
    summaries, representatives, summary_ids, decoded = [], [], {}, []
    for i, state in enumerate(logs):
        budget.tick(1 + len(state.events))
        summary = decode(state, selected)
        decoded.append(summary)
        if summary is not None and summary not in summary_ids:
            summary_ids[summary] = len(summaries)
            summaries.append(summary)
            representatives.append(i)
    successors = {}
    for i, summary in enumerate(decoded):
        if summary is None:
            continue
        source = summary_ids[summary]
        for letter in ("p", "d"):
            budget.tick()
            target = decoded[edges[i, letter]]
            if target is None:
                raise RuntimeError("generated registration did not persist")
            target_id = summary_ids[target]
            if successors.setdefault((source, letter), target_id) != target_id:
                raise RuntimeError("causal-summary successor is not well defined")
    return Domain(logs, predecessors, summaries, representatives, successors)
