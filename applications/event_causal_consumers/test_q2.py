"""Syntax-wide Q2 contracts, using only the existing fixed environments."""

from contextlib import ExitStack
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from q2 import check, verify_rejection
from q2.common import Budget, InputError
from q2.model import decode, initial, saturate, step
from q2.replay import replay_registered
from q2.request import prepare
from q2.syntax import NODE_KINDS, OPERATIONS, compile_expr, evaluate
from q2.values import BASE, RECORDS, Value, encode, leaves, literal
from q2_cli import unique_object
from q2_examples import (
    A, COUNT, F, GAMMA, O, P, PARITY, case, choose, controls, field, fold,
    fst, lit, op, pair, query, request, snd, var,
)

HERE = Path(__file__).resolve().parent


def execute(raw, word):
    req = prepare(raw)
    state = initial(req.env)
    for letter in word:
        state = step(req.env, state, letter)
    return req, decode(state, req.selected)


def interpret(expr, raw=None, word="dd"):
    req, summary = execute(request(3) if raw is None else raw, word)
    term = compile_expr(expr, req.env, req.budget)
    return encode(evaluate(term, leaves(summary), req.env, req.budget), req.env)["value"]


class DecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = controls()
        cls.results = {name: check(value) for name, value in cls.inputs.items()}

    def test_nine_existing_controls_as_closed_syntax(self):
        expected = {name: "PASS_EXACT" for name in self.inputs}
        expected.update(forget_ports="FAIL_READ", forget_origin="FAIL_READ",
                        forget_partition="FAIL_GUARD", parity_only="FAIL_SUCCESSOR")
        self.assertEqual({name: result["status"] for name, result in self.results.items()}, expected)
        for name, result in self.results.items():
            with self.subTest(name=name):
                self.assertTrue(result["domain_complete"])
                self.assertFalse(result["canonical_compiler_admission"])
                self.assertEqual(result["implementation_status"], "SYNTAX_WIDE_Q2_IMPLEMENTED")
        for n, counts in ((2, (6, 4)), (3, (39, 18)), (4, (292, 72))):
            self.assertEqual(tuple(self.results[f"gamma_n{n}"]["domain"].values()), counts)
        # The consumer changes, not the environment, selected event, q or menu.
        packet, origin = self.inputs["packet_only"], self.inputs["forget_origin"]
        for key in ("environment", "selected"):
            self.assertEqual(packet[key], origin[key])
        for key in ("q", "commands"):
            self.assertEqual(packet["program"][key], origin["program"][key])

    def test_all_rejections_independently_replay(self):
        for name, result in self.results.items():
            if "witness" not in result:
                continue
            with self.subTest(name=name):
                replay = verify_rejection(self.inputs[name], result)
                self.assertEqual(replay["status"], "VALID_REJECTION_WITNESS")
                self.assertFalse(replay["domain_completeness_verified"])

    def test_replay_does_not_call_producer_algorithms(self):
        with ExitStack() as stack:
            for name in ("q2.model.step", "q2.model.decode", "q2.model.saturate", "q2.engine.decide"):
                stack.enter_context(patch(name, side_effect=AssertionError("producer called")))
            for name in ("forget_ports", "forget_origin", "forget_partition", "parity_only"):
                self.assertEqual(verify_rejection(self.inputs[name], self.results[name])["status"],
                                 "VALID_REJECTION_WITNESS")

    def test_tampered_histories_payloads_and_bindings_rejected(self):
        name = "parity_only"
        raw, result = self.inputs[name], self.results[name]
        mutations = [
            lambda r: r.update(request_sha256="0" * 64),
            lambda r: r.update(status=[]),
            lambda r: r["witness"]["clause"].update(kind="G"),
            lambda r: r["witness"]["clause"].update(label="invented"),
            lambda r: r["witness"]["left"].update(word=""),
            lambda r: r["witness"]["left"].update(word="other"),
            lambda r: r["witness"]["left"]["guards"][0].update(value=1),
            lambda r: r["witness"]["left"]["q"].update(type="Pos"),
            lambda r: r["witness"]["left"]["after"].update(word="d"),
            lambda r: r["witness"]["left"]["after"]["q"].update(value=99),
            lambda r: r["witness"]["left"]["causal"]["OriginSnapshot"]["value"].update(target=3),
        ]
        for mutate in mutations:
            damaged = deepcopy(result)
            mutate(damaged)
            with self.subTest(mutation=mutations.index(mutate)):
                self.assertEqual(verify_rejection(raw, damaged)["status"], "INVALID_REJECTION_WITNESS")
        changed = deepcopy(raw)
        changed["selected"] = [0, 2]
        self.assertEqual(verify_rejection(changed, result)["status"], "INVALID_REJECTION_WITNESS")

    def test_replay_rejects_equal_history_without_separation(self):
        damaged = deepcopy(self.results["forget_origin"])
        damaged["witness"]["right"] = deepcopy(damaged["witness"]["left"])
        self.assertEqual(verify_rejection(self.inputs["forget_origin"], damaged)["status"],
                         "INVALID_REJECTION_WITNESS")

    def test_all_generated_predecessors_and_successors_have_same_replay(self):
        for n in (2, 3, 4):
            req = prepare(request(n))
            domain = saturate(req.env, req.selected, req.budget)
            for i, log in enumerate(domain.logs):
                actual = decode(log, req.selected)
                if actual is not None:
                    word = domain.word(i)
                    self.assertEqual(actual, replay_registered(req.env, req.selected, word, Budget()))
                    for letter in ("p", "d"):
                        self.assertEqual(decode(step(req.env, log, letter), req.selected),
                                         replay_registered(req.env, req.selected, word + letter, Budget()))

    def test_same_invocation_existing_unrelated_carry(self):
        raw = request(4)
        raw["environment"] = {"defect": [0, 3, 2, 5, 1, 4, 0], "seed": list(range(7))}
        raw["selected"] = [3, 5]
        before_req, before = execute(raw, "dppdpp")
        _, after_carry = execute(raw, "dppdppd")
        _, after_absorb = execute(raw, "dppdppdpppppd")
        self.assertEqual((len(before.partition), len(after_carry.partition)), (5, 4))
        self.assertEqual((len(after_carry.absorptions), len(after_absorb.absorptions)), (0, 1))
        self.assertEqual(before.origin, after_absorb.origin)
        for word, expected in (("dppdppd", after_carry), ("dppdppdpppppd", after_absorb)):
            self.assertEqual(replay_registered(before_req.env, before_req.selected, word, Budget()), expected)

    def test_history_length_is_not_a_saturation_key_or_cutoff(self):
        req, short = execute(request(4), "d")
        long = replay_registered(req.env, req.selected, "d" + "p" * 10000, Budget())
        self.assertEqual(long, short)
        self.assertFalse(hasattr(short, "word"))

    def test_pivot_decision_matches_all_pairs_on_existing_controls(self):
        for name, raw in self.inputs.items():
            req = prepare(raw)
            domain = saturate(req.env, req.selected, req.budget)
            qs = [evaluate(req.q, leaves(x), req.env, Budget()) for x in domain.summaries]
            rows = [tuple(evaluate(expr, leaves(x), req.env, Budget()) for _, expr in req.reports)
                    for x in domain.summaries]
            guards = [tuple(evaluate(c.guard, leaves(x), req.env, Budget()).data for c in req.commands)
                      for x in domain.summaries]
            pairs = [(i, j) for i in range(len(qs)) for j in range(i) if qs[i] == qs[j]]
            if any(rows[i] != rows[j] for i, j in pairs):
                expected = "FAIL_READ"
            elif any(guards[i] != guards[j] for i, j in pairs):
                expected = "FAIL_GUARD"
            elif any(guards[i][col] and qs[domain.successors[i, c.letter]] !=
                     qs[domain.successors[j, c.letter]]
                     for i, j in pairs for col, c in enumerate(req.commands)):
                expected = "FAIL_SUCCESSOR"
            else:
                expected = "PASS_EXACT"
            with self.subTest(name=name):
                self.assertEqual(self.results[name]["status"], expected)

    def test_valid_none_q_is_not_an_undefined_command(self):
        raw = request(3, {"kind": "none", "element_type": "Nat"}, [], [
            {"label": "raw_p", "letter": "p", "guard": lit("Bool", True)}])
        result = check(raw)
        self.assertEqual(result["status"], "PASS_EXACT")
        self.assertEqual(result["q_states"], 1)

    def test_distinct_labels_with_same_action_are_not_deduplicated(self):
        raw = request(2, commands=[{"label": name, "letter": "p", "guard": lit("Bool", True)}
                                   for name in ("first", "second")])
        self.assertEqual(check(raw)["command_labels"], ["first", "second"])

    def test_empty_domain_and_every_resource_stop_are_not_pass(self):
        raw = request(2)
        raw["selected"] = [0]
        self.assertEqual(check(raw)["status"], "EMPTY_REGISTERED_DOMAIN")
        for resource in ({"max_states": 1}, {"max_steps": 1}, {"max_ast_nodes": 1}, {"max_seconds": 1e-30}):
            limited = request(4)
            limited["resources"] = resource
            result = check(limited)
            self.assertEqual(result["status"], "UNRESOLVED_LIMIT")
            self.assertFalse(result["domain_complete"])
            self.assertNotIn("witness", result)
        for error in (MemoryError(), RecursionError()):
            with patch("q2.engine.saturate", side_effect=error):
                self.assertEqual(check(request(2))["status"], "UNRESOLVED_LIMIT")

    def test_atom_renaming_and_port_order_are_explicit_inputs(self):
        raw = request(2)
        raw["environment"].update(atoms=["x", "y"], kernel_ports=[1, 0])
        raw["selected"] = ["x", "y"]
        self.assertEqual(check(raw)["status"], "PASS_EXACT")
        req, summary = execute(raw, "d")
        parent = encode(leaves(summary)["OriginSnapshot"], req.env)["value"]["parents"][0]
        self.assertEqual(parent, [1, ["y"]])


