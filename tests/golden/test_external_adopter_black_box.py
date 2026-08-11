from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import venv


ROOT = Path(__file__).resolve().parents[2]


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _compiler_profile() -> dict[str, object]:
    return {
        "profile_version": "1.0",
        "profile_id": "third-party.finite-state.compiler",
        "title": "Third-party compiler profile",
        "description": "An independently declared minimal compiler profile.",
        "applies_to": ["strict_sof"],
        "ir_version": "1.0",
        "modules": [{
            "id": "sof-basic",
            "title": "Third-party direct support",
            "capability_requirements": {"all_of": ["sectorization", "operator_carrier"], "any_of": [], "none_of": ["diagnostic_analogue"]},
            "object_kind_requirements": {"all_of": ["sectorization", "labelled_alphabet"], "any_of": [], "none_of": ["diagnostic_analogue"]},
            "semantic_convention_requirements": {"all_of": ["operative_alphabet", "direction_convention"], "any_of": [], "none_of": []},
            "run_policy_requirements": {"all_of": ["threshold", "norm", "numerical_tolerance"], "any_of": [], "none_of": []},
            "accepted_result_states": ["CERTIFIED", "OBSERVED"],
            "accepted_claim_statuses": ["Computational Certificate", "Computational Observation"],
            "carrier_kinds": ["sector", "operator", "operator_system"],
            "evidence_requirements": {"Theorem": "PROOF_REFERENCE", "Computational Certificate": "PASS_CERTIFICATE", "Computational Observation": "SOURCE_ARTIFACT", "Research Program": "NO_EVIDENCE_REQUIRED", "null": "NO_CLAIM"},
            "forbidden_promotion_ids": ["PATH_TO_ROUTE", "OPERATOR_SYSTEM_TO_LABELLED_WITNESS"],
            "forbidden_promotion_notes": ["A path does not establish a routed product.", "An operator system does not recover labelled generator witnesses."],
            "output_sections": ["Sectorization", "Observable Alphabet", "Direct Support"]
        }],
        "degradation_policy": {
            "unsatisfied_capability_expression": "omit_module",
            "unsatisfied_object_expression": "omit_module",
            "unsatisfied_policy_expression": "emit_unavailable",
            "not_declared_message": "The selected capability was not declared.",
            "not_applicable_message": "The selected module is not applicable.",
            "unreached_message": "The selected channel was not reached within cutoff."
        },
        "outputs": ["json_api"]
    }


def _assembly_profile() -> dict[str, object]:
    return {
        "assembly_profile_version": "2.0",
        "assembly_profile_id": "third-party.finite-state.assembly",
        "title": "Third-party assembly profile",
        "record_kind": "strict_sof",
        "compiler_profile_id": "third-party.finite-state.compiler",
        "assembly_contract_version": "2.0",
        "normative_item_policy": {
            "mapping": "typed_identity_bijection",
            "order": "compiler_output_order",
            "claim_rendering": "ir_summary_with_source_item_identity",
            "degradation_rendering": "lossless_compiler_item"
        },
        "presentation_fields": ["modules", "findings", "failure_modes", "alignment_readiness", "source_mapping", "provenance"]
    }


