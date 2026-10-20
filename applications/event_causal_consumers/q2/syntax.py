"""Closed typed query syntax, static checking, and a total-value interpreter."""

from dataclasses import dataclass

from .common import fields, require
from .values import (
    BLOCK, BOOL, ENTRY, NAT, PARTITION, POS, QUERIES, RECORDS,
    Sort, Value, list_of, literal, option, parse_sort, prod,
)

NODE_KINDS = frozenset(("literal", "var", "query", "pair", "fst", "snd", "if", "fold",
                        "op", "record", "field", "list", "some", "none", "case"))
OPERATIONS = frozenset(("eq", "not", "and", "or", "add", "lt", "le", "mod", "union",
                        "intersection", "subset", "cardinality", "cons", "lookup",
                        "entries", "carrier", "f_p", "f_d"))


@dataclass(frozen=True)
class Expr:
    kind: str
    sort: Sort
    children: tuple = ()
    data: object = None


def binding(name):
    require(type(name) is str and bool(name) and name.isidentifier(), "invalid variable name")
    return name


def same(actual, expected):
    require(actual == expected, f"type mismatch: expected {expected.json()}, got {actual.json()}")


def operation_type(name, args, modulus):
    types = [x.sort for x in args]
    if name == "eq":
        require(len(args) == 2, "eq arity")
        same(types[0], types[1])
        return BOOL
    signatures = {
        "not": ((BOOL,), BOOL), "and": ((BOOL, BOOL), BOOL), "or": ((BOOL, BOOL), BOOL),
        "add": ((NAT, NAT), NAT), "lt": ((NAT, NAT), BOOL), "le": ((NAT, NAT), BOOL),
        "mod": ((NAT,), NAT), "union": ((BLOCK, BLOCK), BLOCK),
        "intersection": ((BLOCK, BLOCK), BLOCK), "subset": ((BLOCK, BLOCK), BOOL),
        "cardinality": ((BLOCK,), NAT), "lookup": ((PARTITION, POS), option(BLOCK)),
        "entries": ((PARTITION,), list_of(ENTRY)), "carrier": ((PARTITION, BLOCK), option(ENTRY)),
        "f_p": ((POS,), POS), "f_d": ((POS,), POS),
    }
    if name == "cons":
        require(len(args) == 2, "cons arity")
        same(types[1], list_of(types[0]))
        return types[1]
    require(name in signatures, "undeclared primitive operation")
    inputs, output = signatures[name]
    require(tuple(types) == inputs, f"invalid {name} argument types or arity")
    if name == "mod":
        require(type(modulus) is int and modulus > 0, "modulus must be a positive literal constant")
    return output


def compile_expr(raw, env, budget, context=None):
    context = {} if context is None else context
    budget.node()
    require(type(raw) is dict and type(raw.get("kind")) is str, "expression needs a kind")
    kind = raw["kind"]
    require(kind in NODE_KINDS, "undeclared expression constructor")

    def child(key, scope=None):
        return compile_expr(raw[key], env, budget, context if scope is None else scope)

    if kind == "literal":
        fields(raw, ("kind", "type", "value"))
        sort = parse_sort(raw["type"], budget)
        return Expr(kind, sort, data=literal(sort, raw["value"], env, budget))
    if kind == "var":
        fields(raw, ("kind", "name"))
        name = binding(raw["name"])
        require(name in context, "unbound variable")
        return Expr(kind, context[name], data=name)
    if kind == "query":
        fields(raw, ("kind", "name"))
        require(type(raw["name"]) is str and raw["name"] in QUERIES, "undeclared history query")
        return Expr(kind, QUERIES[raw["name"]], data=raw["name"])
    if kind == "pair":
        fields(raw, ("kind", "left", "right"))
        a, b = child("left"), child("right")
        return Expr(kind, prod(a.sort, b.sort), (a, b))
    if kind in ("fst", "snd"):
        fields(raw, ("kind", "value"))
        value = child("value")
        require(value.sort.name == "Prod", "projection needs a product")
        return Expr(kind, value.sort.args[0 if kind == "fst" else 1], (value,))
    if kind == "if":
        fields(raw, ("kind", "condition", "then", "else"))
        condition, yes, no = child("condition"), child("then"), child("else")
        same(condition.sort, BOOL)
        same(yes.sort, no.sort)
        return Expr(kind, yes.sort, (condition, yes, no))
    if kind == "fold":
        fields(raw, ("kind", "list", "seed", "acc", "item", "body"))
        items, seed = child("list"), child("seed")
        require(items.sort.name == "List", "fold needs a List")
        acc, item = binding(raw["acc"]), binding(raw["item"])
        require(acc != item, "fold binders must differ")
        scope = {**context, acc: seed.sort, item: items.sort.args[0]}
        body = child("body", scope)
        same(body.sort, seed.sort)
        return Expr(kind, seed.sort, (items, seed, body), (acc, item))
    if kind == "op":
        fields(raw, ("kind", "name", "args"), ("modulus",))
        name = raw["name"]
        require(type(name) is str and name in OPERATIONS and type(raw["args"]) is list,
                "undeclared operation or invalid argument list")
        require(("modulus" in raw) == (name == "mod"), "only mod has a modulus parameter")
        args = tuple(compile_expr(x, env, budget, context) for x in raw["args"])
        sort = operation_type(name, args, raw.get("modulus"))
        return Expr(kind, sort, args, (name, raw.get("modulus")))
    if kind == "record":
        fields(raw, ("kind", "type", "fields"))
        sort = parse_sort(raw["type"], budget)
        require(sort in RECORDS and type(raw["fields"]) is dict, "unknown record type")
        require(set(raw["fields"]) == {k for k, _ in RECORDS[sort]}, "wrong record constructor fields")
        args = []
        for name, expected in RECORDS[sort]:
            item = compile_expr(raw["fields"][name], env, budget, context)
            same(item.sort, expected)
            args.append(item)
        return Expr(kind, sort, tuple(args))
    if kind == "field":
        fields(raw, ("kind", "value", "name"))
        value = child("value")
        require(value.sort in RECORDS and type(raw["name"]) is str, "field projection needs a record")
        names = [name for name, _ in RECORDS[value.sort]]
        require(raw["name"] in names, "undeclared record field")
        index = names.index(raw["name"])
        return Expr(kind, RECORDS[value.sort][index][1], (value,), index)
    if kind == "list":
        fields(raw, ("kind", "element_type", "items"))
        item_type = parse_sort(raw["element_type"], budget)
        require(type(raw["items"]) is list, "invalid list constructor")
        args = tuple(compile_expr(x, env, budget, context) for x in raw["items"])
        for item in args:
            same(item.sort, item_type)
        return Expr(kind, list_of(item_type), args)
    if kind == "some":
        fields(raw, ("kind", "value"))
        value = child("value")
        return Expr(kind, option(value.sort), (value,))
    if kind == "none":
        fields(raw, ("kind", "element_type"))
        return Expr(kind, option(parse_sort(raw["element_type"], budget)))
    fields(raw, ("kind", "value", "none", "binder", "some"))
    value, no = child("value"), child("none")
    require(value.sort.name == "Option", "case needs Option")
    name = binding(raw["binder"])
    yes = child("some", {**context, name: value.sort.args[0]})
    same(yes.sort, no.sort)
    return Expr(kind, no.sort, (value, no, yes), name)