class SyntaxTests(unittest.TestCase):
    def test_typed_value_keys_do_not_identify_bool_nat_atom_pos(self):
        keys = {Value(BASE[name], value) for name, value in
                (("Bool", True), ("Nat", 1), ("Atom", 1), ("Pos", 1))}
        self.assertEqual(len(keys), 4)

    def test_all_constructors_and_primitives_executed(self):
        some = {"kind": "some", "value": lit("Nat", 7)}
        none = {"kind": "none", "element_type": "Nat"}
        seq = {"kind": "list", "element_type": "Nat", "items": [lit("Nat", 1), lit("Nat", 2)]}
        record = {"kind": "record", "type": "Origin", "fields": {
            name: field(O, name) for name, _ in RECORDS[BASE["Origin"]]}}
        samples = [
            (lit("Nat", 3), 3), (query("SelectedBlock"), [0, 1, 2]),
            (pair(lit("Nat", 1), lit("Bool", False)), [1, False]),
            (fst(pair(lit("Nat", 1), lit("Bool", False))), 1),
            (snd(pair(lit("Nat", 1), lit("Bool", False))), False),
            (choose(lit("Bool", True), lit("Nat", 3), lit("Nat", 4)), 3),
            (fold(seq, lit("Nat", 0), "acc", "x", op("add", var("acc"), var("x"))), 3),
            (record, interpret(O)), (field(record, "label"), "d"), (seq, [1, 2]),
            (some, {"some": 7}), (none, None), (case(some, lit("Nat", 0), "x", var("x")), 7),
            (case(none, lit("Nat", 0), "x", var("x")), 0),
        ]
        primitive_samples = {
            "eq": (op("eq", lit("Atom", 1), lit("Atom", 1)), True),
            "not": (op("not", lit("Bool", False)), True),
            "and": (op("and", lit("Bool", True), lit("Bool", False)), False),
            "or": (op("or", lit("Bool", False), lit("Bool", True)), True),
            "add": (op("add", lit("Nat", 3), lit("Nat", 4)), 7),
            "lt": (op("lt", lit("Nat", 3), lit("Nat", 4)), True),
            "le": (op("le", lit("Nat", 4), lit("Nat", 4)), True),
            "mod": (op("mod", lit("Nat", 7), modulus=3), 1),
            "union": (op("union", lit("Block", [0]), lit("Block", [1])), [0, 1]),
            "intersection": (op("intersection", lit("Block", [0]), lit("Block", [1])), []),
            "subset": (op("subset", lit("Block", [0]), F), True),
            "cardinality": (op("cardinality", F), 3),
            "cons": (op("cons", lit("Nat", 0), seq), [0, 1, 2]),
            "lookup": (op("lookup", P, lit("Pos", 0)), {"some": [0, 1, 2]}),
            "entries": (op("entries", P), [[0, [0, 1, 2]]]),
            "carrier": (op("carrier", P, F), {"some": [0, [0, 1, 2]]}),
            "f_p": (op("f_p", lit("Pos", 2)), 0),
            "f_d": (op("f_d", lit("Pos", 1)), 2),
        }
        self.assertEqual(set(primitive_samples), OPERATIONS)
        seen = set()

        def visit(node):
            if isinstance(node, dict):
                if "kind" in node:
                    seen.add(node["kind"])
                for value in node.values():
                    visit(value)
            elif isinstance(node, list):
                for value in node:
                    visit(value)

        for expr, expected in samples + list(primitive_samples.values()):
            with self.subTest(expr=expr["kind"]):
                self.assertEqual(interpret(expr), expected)
                visit(expr)
                self.assertEqual(check(request(3, GAMMA, [{"label": "r", "expr": expr}]))["status"],
                                 "PASS_EXACT")
        self.assertEqual(seen, NODE_KINDS)

    def test_literal_roundtrip_all_sorts_and_record_constructors(self):
        req, summary = execute(request(3), "dd")
        extra = {"Bool": True, "Nat": 0, "Atom": 1, "Pos": 1, "Letter": "d", "Block": [0],
                 "Partition": [[0, [0]], [1, [1]], [2, [2]]],
                 "Origin": {"label": "d", "parents": [[0, [0]], [2, [2]]], "target": 0},
                 "AbsRecord": {"label": "d", "carrier_at": 0, "carrier": [0], "partner_at": 2,
                               "partner": [2], "target": 0, "merged": [0, 2]}}
        self.assertEqual(set(extra), set(BASE))
        for name, raw in extra.items():
            value = literal(BASE[name], raw, req.env, Budget())
            self.assertEqual(encode(value, req.env)["value"], raw)
            if BASE[name] in RECORDS:
                expression = {"kind": "record", "type": name, "fields": {
                    key: lit(sort.json(), raw[key]) for key, sort in RECORDS[BASE[name]]}}
                self.assertEqual(interpret(expression), raw)
        for sort, raw in ((["Prod", "Nat", ["Option", "Bool"]], [2, {"some": False}]),
                          (["List", ["Option", "Nat"]], [None, {"some": 1}])):
            self.assertEqual(interpret(lit(sort, raw)), raw)

    def test_left_fold_order_nested_capture_and_current_reads(self):
        seq = lit(["List", "Nat"], [1, 2, 3])
        reverse = fold(seq, lit(["List", "Nat"], []), "acc", "x", op("cons", var("x"), var("acc")))
        self.assertEqual(interpret(reverse), [3, 2, 1])
        nested = fold(seq, lit("Nat", 0), "outer", "x", op("add", var("outer"),
            fold(lit(["List", "Nat"], [1, 2]), lit("Nat", 0), "inner", "y",
                 op("add", var("inner"), op("add", var("x"), var("y"))))))
        self.assertEqual(interpret(nested), 21)
        shadow = fold(seq, lit("Nat", 0), "acc", "x", op("add", var("acc"),
            fold(lit(["List", "Nat"], [7]), lit("Nat", 0), "acc", "x", var("x"))))
        self.assertEqual(interpret(shadow), 21)
        body_read = fold(A, lit("Nat", 0), "acc", "x", op("add", var("acc"), op("cardinality", F)))
        self.assertEqual(interpret(body_read, request(4), "dppdd"),
                         len(execute(request(4), "dppdd")[1].absorptions) * 2)

    def test_chronological_fold_over_actual_multi_absorption_history(self):
        req = prepare(request(4))
        domain = saturate(req.env, req.selected, req.budget)
        index = next(i for i, s in enumerate(domain.summaries) if len(s.absorptions) == 2)
        summary = domain.summaries[index]
        word = domain.word(domain.representatives[index])
        records = fold(A, lit(["List", "Block"], []), "result", "record",
                       op("cons", field(var("record"), "partner"), var("result")))
        expected = [list(sorted(x.partner)) for x in reversed(summary.absorptions)]
        self.assertEqual(interpret(records, request(4), word), expected)

    def test_lookup_none_and_nonunique_carrier_are_total_values(self):
        self.assertIsNone(interpret(op("lookup", P, lit("Pos", 2))))
        self.assertIsNone(interpret(op("carrier", lit("Partition", [[0, [0]], [1, [1]], [2, [2]]]),
                                     lit("Block", []))))

    def test_invalid_terms_including_unexecuted_branches_rejected(self):
        invalid = [
            lit("Nat", True), lit("Bool", 1), lit("Pos", 3), lit("Atom", "missing"),
            lit("Letter", "x"), lit("Block", [0, 0]), lit("Block", [99]),
            lit("Partition", [[0, [0, 1]], [1, [1, 2]]]),
            lit(["Option", "Nat"], 1), lit(["Prod", "Nat", "Nat"], [1]),
            lit(["List", "Nat"], [False]), lit(["List"], []),
            lit("Origin", {}), var("free"), query("word"), query("success"), query("marker"),
            {"kind": "eval", "code": "print(1)"}, op("unknown"), op("add", lit("Nat", 1)),
            op("eq", lit("Atom", 1), lit("Pos", 1)), op("mod", lit("Nat", 7), modulus=0),
            op("mod", lit("Nat", 7), modulus=lit("Nat", 2)),
            op("add", lit("Nat", 1), lit("Nat", 2), modulus=2),
            choose(lit("Bool", True), lit("Nat", 1), query("timestamp")),
            fold(A, lit("Nat", 0), "acc", "item", lit("Bool", False)),
            fold(A, lit("Nat", 0), "same", "same", lit("Nat", 0)),
            case({"kind": "none", "element_type": "Nat"}, lit("Nat", 0), "x", lit("Bool", True)),
            fst(lit("Nat", 0)), field(O, "success"),
            {"kind": "list", "element_type": "Nat", "items": [lit("Bool", False)]},
        ]
        for expr in invalid:
            with self.subTest(expr=expr):
                raw = request(3, expr)
                self.assertEqual(check(raw)["status"], "INVALID_INPUT")
                raw["selected"] = [0]
                self.assertEqual(check(raw)["status"], "INVALID_INPUT")

    def test_invalid_envelopes_and_guards_rejected(self):
        mutations = [
            lambda r: r.update(extra=True), lambda r: r.update(language="python"),
            lambda r: r.update(selected=[]), lambda r: r.update(selected=[True]),
            lambda r: r["environment"].update(defect=[0, 1]),
            lambda r: r["environment"].update(seed=[0, 0]),
            lambda r: r["environment"].update(kernel_ports=[0, 0]),
            lambda r: r["environment"].update(atoms=[0, 0]),
            lambda r: r["program"]["commands"][0].update(guard=lit("Nat", 1)),
            lambda r: r["program"]["commands"][0].update(letter="e"),
            lambda r: r["program"]["commands"].append(deepcopy(r["program"]["commands"][0])),
            lambda r: r["program"]["reports"].append(deepcopy(r["program"]["reports"][0])),
            lambda r: r.update(resources={"max_states": True}),
        ]
        for mutate in mutations:
            raw = request(2)
            mutate(raw)
            self.assertEqual(check(raw)["status"], "INVALID_INPUT")
        with self.assertRaises(InputError):
            unique_object([("x", 1), ("x", 2)])


