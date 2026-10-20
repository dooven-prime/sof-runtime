"""Independent streaming replay of rejection histories, not domain saturation.

Shares the declared data types and typed value interpreter, but imports no
producer step, decode, saturation, or admission function.
"""

from .common import IMPLEMENTATION_STATUS, InputError, ResourceLimit, digest
from .model import AbsRecord, Event, Summary
from .request import prepare
from .syntax import evaluate
from .values import encode, leaves


class WitnessError(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise WitnessError(message)


def replay_registered(env, selected, word, budget):
    need(type(word) is str and set(word) <= {"p", "d"}, "witness is not a raw p/d word")
    packets = [(q, frozenset({i})) for i, q in enumerate(env.seed)]
    origin, records = None, []
    for letter in word:
        # Scan targets directly and maintain just the selected causal subsequence.
        moved = []
        for target in range(env.n):
            budget.tick(1 + len(packets))
            sources = [(q, block) for q, block in packets
                       if (q + 1) % env.n == target] if letter == "p" else [
                           (q, block) for q, block in packets if env.defect[q] == target]
            if not sources:
                continue
            block = frozenset().union(*(part for _, part in sources))
            moved.append((target, block))
            if len(sources) == 2:
                parents = tuple(next((q, part) for q, part in sources if q == port) for port in env.ports)
                if origin is None and block == selected:
                    origin = Event(parents, target)
                elif origin is not None:
                    carriers = [(q, part) for q, part in parents if selected <= part]
                    if carriers:
                        q, carrier = carriers[0]
                        s, partner = next((pos, part) for pos, part in parents if pos != q)
                        records.append(AbsRecord(q, carrier, s, partner, target, carrier | partner))
        packets = moved
    need(origin is not None, "history did not create the selected fresh block")
    return Summary(tuple(packets), selected, origin, tuple(records))


def recompute(request, word):
    summary = replay_registered(request.env, request.selected, word, request.budget)
    query = leaves(summary)
    return {
        "word": word,
        "causal": {name: encode(value, request.env) for name, value in query.items()},
        "q": encode(evaluate(request.q, query, request.env, request.budget), request.env),
        "reports": [{"label": label, "value": encode(evaluate(expr, query, request.env, request.budget), request.env)}
                    for label, expr in request.reports],
        "guards": [{"label": c.label, "value": evaluate(c.guard, query, request.env, request.budget).data}
                   for c in request.commands],
    }


def verify_rejection(raw, result):
    base = {"implementation_status": IMPLEMENTATION_STATUS, "domain_completeness_verified": False}
    try:
        request = prepare(raw)
        need(type(result) is dict and result.get("request_sha256") == request.sha256, "request binding mismatch")
        need(type(result.get("status")) is str, "invalid result status")
        expected_kind = {"FAIL_READ": "R", "FAIL_GUARD": "G", "FAIL_SUCCESSOR": "T"}.get(result["status"])
        need(expected_kind is not None, "result is not a rejection")
        witness = result.get("witness")
        need(type(witness) is dict and set(witness) == {"clause", "left", "right"}, "invalid witness shape")
        clause = witness["clause"]
        need(type(clause) is dict and set(clause) == {"kind", "label"} and
             clause["kind"] == expected_kind, "clause/status mismatch")
        label = clause["label"]
        report_labels = [name for name, _ in request.reports]
        command_labels = [c.label for c in request.commands]
        need(type(label) is str and label in (report_labels if expected_kind == "R" else command_labels),
             "unknown witness clause label")
        command = None if expected_kind == "R" else request.commands[command_labels.index(label)]
        actual = []
        for key in ("left", "right"):
            supplied = witness[key]
            need(type(supplied) is dict and "word" in supplied, "missing history")
            item = recompute(request, supplied["word"])
            if expected_kind == "T":
                after = replay_registered(request.env, request.selected, supplied["word"] + command.letter,
                                          request.budget)
                item["after"] = {"word": supplied["word"] + command.letter,
                                 "q": encode(evaluate(request.q, leaves(after), request.env, request.budget), request.env)}
            # JSON identity must distinguish True from 1, including nested payloads.
            need(digest(item) == digest(supplied), "serialized witness does not match independent replay")
            actual.append(item)
        left, right = actual
        need(left["q"] == right["q"], "histories do not share a q-value")
        if expected_kind == "R":
            index = report_labels.index(label)
            need(left["reports"][index]["value"] != right["reports"][index]["value"], "no read separation")
        elif expected_kind == "G":
            index = command_labels.index(label)
            need(left["guards"][index]["value"] != right["guards"][index]["value"], "no guard separation")
        else:
            index = command_labels.index(label)
            need(left["guards"][index]["value"] and right["guards"][index]["value"], "T guards not both enabled")
            need(left["after"]["q"] != right["after"]["q"], "no successor separation")
        return {**base, "status": "VALID_REJECTION_WITNESS", "request_sha256": request.sha256,
                "clause": clause, "canonical_compiler_admission": False}
    except WitnessError as exc:
        return {**base, "status": "INVALID_REJECTION_WITNESS", "detail": str(exc)}
    except InputError as exc:
        return {**base, "status": "INVALID_INPUT", "detail": str(exc)}
    except (ResourceLimit, RecursionError, MemoryError) as exc:
        return {**base, "status": "UNRESOLVED_LIMIT", "detail": str(exc) or type(exc).__name__}
