"""Fixed-domain Q2/forward-operator controls, not a syntax-wide Q2 adapter."""

from __future__ import annotations

import argparse
from collections import Counter, deque
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType


COMMIT = "b032b47ec47f28c8b2f65844abbe30dc3b38fef8"
BLOBS = {
    "contract.py": "001ce3824a4cde7c2e1e37ba1cebabbdeed49e1e3b57d5664dcdf609d3e909a1",
    "log_consumer.py": "f0c6786ecdfbd54209487db725340469c4816cae574e55b966d7323955dd2640",
    "forest.py": "ab2d6913f29bb4008f80d9f6d48db7e5b246fe75382ef0b2df2b2f2639d66336",
}
TRACK = (("Carry", "p"), ("Absorb", "p"), ("Carry", "d"), ("Absorb", "d"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


class LimitReached(RuntimeError):
    """The declared state domain has not been exhausted."""


@contextmanager
def frozen_models(upstream_root=None, *, source_dir=None):
    """Read pinned release bytes, from Git or an explicit offline snapshot."""
    require((upstream_root is None) != (source_dir is None), "choose exactly one frozen source")
    saved = {name: sys.modules.get(name) for name in ("contract", "log_consumer", "forest")}
    try:
        sources = {}
        for filename, expected in BLOBS.items():
            if source_dir is not None:
                data = (Path(source_dir) / filename).read_bytes()
            else:
                data = subprocess.check_output([
                    "git", "--no-optional-locks", "-C", str(upstream_root), "show",
                    f"{COMMIT}:experiments/paper39/{filename}",
                ])
            require(hashlib.sha256(data).hexdigest() == expected, f"blob drift: {filename}")
            sources[filename.removesuffix(".py")] = data
        loaded = {}
        for name, data in sources.items():
            origin = f"{COMMIT}:experiments/paper39/{name}.py"
            module = ModuleType(name)
            module.__file__ = origin
            sys.modules[name] = module
            exec(compile(data, origin, "exec"), module.__dict__)
            loaded[name] = module
        yield loaded
    finally:
        for name, module in saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


def saturate(initial, step, max_states):
    require(type(max_states) is int and max_states > 0, "invalid state limit")
    words, successors, pending = {initial: ""}, {}, deque([initial])
    while pending:
        state = pending.popleft()
        for letter in ("p", "d"):
            target = step(state, letter)
            successors[state, letter] = target
            if target not in words:
                if len(words) >= max_states:
                    raise LimitReached(f"state limit {max_states} reached before saturation")
                words[target] = words[state] + letter
                pending.append(target)
    return words, successors


def replay(module, env, word):
    state = module.initial(env)
    for letter in word:
        state = module.step(env, state, letter)
    return state


@dataclass
class Domain:
    env: object
    selected: frozenset
    summaries: dict
    forest_states: dict
    log_words: dict
    forest_words: dict


def generated_domain(models, env, selected, max_states=100000):
    log, forest = models["log_consumer"], models["forest"]
    log_words, _ = saturate(log.initial(env), lambda x, a: log.step(env, x, a), max_states)
    forest_words, _ = saturate(
        forest.initial(env), lambda x, a: forest.step(env, x, a), max_states,
    )
    summaries, forest_states = {}, {}
    for state, word in log_words.items():
        summary = log.decode(state, selected)
        if summary is not None:
            summaries.setdefault(summary, word)
    for state, word in forest_words.items():
        forest.check_wellformed(env, state)
        summary = forest.decode(state, selected)
        if summary is not None:
            forest_states[state] = summary
    require(set(forest_states.values()) == set(summaries), "generated decoder-image mismatch")
    for summary in summaries:
        for letter in ("p", "d"):
            targets = [log.command(env, summary, kind, letter) for kind in ("Carry", "Absorb")]
            require(sum(x is not None for x in targets) == 1, "command partition failed")
            require(next(x for x in targets if x is not None) in summaries, "summary is not closed")
    return Domain(env, selected, summaries, forest_states, log_words, forest_words)


def log_command(log, env, state, command):
    kind, letter = command
    if kind == "Raw":
        for candidate in ("Carry", "Absorb"):
            target = log.command(env, state, candidate, letter)
            if target is not None:
                return target
        raise ValueError("registered raw command unexpectedly undefined")
    return log.command(env, state, kind, letter)


def forest_command(forest, domain, state, command):
    kind, letter = command
    if kind == "Raw":
        return forest.step(domain.env, state, letter)
    return forest.command(domain.env, state, domain.selected, kind, letter)


def semantic_check(models, domain, q, report, commands):
    """Q1 on the log-defined causal image; no forest transition calls."""
    if not domain.summaries:
        return {"status": "EMPTY_REGISTERED_DOMAIN"}
    fibers = {}
    for state in domain.summaries:
        fibers.setdefault(q(state), []).append(state)
    for states in fibers.values():
        first = states[0]
        for other in states[1:]:
            detail = None
            if report(first) != report(other):
                detail = ("FAIL_READ", None)
            else:
                for command in commands:
                    left = log_command(models["log_consumer"], domain.env, first, command)
                    right = log_command(models["log_consumer"], domain.env, other, command)
                    if (left is None) != (right is None):
                        detail = ("FAIL_GUARD", command)
                        break
                    if left is not None and q(left) != q(right):
                        detail = ("FAIL_SUCCESSOR", command)
                        break
            if detail is not None:
                return {
                    "status": detail[0], "command": detail[1],
                    "left_word": domain.summaries[first],
                    "right_word": domain.summaries[other],
                }
    return {"status": "PASS_EXACT", "fibers": len(fibers)}


def operator_check(models, domain, q, report, commands):
    """Build fine/coarse basis columns independently on the forest image."""
    if not domain.forest_states:
        return {"status": "EMPTY_REGISTERED_DOMAIN"}
    forest = models["forest"]
    states = tuple(domain.forest_states)
    indices = {state: i for i, state in enumerate(states)}
    values = [q(domain.forest_states[state]) for state in states]
    sectors = {value: i for i, value in enumerate(dict.fromkeys(values))}
    l_column = [sectors[value] for value in values]
    report_by_sector = {}
    for i, state in enumerate(states):
        value = report(domain.forest_states[state])
        previous = report_by_sector.setdefault(l_column[i], value)
        if previous != value:
            return {"status": "FAIL_READ"}
    fine_columns, coarse_columns = {}, {}
    for command in commands:
        fine, coarse = [], {}
        for i, state in enumerate(states):
            target = forest_command(forest, domain, state, command)
            col = None if target is None else indices[target]
            fine.append(col)
            image = None if col is None else l_column[col]
            if l_column[i] in coarse and coarse[l_column[i]] != image:
                status = "FAIL_GUARD" if (coarse[l_column[i]] is None) != (image is None) else "FAIL_SUCCESSOR"
                return {"status": status}
            coarse[l_column[i]] = image
        fine_columns[command], coarse_columns[command] = fine, coarse
        for i, col in enumerate(fine):
            require((None if col is None else l_column[col]) == coarse[l_column[i]], "LT != bar-T L")
    # Check products on concrete columns as well as individual transitions.
    for first in commands:
        for second in commands:
            for i, middle in enumerate(fine_columns[first]):
                end = None if middle is None else fine_columns[second][middle]
                coarse_middle = coarse_columns[first][l_column[i]]
                coarse_end = None if coarse_middle is None else coarse_columns[second][coarse_middle]
                require((None if end is None else l_column[end]) == coarse_end, "word intertwining failed")
    return {"status": "PASS_EXACT", "fibers": len(sectors), "basis_columns": len(states)}


def kernel_check(models, domain, q, report, commands):
    """Test invariance of a fiber-difference basis with exact integer sums."""
    if not domain.forest_states:
        return {"status": "EMPTY_REGISTERED_DOMAIN"}
    states = tuple(domain.forest_states)
    indices = {state: i for i, state in enumerate(states)}
    fibers = {}
    for i, state in enumerate(states):
        fibers.setdefault(q(domain.forest_states[state]), []).append(i)
    sectors = [None] * len(states)
    basis = []
    for sector, members in enumerate(fibers.values()):
        for i in members:
            sectors[i] = sector
        basis.extend((i, members[0]) for i in members[1:])
    profile = {
        "kernel_dimension": len(basis),
        "fiber_size_distribution": dict(sorted(Counter(map(len, fibers.values())).items())),
    }

    def leaves_kernel(terms):
        sums = {}
        for target, coefficient in terms:
            if target is not None:
                sector = sectors[target]
                sums[sector] = sums.get(sector, 0) + coefficient
        return any(sums.values())

    reports = [report(domain.forest_states[state]) for state in states]
    for value in dict.fromkeys(reports):
        for i, pivot in basis:
            if leaves_kernel(((i, int(reports[i] == value)),
                              (pivot, -int(reports[pivot] == value)))):
                return {"status": "FAIL_READ", **profile}
    for command in commands:
        columns = []
        for state in states:
            target = forest_command(models["forest"], domain, state, command)
            columns.append(None if target is None else indices[target])
        for i, pivot in basis:
            left, right = columns[i], columns[pivot]
            if leaves_kernel(((left, 1), (right, -1))):
                status = "FAIL_GUARD" if (left is None) != (right is None) else "FAIL_SUCCESSOR"
                return {"status": status, **profile}
    return {"status": "PASS_EXACT", **profile}


def verify_failure(models, domain, q, report, decision):
    states = []
    for key in ("left_word", "right_word"):
        log_state = replay(models["log_consumer"], domain.env, decision[key])
        forest_state = replay(models["forest"], domain.env, decision[key])
        summary = models["log_consumer"].decode(log_state, domain.selected)
        require(summary is not None, "witness is unregistered")
        require(summary == models["forest"].decode(forest_state, domain.selected), "witness read mismatch")
        states.append(summary)
    left, right = states
    require(q(left) == q(right), "witness does not share a q-value")
    if decision["status"] == "FAIL_READ":
        require(report(left) != report(right), "read failure not reproduced")
    else:
        targets = [log_command(models["log_consumer"], domain.env, s, decision["command"]) for s in states]
        if decision["status"] == "FAIL_GUARD":
            require((targets[0] is None) != (targets[1] is None), "guard failure not reproduced")
        else:
            require(all(s is not None for s in targets), "T witness is not jointly enabled")
            require(q(targets[0]) != q(targets[1]), "successor failure not reproduced")


def track_report(state):
    return state.origin, state.absorptions, state.carrier


def fixed_cases(domains):
    d2, d3, d4 = domains
    packet_q = lambda s: (s.partition, s.selected)
    parent_read = lambda s: s.origin.parents[0][1]
    no_partition = lambda s: (s.selected, s.origin, s.absorptions, s.carrier)
    unordered = lambda s: (
        s.partition, s.selected, frozenset(b for _, b in s.origin.parents),
        s.origin.target, s.origin.label, s.absorptions, s.carrier,
    )
    count_q = lambda s: (s.partition, s.selected, s.origin, len(s.absorptions))
    count_read = lambda s: (s.origin, len(s.absorptions), s.carrier)
    return [
        ("gamma_n2", d2, lambda s: s, track_report, TRACK, "PASS_EXACT"),
        ("unordered_parent_binding", d2, unordered, parent_read, TRACK, "FAIL_READ"),
        ("gamma_n3", d3, lambda s: s, track_report, TRACK, "PASS_EXACT"),
        ("packet_only_consumer", d3, packet_q, lambda s: s.partition, TRACK, "PASS_EXACT"),
        ("packet_q_origin_report", d3, packet_q, parent_read, TRACK, "FAIL_READ"),
        ("gamma_n4", d4, lambda s: s, track_report, TRACK, "PASS_EXACT"),
        ("missing_partition_guard", d4, no_partition, track_report, TRACK, "FAIL_GUARD"),
        ("parity_not_a_state", d4, lambda s: len(s.absorptions) % 2,
         lambda s: len(s.absorptions) % 2, (("Raw", "d"),), "FAIL_SUCCESSOR"),
        ("immutable_context_count", d4, count_q, count_read, TRACK, "PASS_EXACT"),
    ]


def matched_examples(models, domains):
    out = []
    specs = ((domains[0], "d", "pd", "R"), (domains[1], "dd", "pdd", "R"),
             (domains[2], "dp", "dppd", "G_and_T"))
    for domain, left_word, right_word, clause in specs:
        left, right = [models["log_consumer"].decode(
            replay(models["log_consumer"], domain.env, word), domain.selected,
        ) for word in (left_word, right_word)]
        if clause == "R":
            require(left.partition == right.partition, "matched partition drift")
            require(left.origin.parents[0][1] != right.origin.parents[0][1], "origin separation lost")
        else:
            require(track_report(left) == track_report(right), "matched carrier report drift")
            targets = [models["log_consumer"].command(domain.env, s, "Absorb", "d") for s in (left, right)]
            require(targets[0] is None and targets[1] is not None, "matched guard separation lost")
            raw = [log_command(models["log_consumer"], domain.env, s, ("Raw", "d")) for s in (left, right)]
            require([len(s.absorptions) % 2 for s in raw] == [0, 1], "matched parity separation lost")
        out.append({"n": domain.env.n, "words": [left_word, right_word], "clauses": clause})
    return out


def unrelated_carry(models):
    env = models["contract"].Environment((0, 3, 2, 5, 1, 4, 0), tuple(range(7)), tuple(range(7)))
    selected = frozenset({3, 5})
    forest, log = models["forest"], models["log_consumer"]
    f, h = replay(forest, env, "dppd"), replay(log, env, "dppd")
    origin = log.decode(h, selected).origin
    trace = []
    for command in (("Carry", "p"),) * 2 + (("Carry", "d"),) + (("Carry", "p"),) * 5 + (("Absorb", "d"),):
        before = log.decode(h, selected)
        next_f = forest.command(env, f, selected, *command)
        expected = log.command(env, before, *command)
        require(next_f is not None and expected is not None, "continuation command disabled")
        h = log.step(env, h, command[1])
        after = log.decode(h, selected)
        require(forest.decode(next_f, selected) == after == expected, "same-call successor mismatch")
        require(after.origin == origin, "selected origin changed")
        trace.append((len(before.partition), len(after.partition), len(before.absorptions), len(after.absorptions)))
        f = next_f
    require(trace[2] == (5, 4, 0, 0), "Carry did not retain unrelated fusion correctly")
    require(trace[-1] == (4, 3, 0, 1), "later selected absorption missing")
    return {"prefix": "dppd", "selected": [3, 5], "suffix": "ppdpppppd", "trace": trace}


def run(models, max_states=100000):
    environments = (((0, 0), frozenset({0, 1})), ((0, 2, 0), frozenset({0, 1, 2})),
                    ((0, 0, 1, 2), frozenset({0, 1})))
    domains = []
    for defect, selected in environments:
        env = models["contract"].Environment(defect, tuple(range(len(defect))), tuple(range(len(defect))))
        domains.append(generated_domain(models, env, selected, max_states))
    decisions = []
    for name, domain, q, report, commands, expected in fixed_cases(domains):
        semantic = semantic_check(models, domain, q, report, commands)
        operator = operator_check(models, domain, q, report, commands)
        kernel = kernel_check(models, domain, q, report, commands)
        require(semantic["status"] == operator["status"] == kernel["status"] == expected,
                f"check-path mismatch: {name}")
        if expected.startswith("FAIL"):
            verify_failure(models, domain, q, report, semantic)
        decisions.append({"name": name, "semantic": semantic, "operator": operator, "kernel": kernel})
    return {
        "status": "PASS_FIXED_CONTROLS", "evidence": "LOCAL_CONSISTENCY_CONTROL",
        "upstream_commit": COMMIT, "upstream_blobs_sha256": BLOBS,
        "scope": [{"n": d.env.n, "defect": d.env.defect, "selected": sorted(d.selected),
                   "saturated_log_states": len(d.log_words), "saturated_forest_states": len(d.forest_words),
                   "registered_summaries": len(d.summaries), "registered_forests": len(d.forest_states)}
                  for d in domains],
        "cases": decisions, "matched": matched_examples(models, domains),
        "same_invocation": unrelated_carry(models),
        "full_grammar_interpreter": False, "canonical_compiler_admission": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sources = parser.add_mutually_exclusive_group(required=True)
    sources.add_argument("--upstream-root", type=Path)
    sources.add_argument("--upstream-snapshot", type=Path)
    parser.add_argument("--max-states", type=int, default=100000)
    args = parser.parse_args()
    try:
        with frozen_models(args.upstream_root, source_dir=args.upstream_snapshot) as models:
            result = run(models, args.max_states)
    except LimitReached as exc:
        print(json.dumps({"status": "UNRESOLVED_LIMIT", "detail": str(exc)}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