class CLITests(unittest.TestCase):
    def run_cli(self, *args, data=None):
        result = subprocess.run([sys.executable, "-B", str(HERE / "q2_cli.py"), *args],
                                input=data, text=True, capture_output=True, check=False)
        return result.returncode, json.loads(result.stdout)

    def test_saved_json_request_and_stdin_rejection_replay(self):
        source = str(HERE / "examples" / "origin_read_failure.json")
        code, result = self.run_cli("check", source)
        self.assertEqual((code, result["status"]), (0, "FAIL_READ"))
        code, replay = self.run_cli("verify", source, "--result", "-", data=json.dumps(result))
        self.assertEqual((code, replay["status"]), (0, "VALID_REJECTION_WITNESS"))

    def test_cli_duplicate_nonfinite_and_byte_limits(self):
        for text in ('{"language":1,"language":2}', '{"value":NaN}', "not json"):
            code, result = self.run_cli("check", "-", data=text)
            self.assertEqual((code, result["status"]), (1, "INVALID_INPUT"))
        code, result = self.run_cli("check", "-", "--max-input-bytes", "1", data="{}")
        self.assertEqual((code, result["status"]), (2, "UNRESOLVED_LIMIT"))


class FrozenDifferentialTests(unittest.TestCase):
    def test_generated_log_image_and_guarded_commands_match_frozen_source(self):
        root = os.environ.get("RIME_LITE_UPSTREAM")
        snapshot = os.environ.get("RIME_PAPER39_SNAPSHOT")
        if not root and not snapshot:
            self.skipTest("optional frozen-source differential: set a pinned source input")
        from fixed_controls import frozen_models, generated_domain
        with frozen_models(None if snapshot else Path(root), source_dir=snapshot) as models:
            old_env_type = models["contract"].Environment
            for n in (2, 3, 4):
                req = prepare(request(n))
                old_env = old_env_type(req.env.defect, req.env.seed, tuple(range(n)))
                old_domain = generated_domain(models, old_env, req.selected)
                new_domain = saturate(req.env, req.selected, req.budget)
                old_summaries = {json.dumps(models["contract"].primitive(s), sort_keys=True)
                                 for s in old_domain.summaries}
                for summary in new_domain.summaries:
                    # Dataclass field names and immutable payloads have the same specification.
                    self.assertIn(json.dumps(models["contract"].primitive(summary), sort_keys=True), old_summaries)
                self.assertEqual(len(old_summaries), len(new_domain.summaries))
                self.assertEqual(len(old_domain.log_words), len(new_domain.logs))
                for old_summary, word in old_domain.summaries.items():
                    new_summary = replay_registered(req.env, req.selected, word, Budget())
                    for command in req.commands:
                        kind = command.label.split("(")[0]
                        old_target = models["log_consumer"].command(old_env, old_summary, kind, command.letter)
                        enabled = evaluate(command.guard, leaves(new_summary), req.env, Budget()).data
                        self.assertEqual(enabled, old_target is not None)
                        if enabled:
                            new_target = replay_registered(req.env, req.selected, word + command.letter, Budget())
                            self.assertEqual(models["contract"].primitive(new_target),
                                             models["contract"].primitive(old_target))


if __name__ == "__main__":
    unittest.main()
