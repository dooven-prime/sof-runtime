"""Build JSON syntax for the already registered controls, never query callbacks."""

from copy import deepcopy


def lit(sort, value):
    return {"kind": "literal", "type": sort, "value": value}


def query(name):
    return {"kind": "query", "name": name}


def var(name):
    return {"kind": "var", "name": name}


def op(name, *args, **extra):
    return {"kind": "op", "name": name, "args": list(args), **extra}


def pair(left, right):
    return {"kind": "pair", "left": left, "right": right}


def fst(value):
    return {"kind": "fst", "value": value}


def snd(value):
    return {"kind": "snd", "value": value}


def field(value, name):
    return {"kind": "field", "value": value, "name": name}


def choose(condition, yes, no):
    return {"kind": "if", "condition": condition, "then": yes, "else": no}


def fold(items, seed, acc, item, body):
    return {"kind": "fold", "list": items, "seed": seed, "acc": acc, "item": item, "body": body}


def case(value, no, binder, yes):
    return {"kind": "case", "value": value, "none": no, "binder": binder, "some": yes}


def tuple_expr(*items):
    result = items[-1]
    for item in reversed(items[:-1]):
        result = pair(item, result)
    return result


P, F = query("CurrentPartition"), query("SelectedBlock")
O, A = query("OriginSnapshot"), query("AbsorptionSequence")
CARRIER = op("carrier", P, F)
COUNT = fold(A, lit("Nat", 0), "total", "record", op("add", var("total"), lit("Nat", 1)))
PARITY = op("mod", COUNT, modulus=2)
GAMMA = tuple_expr(P, F, O, A)
TRACK_REPORT = tuple_expr(O, A, CARRIER)
PARENT0 = snd(fst(field(O, "parents")))


def collision_guard(letter, size):
    # A fold over the complete partition handles unrelated collisions correctly.
    destination = op("f_" + letter, fst(var("selected_carrier")))
    count = fold(op("entries", P), lit("Nat", 0), "number", "entry",
                 op("add", var("number"), choose(
                     op("eq", op("f_" + letter, fst(var("entry"))), destination),
                     lit("Nat", 1), lit("Nat", 0))))
    return case(CARRIER, lit("Bool", False), "selected_carrier", op("eq", count, lit("Nat", size)))


def track_commands():
    return [{"label": name + "(" + letter + ")", "letter": letter,
             "guard": collision_guard(letter, size)}
            for letter in ("p", "d") for name, size in (("Carry", 1), ("Absorb", 2))]


def request(n=4, q=None, reports=None, commands=None):
    defects = {2: [0, 0], 3: [0, 2, 0], 4: [0, 0, 1, 2]}
    return deepcopy({
        "language": "ECC_SYN_V1",
        "environment": {"defect": defects[n], "seed": list(range(n))},
        "selected": list(range(n)) if n < 4 else [0, 1],
        "program": {"q": GAMMA if q is None else q,
                    "reports": [{"label": "Track", "expr": TRACK_REPORT}] if reports is None else reports,
                    "commands": track_commands() if commands is None else commands},
    })


def block_code(block, atoms):
    result = lit("Nat", 0)
    for i, atom in enumerate(atoms):
        result = op("add", result, choose(op("subset", lit("Block", [atom]), block),
                                         lit("Nat", 2 ** i), lit("Nat", 0)))
    return result


def controls():
    """The same nine specifications as the earlier fixed-control prototype."""
    result = {f"gamma_n{n}": request(n) for n in (2, 3, 4)}
    parents = field(O, "parents")
    left, right = snd(fst(parents)), snd(snd(parents))
    unordered = choose(op("le", block_code(left, [0, 1]), block_code(right, [0, 1])),
                       pair(left, right), pair(right, left))
    result["forget_ports"] = request(2, tuple_expr(P, F, unordered, field(O, "target"), A, CARRIER),
                                       [{"label": "origin_port0", "expr": PARENT0}])
    result["forget_origin"] = request(3, pair(P, F), [{"label": "origin_port0", "expr": PARENT0}])
    result["forget_partition"] = request(4, tuple_expr(F, O, A, CARRIER))
    result["parity_only"] = request(4, PARITY, [{"label": "parity", "expr": PARITY}], [
        {"label": "Raw(d)", "letter": "d", "guard": lit("Bool", True)}])
    result["packet_only"] = request(3, pair(P, F), [{"label": "partition", "expr": P}], track_commands())
    result["count_state"] = request(4, tuple_expr(P, F, O, COUNT),
                                     [{"label": "count", "expr": tuple_expr(O, COUNT, CARRIER)}], track_commands())
    return result
