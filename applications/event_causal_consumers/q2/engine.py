"""Syntax-wide finite Q2 admission with actual predecessor-history witnesses."""

from .common import IMPLEMENTATION_STATUS, InputError, ResourceLimit, digest
from .model import saturate
from .request import prepare
from .syntax import evaluate
from .values import encode, leaves


def observation(request, summary, word):
    queries = leaves(summary)
    env, budget = request.env, request.budget
    return {
        "word": word,
        "causal": {name: encode(value, env) for name, value in queries.items()},
        "q": encode(evaluate(request.q, queries, env, budget), env),
        "reports": [{"label": name, "value": encode(evaluate(expr, queries, env, budget), env)}
                    for name, expr in request.reports],
        "guards": [{"label": c.label, "value": evaluate(c.guard, queries, env, budget).data}
                   for c in request.commands],
    }


def decide(request, domain):
    env, budget = request.env, request.budget
    values, reports, guards, fibers = [], [], [], {}
    for index, summary in enumerate(domain.summaries):
        query = leaves(summary)
        value = evaluate(request.q, query, env, budget)
        values.append(value)
        reports.append(tuple(evaluate(expr, query, env, budget) for _, expr in request.reports))
        guards.append(tuple(evaluate(c.guard, query, env, budget).data for c in request.commands))
        fibers.setdefault(value, []).append(index)
    # Test clauses globally in a fixed R/G/T order, not an accidental pair order.
    for column, (label, _) in enumerate(request.reports):
        for members in fibers.values():
            pivot = members[0]
            for other in members[1:]:
                budget.tick()
                if reports[pivot][column] != reports[other][column]:
                    return "FAIL_READ", {"kind": "R", "label": label}, pivot, other, len(fibers)
    for column, command in enumerate(request.commands):
        for members in fibers.values():
            pivot = members[0]
            for other in members[1:]:
                budget.tick()
                if guards[pivot][column] != guards[other][column]:
                    return "FAIL_GUARD", {"kind": "G", "label": command.label}, pivot, other, len(fibers)
    for column, command in enumerate(request.commands):
        for members in fibers.values():
            pivot = members[0]
            if not guards[pivot][column]:
                continue
            target = domain.successors[pivot, command.letter]
            for other in members[1:]:
                budget.tick()
                other_target = domain.successors[other, command.letter]
                if values[target] != values[other_target]:
                    return "FAIL_SUCCESSOR", {"kind": "T", "label": command.label}, pivot, other, len(fibers)
    return "PASS_EXACT", None, None, None, len(fibers)


def check(raw):
    base = {"implementation_status": IMPLEMENTATION_STATUS,
            "canonical_compiler_admission": False, "domain_complete": False}
    try:
        base["request_sha256"] = digest(raw)
        request = prepare(raw)
        domain = saturate(request.env, request.selected, request.budget)
        result = {**base, "domain_complete": True,
                  "domain": {"log_states": len(domain.logs), "causal_states": len(domain.summaries)},
                  "types": {"q": request.q.sort.json(),
                            "reports": [{"label": name, "type": expr.sort.json()}
                                        for name, expr in request.reports]},
                  "command_labels": [c.label for c in request.commands]}
        if not domain.summaries:
            return {**result, "status": "EMPTY_REGISTERED_DOMAIN", "vacuous": True}
        status, clause, left, right, size = decide(request, domain)
        result.update(status=status, q_states=size)
        if clause is not None:
            witness = {"clause": clause}
            command = next((c for c in request.commands if c.label == clause["label"]), None)
            for key, index in (("left", left), ("right", right)):
                word = domain.word(domain.representatives[index])
                item = observation(request, domain.summaries[index], word)
                if clause["kind"] == "T":
                    next_id = domain.successors[index, command.letter]
                    q_next = evaluate(request.q, leaves(domain.summaries[next_id]), request.env, request.budget)
                    item["after"] = {"word": word + command.letter, "q": encode(q_next, request.env)}
                witness[key] = item
            result["witness"] = witness
        result["evaluation_steps"] = request.budget.steps
        return result
    except InputError as exc:
        return {**base, "status": "INVALID_INPUT", "detail": str(exc)}
    except (ResourceLimit, RecursionError, MemoryError) as exc:
        return {**base, "status": "UNRESOLVED_LIMIT", "detail": str(exc) or type(exc).__name__}
