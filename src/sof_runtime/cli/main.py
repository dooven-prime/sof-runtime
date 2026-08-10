from __future__ import annotations

import argparse
import json
from pathlib import Path

from sof_runtime.adapters.automata import (
    build_manifest as build_automata_manifest,
    normalize_source as normalize_automata_source,
)
from sof_runtime.adapters.markov import (
    build_manifest as build_markov_manifest,
    normalize_source as normalize_markov_source,
)
from sof_runtime.compiler import compile_documents
from sof_runtime.comparison import validate_audit
from sof_runtime.action import validate_action
from sof_runtime.api import Comparison, Report, RuntimeAPI
from sof_runtime.contracts import load_json
from sof_runtime.contracts.validation import write_json
from sof_runtime.artifacts.store import ArtifactStore
from sof_runtime.explain import explain_run
from sof_runtime.paths import PROJECT_ROOT
from sof_runtime.reporting import (
    assemble_report,
    build_validation_receipt,
    validate_receipt,
    validate_report,
)
from sof_runtime.reporting import assembly_v2 as assembly_implementation
from sof_runtime.reporting import validation_v2 as validation_implementation
from sof_runtime.serializers import compiler_output_markdown
from sof_runtime.workflow import (
    run_rank_collapse,
    validate_promotion_package,
    validate_run_response,
)
from sof_runtime.workflow_positive_word import (
    run_positive_word_support,
    validate_positive_word_promotion,
    validate_positive_word_response,
)
from sof_runtime.workflow_external_adapter import run_external_adapter

from .scaffold import init_adapter


SOURCE_HANDLERS = {
    "rime.automata.source.v1": (
        normalize_automata_source,
        build_automata_manifest,
    ),
    "rime.markov.source.v1": (
        normalize_markov_source,
        build_markov_manifest,
    ),
}


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def command_validate_source(args: argparse.Namespace) -> None:
    source = load_json(args.source)
    try:
        normalize, _ = SOURCE_HANDLERS[source.get("schema_id")]
    except KeyError as error:
        raise SystemExit(f"unsupported source schema: {source.get('schema_id')!r}") from error
    source = normalize(source)
    _print({"status": "PASS", "source_id": source["source_id"]})


def command_admit(args: argparse.Namespace) -> None:
    source = load_json(args.source)
    try:
        _, build_manifest = SOURCE_HANDLERS[source.get("schema_id")]
    except KeyError as error:
        raise SystemExit(f"unsupported source schema: {source.get('schema_id')!r}") from error
    manifest = build_manifest(source)
    write_json(args.out, manifest)
    _print({"status": "PASS", "manifest": str(args.out)})


def command_run(args: argparse.Namespace) -> None:
    runners = {
        "rank-collapse": run_rank_collapse,
        "positive-word-support": run_positive_word_support,
    }
    try:
        runner = runners[args.carrier]
    except KeyError as error:
        raise SystemExit(f"unknown carrier plugin: {args.carrier}") from error
    response = runner(
        load_json(args.source), args.run_dir,
        execution_id=args.execution_id, created_at=args.created_at,
    )
    _print(response)


def command_external_adapter(args: argparse.Namespace) -> None:
    result = run_external_adapter(args.case_directory, args.run_dir)
    _print(result)


def command_realize(args: argparse.Namespace) -> None:
    realization = RuntimeAPI().realize(args.case_directory, args.run_dir)
    _print(
        {
            "status": "PASS",
            "stage": "realization",
            "source_id": realization.source_id,
            "eligibility": realization.eligibility,
            "canonical_compilable": realization.canonical_compilable,
            "candidate": str(realization.candidate_path),
            "run_receipt": str(realization.run_receipt_path),
        }
    )


def command_report(args: argparse.Namespace) -> None:
    runtime = RuntimeAPI()
    realization = runtime.load_realization(args.realization_run)
    report = runtime.report(
        realization,
        args.out_dir,
        compiler_profile_path=args.compiler_profile,
        assembly_profile_path=args.assembly_profile,
    )
    _print(
        {
            "status": "PASS",
            "stage": "report",
            "report_id": report.report_id,
            "report": str(report.artifact_path),
            "validation_receipt": str(report.validation_receipt_path),
        }
    )


def _report_handle(report_path: Path, receipt_path: Path) -> Report:
    report = load_json(report_path)
    return Report(
        report_id=report["report_id"],
        artifact_path=report_path.resolve(),
        validation_receipt_path=receipt_path.resolve(),
    )