def _comparison_profile() -> dict[str, object]:
    return {
        "profile_id": "third-party.finite-state.comparison",
        "profile_version": "2.0",
        "audit_profile": {
            "applicable_regime": "strict_vs_strict",
            "requested_coordinate_ids": ["operator.support.summary"],
            "coordinate_registry_ref": "schemas/sofaudit/coordinate-semantics-registry-v1.0.json",
            "coordinate_families": ["operator"],
            "availability_semantics": {
                "unavailable_states": ["NOT_DECLARED", "NOT_APPLICABLE", "INCOMPARABLE", "UNRESOLVED"],
                "null_value_states": ["NOT_DECLARED", "NOT_APPLICABLE", "INCOMPARABLE", "UNRESOLVED"],
                "zero_is_unavailable": False
            },
            "comparison_semantics": {"matched_states": ["ALIGNED", "MISMATCH"], "comparison_is_pairwise": True},
            "carrier_requirements": {"strict": ["operator"], "analogue": []},
            "required_evidence_roles": [
                "reference-report",
                "target-report",
                "reference-report-validation-receipt",
                "target-report-validation-receipt",
                "audit-profile",
                "coordinate-semantics-registry",
            ]
        },
        "comparison_specification": {
            "specification_id": "third-party.finite-state.comparison",
            "normalization": {"normalization_id": "identity", "numeric_policy": "exact", "equality_tolerance": 0, "sentinel_policy": "state-not-infinity", "generator_policy": "report-bound-generators"},
            "metric": {"metric_id": "absolute-difference", "domain": "integer", "unit_policy": "unitless", "missing_value_policy": "incomparable", "zero_denominator_policy": "not-applicable"},
            "depth_semantics": {"carrier": "not-applicable", "mode": "not-applicable", "reference_cutoff": None, "target_cutoff": None, "unreached_policy": "incomparable"},
            "thresholds": {"threshold_id": "not-applicable", "value": None, "source": "not-applicable"},
            "parameter_synchronization": {"kind": "identity", "map_artifact_id": None, "interpolation_method": "not-applicable", "extrapolation_forbidden": True},
            "aggregation": {"kind": "coordinatewise", "scalarization": "none", "weights_artifact_id": None, "weight_declaration": None}
        }
    }


def _adapter_source() -> str:
    return '''
from sof_runtime.sdk import ExpertAdapter, SourceBundle, RealizationCandidate, CapabilityDeclaration

class ThirdPartyAdapter:
    def describe(self) -> CapabilityDeclaration:
        return {
            "declaration_version": "1.0",
            "adapter_id": "third-party.finite-state.adapter",
            "adapter_version": "1.0",
            "domain_id": "third-party-finite-state",
            "native_objects": ["finite state set", "labelled transition matrix"],
            "supported_carriers": ["sectorization", "operator_carrier", "operator_system"],
            "supported_observables": ["thresholded direct support"],
            "sectorization_origin": "third-party one-hot state basis",
            "capabilities": ["complete finite sectorization", "labelled transition operators"],
            "unsupported_capabilities": ["route filtration", "Lie/Hall depth"],
            "parameterization": {"channel_direction": "j_to_i"},
            "normalization_threshold_requirements": {"threshold_field": "source.threshold"},
            "evidence_requirements": ["source snapshot", "support recomputation"]
        }

    def inspect_source(self, source: SourceBundle) -> dict:
        if source["matrix_convention"] != "row_i_column_j_is_channel_j_to_i":
            raise ValueError("unsupported convention")
        if len(source["states"]) != 3 or len(source["operators"]) != 1:
            raise ValueError("unexpected third-party fixture")
        return {"status": "PASS", "checks": ["state labels", "matrix convention"]}

    def realize(self, source: SourceBundle, request: dict) -> RealizationCandidate:
        self.inspect_source(source)
        states = source["states"]
        pairs = []
        for row_index, row in enumerate(source["operators"][0]["matrix"]):
            for column_index, value in enumerate(row):
                if abs(float(value)) > float(source["threshold"]):
                    pairs.append([states[column_index], states[row_index]])
        return {
            "candidate_version": "1.0",
            "record_kind": "strict_sof",
            "source_id": request["source_id"],
            "space": {"dimension": len(states), "scalar_field": "complex"},
            "sectorization": {"labels": states, "origin": "third-party one-hot state basis", "complete": True},
            "operative_alphabet": {"labels": ["advance"], "semantics": "third-party transition matrix"},
            "direct_support": {"present": bool(pairs), "support_pairs": pairs, "threshold_statement": "absolute matrix entry > source.threshold"},
            "claim": {"statement": "Third-party thresholded direct support was recomputed.", "scope": "The supplied finite-state matrix.", "negative_boundary": "This does not establish route, word, Lie/Hall, causal, or domain-adequacy conclusions."}
        }

    def evidence(self) -> dict:
        return {"status": "PASS", "method": "third-party source inspection and support recomputation"}

ADAPTER: ExpertAdapter = ThirdPartyAdapter()
'''