def apply_operation(expr, values, env):
    name, modulus = expr.data
    data = [v.data for v in values]
    if name == "eq":
        result = values[0] == values[1]
    elif name == "not":
        result = not data[0]
    elif name == "and":
        result = data[0] and data[1]
    elif name == "or":
        result = data[0] or data[1]
    elif name == "add":
        result = data[0] + data[1]
    elif name == "lt":
        result = data[0] < data[1]
    elif name == "le":
        result = data[0] <= data[1]
    elif name == "mod":
        result = data[0] % modulus
    elif name == "union":
        result = data[0] | data[1]
    elif name == "intersection":
        result = data[0] & data[1]
    elif name == "subset":
        result = data[0] <= data[1]
    elif name == "cardinality":
        result = len(data[0])
    elif name == "cons":
        result = (values[0],) + data[1]
    elif name == "entries":
        result = data[0]
    elif name == "lookup":
        result = next((entry.data[1] for entry in data[0] if entry.data[0] == values[1]), None)
    elif name == "carrier":
        matches = [entry for entry in data[0] if data[1] <= entry.data[1].data]
        result = matches[0] if len(matches) == 1 else None
    elif name in ("f_p", "f_d"):
        result = env.action("p" if name == "f_p" else "d", data[0])
    else:
        raise RuntimeError("compiled operation not implemented")
    return Value(expr.sort, result)


def evaluate(expr, queries, env, budget, variables=None):
    variables = {} if variables is None else variables
    budget.tick()
    kind = expr.kind
    if kind == "literal":
        return expr.data
    if kind == "query":
        return queries[expr.data]
    if kind == "var":
        return variables[expr.data]
    if kind == "if":
        condition = evaluate(expr.children[0], queries, env, budget, variables)
        branch = expr.children[1 if condition.data else 2]
        return evaluate(branch, queries, env, budget, variables)
    if kind == "case":
        value = evaluate(expr.children[0], queries, env, budget, variables)
        if value.data is None:
            return evaluate(expr.children[1], queries, env, budget, variables)
        return evaluate(expr.children[2], queries, env, budget, {**variables, expr.data: value.data})
    if kind == "fold":
        items = evaluate(expr.children[0], queries, env, budget, variables)
        acc = evaluate(expr.children[1], queries, env, budget, variables)
        acc_name, item_name = expr.data
        for item in items.data:
            budget.tick()
            acc = evaluate(expr.children[2], queries, env, budget,
                           {**variables, acc_name: acc, item_name: item})
        return acc
    args = tuple(evaluate(x, queries, env, budget, variables) for x in expr.children)
    if kind in ("fst", "snd", "field"):
        index = expr.data if kind == "field" else (0 if kind == "fst" else 1)
        return args[0].data[index]
    if kind == "some":
        return Value(expr.sort, args[0])
    if kind == "none":
        return Value(expr.sort, None)
    if kind in ("pair", "list", "record"):
        return Value(expr.sort, args)
    if kind == "op":
        return apply_operation(expr, args, env)
    raise RuntimeError("compiled expression not implemented")