def command_compare(args: argparse.Namespace) -> None:
    reference = _report_handle(args.reference_report, args.reference_receipt)
    target = _report_handle(args.target_report, args.target_receipt)
    comparison = RuntimeAPI().compare(
        reference,
        target,
        alignment=args.alignment,
        profile=args.comparison_profile,
        out_dir=args.out_dir,
    )
    _print(
        {
            "status": "PASS",
            "comparison_id": comparison.audit_id,
            "audit": str(comparison.artifact_path),
            "validation_receipt": str(comparison.validation_receipt_path),
        }
    )


def command_interpret(args: argparse.Namespace) -> None:
    audit = load_json(args.audit)
    comparison = Comparison(
        audit_id=audit["audit_id"],
        artifact_path=args.audit.resolve(),
        validation_receipt_path=args.receipt.resolve(),
    )
    interpretation, candidates = RuntimeAPI().interpret(
        comparison,
        args.context,
        args.policy,
        args.out_dir,
    )
    _print(
        {
            "status": "PASS",
            "interpretation_id": interpretation.action_record_id,
            "action": str(interpretation.artifact_path),
            "validation_receipt": str(interpretation.validation_receipt_path),
            "candidate_actions": [
                {"action_id": item.action_id, "disposition": item.disposition}
                for item in candidates
            ],
        }
    )


def command_full_pipeline(args: argparse.Namespace) -> None:
    result = RuntimeAPI().full_pipeline(
        args.reference_case,
        args.target_case,
        alignment=args.alignment,
        comparison_profile=args.comparison_profile,
        action_context=args.context,
        policy_profile=args.policy,
        run_dir=args.run_dir,
    )
    realizations = result["realizations"]
    reports = result["reports"]
    comparison = result["comparison"]
    interpretation = result["interpretation"]
    _print(
        {
            "status": "PASS",
            "realizations": [
                {
                    "source_id": item.source_id,
                    "candidate": str(item.candidate_path),
                    "run_receipt": str(item.run_receipt_path),
                }
                for item in realizations
            ],
            "reports": [
                {
                    "report_id": item.report_id,
                    "report": str(item.artifact_path),
                    "validation_receipt": str(item.validation_receipt_path),
                }
                for item in reports
            ],
            "comparison": {
                "audit_id": comparison.audit_id,
                "audit": str(comparison.artifact_path),
                "validation_receipt": str(comparison.validation_receipt_path),
            },
            "interpretation": {
                "action_record_id": interpretation.action_record_id,
                "action": str(interpretation.artifact_path),
                "validation_receipt": str(interpretation.validation_receipt_path),
            },
            "candidate_actions": [
                {"action_id": item.action_id, "disposition": item.disposition}
                for item in result["candidates"]
            ],
        }
    )


def command_explain_run(args: argparse.Namespace) -> None:
    _print(explain_run(args.run_id))


def command_init_adapter(args: argparse.Namespace) -> None:
    destination = init_adapter(args.domain, args.out_dir)
    _print({"status": "PASS", "scaffold": str(destination), "runnable": False})


def command_validate(args: argparse.Namespace) -> None:
    response = load_json(args.response)
    validators = {
        "rank_collapse": validate_run_response,
        "positive_word_support": validate_positive_word_response,
    }
    try:
        validator = validators[response.get("carrier_kind")]
    except KeyError as error:
        raise SystemExit(
            f"unsupported response carrier: {response.get('carrier_kind')!r}"
        ) from error
    certificate = validator(args.response)
    _print(certificate)


def command_validate_promotion(args: argparse.Namespace) -> None:
    response = load_json(args.response)
    validators = {
        "rank_collapse": validate_promotion_package,
        "positive_word_support": validate_positive_word_promotion,
    }
    try:
        validator = validators[response.get("carrier_kind")]
    except KeyError as error:
        raise SystemExit(
            f"unsupported response carrier: {response.get('carrier_kind')!r}"
        ) from error
    package = validator(args.package, args.response)
    _print({"status": "PASS", "package_id": package["package_id"]})


def command_compile(args: argparse.Namespace) -> None:
    output = compile_documents(
        load_json(args.manifest),
        load_json(args.ir),
        load_json(args.profile),
        repository_root=PROJECT_ROOT,
        verify_artifacts=True,
    )
    write_json(args.out, output)
    _print({"status": "PASS", "compiler_output": str(args.out), "items": len(output["items"])})


def _snapshot_reference(
    source_path: Path,
    *,
    output_directory: Path,
    artifact_id: str,
    role: str,
) -> dict[str, object]:
    store = ArtifactStore(output_directory, PROJECT_ROOT)
    stored = store.put_bytes(
        source_path.read_bytes(),
        artifact_id=artifact_id,
        media_type="text/x-python",
        role=role,
        schema_version=None,
        suffix=".py",
    )
    return {"uri": stored["uri"], "digest": stored["digest"]}


