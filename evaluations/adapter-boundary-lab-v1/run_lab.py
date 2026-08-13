"""Run the deterministic adapter-boundary lab without producing SOF artifacts."""

from __future__ import annotations

from argparse import ArgumentParser
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures.json"
DEFAULT_OUTPUT = ROOT / "results" / "summary.json"


def _matrix_multiply(left: list[list[Fraction]], right: list[list[Fraction]]) -> list[list[Fraction]]:
    width = len(right)
    return [
        [sum(left[row][inner] * right[inner][column] for inner in range(width)) for column in range(len(right[0]))]
        for row in range(len(left))
    ]


def _matrix_power(matrix: list[list[Fraction]], exponent: int) -> list[list[Fraction]]:
    size = len(matrix)
    result = [[Fraction(int(row == column)) for column in range(size)] for row in range(size)]
    for _ in range(exponent):
        result = _matrix_multiply(result, matrix)
    return result


def _support_pairs(matrix: list[list[Fraction]]) -> list[list[int]]:
    return [
        [row, column]
        for row in range(len(matrix))
        for column in range(len(matrix[row]))
        if row != column and matrix[row][column] != 0
    ]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _markov_positive(fixture: dict[str, Any]) -> dict[str, Any]:
    source = fixture["source"]
    matrix = [
        [Fraction(value, denominator) for value in row]
        for row, denominator in zip(
            source["transition_numerators"], source["row_denominators"], strict=True
        )
    ]
    states = source["states"]
    adjacency = [[value > 0 for value in row] for row in source["transition_numerators"]]
    graph_distances: dict[tuple[int, int], int | None] = {}
    for start in range(len(states)):
        distances = {start: 0}
        frontier = [start]
        while frontier:
            current = frontier.pop(0)
            for target, present in enumerate(adjacency[current]):
                if present and target not in distances:
                    distances[target] = distances[current] + 1
                    frontier.append(target)
        for target in range(len(states)):
            if start != target:
                graph_distances[(start, target)] = distances.get(target)

    matrix_first_hits: dict[tuple[int, int], int | None] = {
        (start, target): None
        for start in range(len(states))
        for target in range(len(states))
        if start != target
    }
    power = matrix
    for depth in range(1, len(states) + 1):
        for start, target in matrix_first_hits:
            if matrix_first_hits[(start, target)] is None and power[start][target] > 0:
                matrix_first_hits[(start, target)] = depth
        power = _matrix_multiply(power, matrix)
    graph_first_hits = [
        {"source": states[start], "target": states[target], "first_positive_depth": graph_distances[(start, target)]}
        for start in range(len(states))
        for target in range(len(states))
        if start != target
    ]
    matrix_power_first_hits = [
        {"source": states[start], "target": states[target], "first_positive_depth": matrix_first_hits[(start, target)]}
        for start in range(len(states))
        for target in range(len(states))
        if start != target
    ]
    return {
        "checks": {
            "row_sums_match_denominators": all(
                sum(row) == denominator
                for row, denominator in zip(
                    source["transition_numerators"], source["row_denominators"], strict=True
                )
            ),
            "graph_first_hits_equal_matrix_power_first_hits": graph_first_hits == matrix_power_first_hits,
            "all_matrix_power_support_pairs_are_graph_reachable": all(
                matrix_first_hits[pair] is None or graph_distances[pair] is not None
                for pair in matrix_first_hits
            )
        },
        "observations": {
            "pair_count": len(graph_first_hits),
            "reachable_pair_count": sum(item["first_positive_depth"] is not None for item in graph_first_hits),
            "maximum_first_hit_depth": max(item["first_positive_depth"] for item in graph_first_hits),
            "graph_first_hits": graph_first_hits,
            "matrix_power_first_hits": matrix_power_first_hits,
        },
        "method": "exact Fraction matrix powers and finite support-graph closure",
    }


def _signed_cancellation(fixture: dict[str, Any]) -> dict[str, Any]:
    matrix = [[Fraction(value) for value in row] for row in fixture["source"]["matrix"]]
    square = _matrix_power(matrix, 2)
    graph_routes = 0
    for middle in range(len(matrix)):
        if matrix[0][middle] != 0 and matrix[middle][2] != 0:
            graph_routes += 1
    contributions = [matrix[0][middle] * matrix[middle][2] for middle in range(len(matrix))]
    return {
        "checks": {
            "two_union_graph_routes": graph_routes == 2,
            "route_contributions_cancel": sum(contributions) == 0,
            "matrix_square_entry_is_zero": square[0][2] == 0,
        },
        "observations": {
            "graph_route_count": graph_routes,
            "route_contributions": [str(value) for value in contributions if value != 0],
            "matrix_square_entry_0_2": str(square[0][2]),
        },
        "method": "exact signed matrix multiplication with explicit route contributions",
    }


