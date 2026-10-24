from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from itertools import combinations
import hashlib
import json
from math import gcd
from pathlib import Path
import sys
from time import perf_counter

from .protocol import canonical_bytes, ensure_eof, iter_records, read_header


def _profile_signature(mass: int, positive: list[int]) -> tuple[int, ...]:
    divisor = gcd(mass, *positive)
    return (mass // divisor, *(value // divisor for value in positive))


def _coordinate_ratio(signature: tuple[int, ...], coordinate: int) -> tuple[int, int]:
    denominator, *positive = signature
    numerator = positive[coordinate]
    divisor = gcd(denominator, numerator)
    return numerator // divisor, denominator // divisor


def _minimum_separators(
    signatures: list[tuple[int, ...]], labels: list[str]
) -> list[list[str]] | None:
    dimension = len(labels)
    if dimension > 8:
        return None
    for width in range(dimension + 1):
        answers = []
        for coordinates in combinations(range(dimension), width):
            projections = {
                tuple(_coordinate_ratio(signature, coordinate) for coordinate in coordinates)
                for signature in signatures
            }
            if len(projections) == len(signatures):
                answers.append([labels[index] for index in coordinates])
        if answers:
            return answers
    return []


def _minimum_global_separators(
    classes_by_sector: list[list[tuple[int, ...]]], labels: list[str]
) -> list[list[str]] | None:
    dimension = len(labels)
    if dimension > 8:
        return None
    for width in range(dimension + 1):
        answers = []
        for coordinates in combinations(range(dimension), width):
            separates_every_fiber = all(
                len({
                    tuple(_coordinate_ratio(signature, coordinate) for coordinate in coordinates)
                    for signature in signatures
                }) == len(signatures)
                for signatures in classes_by_sector
            )
            if separates_every_fiber:
                answers.append([labels[index] for index in coordinates])
        if answers:
            return answers
    return []


def census(header: dict, records, *, metrics: dict | None = None) -> dict:
    started = perf_counter()
    labels = header["sector_labels"]
    classes: list[dict[tuple[int, ...], int]] = [defaultdict(int) for _ in labels]
    edge_count = 0
    for record in records:
        positive = [0] * len(labels)
        mass = 0
        for target_sector, weight in record["edges"]:
            mass += weight
            if record["sign"] > 0:
                positive[target_sector] += weight
        signature = _profile_signature(mass, positive)
        classes[record["source_sector"]][signature] += 1
        edge_count += len(record["edges"])

    aggregated = perf_counter()
    class_rows = []
    sector_results = []
    total_classes = 0
    for sector_index, label in enumerate(labels):
        ordered = sorted(classes[sector_index].items())
        signatures = [signature for signature, _ in ordered]
        frequencies = [frequency for _, frequency in ordered]
        class_rows.extend(
            [[sector_index, list(signature), frequency] for signature, frequency in ordered]
        )
        class_count = len(ordered)
        total_classes += class_count
        pair_count = class_count * (class_count - 1) // 2
        separated = []
        for coordinate in range(len(labels)):
            counts = Counter(_coordinate_ratio(signature, coordinate) for signature in signatures)
            same_pairs = sum(count * (count - 1) // 2 for count in counts.values())
            separated.append(pair_count - same_pairs)
        sector_results.append({
            "sector_index": sector_index,
            "sector_label": label,
            "eligible_sources": sum(frequencies),
            "profile_classes": class_count,
            "largest_class_sources": max(frequencies, default=0),
            "class_pairs": pair_count,
            "coordinate_separated_class_pairs": separated,
            "minimum_separating_coordinate_sets": _minimum_separators(signatures, labels),
        })

    result = {
        "schema": "rime.malecns.profile-census-result.v1",
        "status": "EXACT_CENSUS",
        "source_field": header["source_field"],
        "source_identity": header["source_identity"],
        "sign_semantics": header["sign_semantics"],
        "sector_labels": labels,
        "eligible_sources": sum(result["eligible_sources"] for result in sector_results),
        "profile_classes": total_classes,
        "profile_classes_sha256": hashlib.sha256(canonical_bytes(class_rows)).hexdigest(),
        "minimum_global_separating_coordinate_sets": _minimum_global_separators(
            [sorted(sector_classes) for sector_classes in classes], labels
        ),
        "sectors": sector_results,
        "source_artifacts": header["source_artifacts"],
        "claim_boundary": "exact integer profile census for the supplied finite input; no biological inference or paper admission",
    }
    if metrics is not None:
        metrics.update({
            "stream_decode_validate_aggregate_seconds": aggregated - started,
            "classify_report_seconds": perf_counter() - aggregated,
            "edge_count": edge_count,
            "record_count": header["record_count"],
        })
    return result


def run(path: str | Path, *, metrics: dict | None = None) -> dict:
    started = perf_counter()
    with Path(path).open("rb") as stream:
        header = read_header(stream)
        if metrics is not None:
            metrics["header_decode_seconds"] = perf_counter() - started
        result = census(header, iter_records(stream, header), metrics=metrics)
        ensure_eof(stream)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Exact streaming profile reference")
    parser.add_argument("input", type=Path)
    parser.add_argument("--metrics", action="store_true")
    args = parser.parse_args()
    metrics = {} if args.metrics else None
    result = run(args.input, metrics=metrics)
    started = perf_counter()
    encoded = canonical_bytes(result).decode("utf-8")
    if metrics is not None:
        metrics["serialize_seconds"] = perf_counter() - started
    print(encoded)
    if metrics is not None:
        print("SOF_PROFILE_METRICS " + json.dumps(metrics, sort_keys=True), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