def command_assemble_sofrs(args: argparse.Namespace) -> None:
    implementation = _snapshot_reference(
        Path(assembly_implementation.__file__).resolve(),
        output_directory=args.out.parent,
        artifact_id="artifact.sofrs-assembly-implementation",
        role="assembly_implementation",
    )
    report = assemble_report(
        args.manifest,
        args.ir,
        args.compiler_profile,
        args.compiler_output,
        args.assembly_profile,
        assembly_implementation=implementation,
        presentation=load_json(args.presentation),
        repository_root=PROJECT_ROOT,
        verify_artifacts=True,
    )
    write_json(args.out, report)
    _print(
        {
            "status": "PASS",
            "report": str(args.out),
            "normative_items": len(report["item_bindings"]),
        }
    )


def command_validate_sofrs(args: argparse.Namespace) -> None:
    report = validate_report(args.report, repository_root=PROJECT_ROOT)
    result: dict[str, object] = {
        "status": "PASS",
        "report_id": report["report_id"],
    }
    if args.receipt:
        validator = _snapshot_reference(
            Path(validation_implementation.__file__).resolve(),
            output_directory=args.receipt.parent,
            artifact_id="artifact.sofrs-validator-implementation",
            role="validator_implementation",
        )
        validator_path = PROJECT_ROOT / validator["uri"]
        receipt_contract = _snapshot_reference(
            Path(validation_implementation.RECEIPT_SCHEMA).resolve(),
            output_directory=args.receipt.parent,
            artifact_id="artifact.sofrs-validation-receipt-contract",
            role="validation_receipt_contract",
        )
        receipt = build_validation_receipt(
            args.report,
            repository_root=PROJECT_ROOT,
            validator_implementation_path=validator_path,
            receipt_contract=receipt_contract,
        )
        write_json(args.receipt, receipt)
        result["receipt"] = str(args.receipt)
    _print(result)


def command_validate_sofrs_receipt(args: argparse.Namespace) -> None:
    receipt = validate_receipt(args.receipt, repository_root=PROJECT_ROOT)
    _print({"status": "PASS", "receipt_id": receipt["receipt_id"]})


def command_validate_sofaudit(args: argparse.Namespace) -> None:
    audit = validate_audit(args.audit, repository_root=PROJECT_ROOT)
    _print({"status": "PASS", "audit_id": audit["audit_id"]})


def command_validate_sofaction(args: argparse.Namespace) -> None:
    action = validate_action(args.action, repository_root=args.repository_root)
    _print({"status": "PASS", "action_record_id": action["action_record_id"]})