def _policy_and_context(workspace: Path) -> None:
    policy_basis = workspace / "third_party_domain" / "policy-basis.json"
    _write(policy_basis, {"basis_id": "third-party-policy-basis", "statement": "A mismatch is a review status, not a defect."})
    digest = hashlib.sha256(policy_basis.read_bytes()).hexdigest()
    adapter_id = "third-party.finite-state.adapter"
    ref_report = f"{adapter_id}.third-party.reference.sofreport"
    target_report = f"{adapter_id}.third-party.target.sofreport"
    audit_id = f"comparison.{ref_report}.{target_report}"
    domain = workspace / "third_party_domain"
    _write(domain / "context.json", {
        "context_id": "third-party-review-context-v1", "context_contract_version": "2.0", "context_revision": "third-party-r1",
        "actor": {"actor_id": "third-party-reviewer", "role": "domain reviewer", "description": "Third-party reviewer."},
        "scope": {"scope_id": "third-party-scope", "description": "Third-party direct-support comparison.", "audit_id": audit_id},
        "objective": {"objective_id": "review-support", "statement": "Review the declared direct-support difference."},
        "constraints": [{"constraint_id": "human-review", "statement": "No candidate is an execution command.", "status": "binding"}],
        "time": {"kind": "source_snapshot", "start": None, "end": None, "timezone": None, "basis": "Source snapshots."},
        "authority": {"authority_id": "third-party-authority", "status": "declared", "description": "Declared bounded review authority.", "actor_ids": ["third-party-reviewer"], "scope_ids": ["third-party-scope"]},
        "uncertainty_conditions": ["A mismatch is not a certified defect."], "comparison_role": "diagnostic_comparison", "mismatch_direction": "reference_to_target", "contract_status": "nonconforming", "evaluator_qualification_note": "Bounded third-party fixture qualification.", "transformation_contract_refs": [], "negative_boundary": ["No authorization or action correctness is claimed."]
    })
    _write(domain / "policy.json", {
        "policy_id": "third-party-review-policy", "policy_contract_version": "2.0", "policy_revision": "third-party-r1",
        "applicability": {"regimes": ["strict_vs_strict"], "comparison_roles": ["diagnostic_comparison"]},
        "normative_basis": [{"basis_id": "third-party-difference-basis", "statement": "A mismatch is a review status, not a defect.", "source_ref": {"artifact_id": "third-party-policy-basis", "role": "policy_source", "uri": "artifact://third_party_domain/policy-basis.json", "digest": {"algorithm": "sha256", "value": digest}, "producer": "third-party-domain", "contract_version": "2.0"}}],
        "rules": [{"rule_id": "mismatch-review", "when": {"predicate_version": "1.0", "op": "coordinate_state_is", "coordinate_id": "*", "value": "MISMATCH"}, "assessment_kind": "defect_candidate", "assessment_note": "A mismatch requires bounded follow-up evidence.", "uncertainty_status": "bounded", "allowed_dispositions": ["Investigate", "RequestEvidence"], "negative_boundary": ["Not a defect or execution command."]}],
        "exceptions": [], "precedence_edges": [], "uncertainty_policy": {"version": "1.0", "unresolved_predicate": "propagate_unresolved", "unavailable_coordinate": "non_satisfying", "not_declared": "propagate_unresolved", "incomparable": "propagate_unresolved", "rule_conflict": "unresolved_disposition", "no_applicable_rule": "no_disposition"}, "candidate_families": ["Investigate", "RequestEvidence"], "selection_status": "downstream"
    })


