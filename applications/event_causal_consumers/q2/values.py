"""Immutable sorts and type-tagged values; Bool, Atom, Pos and Nat differ."""

from dataclasses import dataclass

from .common import InputError, require
from .model import parse_block


@dataclass(frozen=True)
class Sort:
    name: str
    args: tuple = ()

    def json(self):
        return self.name if not self.args else [self.name, *(a.json() for a in self.args)]


BASE = {name: Sort(name) for name in (
    "Bool", "Nat", "Atom", "Pos", "Letter", "Block", "Partition", "Origin", "AbsRecord",
)}
BOOL, NAT, ATOM, POS, LETTER, BLOCK, PARTITION, ORIGIN, ABS = BASE.values()


def prod(a, b):
    return Sort("Prod", (a, b))


def list_of(a):
    return Sort("List", (a,))


def option(a):
    return Sort("Option", (a,))


ENTRY = prod(POS, BLOCK)
RECORDS = {
    ORIGIN: (("label", LETTER), ("parents", prod(ENTRY, ENTRY)), ("target", POS)),
    ABS: (("carrier_at", POS), ("carrier", BLOCK), ("partner_at", POS),
          ("partner", BLOCK), ("target", POS), ("merged", BLOCK), ("label", LETTER)),
}
QUERIES = {"CurrentPartition": PARTITION, "SelectedBlock": BLOCK,
           "OriginSnapshot": ORIGIN, "AbsorptionSequence": list_of(ABS)}


@dataclass(frozen=True)
class Value:
    sort: Sort
    data: object


def parse_sort(raw, budget):
    budget.node()
    if type(raw) is str and raw in BASE:
        return BASE[raw]
    require(type(raw) is list and raw, "unknown type")
    require(raw[0] in ("Prod", "List", "Option"), "unknown type constructor")
    require(len(raw) == (3 if raw[0] == "Prod" else 2), "wrong type arity")
    return Sort(raw[0], tuple(parse_sort(x, budget) for x in raw[1:]))


def pair(a, b):
    return Value(prod(a.sort, b.sort), (a, b))


def record(sort, **fields):
    return Value(sort, tuple(fields[name] for name, _ in RECORDS[sort]))


def literal(sort, raw, env, budget):
    budget.tick()
    name = sort.name
    if name == "Bool":
        require(type(raw) is bool, "Bool literal must be a boolean")
    elif name == "Nat":
        require(type(raw) is int and raw >= 0, "Nat literal must be nonnegative integer")
    elif name == "Pos":
        require(type(raw) is int and 0 <= raw < env.n, "position outside carrier")
    elif name == "Atom":
        try:
            raw = env.atom_index(raw)
        except ValueError as exc:
            raise InputError("undeclared atom literal") from exc
    elif name == "Letter":
        require(type(raw) is str and raw in ("p", "d"), "undeclared letter literal")
    elif name == "Block":
        raw = parse_block(raw, env)
    elif name in ("List", "Prod", "Partition"):
        require(type(raw) is list, "list/product/partition literal must be an array")
        if name == "Prod":
            require(len(raw) == 2, "product literal must have two entries")
            raw = tuple(literal(t, x, env, budget) for t, x in zip(sort.args, raw))
        else:
            item_type = ENTRY if name == "Partition" else sort.args[0]
            raw = tuple(literal(item_type, x, env, budget) for x in raw)
            if name == "Partition":
                positions, atoms = set(), set()
                for entry in raw:
                    q, block = entry.data[0].data, entry.data[1].data
                    require(q not in positions and block and atoms.isdisjoint(block), "invalid partition literal")
                    positions.add(q)
                    atoms.update(block)
                require(atoms == set(range(len(env.seed))), "partition does not cover the atom set")
                raw = tuple(sorted(raw, key=lambda entry: entry.data[0].data))
    elif name == "Option":
        if raw is not None:
            require(type(raw) is dict and set(raw) == {"some"}, "invalid Option literal")
            raw = literal(sort.args[0], raw["some"], env, budget)
    elif sort in RECORDS:
        require(type(raw) is dict and set(raw) == {k for k, _ in RECORDS[sort]}, "invalid record fields")
        raw = tuple(literal(t, raw[k], env, budget) for k, t in RECORDS[sort])
    else:
        raise InputError("unsupported literal sort")
    return Value(sort, raw)


def bare(value, env):
    sort, data = value.sort, value.data
    if sort == ATOM:
        return env.atoms[data]
    if sort == BLOCK:
        return [env.atoms[i] for i in sorted(data)]
    if sort.name in ("Prod", "List", "Partition"):
        return [bare(x, env) for x in data]
    if sort.name == "Option":
        return None if data is None else {"some": bare(data, env)}
    if sort in RECORDS:
        return {name: bare(x, env) for (name, _), x in zip(RECORDS[sort], data)}
    return data


def encode(value, env):
    return {"type": value.sort.json(), "value": bare(value, env)}


def leaves(summary):
    entries = tuple(pair(Value(POS, q), Value(BLOCK, block)) for q, block in summary.partition)
    parents = [pair(Value(POS, q), Value(BLOCK, block)) for q, block in summary.origin.parents]
    origin = record(ORIGIN, label=Value(LETTER, summary.origin.label),
                    parents=pair(*parents), target=Value(POS, summary.origin.target))
    records = tuple(record(ABS, **{
        name: Value(sort, getattr(item, name)) for name, sort in RECORDS[ABS]
    }) for item in summary.absorptions)
    return {"CurrentPartition": Value(PARTITION, entries),
            "SelectedBlock": Value(BLOCK, summary.selected), "OriginSnapshot": origin,
            "AbsorptionSequence": Value(list_of(ABS), records)}