def command_inspect(args: argparse.Namespace) -> None:
    output = load_json(args.compiler_output)
    markdown = compiler_output_markdown(output)
    if args.out:
        Path(args.out).write_text(markdown, encoding="utf-8")
    else:
        print(markdown, end="")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sof")
    subparsers = parser.add_subparsers(required=True)

    source = subparsers.add_parser("validate-source")
    source.add_argument("source", type=Path)
    source.set_defaults(func=command_validate_source)

    admit = subparsers.add_parser("admit")
    admit.add_argument("source", type=Path)
    admit.add_argument("--out", type=Path, required=True)
    admit.set_defaults(func=command_admit)

    run = subparsers.add_parser("run")
    run.add_argument("carrier")
    run.add_argument("source", type=Path)
    run.add_argument("--run-dir", type=Path, required=True)
    run.add_argument("--execution-id")
    run.add_argument("--created-at")
    run.set_defaults(func=command_run)

    realize = subparsers.add_parser(
        "realize",
        help="run a domain ExpertAdapter and stop at a validated realization",
    )
    realize.add_argument("case_directory", type=Path)
    realize.add_argument("--run-dir", type=Path, required=True)
    realize.set_defaults(func=command_realize)

    report = subparsers.add_parser(
        "report",
        help="compile a canonical-eligible realization into a SOFRS report",
    )
    report.add_argument("realization_run", type=Path)
    report.add_argument("--out-dir", type=Path)
    report.add_argument("--compiler-profile", type=Path)
    report.add_argument("--assembly-profile", type=Path)
    report.set_defaults(func=command_report)

    external = subparsers.add_parser(
        "external-adapter",
        help="reference convenience: realization plus canonical SOFRS report",
    )
    external.add_argument("case_directory", type=Path)
    external.add_argument("--run-dir", type=Path, required=True)
    external.set_defaults(func=command_external_adapter)

    compare = subparsers.add_parser(
        "compare",
        help="compare two validated SOFRS reports into a bounded SOFAUDIT",
    )
    compare.add_argument("reference_report", type=Path)
    compare.add_argument("reference_receipt", type=Path)
    compare.add_argument("target_report", type=Path)
    compare.add_argument("target_receipt", type=Path)
    compare.add_argument("--alignment", type=Path, required=True)
    compare.add_argument("--comparison-profile", type=Path, required=True)
    compare.add_argument("--out-dir", type=Path, required=True)
    compare.set_defaults(func=command_compare)

    interpret = subparsers.add_parser(
        "interpret",
        help="interpret a validated SOFAUDIT into a bounded candidate set",
    )
    interpret.add_argument("audit", type=Path)
    interpret.add_argument("receipt", type=Path)
    interpret.add_argument("context", type=Path)
    interpret.add_argument("policy", type=Path)
    interpret.add_argument("--out-dir", type=Path, required=True)
    interpret.set_defaults(func=command_interpret)

    full_pipeline = subparsers.add_parser(
        "full-pipeline",
        help="run two external adapters through SOFRS, SOFAUDIT, and SOFaction",
    )
    full_pipeline.add_argument("reference_case", type=Path)
    full_pipeline.add_argument("target_case", type=Path)
    full_pipeline.add_argument("context", type=Path)
    full_pipeline.add_argument("policy", type=Path)
    full_pipeline.add_argument("--alignment", type=Path, required=True)
    full_pipeline.add_argument("--comparison-profile", type=Path, required=True)
    full_pipeline.add_argument("--run-dir", type=Path, required=True)
    full_pipeline.set_defaults(func=command_full_pipeline)

    explain = subparsers.add_parser(
        "explain",
        help="show a structured, source-addressed explanation",
    )
    explain_subparsers = explain.add_subparsers(required=True)
    explain_run = explain_subparsers.add_parser(
        "run",
        help="explain a Level 1-3 run directory",
    )
    explain_run.add_argument("run_id", type=Path)
    explain_run.set_defaults(func=command_explain_run)

    init = subparsers.add_parser(
        "init-adapter",
        help="create a non-runnable ExpertAdapter scaffold",
    )
    init.add_argument("--domain", required=True)
    init.add_argument("--out-dir", type=Path, default=Path.cwd())
    init.set_defaults(func=command_init_adapter)

    validate = subparsers.add_parser("validate")
    validate.add_argument("response", type=Path)
    validate.set_defaults(func=command_validate)

    validate_promotion = subparsers.add_parser("validate-promotion")
    validate_promotion.add_argument("package", type=Path)
    validate_promotion.add_argument("response", type=Path)
    validate_promotion.set_defaults(func=command_validate_promotion)

    compile_parser = subparsers.add_parser("compile")
    compile_parser.add_argument("manifest", type=Path)
    compile_parser.add_argument("ir", type=Path)
    compile_parser.add_argument("profile", type=Path)
    compile_parser.add_argument("--out", type=Path, required=True)
    compile_parser.set_defaults(func=command_compile)

    assemble_sofrs = subparsers.add_parser("assemble-sofrs")
    assemble_sofrs.add_argument("manifest", type=Path)
    assemble_sofrs.add_argument("ir", type=Path)
    assemble_sofrs.add_argument("compiler_profile", type=Path)
    assemble_sofrs.add_argument("compiler_output", type=Path)
    assemble_sofrs.add_argument("assembly_profile", type=Path)
    assemble_sofrs.add_argument("presentation", type=Path)
    assemble_sofrs.add_argument("--out", type=Path, required=True)
    assemble_sofrs.set_defaults(func=command_assemble_sofrs)

    validate_sofrs = subparsers.add_parser("validate-sofrs")
    validate_sofrs.add_argument("report", type=Path)
    validate_sofrs.add_argument("--receipt", type=Path)
    validate_sofrs.set_defaults(func=command_validate_sofrs)

    validate_sofrs_receipt = subparsers.add_parser("validate-sofrs-receipt")
    validate_sofrs_receipt.add_argument("receipt", type=Path)
    validate_sofrs_receipt.set_defaults(func=command_validate_sofrs_receipt)

    validate_sofaudit = subparsers.add_parser("validate-sofaudit")
    validate_sofaudit.add_argument("audit", type=Path)
    validate_sofaudit.set_defaults(func=command_validate_sofaudit)

    validate_sofaction = subparsers.add_parser("validate-sofaction")
    validate_sofaction.add_argument("action", type=Path)
    validate_sofaction.add_argument("--repository-root", type=Path)
    validate_sofaction.set_defaults(func=command_validate_sofaction)

    inspect = subparsers.add_parser("inspect")
    inspect.add_argument("compiler_output", type=Path)
    inspect.add_argument("--out", type=Path)
    inspect.set_defaults(func=command_inspect)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