class ExternalAdopterBlackBoxTests(unittest.TestCase):
    def test_installed_wheel_accepts_independent_public_facade_adapter(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sof-runtime-black-box-") as temporary:
            root = Path(temporary)
            wheel_dir = root / "wheel"
            subprocess.run([sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "--wheel-dir", str(wheel_dir)], cwd=ROOT, check=True, capture_output=True, text=True)
            environment_dir = root / "venv"
            venv.EnvBuilder(with_pip=True, system_site_packages=True).create(environment_dir)
            scripts = environment_dir / ("Scripts" if os.name == "nt" else "bin")
            python = scripts / ("python.exe" if os.name == "nt" else "python")
            sof = scripts / ("sof.exe" if os.name == "nt" else "sof")
            wheel = next(wheel_dir.glob("*.whl"))
            subprocess.run([str(python), "-m", "pip", "install", "--no-deps", str(wheel)], check=True, capture_output=True, text=True)

            workspace = root / "workspace"
            domain = workspace / "third_party_domain"
            reference = domain / "reference"
            target = domain / "target"
            workspace.mkdir(parents=True)
            domain.mkdir(parents=True, exist_ok=True)
            adapter = domain / "adapter.py"
            adapter.write_text(_adapter_source(), encoding="utf-8")
            forbidden = ("sof_runtime.compiler", "sof_runtime.reporting", "sof_runtime.validation", "rime-lite", "tests", "applications")
            self.assertFalse(any(token in adapter.read_text(encoding="utf-8") for token in forbidden))
            _write(domain / "compiler-profile.json", _compiler_profile())
            _write(domain / "assembly-profile.json", _assembly_profile())
            _write(domain / "comparison-profile.json", _comparison_profile())
            _write(domain / "alignment.json", {"alignment_version": "1.0", "alignment_id": "third-party.identity", "alignment_kind": "identity", "map_kind": "bijection", "reference_carrier": "report-bound-labels", "target_carrier": "report-bound-labels", "sector_pairs": [{"reference_id": x, "target_id": x, "relation": "equivalent"} for x in ("s0", "s1", "s2")], "observable_pairs": [{"reference_id": "advance", "target_id": "advance", "relation": "equivalent"}], "semantic_basis": "Third-party declared identity alignment.", "negative_boundary": ["Not cross-domain equivalence."]})
            source_base = {"states": ["s0", "s1", "s2"], "matrix_convention": "row_i_column_j_is_channel_j_to_i", "threshold": 0.0, "operators": [{"id": "advance", "matrix": [[0, 1, 0], [0, 0, 1], [0, 0, 0]]}]}
            _write(reference / "source.json", {"source_id": "third-party.reference", **source_base})
            _write(target / "source.json", {"source_id": "third-party.target", **{**source_base, "operators": [{"id": "advance", "matrix": [[0, 1, 0], [0, 0, 1], [1, 0, 0]]}]}})
            for case_dir in (reference, target):
                _write(case_dir / "case.json", {"case_id": f"third-party.{case_dir.name}.v1", "source": "source.json", "adapter": "../adapter.py", "compiler_profile": "../compiler-profile.json", "assembly_profile": "../assembly-profile.json"})
            _policy_and_context(workspace)

            env = os.environ.copy()
            env["SOF_RUNTIME_WORKSPACE"] = str(workspace)
            env.pop("PYTHONPATH", None)
            env["PATH"] = str(scripts) + os.pathsep + env.get("PATH", "")

            def run(*args: str) -> dict[str, object]:
                completed = subprocess.run([str(sof), *args], cwd=domain, env=env, capture_output=True, text=True)
                if completed.returncode != 0:
                    raise AssertionError(f"command failed: {args}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}")
                return json.loads(completed.stdout)

            realization = run("realize", "reference", "--run-dir", str(workspace / "reference-run"))
            self.assertEqual(realization["eligibility"], "canonical_compilable")
            report = run("report", str(workspace / "reference-run"), "--out-dir", str(workspace / "reference-report"))
            target_realization = run("realize", "target", "--run-dir", str(workspace / "target-run"))
            target_report = run("report", str(workspace / "target-run"), "--out-dir", str(workspace / "target-report"))
            comparison = run("compare", report["report"], report["validation_receipt"], target_report["report"], target_report["validation_receipt"], "--alignment", "alignment.json", "--comparison-profile", "comparison-profile.json", "--out-dir", str(workspace / "comparison"))
            interpretation = run("interpret", comparison["audit"], comparison["validation_receipt"], "context.json", "policy.json", "--out-dir", str(workspace / "action"))
            explanation = run("explain", "run", str(workspace))
            self.assertEqual(target_realization["eligibility"], "canonical_compilable")
            self.assertTrue(str(report["report"]).endswith("result.sofreport.json"))
            self.assertTrue(str(interpretation["action"]).endswith("result.sofaction.json"))
            self.assertEqual(explanation["comparison"]["validation"]["status"], "PASS")
            self.assertEqual(explanation["interpretation"]["validation"]["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