def _multi_letter_word(fixture: dict[str, Any]) -> dict[str, Any]:
    source = fixture["source"]
    matrices = {
        label: [[Fraction(value) for value in row] for row in matrix]
        for label, matrix in source["matrices"].items()
    }
    union_edges = {
        (row, column)
        for matrix in matrices.values()
        for row in range(len(matrix))
        for column in range(len(matrix[row]))
        if matrix[row][column] != 0
    }

    def evaluate(word: list[str]) -> Fraction:
        product = _matrix_power(matrices[word[0]], 1)
        for label in word[1:]:
            product = _matrix_multiply(product, matrices[label])
        return product[0][2]

    return {
        "checks": {
            "union_graph_has_0_to_2_path": (0, 1) in union_edges and (1, 2) in union_edges,
            "selected_word_AA_is_zero": evaluate(source["selected_word"]) == 0,
            "control_word_AB_is_nonzero": evaluate(source["control_word"]) != 0,
        },
        "observations": {
            "union_graph_path": ["0", "1", "2"],
            "selected_word": source["selected_word"],
            "selected_word_entry_0_2": str(evaluate(source["selected_word"])),
            "control_word": source["control_word"],
            "control_word_entry_0_2": str(evaluate(source["control_word"])),
        },
        "method": "label-preserving exact matrix products; union graph is computed separately",
    }


def _cutoff_unreached(fixture: dict[str, Any]) -> dict[str, Any]:
    source = fixture["source"]
    adjacency = {state: [] for state in source["states"]}
    for left, right in source["edges"]:
        adjacency[left].append(right)
    maximum_depth = source["maximum_depth"]
    values = {}
    for target in source["states"][1:]:
        frontier = {source["states"][0]}
        depth = None
        for current_depth in range(1, maximum_depth + 1):
            frontier = {next_state for state in frontier for next_state in adjacency[state]}
            if target in frontier:
                depth = current_depth
                break
        values[f"0->{target}"] = depth if depth is not None else source["unreached_value"]
    return {
        "checks": {
            "finite_depths_are_recorded": values["0->1"] == 1 and values["0->2"] == 2,
            "cutoff_unreached_is_explicit": values["0->3"] == "UNREACHED_AT_CUTOFF",
            "unreached_is_not_infinity": values["0->3"] != "infinity",
        },
        "observations": {"maximum_depth": maximum_depth, "pair_values": values},
        "method": "bounded breadth-first traversal with explicit cutoff state",
    }


def _threshold_sweep(fixture: dict[str, Any]) -> dict[str, Any]:
    source = fixture["source"]
    entries = [(item["pair"], Fraction(item["value"])) for item in source["candidate_entries"]]
    rows = []
    for threshold_text in source["thresholds"]:
        threshold = Fraction(threshold_text)
        selected = [pair for pair, value in entries if value > threshold]
        rows.append({"threshold": threshold_text, "support_pairs": selected, "support_count": len(selected)})
    return {
        "checks": {
            "strict_greater_than_is_used": rows[0]["support_count"] == 2 and rows[1]["support_count"] == 1 and rows[2]["support_count"] == 0,
            "sweep_changes_support_count": len({row["support_count"] for row in rows}) == 3,
        },
        "observations": {"comparison": source["comparison"], "rows": rows},
        "method": "exact decimal Fraction threshold sweep under strict-greater-than",
    }


RUNNERS = {
    "markov-positive": _markov_positive,
    "signed-cancellation": _signed_cancellation,
    "multi-letter-word": _multi_letter_word,
    "cutoff-unreached": _cutoff_unreached,
    "threshold-sweep": _threshold_sweep,
}


def run_lab(fixtures: dict[str, Any]) -> dict[str, Any]:
    common_nonclaims = fixtures["common_known_nonclaims"]
    results = []
    for fixture in fixtures["fixtures"]:
        result = RUNNERS[fixture["fixture_id"]](fixture)
        passed = all(result["checks"].values())
        results.append(
            {
                "fixture_id": fixture["fixture_id"],
                "kind": fixture["kind"],
                "status": "PASS" if passed else "FAIL",
                "strongest_claim_level": fixture["strongest_claim_level"],
                "strongest_claim": fixture["strongest_claim"],
                "known_nonclaims": common_nonclaims + fixture["known_nonclaims"],
                "checks": result["checks"],
                "observations": result["observations"],
                "method": result["method"],
            }
        )
    return {
        "lab_id": fixtures["lab_id"],
        "lab_version": fixtures["lab_version"],
        "status": "PASS" if all(item["status"] == "PASS" for item in results) else "FAIL",
        "fixture_count": len(results),
        "results": results,
        "input_closure": {
            "fixtures_sha256": _sha256(FIXTURES),
            "runner_sha256": _sha256(Path(__file__).resolve()),
        },
        "negative_boundary": common_nonclaims,
    }


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    summary = run_lab(json.loads(FIXTURES.read_text(encoding="utf-8")))
    if args.check:
        if not args.output.is_file():
            print(json.dumps({"status": "FAIL", "reason": "committed summary is missing"}, sort_keys=True))
            return 1
        committed = json.loads(args.output.read_text(encoding="utf-8"))
        if committed != summary:
            print(json.dumps({"status": "FAIL", "reason": "committed summary differs from recomputation"}, sort_keys=True))
            return 1
        print(json.dumps({"status": "PASS", "output": str(args.output), "fixture_count": summary["fixture_count"]}, sort_keys=True))
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": summary["status"], "output": str(args.output), "fixture_count": summary["fixture_count"]}, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
