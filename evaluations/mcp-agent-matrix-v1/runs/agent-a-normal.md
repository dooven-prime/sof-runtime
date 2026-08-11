# Agent A — Normal Workflow

## Raw response

I discovered exactly nine SOF Runtime MCP tools: `sof_get_contract`, `sof_realize`, `sof_report`, `sof_compare`, `sof_interpret`, `sof_validate`, `sof_get_artifact`, `sof_get_receipt`, and `sof_explain`. The explicitly retrieved `service-request.schema.json` has SHA-256 `875c53bb39f0627d2e3e8d8dd572a98480a76f610dd6515d96e0e6caba8fc407`.

The admitted workflow was:

1. Realize `case/reference` and `case/target`.
2. Check both realization results before reporting. Both returned `eligibility: canonical_compilable` and `canonical_compilable: true`.
3. Create and validate the reference and target SOFRS reports and their receipts.
4. Compare them using only `case/comparison/alignment.json` and `comparison-profile.json`; validate the SOFAUDIT and its receipt.
5. Interpret the validated audit using only `case/action/context.json` and `case/action/policy.json`; validate the SOFAction and its receipt.
6. Retrieve the final SOFAction and receipt by workspace-relative locator plus exact SHA-256, then call `sof_explain` for the final run provenance.

Ordered semantic run IDs:

- reference realization: `semrun:sha256:40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b`
- target realization: `semrun:sha256:3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e`
- reference report: `semrun:sha256:39d7a0ce61f38d02ead291108de7cab397d64deacb3a14f389f599bebf6e48be`
- target report: `semrun:sha256:c191bddc3c87eb97508d21d140c95f738ab839b8cc65f0f94c701339fe0905c0`
- comparison: `semrun:sha256:bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7`
- interpretation: `semrun:sha256:96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636`
- final explanation: `semrun:sha256:901b991f4aada9b6876d06c6222282cfa438efab843ac3864edc39121059f789`

Primary artifact chain:

- reference SOFRS: `sof-workspace://mcp-adopter-20260811a/matrix/agent-a/reference-report/report/result.sofreport.json`, SHA-256 `166b0de4269bbde554baaac4b07214436942d3a9bfcecd1c073c2ee924c33ae1`
- reference receipt: `sof-workspace://mcp-adopter-20260811a/matrix/agent-a/reference-report/report/validation-receipt.json`, SHA-256 `ef16e622b0e9e05d8f621d87792d100cdb701edd0ae169fcc4bed75cbc23b2b5`
- target SOFRS: `sof-workspace://mcp-adopter-20260811a/matrix/agent-a/target-report/report/result.sofreport.json`, SHA-256 `bc783aee6c4705ea535a4e8bfd97c696e26b4db3fe81c8d4deb76dbe93dc29dd`
- target receipt: `sof-workspace://mcp-adopter-20260811a/matrix/agent-a/target-report/report/validation-receipt.json`, SHA-256 `89c7fc342ae0cdd56f2bed4bf0b62a213f271fd87747de97f86d70cf7d14b14b`
- SOFAUDIT: `sof-workspace://mcp-adopter-20260811a/matrix/agent-a/comparison/result.sofaudit.json`, SHA-256 `40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef`
- SOFAUDIT receipt: `sof-workspace://mcp-adopter-20260811a/matrix/agent-a/comparison/validation-receipt.json`, SHA-256 `8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07`
- final SOFAction: `sof-workspace://mcp-adopter-20260811a/matrix/agent-a/interpretation/result.sofaction.json`, SHA-256 `63be634de4baf64dc85da3a3ca168933676ba94a2d4b89553da7db18bd03ca4d`
- final receipt: `sof-workspace://mcp-adopter-20260811a/matrix/agent-a/interpretation/validation-receipt.json`, SHA-256 `447c62bf1a1800318051907539bc36339974e68df2f2f2ddedf60e4f0cf34fe2`

Strongest justified claims:

- Each realization is structurally eligible for canonical compilation; this does not establish adapter scientific adequacy.
- Each SOFRS contains a protocol-bound Computational Certificate for thresholded direct support. Associative route/word and closure modules are unavailable because the required carriers, object kinds, cutoff, and saturation audit were not declared.
- The comparison is a validated alignment-relative Computational Certificate. Its sole selected coordinate, `operator.support.summary`, is a Computational Observation with state `MISMATCH`: reference support count 2, target support count 3, absolute delta 1 support pair.
- The mismatch does not establish reference truth, defect status, severity, or action. Object-level oracle status and domain semantic adequacy remain not assessed.
- The policy-relative interpretation yields exactly two bounded candidates: `investigate:operator.support.summary` (Investigate) and `requestevidence:operator.support.summary` (RequestEvidence). Both have `authorization_state: not_requested`.
- Final validation and receipt retrieval establish contract/artifact closure only. They do not establish policy correctness, feasibility, recommendation, selection, authorization, execution, outcome, or causal effect.

The provenance explanation reports both source-addressed realizations, the declared adapter and carriers, the explicit identity sector/observable alignment, the validated mismatch coordinate, and the same negative boundaries. Its returned `interpretation` field is null even though the separately retrieved and validated SOFAction exists, so I do not infer additional provenance content from that absent field.

## MCP transcript

### Call 1: sof_get_contract

Arguments:

```json
{
  "contract_name": "service-request.schema.json"
}
```

Result:

```json
{
  "contract_name": "service-request.schema.json",
  "media_type": "application/schema+json",
  "sha256": "875c53bb39f0627d2e3e8d8dd572a98480a76f610dd6515d96e0e6caba8fc407",
  "schema_id": null,
  "content": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://sof-runtime.local/contracts/service/v1.0/service-request.schema.json",
    "title": "SOF Runtime Service Request v1",
    "oneOf": [
      {
        "$ref": "#/$defs/realize"
      },
      {
        "$ref": "#/$defs/report"
      },
      {
        "$ref": "#/$defs/compare"
      },
      {
        "$ref": "#/$defs/interpret"
      },
      {
        "$ref": "#/$defs/validate"
      },
      {
        "$ref": "#/$defs/explain"
      }
    ],
    "$defs": {
      "relativePath": {
        "type": "string",
        "minLength": 1,
        "pattern": "^(?![A-Za-z]:)(?![/\\\\]).+$"
      },
      "base": {
        "type": "object",
        "required": [
          "contract_id",
          "request_id",
          "workspace_id",
          "operation",
          "input"
        ],
        "properties": {
          "contract_id": {
            "const": "sof-runtime.service-request.v1"
          },
          "request_id": {
            "type": "string",
            "pattern": "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
          },
          "workspace_id": {
            "type": "string",
            "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
          },
          "operation": {
            "enum": [
              "realize",
              "report",
              "compare",
              "interpret",
              "validate",
              "explain"
            ]
          },
          "input": {
            "type": "object"
          }
        },
        "additionalProperties": false
      },
      "realize": {
        "allOf": [
          {
            "$ref": "#/$defs/base"
          },
          {
            "properties": {
              "operation": {
                "const": "realize"
              },
              "input": {
                "type": "object",
                "required": [
                  "case_directory",
                  "run_directory"
                ],
                "properties": {
                  "case_directory": {
                    "$ref": "#/$defs/relativePath"
                  },
                  "run_directory": {
                    "$ref": "#/$defs/relativePath"
                  }
                },
                "additionalProperties": false
              }
            }
          }
        ]
      },
      "report": {
        "allOf": [
          {
            "$ref": "#/$defs/base"
          },
          {
            "properties": {
              "operation": {
                "const": "report"
              },
              "input": {
                "type": "object",
                "required": [
                  "realization_run_directory",
                  "out_directory"
                ],
                "properties": {
                  "realization_run_directory": {
                    "$ref": "#/$defs/relativePath"
                  },
                  "out_directory": {
                    "$ref": "#/$defs/relativePath"
                  },
                  "compiler_profile": {
                    "$ref": "#/$defs/relativePath"
                  },
                  "assembly_profile": {
                    "$ref": "#/$defs/relativePath"
                  }
                },
                "additionalProperties": false
              }
            }
          }
        ]
      },
      "reportRef": {
        "type": "object",
        "required": [
          "report",
          "receipt"
        ],
        "properties": {
          "report": {
            "$ref": "#/$defs/relativePath"
          },
          "receipt": {
            "$ref": "#/$defs/relativePath"
          }
        },
        "additionalProperties": false
      },
      "compare": {
        "allOf": [
          {
            "$ref": "#/$defs/base"
          },
          {
            "properties": {
              "operation": {
                "const": "compare"
              },
              "input": {
                "type": "object",
                "required": [
                  "reference",
                  "target",
                  "alignment",
                  "comparison_profile",
                  "out_directory"
                ],
                "properties": {
                  "reference": {
                    "$ref": "#/$defs/reportRef"
                  },
                  "target": {
                    "$ref": "#/$defs/reportRef"
                  },
                  "alignment": {
                    "$ref": "#/$defs/relativePath"
                  },
                  "comparison_profile": {
                    "$ref": "#/$defs/relativePath"
                  },
                  "out_directory": {
                    "$ref": "#/$defs/relativePath"
                  }
                },
                "additionalProperties": false
              }
            }
          }
        ]
      },
      "interpret": {
        "allOf": [
          {
            "$ref": "#/$defs/base"
          },
          {
            "properties": {
              "operation": {
                "const": "interpret"
              },
              "input": {
                "type": "object",
                "required": [
                  "audit",
                  "receipt",
                  "context",
                  "policy",
                  "out_directory"
                ],
                "properties": {
                  "audit": {
                    "$ref": "#/$defs/relativePath"
                  },
                  "receipt": {
                    "$ref": "#/$defs/relativePath"
                  },
                  "context": {
                    "$ref": "#/$defs/relativePath"
                  },
                  "policy": {
                    "$ref": "#/$defs/relativePath"
                  },
                  "out_directory": {
                    "$ref": "#/$defs/relativePath"
                  }
                },
                "additionalProperties": false
              }
            }
          }
        ]
      },
      "validate": {
        "allOf": [
          {
            "$ref": "#/$defs/base"
          },
          {
            "properties": {
              "operation": {
                "const": "validate"
              },
              "input": {
                "type": "object",
                "required": [
                  "validation_kind",
                  "artifact"
                ],
                "properties": {
                  "validation_kind": {
                    "enum": [
                      "sofrs",
                      "sofrs_receipt",
                      "sofaudit",
                      "sofaudit_receipt",
                      "sofaction",
                      "sofaction_receipt"
                    ]
                  },
                  "artifact": {
                    "$ref": "#/$defs/relativePath"
                  }
                },
                "additionalProperties": false
              }
            }
          }
        ]
      },
      "explain": {
        "allOf": [
          {
            "$ref": "#/$defs/base"
          },
          {
            "properties": {
              "operation": {
                "const": "explain"
              },
              "input": {
                "type": "object",
                "required": [
                  "run_directory"
                ],
                "properties": {
                  "run_directory": {
                    "$ref": "#/$defs/relativePath"
                  }
                },
                "additionalProperties": false
              }
            }
          }
        ]
      }
    }
  }
}
```

### Call 2: sof_realize

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "case_directory": "case/reference",
  "run_directory": "matrix/agent-a/reference-realization",
  "request_id": "matrix-agent-a-realize-reference"
}
```

Result:

```json
{
  "contract_id": "sof-runtime.service-response.v1",
  "request_id": "matrix-agent-a-realize-reference",
  "job_id": "job:ee75bfb186414b388ee1677df862f03b",
  "semantic_run_id": "semrun:sha256:40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b",
  "workspace_id": "mcp-adopter-20260811a",
  "operation": "realize",
  "status": "succeeded",
  "result": {
    "source_id": "finite-state.transition.reference",
    "eligibility": "canonical_compilable",
    "canonical_compilable": true
  },
  "artifacts": [
    {
      "artifact_id": "realization_candidate:3559dd19203b73a1",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/reference-realization/realization/candidate.json",
      "sha256": "3559dd19203b73a14c22b38987055f5a4f1d26c4dc1bdf2ff8b42aa1cf9573f3",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    },
    {
      "artifact_id": "adapter_declaration:7284ed390f68c27f",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/reference-realization/adapter/declaration.json",
      "sha256": "7284ed390f68c27f370bc7470ab3e351b0922150145e01e2a89c34bb158b69d4",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    },
    {
      "artifact_id": "source_inspection:2e2f51bbdcf95b71",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/reference-realization/adapter/inspection.json",
      "sha256": "2e2f51bbdcf95b71a4ebf0ef6fa7fc1a332c79c638946ab5312d8823eaac34f2",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    },
    {
      "artifact_id": "realization_evidence:383b067ca5eda48f",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/reference-realization/realization/evidence.json",
      "sha256": "383b067ca5eda48f82603d3a12fff091085e0ba99a399a8b2e99c4f7efa97158",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    },
    {
      "artifact_id": "realization_receipt:c0b29bf970c7e289",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/reference-realization/run-receipt.json",
      "sha256": "c0b29bf970c7e28930cf1b471cf51282d9314edf31fe6001fee5db4b2ad396f2",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    }
  ]
}
```

### Call 3: sof_realize

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "case_directory": "case/target",
  "run_directory": "matrix/agent-a/target-realization",
  "request_id": "matrix-agent-a-realize-target"
}
```

Result:

```json
{
  "contract_id": "sof-runtime.service-response.v1",
  "request_id": "matrix-agent-a-realize-target",
  "job_id": "job:8c3a8f1d507f4540b95d486086c486fc",
  "semantic_run_id": "semrun:sha256:3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e",
  "workspace_id": "mcp-adopter-20260811a",
  "operation": "realize",
  "status": "succeeded",
  "result": {
    "source_id": "finite-state.transition.target",
    "eligibility": "canonical_compilable",
    "canonical_compilable": true
  },
  "artifacts": [
    {
      "artifact_id": "realization_candidate:c120c334d96cf906",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/target-realization/realization/candidate.json",
      "sha256": "c120c334d96cf906c3278c9132984345e9da4e87b2a44c863818f99916129907",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    },
    {
      "artifact_id": "adapter_declaration:7284ed390f68c27f",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/target-realization/adapter/declaration.json",
      "sha256": "7284ed390f68c27f370bc7470ab3e351b0922150145e01e2a89c34bb158b69d4",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    },
    {
      "artifact_id": "source_inspection:2e2f51bbdcf95b71",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/target-realization/adapter/inspection.json",
      "sha256": "2e2f51bbdcf95b71a4ebf0ef6fa7fc1a332c79c638946ab5312d8823eaac34f2",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    },
    {
      "artifact_id": "realization_evidence:383b067ca5eda48f",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/target-realization/realization/evidence.json",
      "sha256": "383b067ca5eda48f82603d3a12fff091085e0ba99a399a8b2e99c4f7efa97158",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    },
    {
      "artifact_id": "realization_receipt:b504012ded11912e",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/target-realization/run-receipt.json",
      "sha256": "b504012ded11912e31867562ef568eb967d00edbd897d4b8a38900debd949389",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    }
  ]
}
```

### Call 4: sof_report

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "realization_run_directory": "matrix/agent-a/reference-realization",
  "out_directory": "matrix/agent-a/reference-report",
  "request_id": "matrix-agent-a-report-reference"
}
```

Result:

```json
{
  "contract_id": "sof-runtime.service-response.v1",
  "request_id": "matrix-agent-a-report-reference",
  "job_id": "job:0c815bf2eb214ae18bc3d35c414d3fd2",
  "semantic_run_id": "semrun:sha256:39d7a0ce61f38d02ead291108de7cab397d64deacb3a14f389f599bebf6e48be",
  "workspace_id": "mcp-adopter-20260811a",
  "operation": "report",
  "status": "succeeded",
  "result": {
    "report_id": "example.finite-state-adapter.finite-state.transition.reference.sofreport"
  },
  "artifacts": [
    {
      "artifact_id": "sofrs_report:166b0de4269bbde5",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/reference-report/report/result.sofreport.json",
      "sha256": "166b0de4269bbde554baaac4b07214436942d3a9bfcecd1c073c2ee924c33ae1",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    },
    {
      "artifact_id": "sofrs_validation_receipt:ef16e622b0e9e05d",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/reference-report/report/validation-receipt.json",
      "sha256": "ef16e622b0e9e05d8f621d87792d100cdb701edd0ae169fcc4bed75cbc23b2b5",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    }
  ]
}
```

### Call 5: sof_report

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "realization_run_directory": "matrix/agent-a/target-realization",
  "out_directory": "matrix/agent-a/target-report",
  "request_id": "matrix-agent-a-report-target"
}
```

Result:

```json
{
  "contract_id": "sof-runtime.service-response.v1",
  "request_id": "matrix-agent-a-report-target",
  "job_id": "job:f3e92d52fd1d49daa3de750bd1d6a70c",
  "semantic_run_id": "semrun:sha256:c191bddc3c87eb97508d21d140c95f738ab839b8cc65f0f94c701339fe0905c0",
  "workspace_id": "mcp-adopter-20260811a",
  "operation": "report",
  "status": "succeeded",
  "result": {
    "report_id": "example.finite-state-adapter.finite-state.transition.target.sofreport"
  },
  "artifacts": [
    {
      "artifact_id": "sofrs_report:bc783aee6c4705ea",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/target-report/report/result.sofreport.json",
      "sha256": "bc783aee6c4705ea535a4e8bfd97c696e26b4db3fe81c8d4deb76dbe93dc29dd",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    },
    {
      "artifact_id": "sofrs_validation_receipt:89c7fc342ae0cdd5",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/target-report/report/validation-receipt.json",
      "sha256": "89c7fc342ae0cdd56f2bed4bf0b62a213f271fd87747de97f86d70cf7d14b14b",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    }
  ]
}
```

### Call 6: sof_validate

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "validation_kind": "sofrs",
  "artifact": "matrix/agent-a/reference-report/report/result.sofreport.json",
  "request_id": "matrix-agent-a-validate-reference-report"
}
```

Result:

```json
{
  "contract_id": "sof-runtime.service-response.v1",
  "request_id": "matrix-agent-a-validate-reference-report",
  "job_id": "job:51298fd70c834519a5c65c9e500c025b",
  "semantic_run_id": "semrun:sha256:dcfbcf8aff422d8adcee7f5c1d5d8076c14278ca2bd2bf0eacf99c3e7f17c9c0",
  "workspace_id": "mcp-adopter-20260811a",
  "operation": "validate",
  "status": "succeeded",
  "result": {
    "validation_kind": "sofrs",
    "validator_result": {
      "alignment_readiness": {
        "adapter": {
          "id": "example.finite-state-adapter",
          "version": "1.0"
        },
        "assembly_profile_id": "sof-runtime.strict-conformance.assembly.v2",
        "carrier_kinds": [
          "operator",
          "operator_system",
          "sector"
        ],
        "comparison_keys": [
          "report:example.finite-state-adapter.finite-state.transition.reference.sofreport",
          "system:external-adapter-reference:-finite-state-transition-system",
          "record-kind:strict_sof"
        ],
        "compiler_profile_id": "sof-runtime.strict-conformance",
        "observable_metadata": {
          "labels": [
            "advance"
          ],
          "provenance": "example.finite-state-adapter",
          "ranks_or_dimensions": [],
          "semantics": "labelled operative alphabet",
          "status": "PRESENT"
        },
        "run_policies": [
          {
            "id": "run.threshold",
            "kind": "threshold"
          },
          {
            "id": "run.norm",
            "kind": "norm"
          },
          {
            "id": "run.tolerance",
            "kind": "numerical_tolerance"
          }
        ],
        "sector_metadata": {
          "labels": [
            "idle",
            "busy",
            "done"
          ],
          "provenance": "example.finite-state-adapter",
          "ranks_or_dimensions": [],
          "semantics": "one-hot basis of the declared finite state set",
          "status": "PRESENT"
        },
        "semantic_conventions": [
          {
            "id": "semantic.alphabet",
            "kind": "operative_alphabet"
          },
          {
            "id": "semantic.word",
            "kind": "word_convention"
          },
          {
            "id": "semantic.projector-letter",
            "kind": "projector_letter_policy"
          },
          {
            "id": "semantic.direction",
            "kind": "direction_convention"
          },
          {
            "id": "semantic.depth-indexing",
            "kind": "depth_indexing"
          }
        ],
        "source_artifact_digests": [
          {
            "digest": {
              "algorithm": "sha256",
              "value": "3d6e6716653c74a2e4a6a8e22c7b99b8accdf6df2c39ac79aceae0556df5a20d"
            },
            "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/source/input.json"
          },
          {
            "digest": {
              "algorithm": "sha256",
              "value": "f2b967456920e50914e0bd4d61c58758974122fdafda4776ebf55ae0a3327286"
            },
            "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/implementation.py"
          },
          {
            "digest": {
              "algorithm": "sha256",
              "value": "7284ed390f68c27f370bc7470ab3e351b0922150145e01e2a89c34bb158b69d4"
            },
            "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/declaration.json"
          },
          {
            "digest": {
              "algorithm": "sha256",
              "value": "2e2f51bbdcf95b71a4ebf0ef6fa7fc1a332c79c638946ab5312d8823eaac34f2"
            },
            "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/inspection.json"
          },
          {
            "digest": {
              "algorithm": "sha256",
              "value": "3559dd19203b73a14c22b38987055f5a4f1d26c4dc1bdf2ff8b42aa1cf9573f3"
            },
            "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/realization/candidate.json"
          },
          {
            "digest": {
              "algorithm": "sha256",
              "value": "383b067ca5eda48f82603d3a12fff091085e0ba99a399a8b2e99c4f7efa97158"
            },
            "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/realization/evidence.json"
          }
        ]
      },
      "assembly_contract": {
        "assembly_profile": {
          "digest": {
            "algorithm": "sha256",
            "value": "a503e80f6361ccafb15654f604727f310ca631b395ee787dd13e9574ad0ec608"
          },
          "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/inputs/case-bundle/case/profiles/assembly/strict-conformance-v2.0.json"
        },
        "assembly_profile_id": "sof-runtime.strict-conformance.assembly.v2",
        "implementation": {
          "digest": {
            "algorithm": "sha256",
            "value": "21137aced870455a6d65b7ec8910d72959002393d556489a2d6fbe01a72f3186"
          },
          "uri": "runs/.sof-service-cache/39/39d7a0ce61f38d02ead291108de7cab397d64deacb3a14f389f599bebf6e48be/report/compiler/assembly-implementation.py"
        },
        "schema_id": "sofrs-assembly-v2.0",
        "version": "2.0"
      },
      "claims": [
        {
          "carrier_kinds": [
            "operator",
            "sector"
          ],
          "certificate_class": "protocol_conformance",
          "claim_id": "claim.direct-support",
          "claim_status": "Computational Certificate",
          "claim_target": "representation_interface",
          "classification_source": "independent_validator",
          "external_basis_refs": [
            "basis.source.identity",
            "basis.structure.level"
          ],
          "external_constraint_ids": [
            "source-snapshot-pinned",
            "realization-structure-validation"
          ],
          "negative_boundary": "This claim does not establish route, word, Lie/Hall, causal, or domain-adequacy conclusions.",
          "report_item_id": "report.claim-item.0000",
          "result_state": "CERTIFIED",
          "scope": "The finite state basis and the supplied transition matrices.",
          "source_output_item_id": "compiler.item.0000",
          "statement": "The external adapter's declared transition family has certified thresholded direct support."
        }
      ],
      "compiler_contracts": {
        "capability_manifest": {
          "digest": {
            "algorithm": "sha256",
            "value": "38bf184162fdcccbc9f696687f8cab263a576f4d33c00abc2d0f8e6e08744515"
          },
          "uri": "runs/.sof-service-cache/39/39d7a0ce61f38d02ead291108de7cab397d64deacb3a14f389f599bebf6e48be/report/compiler/manifest.json"
        },
        "compiler_output": {
          "digest": {
            "algorithm": "sha256",
            "value": "c4cde3a3ece28e40aa14cdade4d30711554f5726eb8dff170d315d69e4668a0d"
          },
          "uri": "runs/.sof-service-cache/39/39d7a0ce61f38d02ead291108de7cab397d64deacb3a14f389f599bebf6e48be/report/compiler/compiler-output.json"
        },
        "compiler_profile": {
          "digest": {
            "algorithm": "sha256",
            "value": "ab0406daf52b99a712a903ae8dbcb49a75137b1e1953a96c65764512a302fdaa"
          },
          "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/inputs/case-bundle/case/profiles/compiler/strict-conformance-v1.0.json"
        },
        "typed_sof_ir": {
          "digest": {
            "algorithm": "sha256",
            "value": "b49b65a631b72ef618efd97d5dd2a61eb0fdd09cbbfa447ec8a5588237485986"
          },
          "uri": "runs/.sof-service-cache/39/39d7a0ce61f38d02ead291108de7cab397d64deacb3a14f389f599bebf6e48be/report/compiler/typed-ir.json"
        }
      },
      "compiler_output_binding": {
        "artifact": {
          "digest": {
            "algorithm": "sha256",
            "value": "c4cde3a3ece28e40aa14cdade4d30711554f5726eb8dff170d315d69e4668a0d"
          },
          "uri": "runs/.sof-service-cache/39/39d7a0ce61f38d02ead291108de7cab397d64deacb3a14f389f599bebf6e48be/report/compiler/compiler-output.json"
        },
        "artifact_id": "artifact.compiler-output",
        "compiler_id": "sofcompiler.compile_v1",
        "compiler_output_version": "1.0",
        "compiler_profile_id": "sof-runtime.strict-conformance"
      },
      "degradation_items": [
        {
          "action": "omit_module",
          "details": [
            "no any_of member present: route_carrier, word_carrier"
          ],
          "module_id": "associative",
          "reason_kind": "unsatisfied_capability_requirements",
          "report_item_id": "report.degradation-item.0001",
          "source_output_item_id": "compiler.item.0001"
        },
        {
          "action": "omit_module",
          "details": [
            "no any_of member present: route_space, word_space, depth_field"
          ],
          "module_id": "associative",
          "reason_kind": "unsatisfied_object_kind_requirements",
          "report_item_id": "report.degradation-item.0002",
          "source_output_item_id": "compiler.item.0002"
        },
        {
          "action": "emit_unavailable",
          "details": [
            "missing all_of: cutoff"
          ],
          "module_id": "associative",
          "reason_kind": "unsatisfied_run_policy_requirements",
          "report_item_id": "report.degradation-item.0003",
          "source_output_item_id": "compiler.item.0003"
        },
        {
          "action": "omit_module",
          "details": [
            "no any_of member present: positive_associative_closure, observable_star_closure, sector_enriched_star_closure"
          ],
          "module_id": "closure",
          "reason_kind": "unsatisfied_capability_requirements",
          "report_item_id": "report.degradation-item.0004",
          "source_output_item_id": "compiler.item.0004"
        },
        {
          "action": "omit_module",
          "details": [
            "no any_of member present: associative_closure, star_closure"
          ],
          "module_id": "closure",
          "reason_kind": "unsatisfied_object_kind_requirements",
          "report_item_id": "report.degradation-item.0005",
          "source_output_item_id": "compiler.item.0005"
        },
        {
          "action": "emit_unavailable",
          "details": [
            "missing all_of: saturation_audit"
          ],
          "module_id": "closure",
          "reason_kind": "unsatisfied_run_policy_requirements",
          "report_item_id": "report.degradation-item.0006",
          "source_output_item_id": "compiler.item.0006"
        }
      ],
      "external_basis_registry": {
        "basis_status": "PARTIAL",
        "constraints": [
          {
            "basis_id": "basis.source.identity",
            "constraint_id": "source-snapshot-pinned",
            "evidence_artifacts": [
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "3d6e6716653c74a2e4a6a8e22c7b99b8accdf6df2c39ac79aceae0556df5a20d"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/source/input.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "f2b967456920e50914e0bd4d61c58758974122fdafda4776ebf55ae0a3327286"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/implementation.py"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "7284ed390f68c27f370bc7470ab3e351b0922150145e01e2a89c34bb158b69d4"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/declaration.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "2e2f51bbdcf95b71a4ebf0ef6fa7fc1a332c79c638946ab5312d8823eaac34f2"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/inspection.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "3559dd19203b73a14c22b38987055f5a4f1d26c4dc1bdf2ff8b42aa1cf9573f3"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/realization/candidate.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "383b067ca5eda48f82603d3a12fff091085e0ba99a399a8b2e99c4f7efa97158"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/realization/evidence.json"
              }
            ],
            "statement": "Declared external-adapter workflow condition.",
            "status": "SATISFIED"
          },
          {
            "basis_id": "basis.object.level",
            "constraint_id": "object-level-recomputation",
            "evidence_artifacts": [],
            "statement": "Declared external-adapter workflow condition.",
            "status": "NOT_ASSESSED"
          },
          {
            "basis_id": "basis.structure.level",
            "constraint_id": "realization-structure-validation",
            "evidence_artifacts": [
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "3d6e6716653c74a2e4a6a8e22c7b99b8accdf6df2c39ac79aceae0556df5a20d"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/source/input.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "f2b967456920e50914e0bd4d61c58758974122fdafda4776ebf55ae0a3327286"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/implementation.py"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "7284ed390f68c27f370bc7470ab3e351b0922150145e01e2a89c34bb158b69d4"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/declaration.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "2e2f51bbdcf95b71a4ebf0ef6fa7fc1a332c79c638946ab5312d8823eaac34f2"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/inspection.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "3559dd19203b73a14c22b38987055f5a4f1d26c4dc1bdf2ff8b42aa1cf9573f3"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/realization/candidate.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "383b067ca5eda48f82603d3a12fff091085e0ba99a399a8b2e99c4f7efa97158"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/realization/evidence.json"
              }
            ],
            "statement": "Declared external-adapter workflow condition.",
            "status": "SATISFIED"
          },
          {
            "basis_id": "basis.semantic.adequacy",
            "constraint_id": "domain-semantic-adequacy",
            "evidence_artifacts": [],
            "statement": "Declared external-adapter workflow condition.",
            "status": "NOT_ASSESSED"
          }
        ],
        "negative_boundary": [
          "The runtime validates the adapter contract and report closure; it does not become the domain authority."
        ],
        "packages": [
          {
            "basis_id": "basis.source.identity",
            "constraint_ids": [
              "source-snapshot-pinned"
            ],
            "evidence_artifacts": [
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "3d6e6716653c74a2e4a6a8e22c7b99b8accdf6df2c39ac79aceae0556df5a20d"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/source/input.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "f2b967456920e50914e0bd4d61c58758974122fdafda4776ebf55ae0a3327286"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/implementation.py"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "7284ed390f68c27f370bc7470ab3e351b0922150145e01e2a89c34bb158b69d4"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/declaration.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "2e2f51bbdcf95b71a4ebf0ef6fa7fc1a332c79c638946ab5312d8823eaac34f2"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/inspection.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "3559dd19203b73a14c22b38987055f5a4f1d26c4dc1bdf2ff8b42aa1cf9573f3"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/realization/candidate.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "383b067ca5eda48f82603d3a12fff091085e0ba99a399a8b2e99c4f7efa97158"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/realization/evidence.json"
              }
            ],
            "level": "source_identity",
            "method": "external-adapter-reference-workflow",
            "negative_boundary": [
              "Protocol conformance does not establish domain adequacy."
            ],
            "scope": "Bounded external-adapter Level 1 workflow.",
            "status": "SATISFIED"
          },
          {
            "basis_id": "basis.object.level",
            "constraint_ids": [
              "object-level-recomputation"
            ],
            "evidence_artifacts": [],
            "level": "object_level",
            "method": "external-adapter-reference-workflow",
            "negative_boundary": [
              "Protocol conformance does not establish domain adequacy."
            ],
            "scope": "Bounded external-adapter Level 1 workflow.",
            "status": "NOT_ASSESSED"
          },
          {
            "basis_id": "basis.structure.level",
            "constraint_ids": [
              "realization-structure-validation"
            ],
            "evidence_artifacts": [
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "3d6e6716653c74a2e4a6a8e22c7b99b8accdf6df2c39ac79aceae0556df5a20d"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/source/input.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "f2b967456920e50914e0bd4d61c58758974122fdafda4776ebf55ae0a3327286"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/implementation.py"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "7284ed390f68c27f370bc7470ab3e351b0922150145e01e2a89c34bb158b69d4"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/declaration.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "2e2f51bbdcf95b71a4ebf0ef6fa7fc1a332c79c638946ab5312d8823eaac34f2"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/inspection.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "3559dd19203b73a14c22b38987055f5a4f1d26c4dc1bdf2ff8b42aa1cf9573f3"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/realization/candidate.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "383b067ca5eda48f82603d3a12fff091085e0ba99a399a8b2e99c4f7efa97158"
                },
                "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/realization/evidence.json"
              }
            ],
            "level": "structure_level",
            "method": "external-adapter-reference-workflow",
            "negative_boundary": [
              "Protocol conformance does not establish domain adequacy."
            ],
            "scope": "Bounded external-adapter Level 1 workflow.",
            "status": "SATISFIED"
          },
          {
            "basis_id": "basis.semantic.adequacy",
            "constraint_ids": [
              "domain-semantic-adequacy"
            ],
            "evidence_artifacts": [],
            "level": "semantic_adequacy",
            "method": "external-adapter-reference-workflow",
            "negative_boundary": [
              "Protocol conformance does not establish domain adequacy."
            ],
            "scope": "Bounded external-adapter Level 1 workflow.",
            "status": "NOT_ASSESSED"
          }
        ],
        "registry_version": "1.0"
      },
      "failure_modes": [
        "This Level 1 workflow does not compare two reports or interpret a SOFAUDIT.",
        "Direct support is certified only under the adapter-declared source and threshold boundary."
      ],
      "findings": [
        {
          "finding_id": "finding.direct-support",
          "kind": "boolean_support",
          "result_state": "CERTIFIED",
          "value": {
            "present": true,
            "support_pairs": [
              [
                "busy",
                "done"
              ],
              [
                "idle",
                "busy"
              ]
            ],
            "threshold_statement": "absolute matrix entry > 1e-12"
          }
        }
      ],
      "item_bindings": [
        {
          "compiler_output_item_id": "compiler.item.0000",
          "item_kind": "claim",
          "rendering_status": "rendered",
          "report_item_id": "report.claim-item.0000"
        },
        {
          "compiler_output_item_id": "compiler.item.0001",
          "item_kind": "degradation",
          "rendering_status": "rendered",
          "report_item_id": "report.degradation-item.0001"
        },
        {
          "compiler_output_item_id": "compiler.item.0002",
          "item_kind": "degradation",
          "rendering_status": "rendered",
          "report_item_id": "report.degradation-item.0002"
        },
        {
          "compiler_output_item_id": "compiler.item.0003",
          "item_kind": "degradation",
          "rendering_status": "rendered",
          "report_item_id": "report.degradation-item.0003"
        },
        {
          "compiler_output_item_id": "compiler.item.0004",
          "item_kind": "degradation",
          "rendering_status": "rendered",
          "report_item_id": "report.degradation-item.0004"
        },
        {
          "compiler_output_item_id": "compiler.item.0005",
          "item_kind": "degradation",
          "rendering_status": "rendered",
          "report_item_id": "report.degradation-item.0005"
        },
        {
          "compiler_output_item_id": "compiler.item.0006",
          "item_kind": "degradation",
          "rendering_status": "rendered",
          "report_item_id": "report.degradation-item.0006"
        }
      ],
      "modules": [
        {
          "carrier_kinds": [
            "sector",
            "operator",
            "operator_system"
          ],
          "claim_ids": [
            "claim.direct-support"
          ],
          "finding_ids": [
            "finding.direct-support"
          ],
          "module_id": "sof-basic",
          "output_sections": [
            "Sectorization",
            "Observable Alphabet",
            "Direct Support"
          ],
          "status": "ENABLED"
        },
        {
          "carrier_kinds": [
            "route",
            "word",
            "positive_associative_closure"
          ],
          "claim_ids": [],
          "finding_ids": [],
          "module_id": "associative",
          "output_sections": [
            "Routed Products",
            "Full Words",
            "First-Hit Cutoff"
          ],
          "reason": "no any_of member present: route_carrier, word_carrier; no any_of member present: route_space, word_space, depth_field; missing all_of: cutoff",
          "status": "UNAVAILABLE"
        },
        {
          "carrier_kinds": [
            "positive_associative_closure",
            "observable_star_closure",
            "sector_enriched_star_closure"
          ],
          "claim_ids": [],
          "finding_ids": [],
          "module_id": "closure",
          "output_sections": [
            "Positive Associative Closure",
            "Observable Star Closure",
            "Sector-Enriched Star Closure"
          ],
          "reason": "no any_of member present: positive_associative_closure, observable_star_closure, sector_enriched_star_closure; no any_of member present: associative_closure, star_closure; missing all_of: saturation_audit",
          "status": "UNAVAILABLE"
        }
      ],
      "provenance": {
        "adapter": {
          "digest": {
            "algorithm": "sha256",
            "value": "f2b967456920e50914e0bd4d61c58758974122fdafda4776ebf55ae0a3327286"
          },
          "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/implementation.py"
        },
        "assembly_profile_ref": {
          "digest": {
            "algorithm": "sha256",
            "value": "a503e80f6361ccafb15654f604727f310ca631b395ee787dd13e9574ad0ec608"
          },
          "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/inputs/case-bundle/case/profiles/assembly/strict-conformance-v2.0.json"
        },
        "compiler_output_ref": {
          "digest": {
            "algorithm": "sha256",
            "value": "c4cde3a3ece28e40aa14cdade4d30711554f5726eb8dff170d315d69e4668a0d"
          },
          "uri": "runs/.sof-service-cache/39/39d7a0ce61f38d02ead291108de7cab397d64deacb3a14f389f599bebf6e48be/report/compiler/compiler-output.json"
        },
        "compiler_profile_ref": {
          "digest": {
            "algorithm": "sha256",
            "value": "ab0406daf52b99a712a903ae8dbcb49a75137b1e1953a96c65764512a302fdaa"
          },
          "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/inputs/case-bundle/case/profiles/compiler/strict-conformance-v1.0.json"
        },
        "kind": "native_generation",
        "producer": {
          "digest": {
            "algorithm": "sha256",
            "value": "e4e68f1cccfbdcd91403ce273dd6dd1e30b219d3113b62790183201eee00641f"
          },
          "uri": "runs/.sof-service-cache/39/39d7a0ce61f38d02ead291108de7cab397d64deacb3a14f389f599bebf6e48be/report/compiler/workflow-implementation.py"
        },
        "source_snapshot": {
          "digest": {
            "algorithm": "sha256",
            "value": "3d6e6716653c74a2e4a6a8e22c7b99b8accdf6df2c39ac79aceae0556df5a20d"
          },
          "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/source/input.json"
        }
      },
      "record_kind": "strict_sof",
      "report_id": "example.finite-state-adapter.finite-state.transition.reference.sofreport",
      "sofrs_version": "2.0",
      "source_artifacts": [
        {
          "digest": {
            "algorithm": "sha256",
            "value": "3d6e6716653c74a2e4a6a8e22c7b99b8accdf6df2c39ac79aceae0556df5a20d"
          },
          "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/source/input.json"
        },
        {
          "digest": {
            "algorithm": "sha256",
            "value": "f2b967456920e50914e0bd4d61c58758974122fdafda4776ebf55ae0a3327286"
          },
          "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/implementation.py"
        },
        {
          "digest": {
            "algorithm": "sha256",
            "value": "7284ed390f68c27f370bc7470ab3e351b0922150145e01e2a89c34bb158b69d4"
          },
          "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/declaration.json"
        },
        {
          "digest": {
            "algorithm": "sha256",
            "value": "2e2f51bbdcf95b71a4ebf0ef6fa7fc1a332c79c638946ab5312d8823eaac34f2"
          },
          "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/inspection.json"
        },
        {
          "digest": {
            "algorithm": "sha256",
            "value": "3559dd19203b73a14c22b38987055f5a4f1d26c4dc1bdf2ff8b42aa1cf9573f3"
          },
          "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/realization/candidate.json"
        },
        {
          "digest": {
            "algorithm": "sha256",
            "value": "383b067ca5eda48f82603d3a12fff091085e0ba99a399a8b2e99c4f7efa97158"
          },
          "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/realization/evidence.json"
        }
      ],
      "source_mapping": {
        "adapter_id": "example.finite-state-adapter",
        "adapter_version": "1.0",
        "construction": "Runtime-owned Manifest/IR construction from an admitted ExpertAdapter RealizationCandidate.",
        "justification": "The adapter maps domain transition matrices to a declared sectorization and operative alphabet.",
        "limitations": [
          "The runtime does not infer omitted carriers or domain adequacy."
        ],
        "status": "adapter-derived"
      },
      "strict_reconstruction": {
        "available_requirements": [],
        "candidate_status": "not_applicable",
        "evaluator_id": "example.finite-state-adapter.source-validator",
        "evaluator_version": "1.0",
        "interpretation": "The external adapter supplied an explicit finite complex realization candidate.",
        "missing_requirements": []
      },
      "system": "External adapter reference: finite-state-transition-system"
    }
  },
  "artifacts": [
    {
      "artifact_id": "sofrs:166b0de4269bbde5",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/reference-report/report/result.sofreport.json",
      "sha256": "166b0de4269bbde554baaac4b07214436942d3a9bfcecd1c073c2ee924c33ae1",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    }
  ]
}
```

### Call 7: sof_validate

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "validation_kind": "sofrs_receipt",
  "artifact": "matrix/agent-a/reference-report/report/validation-receipt.json",
  "request_id": "matrix-agent-a-validate-reference-receipt"
}
```

Result:

```json
{
  "contract_id": "sof-runtime.service-response.v1",
  "request_id": "matrix-agent-a-validate-reference-receipt",
  "job_id": "job:6b8a4be4f9dc40beb076ec2084a9c798",
  "semantic_run_id": "semrun:sha256:e81fab79e50f695c615359ade188171f235219edc1dadfbc4aa2af964e3c1426",
  "workspace_id": "mcp-adopter-20260811a",
  "operation": "validate",
  "status": "succeeded",
  "result": {
    "validation_kind": "sofrs_receipt",
    "validator_result": {
      "artifact_closure": {
        "artifact_count": 7,
        "closure_digest": {
          "algorithm": "sha256",
          "value": "0d99c7adf7b9e47a57bd92cd6dfa71b36177c02b17306169482da3079ee5d40b"
        },
        "ordered_artifacts": [
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "166b0de4269bbde554baaac4b07214436942d3a9bfcecd1c073c2ee924c33ae1"
              },
              "uri": "runs/.sof-service-cache/39/39d7a0ce61f38d02ead291108de7cab397d64deacb3a14f389f599bebf6e48be/report/report/result.sofreport.json"
            },
            "role": "report"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "38bf184162fdcccbc9f696687f8cab263a576f4d33c00abc2d0f8e6e08744515"
              },
              "uri": "runs/.sof-service-cache/39/39d7a0ce61f38d02ead291108de7cab397d64deacb3a14f389f599bebf6e48be/report/compiler/manifest.json"
            },
            "role": "capability_manifest"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "b49b65a631b72ef618efd97d5dd2a61eb0fdd09cbbfa447ec8a5588237485986"
              },
              "uri": "runs/.sof-service-cache/39/39d7a0ce61f38d02ead291108de7cab397d64deacb3a14f389f599bebf6e48be/report/compiler/typed-ir.json"
            },
            "role": "typed_sof_ir"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "ab0406daf52b99a712a903ae8dbcb49a75137b1e1953a96c65764512a302fdaa"
              },
              "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/inputs/case-bundle/case/profiles/compiler/strict-conformance-v1.0.json"
            },
            "role": "compiler_profile"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "c4cde3a3ece28e40aa14cdade4d30711554f5726eb8dff170d315d69e4668a0d"
              },
              "uri": "runs/.sof-service-cache/39/39d7a0ce61f38d02ead291108de7cab397d64deacb3a14f389f599bebf6e48be/report/compiler/compiler-output.json"
            },
            "role": "compiler_output"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "a503e80f6361ccafb15654f604727f310ca631b395ee787dd13e9574ad0ec608"
              },
              "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/inputs/case-bundle/case/profiles/assembly/strict-conformance-v2.0.json"
            },
            "role": "assembly_profile"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "21137aced870455a6d65b7ec8910d72959002393d556489a2d6fbe01a72f3186"
              },
              "uri": "runs/.sof-service-cache/39/39d7a0ce61f38d02ead291108de7cab397d64deacb3a14f389f599bebf6e48be/report/compiler/assembly-implementation.py"
            },
            "role": "assembly_implementation"
          }
        ]
      },
      "artifact_type": "sofrs_report_validation_receipt",
      "checks": [
        {
          "check_id": "artifact-closure",
          "status": "PASS"
        },
        {
          "check_id": "claim-compatibility",
          "status": "PASS"
        },
        {
          "check_id": "claim-external-basis-binding",
          "status": "PASS"
        },
        {
          "check_id": "compiler-output-recompilation",
          "status": "PASS"
        },
        {
          "check_id": "cutoff-provenance",
          "status": "PASS"
        },
        {
          "check_id": "record-kind-boundary",
          "status": "PASS"
        },
        {
          "check_id": "report-assembly-recomputation",
          "status": "PASS"
        },
        {
          "check_id": "schema-validation",
          "status": "PASS"
        }
      ],
      "negative_boundaries": [
        "This receipt validates faithful SOFRS assembly and its bound compiler-contract closure; it does not establish adapter scientific adequacy, cross-report alignment, or downstream interpretation."
      ],
      "receipt_id": "receipt.example.finite-state-adapter.finite-state.transition.reference.sofreport.sofrs-v2",
      "receipt_version": "2.0",
      "report": {
        "artifact": {
          "digest": {
            "algorithm": "sha256",
            "value": "166b0de4269bbde554baaac4b07214436942d3a9bfcecd1c073c2ee924c33ae1"
          },
          "uri": "runs/.sof-service-cache/39/39d7a0ce61f38d02ead291108de7cab397d64deacb3a14f389f599bebf6e48be/report/report/result.sofreport.json"
        },
        "record_kind": "strict_sof",
        "report_id": "example.finite-state-adapter.finite-state.transition.reference.sofreport",
        "sofrs_version": "2.0"
      },
      "status": "PASS",
      "validator": {
        "implementation": {
          "digest": {
            "algorithm": "sha256",
            "value": "299c716b7ee398b4a5fa37928efba5d178bda071be1f8785810e536547fcd3ee"
          },
          "uri": "runs/.sof-service-cache/39/39d7a0ce61f38d02ead291108de7cab397d64deacb3a14f389f599bebf6e48be/report/compiler/report-validator.py"
        },
        "receipt_contract": {
          "digest": {
            "algorithm": "sha256",
            "value": "84254cf908ce21a5d8ab6267e7e5c9a0b06bca3aa8caaa9246e1f9b492855647"
          },
          "uri": "runs/.sof-service-cache/39/39d7a0ce61f38d02ead291108de7cab397d64deacb3a14f389f599bebf6e48be/report/compiler/sofrs-validation-receipt.schema.json"
        },
        "validator_id": "sofrs.report-validator.v2",
        "validator_version": "2.0"
      }
    }
  },
  "artifacts": [
    {
      "artifact_id": "sofrs_receipt:ef16e622b0e9e05d",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/reference-report/report/validation-receipt.json",
      "sha256": "ef16e622b0e9e05d8f621d87792d100cdb701edd0ae169fcc4bed75cbc23b2b5",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    }
  ]
}
```

### Call 8: sof_validate

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "validation_kind": "sofrs",
  "artifact": "matrix/agent-a/target-report/report/result.sofreport.json",
  "request_id": "matrix-agent-a-validate-target-report"
}
```

Result:

```json
{
  "contract_id": "sof-runtime.service-response.v1",
  "request_id": "matrix-agent-a-validate-target-report",
  "job_id": "job:043f9c22c4b4492b8618154cb991b237",
  "semantic_run_id": "semrun:sha256:c1a4e02710095cd7ae3d9f1d9bfa356b02ff0bbd67ebc320066cc0e7746a5150",
  "workspace_id": "mcp-adopter-20260811a",
  "operation": "validate",
  "status": "succeeded",
  "result": {
    "validation_kind": "sofrs",
    "validator_result": {
      "alignment_readiness": {
        "adapter": {
          "id": "example.finite-state-adapter",
          "version": "1.0"
        },
        "assembly_profile_id": "sof-runtime.strict-conformance.assembly.v2",
        "carrier_kinds": [
          "operator",
          "operator_system",
          "sector"
        ],
        "comparison_keys": [
          "report:example.finite-state-adapter.finite-state.transition.target.sofreport",
          "system:external-adapter-reference:-finite-state-transition-system",
          "record-kind:strict_sof"
        ],
        "compiler_profile_id": "sof-runtime.strict-conformance",
        "observable_metadata": {
          "labels": [
            "advance"
          ],
          "provenance": "example.finite-state-adapter",
          "ranks_or_dimensions": [],
          "semantics": "labelled operative alphabet",
          "status": "PRESENT"
        },
        "run_policies": [
          {
            "id": "run.threshold",
            "kind": "threshold"
          },
          {
            "id": "run.norm",
            "kind": "norm"
          },
          {
            "id": "run.tolerance",
            "kind": "numerical_tolerance"
          }
        ],
        "sector_metadata": {
          "labels": [
            "idle",
            "busy",
            "done"
          ],
          "provenance": "example.finite-state-adapter",
          "ranks_or_dimensions": [],
          "semantics": "one-hot basis of the declared finite state set",
          "status": "PRESENT"
        },
        "semantic_conventions": [
          {
            "id": "semantic.alphabet",
            "kind": "operative_alphabet"
          },
          {
            "id": "semantic.word",
            "kind": "word_convention"
          },
          {
            "id": "semantic.projector-letter",
            "kind": "projector_letter_policy"
          },
          {
            "id": "semantic.direction",
            "kind": "direction_convention"
          },
          {
            "id": "semantic.depth-indexing",
            "kind": "depth_indexing"
          }
        ],
        "source_artifact_digests": [
          {
            "digest": {
              "algorithm": "sha256",
              "value": "a4a46d473151eac268376c3668bb69ad3ba5e2fe5de4d24ddd27be143c467e33"
            },
            "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/source/input.json"
          },
          {
            "digest": {
              "algorithm": "sha256",
              "value": "f2b967456920e50914e0bd4d61c58758974122fdafda4776ebf55ae0a3327286"
            },
            "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/implementation.py"
          },
          {
            "digest": {
              "algorithm": "sha256",
              "value": "7284ed390f68c27f370bc7470ab3e351b0922150145e01e2a89c34bb158b69d4"
            },
            "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/declaration.json"
          },
          {
            "digest": {
              "algorithm": "sha256",
              "value": "2e2f51bbdcf95b71a4ebf0ef6fa7fc1a332c79c638946ab5312d8823eaac34f2"
            },
            "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/inspection.json"
          },
          {
            "digest": {
              "algorithm": "sha256",
              "value": "c120c334d96cf906c3278c9132984345e9da4e87b2a44c863818f99916129907"
            },
            "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/realization/candidate.json"
          },
          {
            "digest": {
              "algorithm": "sha256",
              "value": "383b067ca5eda48f82603d3a12fff091085e0ba99a399a8b2e99c4f7efa97158"
            },
            "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/realization/evidence.json"
          }
        ]
      },
      "assembly_contract": {
        "assembly_profile": {
          "digest": {
            "algorithm": "sha256",
            "value": "a503e80f6361ccafb15654f604727f310ca631b395ee787dd13e9574ad0ec608"
          },
          "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/inputs/case-bundle/case/profiles/assembly/strict-conformance-v2.0.json"
        },
        "assembly_profile_id": "sof-runtime.strict-conformance.assembly.v2",
        "implementation": {
          "digest": {
            "algorithm": "sha256",
            "value": "21137aced870455a6d65b7ec8910d72959002393d556489a2d6fbe01a72f3186"
          },
          "uri": "runs/.sof-service-cache/c1/c191bddc3c87eb97508d21d140c95f738ab839b8cc65f0f94c701339fe0905c0/report/compiler/assembly-implementation.py"
        },
        "schema_id": "sofrs-assembly-v2.0",
        "version": "2.0"
      },
      "claims": [
        {
          "carrier_kinds": [
            "operator",
            "sector"
          ],
          "certificate_class": "protocol_conformance",
          "claim_id": "claim.direct-support",
          "claim_status": "Computational Certificate",
          "claim_target": "representation_interface",
          "classification_source": "independent_validator",
          "external_basis_refs": [
            "basis.source.identity",
            "basis.structure.level"
          ],
          "external_constraint_ids": [
            "source-snapshot-pinned",
            "realization-structure-validation"
          ],
          "negative_boundary": "This claim does not establish route, word, Lie/Hall, causal, or domain-adequacy conclusions.",
          "report_item_id": "report.claim-item.0000",
          "result_state": "CERTIFIED",
          "scope": "The finite state basis and the supplied transition matrices.",
          "source_output_item_id": "compiler.item.0000",
          "statement": "The external adapter's declared transition family has certified thresholded direct support."
        }
      ],
      "compiler_contracts": {
        "capability_manifest": {
          "digest": {
            "algorithm": "sha256",
            "value": "2453619f73a41cda176fec0a3956b5da97a4d3cc6eb262445ff77f1ece2aa54a"
          },
          "uri": "runs/.sof-service-cache/c1/c191bddc3c87eb97508d21d140c95f738ab839b8cc65f0f94c701339fe0905c0/report/compiler/manifest.json"
        },
        "compiler_output": {
          "digest": {
            "algorithm": "sha256",
            "value": "0629da949f3fb066832143adcc544d0be93205101c62099f5ee587047807405d"
          },
          "uri": "runs/.sof-service-cache/c1/c191bddc3c87eb97508d21d140c95f738ab839b8cc65f0f94c701339fe0905c0/report/compiler/compiler-output.json"
        },
        "compiler_profile": {
          "digest": {
            "algorithm": "sha256",
            "value": "ab0406daf52b99a712a903ae8dbcb49a75137b1e1953a96c65764512a302fdaa"
          },
          "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/inputs/case-bundle/case/profiles/compiler/strict-conformance-v1.0.json"
        },
        "typed_sof_ir": {
          "digest": {
            "algorithm": "sha256",
            "value": "dd84e193225b58f72030a278a86288c7640722e0629bb67902a65a137af73c5f"
          },
          "uri": "runs/.sof-service-cache/c1/c191bddc3c87eb97508d21d140c95f738ab839b8cc65f0f94c701339fe0905c0/report/compiler/typed-ir.json"
        }
      },
      "compiler_output_binding": {
        "artifact": {
          "digest": {
            "algorithm": "sha256",
            "value": "0629da949f3fb066832143adcc544d0be93205101c62099f5ee587047807405d"
          },
          "uri": "runs/.sof-service-cache/c1/c191bddc3c87eb97508d21d140c95f738ab839b8cc65f0f94c701339fe0905c0/report/compiler/compiler-output.json"
        },
        "artifact_id": "artifact.compiler-output",
        "compiler_id": "sofcompiler.compile_v1",
        "compiler_output_version": "1.0",
        "compiler_profile_id": "sof-runtime.strict-conformance"
      },
      "degradation_items": [
        {
          "action": "omit_module",
          "details": [
            "no any_of member present: route_carrier, word_carrier"
          ],
          "module_id": "associative",
          "reason_kind": "unsatisfied_capability_requirements",
          "report_item_id": "report.degradation-item.0001",
          "source_output_item_id": "compiler.item.0001"
        },
        {
          "action": "omit_module",
          "details": [
            "no any_of member present: route_space, word_space, depth_field"
          ],
          "module_id": "associative",
          "reason_kind": "unsatisfied_object_kind_requirements",
          "report_item_id": "report.degradation-item.0002",
          "source_output_item_id": "compiler.item.0002"
        },
        {
          "action": "emit_unavailable",
          "details": [
            "missing all_of: cutoff"
          ],
          "module_id": "associative",
          "reason_kind": "unsatisfied_run_policy_requirements",
          "report_item_id": "report.degradation-item.0003",
          "source_output_item_id": "compiler.item.0003"
        },
        {
          "action": "omit_module",
          "details": [
            "no any_of member present: positive_associative_closure, observable_star_closure, sector_enriched_star_closure"
          ],
          "module_id": "closure",
          "reason_kind": "unsatisfied_capability_requirements",
          "report_item_id": "report.degradation-item.0004",
          "source_output_item_id": "compiler.item.0004"
        },
        {
          "action": "omit_module",
          "details": [
            "no any_of member present: associative_closure, star_closure"
          ],
          "module_id": "closure",
          "reason_kind": "unsatisfied_object_kind_requirements",
          "report_item_id": "report.degradation-item.0005",
          "source_output_item_id": "compiler.item.0005"
        },
        {
          "action": "emit_unavailable",
          "details": [
            "missing all_of: saturation_audit"
          ],
          "module_id": "closure",
          "reason_kind": "unsatisfied_run_policy_requirements",
          "report_item_id": "report.degradation-item.0006",
          "source_output_item_id": "compiler.item.0006"
        }
      ],
      "external_basis_registry": {
        "basis_status": "PARTIAL",
        "constraints": [
          {
            "basis_id": "basis.source.identity",
            "constraint_id": "source-snapshot-pinned",
            "evidence_artifacts": [
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "a4a46d473151eac268376c3668bb69ad3ba5e2fe5de4d24ddd27be143c467e33"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/source/input.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "f2b967456920e50914e0bd4d61c58758974122fdafda4776ebf55ae0a3327286"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/implementation.py"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "7284ed390f68c27f370bc7470ab3e351b0922150145e01e2a89c34bb158b69d4"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/declaration.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "2e2f51bbdcf95b71a4ebf0ef6fa7fc1a332c79c638946ab5312d8823eaac34f2"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/inspection.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "c120c334d96cf906c3278c9132984345e9da4e87b2a44c863818f99916129907"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/realization/candidate.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "383b067ca5eda48f82603d3a12fff091085e0ba99a399a8b2e99c4f7efa97158"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/realization/evidence.json"
              }
            ],
            "statement": "Declared external-adapter workflow condition.",
            "status": "SATISFIED"
          },
          {
            "basis_id": "basis.object.level",
            "constraint_id": "object-level-recomputation",
            "evidence_artifacts": [],
            "statement": "Declared external-adapter workflow condition.",
            "status": "NOT_ASSESSED"
          },
          {
            "basis_id": "basis.structure.level",
            "constraint_id": "realization-structure-validation",
            "evidence_artifacts": [
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "a4a46d473151eac268376c3668bb69ad3ba5e2fe5de4d24ddd27be143c467e33"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/source/input.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "f2b967456920e50914e0bd4d61c58758974122fdafda4776ebf55ae0a3327286"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/implementation.py"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "7284ed390f68c27f370bc7470ab3e351b0922150145e01e2a89c34bb158b69d4"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/declaration.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "2e2f51bbdcf95b71a4ebf0ef6fa7fc1a332c79c638946ab5312d8823eaac34f2"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/inspection.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "c120c334d96cf906c3278c9132984345e9da4e87b2a44c863818f99916129907"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/realization/candidate.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "383b067ca5eda48f82603d3a12fff091085e0ba99a399a8b2e99c4f7efa97158"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/realization/evidence.json"
              }
            ],
            "statement": "Declared external-adapter workflow condition.",
            "status": "SATISFIED"
          },
          {
            "basis_id": "basis.semantic.adequacy",
            "constraint_id": "domain-semantic-adequacy",
            "evidence_artifacts": [],
            "statement": "Declared external-adapter workflow condition.",
            "status": "NOT_ASSESSED"
          }
        ],
        "negative_boundary": [
          "The runtime validates the adapter contract and report closure; it does not become the domain authority."
        ],
        "packages": [
          {
            "basis_id": "basis.source.identity",
            "constraint_ids": [
              "source-snapshot-pinned"
            ],
            "evidence_artifacts": [
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "a4a46d473151eac268376c3668bb69ad3ba5e2fe5de4d24ddd27be143c467e33"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/source/input.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "f2b967456920e50914e0bd4d61c58758974122fdafda4776ebf55ae0a3327286"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/implementation.py"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "7284ed390f68c27f370bc7470ab3e351b0922150145e01e2a89c34bb158b69d4"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/declaration.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "2e2f51bbdcf95b71a4ebf0ef6fa7fc1a332c79c638946ab5312d8823eaac34f2"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/inspection.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "c120c334d96cf906c3278c9132984345e9da4e87b2a44c863818f99916129907"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/realization/candidate.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "383b067ca5eda48f82603d3a12fff091085e0ba99a399a8b2e99c4f7efa97158"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/realization/evidence.json"
              }
            ],
            "level": "source_identity",
            "method": "external-adapter-reference-workflow",
            "negative_boundary": [
              "Protocol conformance does not establish domain adequacy."
            ],
            "scope": "Bounded external-adapter Level 1 workflow.",
            "status": "SATISFIED"
          },
          {
            "basis_id": "basis.object.level",
            "constraint_ids": [
              "object-level-recomputation"
            ],
            "evidence_artifacts": [],
            "level": "object_level",
            "method": "external-adapter-reference-workflow",
            "negative_boundary": [
              "Protocol conformance does not establish domain adequacy."
            ],
            "scope": "Bounded external-adapter Level 1 workflow.",
            "status": "NOT_ASSESSED"
          },
          {
            "basis_id": "basis.structure.level",
            "constraint_ids": [
              "realization-structure-validation"
            ],
            "evidence_artifacts": [
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "a4a46d473151eac268376c3668bb69ad3ba5e2fe5de4d24ddd27be143c467e33"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/source/input.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "f2b967456920e50914e0bd4d61c58758974122fdafda4776ebf55ae0a3327286"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/implementation.py"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "7284ed390f68c27f370bc7470ab3e351b0922150145e01e2a89c34bb158b69d4"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/declaration.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "2e2f51bbdcf95b71a4ebf0ef6fa7fc1a332c79c638946ab5312d8823eaac34f2"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/inspection.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "c120c334d96cf906c3278c9132984345e9da4e87b2a44c863818f99916129907"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/realization/candidate.json"
              },
              {
                "digest": {
                  "algorithm": "sha256",
                  "value": "383b067ca5eda48f82603d3a12fff091085e0ba99a399a8b2e99c4f7efa97158"
                },
                "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/realization/evidence.json"
              }
            ],
            "level": "structure_level",
            "method": "external-adapter-reference-workflow",
            "negative_boundary": [
              "Protocol conformance does not establish domain adequacy."
            ],
            "scope": "Bounded external-adapter Level 1 workflow.",
            "status": "SATISFIED"
          },
          {
            "basis_id": "basis.semantic.adequacy",
            "constraint_ids": [
              "domain-semantic-adequacy"
            ],
            "evidence_artifacts": [],
            "level": "semantic_adequacy",
            "method": "external-adapter-reference-workflow",
            "negative_boundary": [
              "Protocol conformance does not establish domain adequacy."
            ],
            "scope": "Bounded external-adapter Level 1 workflow.",
            "status": "NOT_ASSESSED"
          }
        ],
        "registry_version": "1.0"
      },
      "failure_modes": [
        "This Level 1 workflow does not compare two reports or interpret a SOFAUDIT.",
        "Direct support is certified only under the adapter-declared source and threshold boundary."
      ],
      "findings": [
        {
          "finding_id": "finding.direct-support",
          "kind": "boolean_support",
          "result_state": "CERTIFIED",
          "value": {
            "present": true,
            "support_pairs": [
              [
                "busy",
                "done"
              ],
              [
                "done",
                "idle"
              ],
              [
                "idle",
                "busy"
              ]
            ],
            "threshold_statement": "absolute matrix entry > 1e-12"
          }
        }
      ],
      "item_bindings": [
        {
          "compiler_output_item_id": "compiler.item.0000",
          "item_kind": "claim",
          "rendering_status": "rendered",
          "report_item_id": "report.claim-item.0000"
        },
        {
          "compiler_output_item_id": "compiler.item.0001",
          "item_kind": "degradation",
          "rendering_status": "rendered",
          "report_item_id": "report.degradation-item.0001"
        },
        {
          "compiler_output_item_id": "compiler.item.0002",
          "item_kind": "degradation",
          "rendering_status": "rendered",
          "report_item_id": "report.degradation-item.0002"
        },
        {
          "compiler_output_item_id": "compiler.item.0003",
          "item_kind": "degradation",
          "rendering_status": "rendered",
          "report_item_id": "report.degradation-item.0003"
        },
        {
          "compiler_output_item_id": "compiler.item.0004",
          "item_kind": "degradation",
          "rendering_status": "rendered",
          "report_item_id": "report.degradation-item.0004"
        },
        {
          "compiler_output_item_id": "compiler.item.0005",
          "item_kind": "degradation",
          "rendering_status": "rendered",
          "report_item_id": "report.degradation-item.0005"
        },
        {
          "compiler_output_item_id": "compiler.item.0006",
          "item_kind": "degradation",
          "rendering_status": "rendered",
          "report_item_id": "report.degradation-item.0006"
        }
      ],
      "modules": [
        {
          "carrier_kinds": [
            "sector",
            "operator",
            "operator_system"
          ],
          "claim_ids": [
            "claim.direct-support"
          ],
          "finding_ids": [
            "finding.direct-support"
          ],
          "module_id": "sof-basic",
          "output_sections": [
            "Sectorization",
            "Observable Alphabet",
            "Direct Support"
          ],
          "status": "ENABLED"
        },
        {
          "carrier_kinds": [
            "route",
            "word",
            "positive_associative_closure"
          ],
          "claim_ids": [],
          "finding_ids": [],
          "module_id": "associative",
          "output_sections": [
            "Routed Products",
            "Full Words",
            "First-Hit Cutoff"
          ],
          "reason": "no any_of member present: route_carrier, word_carrier; no any_of member present: route_space, word_space, depth_field; missing all_of: cutoff",
          "status": "UNAVAILABLE"
        },
        {
          "carrier_kinds": [
            "positive_associative_closure",
            "observable_star_closure",
            "sector_enriched_star_closure"
          ],
          "claim_ids": [],
          "finding_ids": [],
          "module_id": "closure",
          "output_sections": [
            "Positive Associative Closure",
            "Observable Star Closure",
            "Sector-Enriched Star Closure"
          ],
          "reason": "no any_of member present: positive_associative_closure, observable_star_closure, sector_enriched_star_closure; no any_of member present: associative_closure, star_closure; missing all_of: saturation_audit",
          "status": "UNAVAILABLE"
        }
      ],
      "provenance": {
        "adapter": {
          "digest": {
            "algorithm": "sha256",
            "value": "f2b967456920e50914e0bd4d61c58758974122fdafda4776ebf55ae0a3327286"
          },
          "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/implementation.py"
        },
        "assembly_profile_ref": {
          "digest": {
            "algorithm": "sha256",
            "value": "a503e80f6361ccafb15654f604727f310ca631b395ee787dd13e9574ad0ec608"
          },
          "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/inputs/case-bundle/case/profiles/assembly/strict-conformance-v2.0.json"
        },
        "compiler_output_ref": {
          "digest": {
            "algorithm": "sha256",
            "value": "0629da949f3fb066832143adcc544d0be93205101c62099f5ee587047807405d"
          },
          "uri": "runs/.sof-service-cache/c1/c191bddc3c87eb97508d21d140c95f738ab839b8cc65f0f94c701339fe0905c0/report/compiler/compiler-output.json"
        },
        "compiler_profile_ref": {
          "digest": {
            "algorithm": "sha256",
            "value": "ab0406daf52b99a712a903ae8dbcb49a75137b1e1953a96c65764512a302fdaa"
          },
          "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/inputs/case-bundle/case/profiles/compiler/strict-conformance-v1.0.json"
        },
        "kind": "native_generation",
        "producer": {
          "digest": {
            "algorithm": "sha256",
            "value": "e4e68f1cccfbdcd91403ce273dd6dd1e30b219d3113b62790183201eee00641f"
          },
          "uri": "runs/.sof-service-cache/c1/c191bddc3c87eb97508d21d140c95f738ab839b8cc65f0f94c701339fe0905c0/report/compiler/workflow-implementation.py"
        },
        "source_snapshot": {
          "digest": {
            "algorithm": "sha256",
            "value": "a4a46d473151eac268376c3668bb69ad3ba5e2fe5de4d24ddd27be143c467e33"
          },
          "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/source/input.json"
        }
      },
      "record_kind": "strict_sof",
      "report_id": "example.finite-state-adapter.finite-state.transition.target.sofreport",
      "sofrs_version": "2.0",
      "source_artifacts": [
        {
          "digest": {
            "algorithm": "sha256",
            "value": "a4a46d473151eac268376c3668bb69ad3ba5e2fe5de4d24ddd27be143c467e33"
          },
          "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/source/input.json"
        },
        {
          "digest": {
            "algorithm": "sha256",
            "value": "f2b967456920e50914e0bd4d61c58758974122fdafda4776ebf55ae0a3327286"
          },
          "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/implementation.py"
        },
        {
          "digest": {
            "algorithm": "sha256",
            "value": "7284ed390f68c27f370bc7470ab3e351b0922150145e01e2a89c34bb158b69d4"
          },
          "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/declaration.json"
        },
        {
          "digest": {
            "algorithm": "sha256",
            "value": "2e2f51bbdcf95b71a4ebf0ef6fa7fc1a332c79c638946ab5312d8823eaac34f2"
          },
          "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/inspection.json"
        },
        {
          "digest": {
            "algorithm": "sha256",
            "value": "c120c334d96cf906c3278c9132984345e9da4e87b2a44c863818f99916129907"
          },
          "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/realization/candidate.json"
        },
        {
          "digest": {
            "algorithm": "sha256",
            "value": "383b067ca5eda48f82603d3a12fff091085e0ba99a399a8b2e99c4f7efa97158"
          },
          "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/realization/evidence.json"
        }
      ],
      "source_mapping": {
        "adapter_id": "example.finite-state-adapter",
        "adapter_version": "1.0",
        "construction": "Runtime-owned Manifest/IR construction from an admitted ExpertAdapter RealizationCandidate.",
        "justification": "The adapter maps domain transition matrices to a declared sectorization and operative alphabet.",
        "limitations": [
          "The runtime does not infer omitted carriers or domain adequacy."
        ],
        "status": "adapter-derived"
      },
      "strict_reconstruction": {
        "available_requirements": [],
        "candidate_status": "not_applicable",
        "evaluator_id": "example.finite-state-adapter.source-validator",
        "evaluator_version": "1.0",
        "interpretation": "The external adapter supplied an explicit finite complex realization candidate.",
        "missing_requirements": []
      },
      "system": "External adapter reference: finite-state-transition-system"
    }
  },
  "artifacts": [
    {
      "artifact_id": "sofrs:bc783aee6c4705ea",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/target-report/report/result.sofreport.json",
      "sha256": "bc783aee6c4705ea535a4e8bfd97c696e26b4db3fe81c8d4deb76dbe93dc29dd",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    }
  ]
}
```

### Call 9: sof_validate

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "validation_kind": "sofrs_receipt",
  "artifact": "matrix/agent-a/target-report/report/validation-receipt.json",
  "request_id": "matrix-agent-a-validate-target-receipt"
}
```

Result:

```json
{
  "contract_id": "sof-runtime.service-response.v1",
  "request_id": "matrix-agent-a-validate-target-receipt",
  "job_id": "job:9b0c764451c3436fa44248100336bd33",
  "semantic_run_id": "semrun:sha256:c59f326ce1d4a96ca73dc57cbfa589ee31140832df5eebbb95606872cd63416f",
  "workspace_id": "mcp-adopter-20260811a",
  "operation": "validate",
  "status": "succeeded",
  "result": {
    "validation_kind": "sofrs_receipt",
    "validator_result": {
      "artifact_closure": {
        "artifact_count": 7,
        "closure_digest": {
          "algorithm": "sha256",
          "value": "a7b44822f3f0ea4b4726260f218c6503ccf8c9446d347995b4595bde2cde2cdb"
        },
        "ordered_artifacts": [
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "bc783aee6c4705ea535a4e8bfd97c696e26b4db3fe81c8d4deb76dbe93dc29dd"
              },
              "uri": "runs/.sof-service-cache/c1/c191bddc3c87eb97508d21d140c95f738ab839b8cc65f0f94c701339fe0905c0/report/report/result.sofreport.json"
            },
            "role": "report"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "2453619f73a41cda176fec0a3956b5da97a4d3cc6eb262445ff77f1ece2aa54a"
              },
              "uri": "runs/.sof-service-cache/c1/c191bddc3c87eb97508d21d140c95f738ab839b8cc65f0f94c701339fe0905c0/report/compiler/manifest.json"
            },
            "role": "capability_manifest"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "dd84e193225b58f72030a278a86288c7640722e0629bb67902a65a137af73c5f"
              },
              "uri": "runs/.sof-service-cache/c1/c191bddc3c87eb97508d21d140c95f738ab839b8cc65f0f94c701339fe0905c0/report/compiler/typed-ir.json"
            },
            "role": "typed_sof_ir"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "ab0406daf52b99a712a903ae8dbcb49a75137b1e1953a96c65764512a302fdaa"
              },
              "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/inputs/case-bundle/case/profiles/compiler/strict-conformance-v1.0.json"
            },
            "role": "compiler_profile"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "0629da949f3fb066832143adcc544d0be93205101c62099f5ee587047807405d"
              },
              "uri": "runs/.sof-service-cache/c1/c191bddc3c87eb97508d21d140c95f738ab839b8cc65f0f94c701339fe0905c0/report/compiler/compiler-output.json"
            },
            "role": "compiler_output"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "a503e80f6361ccafb15654f604727f310ca631b395ee787dd13e9574ad0ec608"
              },
              "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/inputs/case-bundle/case/profiles/assembly/strict-conformance-v2.0.json"
            },
            "role": "assembly_profile"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "21137aced870455a6d65b7ec8910d72959002393d556489a2d6fbe01a72f3186"
              },
              "uri": "runs/.sof-service-cache/c1/c191bddc3c87eb97508d21d140c95f738ab839b8cc65f0f94c701339fe0905c0/report/compiler/assembly-implementation.py"
            },
            "role": "assembly_implementation"
          }
        ]
      },
      "artifact_type": "sofrs_report_validation_receipt",
      "checks": [
        {
          "check_id": "artifact-closure",
          "status": "PASS"
        },
        {
          "check_id": "claim-compatibility",
          "status": "PASS"
        },
        {
          "check_id": "claim-external-basis-binding",
          "status": "PASS"
        },
        {
          "check_id": "compiler-output-recompilation",
          "status": "PASS"
        },
        {
          "check_id": "cutoff-provenance",
          "status": "PASS"
        },
        {
          "check_id": "record-kind-boundary",
          "status": "PASS"
        },
        {
          "check_id": "report-assembly-recomputation",
          "status": "PASS"
        },
        {
          "check_id": "schema-validation",
          "status": "PASS"
        }
      ],
      "negative_boundaries": [
        "This receipt validates faithful SOFRS assembly and its bound compiler-contract closure; it does not establish adapter scientific adequacy, cross-report alignment, or downstream interpretation."
      ],
      "receipt_id": "receipt.example.finite-state-adapter.finite-state.transition.target.sofreport.sofrs-v2",
      "receipt_version": "2.0",
      "report": {
        "artifact": {
          "digest": {
            "algorithm": "sha256",
            "value": "bc783aee6c4705ea535a4e8bfd97c696e26b4db3fe81c8d4deb76dbe93dc29dd"
          },
          "uri": "runs/.sof-service-cache/c1/c191bddc3c87eb97508d21d140c95f738ab839b8cc65f0f94c701339fe0905c0/report/report/result.sofreport.json"
        },
        "record_kind": "strict_sof",
        "report_id": "example.finite-state-adapter.finite-state.transition.target.sofreport",
        "sofrs_version": "2.0"
      },
      "status": "PASS",
      "validator": {
        "implementation": {
          "digest": {
            "algorithm": "sha256",
            "value": "299c716b7ee398b4a5fa37928efba5d178bda071be1f8785810e536547fcd3ee"
          },
          "uri": "runs/.sof-service-cache/c1/c191bddc3c87eb97508d21d140c95f738ab839b8cc65f0f94c701339fe0905c0/report/compiler/report-validator.py"
        },
        "receipt_contract": {
          "digest": {
            "algorithm": "sha256",
            "value": "84254cf908ce21a5d8ab6267e7e5c9a0b06bca3aa8caaa9246e1f9b492855647"
          },
          "uri": "runs/.sof-service-cache/c1/c191bddc3c87eb97508d21d140c95f738ab839b8cc65f0f94c701339fe0905c0/report/compiler/sofrs-validation-receipt.schema.json"
        },
        "validator_id": "sofrs.report-validator.v2",
        "validator_version": "2.0"
      }
    }
  },
  "artifacts": [
    {
      "artifact_id": "sofrs_receipt:89c7fc342ae0cdd5",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/target-report/report/validation-receipt.json",
      "sha256": "89c7fc342ae0cdd56f2bed4bf0b62a213f271fd87747de97f86d70cf7d14b14b",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    }
  ]
}
```

### Call 10: sof_compare

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "reference_report": "matrix/agent-a/reference-report/report/result.sofreport.json",
  "reference_receipt": "matrix/agent-a/reference-report/report/validation-receipt.json",
  "target_report": "matrix/agent-a/target-report/report/result.sofreport.json",
  "target_receipt": "matrix/agent-a/target-report/report/validation-receipt.json",
  "alignment": "case/comparison/alignment.json",
  "comparison_profile": "comparison-profile.json",
  "out_directory": "matrix/agent-a/comparison",
  "request_id": "matrix-agent-a-compare"
}
```

Result:

```json
{
  "contract_id": "sof-runtime.service-response.v1",
  "request_id": "matrix-agent-a-compare",
  "job_id": "job:a0315ade06fd496b86d64fda3d6110f1",
  "semantic_run_id": "semrun:sha256:bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7",
  "workspace_id": "mcp-adopter-20260811a",
  "operation": "compare",
  "status": "succeeded",
  "result": {
    "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport"
  },
  "artifacts": [
    {
      "artifact_id": "sofaudit:40125672cfd042ea",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/comparison/result.sofaudit.json",
      "sha256": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    },
    {
      "artifact_id": "sofaudit_validation_receipt:8cb9ccbce7fa6711",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/comparison/validation-receipt.json",
      "sha256": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    }
  ]
}
```

### Call 11: sof_validate

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "validation_kind": "sofaudit",
  "artifact": "matrix/agent-a/comparison/result.sofaudit.json",
  "request_id": "matrix-agent-a-validate-audit"
}
```

Result:

```json
{
  "contract_id": "sof-runtime.service-response.v1",
  "request_id": "matrix-agent-a-validate-audit",
  "job_id": "job:08cd1ee821ce4b8ab8f1f34bf18d06a6",
  "semantic_run_id": "semrun:sha256:d9c06c04e74766e404a7a07ca36c4506bd67004d1d201d3eca24757c38800845",
  "workspace_id": "mcp-adopter-20260811a",
  "operation": "validate",
  "status": "succeeded",
  "result": {
    "validation_kind": "sofaudit",
    "validator_result": {
      "alignment": {
        "observable_alignment": {
          "alignment_id": "example.finite-state.identity.observable",
          "alignment_kind": "observable",
          "map_kind": "bijection",
          "negative_boundary": [
            "Identity alignment does not establish cross-domain semantic equivalence."
          ],
          "pairs": [
            {
              "evidence_artifact_ids": [
                "artifact.alignment-evidence"
              ],
              "reference_id": "advance",
              "relation": "equivalent",
              "target_id": "advance"
            }
          ],
          "properties": {
            "injective": true,
            "surjective": true,
            "total_on_reference": true,
            "total_on_target": true
          },
          "reference_carrier": "report-bound-labels",
          "semantic_basis": "Declared identity alignment on the shared finite-state labels.",
          "state": "TOTAL",
          "target_carrier": "report-bound-labels",
          "unmatched_reference_ids": [],
          "unmatched_target_ids": []
        },
        "sector_alignment": {
          "alignment_id": "example.finite-state.identity.sector",
          "alignment_kind": "sector",
          "map_kind": "bijection",
          "negative_boundary": [
            "Identity alignment does not establish cross-domain semantic equivalence."
          ],
          "pairs": [
            {
              "evidence_artifact_ids": [
                "artifact.alignment-evidence"
              ],
              "reference_id": "idle",
              "relation": "equivalent",
              "target_id": "idle"
            },
            {
              "evidence_artifact_ids": [
                "artifact.alignment-evidence"
              ],
              "reference_id": "busy",
              "relation": "equivalent",
              "target_id": "busy"
            },
            {
              "evidence_artifact_ids": [
                "artifact.alignment-evidence"
              ],
              "reference_id": "done",
              "relation": "equivalent",
              "target_id": "done"
            }
          ],
          "properties": {
            "injective": true,
            "surjective": true,
            "total_on_reference": true,
            "total_on_target": true
          },
          "reference_carrier": "report-bound-labels",
          "semantic_basis": "Declared identity alignment on the shared finite-state labels.",
          "state": "TOTAL",
          "target_carrier": "report-bound-labels",
          "unmatched_reference_ids": [],
          "unmatched_target_ids": []
        }
      },
      "artifact_type": "sofaudit",
      "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
      "audit_profile": {
        "applicable_regime": "strict_vs_strict",
        "availability_semantics": {
          "null_value_states": [
            "NOT_DECLARED",
            "NOT_APPLICABLE",
            "INCOMPARABLE",
            "UNRESOLVED"
          ],
          "unavailable_states": [
            "NOT_DECLARED",
            "NOT_APPLICABLE",
            "INCOMPARABLE",
            "UNRESOLVED"
          ],
          "zero_is_unavailable": false
        },
        "carrier_requirements": {
          "analogue": [],
          "strict": [
            "operator"
          ]
        },
        "comparison_semantics": {
          "comparison_is_pairwise": true,
          "matched_states": [
            "ALIGNED",
            "MISMATCH"
          ]
        },
        "coordinate_families": [
          "operator"
        ],
        "coordinate_registry_artifact_id": "artifact.coordinate-semantics-registry",
        "coordinate_registry_ref": "schemas/sofaudit/coordinate-semantics-registry-v1.0.json",
        "profile_artifact_id": "artifact.audit-profile",
        "profile_id": "sof-runtime.external-adapter.identity.v2",
        "profile_version": "2.0",
        "requested_coordinate_ids": [
          "operator.support.summary"
        ],
        "required_evidence_roles": [
          "reference-report",
          "target-report",
          "reference-report-validation-receipt",
          "target-report-validation-receipt",
          "audit-profile",
          "coordinate-semantics-registry"
        ]
      },
      "claim": {
        "certificate_class": "comparison_audit",
        "claim_status": "Computational Certificate",
        "claim_target": "comparison_relation",
        "classification_source": "audit_engine",
        "negative_boundary": "This comparison does not establish reference truth, defect status, severity, or action.",
        "result_state": "CERTIFIED",
        "source_artifact_ids": [
          "artifact.reference-report",
          "artifact.target-report",
          "artifact.reference-report-validation-receipt",
          "artifact.target-report-validation-receipt",
          "artifact.alignment-input",
          "artifact.audit-profile",
          "artifact.coordinate-semantics-registry",
          "artifact.alignment-evidence"
        ],
        "statement": "The selected direct-support coordinate was recomputed under declared identity alignment."
      },
      "comparison_basis": {
        "alignment_evidence": [
          "artifact.alignment-input",
          "artifact.audit-profile",
          "artifact.coordinate-semantics-registry",
          "artifact.alignment-evidence"
        ],
        "basis_status": "COMPLETE",
        "negative_boundary": [
          "This basis supports only an alignment-relative comparison."
        ],
        "object_level_oracle": {
          "audit_result_artifact": null,
          "independence": {
            "implementation_relation": "not_assessed",
            "input_source": "not_assessed",
            "producer_cache_used": null,
            "producer_relation": "not_assessed"
          },
          "independent_recomputation_artifacts": [],
          "oracle_result_artifact": null,
          "raw_source_artifacts": [],
          "status": "NOT_ASSESSED"
        },
        "policy_compatibility": {
          "negative_boundary": [
            "Policy compatibility does not establish object truth."
          ],
          "policy_artifact_ids": [
            "artifact.audit-profile",
            "artifact.coordinate-semantics-registry"
          ],
          "status": "SATISFIED"
        },
        "reference_role_basis": {
          "authority_status": "DECLARED",
          "basis_kind": "declared_baseline_only",
          "evidence_artifacts": [
            "artifact.reference-report",
            "artifact.reference-report-validation-receipt"
          ],
          "negative_boundary": [
            "The selected reference is not thereby a truth oracle."
          ],
          "role": "reference",
          "scope": "Selected SOFRS report role for this runtime comparison."
        }
      },
      "comparison_object": "SOFReportComparison",
      "comparison_specification": {
        "aggregation": {
          "kind": "coordinatewise",
          "scalarization": "none",
          "weight_declaration": null,
          "weights_artifact_id": null
        },
        "depth_semantics": {
          "carrier": "not-applicable",
          "mode": "not-applicable",
          "reference_cutoff": null,
          "target_cutoff": null,
          "unreached_policy": "incomparable"
        },
        "metric": {
          "domain": "integer",
          "metric_id": "absolute-difference",
          "missing_value_policy": "incomparable",
          "unit_policy": "unitless",
          "zero_denominator_policy": "not-applicable"
        },
        "normalization": {
          "equality_tolerance": 0,
          "generator_policy": "report-bound-generators",
          "normalization_id": "identity",
          "numeric_policy": "exact",
          "sentinel_policy": "state-not-infinity"
        },
        "parameter_synchronization": {
          "extrapolation_forbidden": true,
          "interpolation_method": "not-applicable",
          "kind": "identity",
          "map_artifact_id": null
        },
        "specification_id": "sof-runtime.external-adapter.identity.v2",
        "thresholds": {
          "source": "not-applicable",
          "threshold_id": "not-applicable",
          "value": null
        }
      },
      "coordinates": {
        "operator.support.summary": {
          "certificate_class": null,
          "claim_status": "Computational Observation",
          "claim_target": "comparison_relation",
          "classification_source": "audit_engine",
          "comparison_state": "MISMATCH",
          "coordinate_family": "operator",
          "report_item_binding": {
            "binding_state": "paired",
            "reason": null,
            "reference_item_ref": {
              "artifact_digest": {
                "algorithm": "sha256",
                "value": "166b0de4269bbde554baaac4b07214436942d3a9bfcecd1c073c2ee924c33ae1"
              },
              "item_kind": "claim",
              "report_id": "example.finite-state-adapter.finite-state.transition.reference.sofreport",
              "report_item_id": "report.claim-item.0000",
              "source_output_item_id": "compiler.item.0000"
            },
            "target_item_ref": {
              "artifact_digest": {
                "algorithm": "sha256",
                "value": "bc783aee6c4705ea535a4e8bfd97c696e26b4db3fe81c8d4deb76dbe93dc29dd"
              },
              "item_kind": "claim",
              "report_id": "example.finite-state-adapter.finite-state.transition.target.sofreport",
              "report_item_id": "report.claim-item.0000",
              "source_output_item_id": "compiler.item.0000"
            }
          },
          "result_state": "OBSERVED",
          "source_artifact_ids": [
            "artifact.alignment-evidence"
          ],
          "value": {
            "delta": 1,
            "metric_result": {
              "metric_id": "absolute-difference",
              "status": "computed",
              "value": 1
            },
            "normalized_reference_value": {
              "support_count": 2
            },
            "normalized_target_value": {
              "support_count": 3
            },
            "oracle_ref": null,
            "policy_refs": [],
            "reference_value": {
              "support_count": 2
            },
            "relation": "mismatch",
            "target_value": {
              "support_count": 3
            },
            "unit": "support pairs"
          },
          "value_schema_id": "operator.support.v1"
        }
      },
      "failure_modes": [
        "This Level 2 control compares one declared coordinate only.",
        "A mismatch is not by itself a defect or action."
      ],
      "inherited_compiler_guards": {
        "condition_checks": [
          {
            "condition_id": "source-report-receipts-validate",
            "evidence_artifact_ids": [
              "artifact.reference-report-validation-receipt",
              "artifact.target-report-validation-receipt"
            ],
            "status": "SATISFIED"
          },
          {
            "condition_id": "paper-x-record-kind-permission",
            "evidence_artifact_ids": [
              "artifact.reference-report",
              "artifact.target-report"
            ],
            "status": "SATISFIED"
          },
          {
            "condition_id": "paper-x-carrier-alignment",
            "evidence_artifact_ids": [
              "artifact.alignment-evidence"
            ],
            "status": "SATISFIED"
          },
          {
            "condition_id": "paper-x-policy-alignment",
            "evidence_artifact_ids": [
              "artifact.alignment-evidence"
            ],
            "status": "SATISFIED"
          },
          {
            "condition_id": "paper-x-evidence-alignment",
            "evidence_artifact_ids": [
              "artifact.alignment-evidence"
            ],
            "status": "SATISFIED"
          },
          {
            "condition_id": "paper-x-promotion-audit",
            "evidence_artifact_ids": [
              "artifact.alignment-evidence"
            ],
            "status": "SATISFIED"
          },
          {
            "condition_id": "paper-xiii-sector-alignment",
            "evidence_artifact_ids": [
              "artifact.alignment-evidence"
            ],
            "status": "SATISFIED"
          },
          {
            "condition_id": "paper-xiii-observable-alignment",
            "evidence_artifact_ids": [
              "artifact.alignment-evidence"
            ],
            "status": "SATISFIED"
          },
          {
            "condition_id": "paper-xiii-comparison-specification",
            "evidence_artifact_ids": [
              "artifact.alignment-evidence"
            ],
            "status": "SATISFIED"
          }
        ],
        "negative_boundaries": [
          "Admission permits this declared comparison only."
        ],
        "paper_x_contract_version": "1.0",
        "state": "ADMITTED"
      },
      "provenance": {
        "generation_artifact_ids": [
          "artifact.alignment-input",
          "artifact.audit-profile",
          "artifact.coordinate-semantics-registry",
          "artifact.alignment-evidence"
        ],
        "generation_notes": [
          "Generated from two validated SOFRS v2 reports and explicit alignment/profile inputs."
        ],
        "generator_id": "sof-runtime.external-adapter-comparison",
        "generator_version": "1.0",
        "kind": "native"
      },
      "regime": "strict_vs_strict",
      "sofaudit_version": "2.0",
      "source_artifacts": [
        {
          "digest": {
            "algorithm": "sha256",
            "value": "166b0de4269bbde554baaac4b07214436942d3a9bfcecd1c073c2ee924c33ae1"
          },
          "id": "artifact.reference-report",
          "role": "reference-report",
          "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/inputs/reference/report.json"
        },
        {
          "digest": {
            "algorithm": "sha256",
            "value": "bc783aee6c4705ea535a4e8bfd97c696e26b4db3fe81c8d4deb76dbe93dc29dd"
          },
          "id": "artifact.target-report",
          "role": "target-report",
          "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/inputs/target/report.json"
        },
        {
          "digest": {
            "algorithm": "sha256",
            "value": "ef16e622b0e9e05d8f621d87792d100cdb701edd0ae169fcc4bed75cbc23b2b5"
          },
          "id": "artifact.reference-report-validation-receipt",
          "role": "reference-report-validation-receipt",
          "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/inputs/reference/receipt.json"
        },
        {
          "digest": {
            "algorithm": "sha256",
            "value": "89c7fc342ae0cdd56f2bed4bf0b62a213f271fd87747de97f86d70cf7d14b14b"
          },
          "id": "artifact.target-report-validation-receipt",
          "role": "target-report-validation-receipt",
          "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/inputs/target/receipt.json"
        },
        {
          "digest": {
            "algorithm": "sha256",
            "value": "5b9e8e73d6df573d858855ad3527ebc1739599b7d6fdc478eaf13f285a436502"
          },
          "id": "artifact.alignment-input",
          "role": "alignment-input",
          "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/inputs/alignment.json"
        },
        {
          "digest": {
            "algorithm": "sha256",
            "value": "bb84d2840a55b3278e509418ffd53a1b98a96fe5ee0c7304d0f5f109d52e9bd1"
          },
          "id": "artifact.audit-profile",
          "role": "audit-profile",
          "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/inputs/comparison-profile.json"
        },
        {
          "digest": {
            "algorithm": "sha256",
            "value": "1d2dc24ae56cfb364b02bccf8c0c3068138e6d07682cf4b0561ec75f765c6d48"
          },
          "id": "artifact.coordinate-semantics-registry",
          "role": "coordinate-semantics-registry",
          "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/output/contracts/coordinate-semantics-registry.json"
        },
        {
          "digest": {
            "algorithm": "sha256",
            "value": "9527b4d6c87152f834f2beefc7260e320ea8d928e1ee84a1ef1d82ec29c2c1e7"
          },
          "id": "artifact.alignment-evidence",
          "role": "alignment-evidence",
          "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/output/alignment-evidence.json"
        }
      ],
      "source_reports": {
        "reference": {
          "admission_basis": "native_sofrs_v2",
          "artifact": {
            "digest": {
              "algorithm": "sha256",
              "value": "166b0de4269bbde554baaac4b07214436942d3a9bfcecd1c073c2ee924c33ae1"
            },
            "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/inputs/reference/report.json"
          },
          "comparison_role_basis": {
            "authority_status": "DECLARED",
            "basis_kind": "declared_baseline_only",
            "evidence_artifacts": [
              "artifact.reference-report",
              "artifact.reference-report-validation-receipt"
            ],
            "negative_boundary": [
              "The selected reference is not thereby a truth oracle."
            ],
            "role": "reference",
            "scope": "Selected SOFRS report role for this runtime comparison."
          },
          "label": "External adapter reference: finite-state-transition-system",
          "record_kind": "strict_sof",
          "report_id": "example.finite-state-adapter.finite-state.transition.reference.sofreport",
          "sofrs_version": "2.0",
          "validation_receipt": {
            "digest": {
              "algorithm": "sha256",
              "value": "ef16e622b0e9e05d8f621d87792d100cdb701edd0ae169fcc4bed75cbc23b2b5"
            },
            "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/inputs/reference/receipt.json"
          }
        },
        "target": {
          "admission_basis": "native_sofrs_v2",
          "artifact": {
            "digest": {
              "algorithm": "sha256",
              "value": "bc783aee6c4705ea535a4e8bfd97c696e26b4db3fe81c8d4deb76dbe93dc29dd"
            },
            "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/inputs/target/report.json"
          },
          "comparison_role_basis": {
            "authority_status": "DECLARED",
            "basis_kind": "declared_baseline_only",
            "evidence_artifacts": [
              "artifact.target-report",
              "artifact.target-report-validation-receipt"
            ],
            "negative_boundary": [
              "The selected reference is not thereby a truth oracle."
            ],
            "role": "target",
            "scope": "Selected SOFRS report role for this runtime comparison."
          },
          "label": "External adapter reference: finite-state-transition-system",
          "record_kind": "strict_sof",
          "report_id": "example.finite-state-adapter.finite-state.transition.target.sofreport",
          "sofrs_version": "2.0",
          "validation_receipt": {
            "digest": {
              "algorithm": "sha256",
              "value": "89c7fc342ae0cdd56f2bed4bf0b62a213f271fd87747de97f86d70cf7d14b14b"
            },
            "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/inputs/target/receipt.json"
          }
        }
      },
      "system": "External adapter identity comparison"
    }
  },
  "artifacts": [
    {
      "artifact_id": "sofaudit:40125672cfd042ea",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/comparison/result.sofaudit.json",
      "sha256": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    }
  ]
}
```

### Call 12: sof_validate

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "validation_kind": "sofaudit_receipt",
  "artifact": "matrix/agent-a/comparison/validation-receipt.json",
  "request_id": "matrix-agent-a-validate-audit-receipt"
}
```

Result:

```json
{
  "contract_id": "sof-runtime.service-response.v1",
  "request_id": "matrix-agent-a-validate-audit-receipt",
  "job_id": "job:5a8c90195ac64eb6bf45623035dee727",
  "semantic_run_id": "semrun:sha256:7ba2c00c2c6f4f348db7a1b28cf0b587ffb15cbca6a6189e6910ac4e0b46d44b",
  "workspace_id": "mcp-adopter-20260811a",
  "operation": "validate",
  "status": "succeeded",
  "result": {
    "validation_kind": "sofaudit_receipt",
    "validator_result": {
      "artifact_closure": {
        "artifact_count": 11,
        "closure_digest": {
          "algorithm": "sha256",
          "value": "976eb2de28ed789cbd098bbcf6a200dd18391e5782c048c85e3fa77a86134c81"
        },
        "ordered_artifacts": [
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
              },
              "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/output/result.sofaudit.json"
            },
            "role": "audit"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "166b0de4269bbde554baaac4b07214436942d3a9bfcecd1c073c2ee924c33ae1"
              },
              "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/inputs/reference/report.json"
            },
            "role": "reference-report"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "bc783aee6c4705ea535a4e8bfd97c696e26b4db3fe81c8d4deb76dbe93dc29dd"
              },
              "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/inputs/target/report.json"
            },
            "role": "target-report"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "ef16e622b0e9e05d8f621d87792d100cdb701edd0ae169fcc4bed75cbc23b2b5"
              },
              "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/inputs/reference/receipt.json"
            },
            "role": "reference-report-validation-receipt"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "89c7fc342ae0cdd56f2bed4bf0b62a213f271fd87747de97f86d70cf7d14b14b"
              },
              "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/inputs/target/receipt.json"
            },
            "role": "target-report-validation-receipt"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "5b9e8e73d6df573d858855ad3527ebc1739599b7d6fdc478eaf13f285a436502"
              },
              "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/inputs/alignment.json"
            },
            "role": "alignment-input"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "bb84d2840a55b3278e509418ffd53a1b98a96fe5ee0c7304d0f5f109d52e9bd1"
              },
              "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/inputs/comparison-profile.json"
            },
            "role": "audit-profile"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "1d2dc24ae56cfb364b02bccf8c0c3068138e6d07682cf4b0561ec75f765c6d48"
              },
              "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/output/contracts/coordinate-semantics-registry.json"
            },
            "role": "coordinate-semantics-registry"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "9527b4d6c87152f834f2beefc7260e320ea8d928e1ee84a1ef1d82ec29c2c1e7"
              },
              "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/output/alignment-evidence.json"
            },
            "role": "alignment-evidence"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "6664701a28865264bbe1c0ee5107e2bb3b95d7fd8054005d60b40a1a59609880"
              },
              "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/output/validator/sofaudit-validator.py"
            },
            "role": "validator-implementation"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "1f2d9bd125fa6dbd27303e86ad5aebbb80821dcc4ee907cd65a8e793cbde3db9"
              },
              "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/output/contracts/sofaudit-validation-receipt.schema.json"
            },
            "role": "validation-receipt-contract"
          }
        ]
      },
      "artifact_type": "sofaudit_validation_receipt",
      "audit": {
        "artifact": {
          "digest": {
            "algorithm": "sha256",
            "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
          },
          "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/output/result.sofaudit.json"
        },
        "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
        "sofaudit_version": "2.0"
      },
      "checks": [
        {
          "check_id": "schema-validation",
          "status": "PASS"
        },
        {
          "check_id": "artifact-digest-closure",
          "status": "PASS"
        },
        {
          "check_id": "source-report-receipt-validation",
          "status": "PASS"
        },
        {
          "check_id": "role-regime-profile-closure",
          "status": "PASS"
        },
        {
          "check_id": "alignment-property-recomputation",
          "status": "PASS"
        },
        {
          "check_id": "guard-coordinate-coupling",
          "status": "PASS"
        },
        {
          "check_id": "comparison-basis-recomputation",
          "status": "PASS"
        },
        {
          "check_id": "claim-certificate-compatibility",
          "status": "PASS"
        }
      ],
      "negative_boundaries": [
        "This receipt establishes SOFAUDIT protocol conformance only; it does not establish reference truth or action meaning."
      ],
      "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
      "receipt_version": "2.0",
      "status": "PASS",
      "validator": {
        "implementation": {
          "digest": {
            "algorithm": "sha256",
            "value": "6664701a28865264bbe1c0ee5107e2bb3b95d7fd8054005d60b40a1a59609880"
          },
          "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/output/validator/sofaudit-validator.py"
        },
        "receipt_contract": {
          "digest": {
            "algorithm": "sha256",
            "value": "1f2d9bd125fa6dbd27303e86ad5aebbb80821dcc4ee907cd65a8e793cbde3db9"
          },
          "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/output/contracts/sofaudit-validation-receipt.schema.json"
        },
        "validator_id": "sofaudit.runtime-semantic-validator.v2",
        "validator_version": "2.0"
      }
    }
  },
  "artifacts": [
    {
      "artifact_id": "sofaudit_receipt:8cb9ccbce7fa6711",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/comparison/validation-receipt.json",
      "sha256": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    }
  ]
}
```

### Call 13: sof_interpret

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "audit": "matrix/agent-a/comparison/result.sofaudit.json",
  "receipt": "matrix/agent-a/comparison/validation-receipt.json",
  "context": "case/action/context.json",
  "policy": "case/action/policy.json",
  "out_directory": "matrix/agent-a/interpretation",
  "request_id": "matrix-agent-a-interpret"
}
```

Result:

```json
{
  "contract_id": "sof-runtime.service-response.v1",
  "request_id": "matrix-agent-a-interpret",
  "job_id": "job:95bf0c70db8247b5bf9d6c1a78d71140",
  "semantic_run_id": "semrun:sha256:96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636",
  "workspace_id": "mcp-adopter-20260811a",
  "operation": "interpret",
  "status": "succeeded",
  "result": {
    "action_record_id": "action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
    "candidate_actions": [
      {
        "action_id": "investigate:operator.support.summary",
        "disposition": "Investigate"
      },
      {
        "action_id": "requestevidence:operator.support.summary",
        "disposition": "RequestEvidence"
      }
    ]
  },
  "artifacts": [
    {
      "artifact_id": "sofaction:63be634de4baf64d",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/interpretation/result.sofaction.json",
      "sha256": "63be634de4baf64dc85da3a3ca168933676ba94a2d4b89553da7db18bd03ca4d",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    },
    {
      "artifact_id": "sofaction_validation_receipt:447c62bf1a180031",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/interpretation/validation-receipt.json",
      "sha256": "447c62bf1a1800318051907539bc36339974e68df2f2f2ddedf60e4f0cf34fe2",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    }
  ]
}
```

### Call 14: sof_validate

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "validation_kind": "sofaction",
  "artifact": "matrix/agent-a/interpretation/result.sofaction.json",
  "request_id": "matrix-agent-a-validate-action"
}
```

Result:

```json
{
  "contract_id": "sof-runtime.service-response.v1",
  "request_id": "matrix-agent-a-validate-action",
  "job_id": "job:1fcd60fb01044b43bae0bda90007962a",
  "semantic_run_id": "semrun:sha256:92bcae20532d74d21ecbe1582fc25bbaa898f166e95f79cb9a61ac1bb82fef08",
  "workspace_id": "mcp-adopter-20260811a",
  "operation": "validate",
  "status": "succeeded",
  "result": {
    "validation_kind": "sofaction",
    "validator_result": {
      "action_context": {
        "actor": {
          "actor_id": "domain-reviewer",
          "description": "A domain expert reviewing a finite-state transition comparison.",
          "role": "domain reviewer"
        },
        "authority": {
          "actor_ids": [
            "domain-reviewer"
          ],
          "authority_id": "finite-state-review-authority",
          "description": "Declared review authority for this bounded diagnostic comparison.",
          "scope_ids": [
            "finite-state-comparison-scope"
          ],
          "status": "declared"
        },
        "comparison_role": "diagnostic_comparison",
        "constraints": [
          {
            "constraint_id": "human-review-required",
            "statement": "No candidate is an execution command and no action is authorized by this context.",
            "status": "binding"
          }
        ],
        "context_contract_version": "2.0",
        "context_id": "finite-state-review-context-v1",
        "context_revision": "finite-state-review-r1",
        "contract_status": "nonconforming",
        "evaluator_qualification_note": "Qualification is declared for this finite-state review only; it is not a general domain certificate.",
        "mismatch_direction": "reference_to_target",
        "negative_boundary": [
          "The context does not establish reference truth, severity, action correctness, or authorization."
        ],
        "objective": {
          "objective_id": "review-direct-support",
          "statement": "Determine whether the observed direct-support difference warrants bounded follow-up evidence."
        },
        "scope": {
          "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
          "description": "The declared direct-support coordinate of the external finite-state comparison.",
          "scope_id": "finite-state-comparison-scope"
        },
        "time": {
          "basis": "The two source snapshots bound the comparison.",
          "end": null,
          "kind": "source_snapshot",
          "start": null,
          "timezone": null
        },
        "transformation_contract_refs": [],
        "uncertainty_conditions": [
          "A mismatch is not a certified defect.",
          "Post-action outcomes require a new audit."
        ]
      },
      "action_record_id": "action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
      "audit_projection": {
        "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
        "signature": {
          "operator.support.summary": {
            "certificate_class": null,
            "claim_status": "Computational Observation",
            "claim_target": "comparison_relation",
            "classification_source": "audit_engine",
            "comparison_state": "MISMATCH",
            "coordinate_family": "operator",
            "report_item_binding": {
              "binding_state": "paired",
              "reason": null,
              "reference_item_ref": {
                "artifact_digest": {
                  "algorithm": "sha256",
                  "value": "166b0de4269bbde554baaac4b07214436942d3a9bfcecd1c073c2ee924c33ae1"
                },
                "item_kind": "claim",
                "report_id": "example.finite-state-adapter.finite-state.transition.reference.sofreport",
                "report_item_id": "report.claim-item.0000",
                "source_output_item_id": "compiler.item.0000"
              },
              "target_item_ref": {
                "artifact_digest": {
                  "algorithm": "sha256",
                  "value": "bc783aee6c4705ea535a4e8bfd97c696e26b4db3fe81c8d4deb76dbe93dc29dd"
                },
                "item_kind": "claim",
                "report_id": "example.finite-state-adapter.finite-state.transition.target.sofreport",
                "report_item_id": "report.claim-item.0000",
                "source_output_item_id": "compiler.item.0000"
              }
            },
            "result_state": "OBSERVED",
            "source_artifact_ids": [
              "artifact.alignment-evidence"
            ],
            "value": {
              "delta": 1,
              "metric_result": {
                "metric_id": "absolute-difference",
                "status": "computed",
                "value": 1
              },
              "normalized_reference_value": {
                "support_count": 2
              },
              "normalized_target_value": {
                "support_count": 3
              },
              "oracle_ref": null,
              "policy_refs": [],
              "reference_value": {
                "support_count": 2
              },
              "relation": "mismatch",
              "target_value": {
                "support_count": 3
              },
              "unit": "support pairs"
            },
            "value_schema_id": "operator.support.v1"
          }
        }
      },
      "candidate_action_set": {
        "actions": [
          {
            "action_id": "investigate:operator.support.summary",
            "audit_coordinate_refs": [
              {
                "carrier": "operator",
                "comparison_state": "MISMATCH",
                "coordinate_id": "operator.support.summary"
              }
            ],
            "authorization_state": "not_requested",
            "carrier": "operator",
            "context_ref": "finite-state-review-context-v1",
            "declared_risk_considerations": [
              "the candidate may be irrelevant after context or policy review",
              "an observed post-action change would require a new Paper XIII audit"
            ],
            "disposition": "Investigate",
            "evidence_refs": [
              {
                "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
                "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
                "digest": {
                  "algorithm": "sha256",
                  "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
                },
                "sofaudit_version": "2.0",
                "validation_receipt": {
                  "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
                  "digest": {
                    "algorithm": "sha256",
                    "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
                  },
                  "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
                  "validator_id": "sofaudit.runtime-semantic-validator.v2",
                  "validator_version": "2.0"
                }
              }
            ],
            "intended_diagnostic_consequence": {
              "statements": [
                "obtain evidence relevant to the declared comparison coordinate"
              ],
              "status": "intended_diagnostic_consequence"
            },
            "negative_boundary": [
              "This is a candidate disposition, not an execution command or correctness claim."
            ],
            "policy_rule_refs": [
              "mismatch-review"
            ],
            "preconditions": [
              "the source audit projection and coordinate state remain unchanged",
              "a domain owner confirms the candidate is applicable"
            ],
            "reversibility": "unknown",
            "supported_by_interpretations": [
              "interp:action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport:operator.support.summary"
            ],
            "target": "operator.support.summary"
          },
          {
            "action_id": "requestevidence:operator.support.summary",
            "audit_coordinate_refs": [
              {
                "carrier": "operator",
                "comparison_state": "MISMATCH",
                "coordinate_id": "operator.support.summary"
              }
            ],
            "authorization_state": "not_requested",
            "carrier": "operator",
            "context_ref": "finite-state-review-context-v1",
            "declared_risk_considerations": [
              "the candidate may be irrelevant after context or policy review",
              "an observed post-action change would require a new Paper XIII audit"
            ],
            "disposition": "RequestEvidence",
            "evidence_refs": [
              {
                "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
                "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
                "digest": {
                  "algorithm": "sha256",
                  "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
                },
                "sofaudit_version": "2.0",
                "validation_receipt": {
                  "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
                  "digest": {
                    "algorithm": "sha256",
                    "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
                  },
                  "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
                  "validator_id": "sofaudit.runtime-semantic-validator.v2",
                  "validator_version": "2.0"
                }
              }
            ],
            "intended_diagnostic_consequence": {
              "statements": [
                "obtain evidence relevant to the declared comparison coordinate"
              ],
              "status": "intended_diagnostic_consequence"
            },
            "negative_boundary": [
              "This is a candidate disposition, not an execution command or correctness claim."
            ],
            "policy_rule_refs": [
              "mismatch-review"
            ],
            "preconditions": [
              "the source audit projection and coordinate state remain unchanged",
              "a domain owner confirms the candidate is applicable"
            ],
            "reversibility": "unknown",
            "supported_by_interpretations": [
              "interp:action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport:operator.support.summary"
            ],
            "target": "operator.support.summary"
          }
        ],
        "count": 2
      },
      "claim_note": "This object records policy-relative interpretation and bounded candidates; it does not select or execute an action.",
      "claim_status": "Computational Certificate",
      "context_admission": {
        "applicability": "applicable",
        "completeness": "complete",
        "contract_validation": "admitted",
        "missing_fields": [],
        "rationale": "ActionContext supplied by the caller.",
        "status": "admitted"
      },
      "disposition_result": {
        "candidate_action_ids": [
          "investigate:operator.support.summary",
          "requestevidence:operator.support.summary"
        ],
        "interpretation_ids": [
          "interp:action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport:operator.support.summary"
        ],
        "kind": "candidate_action_set",
        "reason": "The admitted policy supports bounded candidate dispositions."
      },
      "failure_modes": [
        "difference is not defect, severity, or action without the admitted context and policy",
        "candidate actions are not execution commands, authorization, feasibility, or causal-effect claims",
        "post-action facts require a new Paper XIII audit"
      ],
      "interpretation_records": [
        {
          "assessment_kind": "defect_candidate",
          "assessment_note": "A mismatch is a policy-relative review status, not a certified defect.",
          "audit_coordinate_refs": [
            {
              "carrier": "operator",
              "comparison_state": "MISMATCH",
              "coordinate_id": "operator.support.summary"
            }
          ],
          "context_refs": [
            "finite-state-review-context-v1"
          ],
          "evidence_refs": [
            {
              "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
              "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
              "digest": {
                "algorithm": "sha256",
                "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
              },
              "sofaudit_version": "2.0",
              "validation_receipt": {
                "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
                "digest": {
                  "algorithm": "sha256",
                  "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
                },
                "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
                "validator_id": "sofaudit.runtime-semantic-validator.v2",
                "validator_version": "2.0"
              }
            }
          ],
          "interpretation_id": "interp:action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport:operator.support.summary",
          "negative_boundary": [
            "The candidate is not a certified defect, execution command, or recommendation."
          ],
          "policy_rule_refs": [
            "mismatch-review"
          ],
          "rationale": "A mismatch is a policy-relative review status, not a certified defect.",
          "supported_dispositions": [
            "Investigate",
            "RequestEvidence"
          ],
          "uncertainty": {
            "reasons": [],
            "status": "bounded"
          }
        }
      ],
      "policy_admission": {
        "applicability": "applicable",
        "completeness": "complete",
        "contract_validation": "admitted",
        "missing_fields": [],
        "rationale": "PolicyProfile supplied by the caller and replayed by the runtime.",
        "status": "admitted"
      },
      "policy_profile": {
        "applicability": {
          "comparison_roles": [
            "diagnostic_comparison"
          ],
          "regimes": [
            "strict_vs_strict"
          ]
        },
        "candidate_families": [
          "Investigate",
          "RequestEvidence"
        ],
        "exceptions": [],
        "normative_basis": [
          {
            "basis_id": "difference-is-not-defect",
            "source_ref": {
              "artifact_id": "finite-state-policy-basis",
              "contract_version": "2.0",
              "digest": {
                "algorithm": "sha256",
                "value": "d4d2e837fd974caccbdde47eccacfad0337d24d3fb9537aac058d76f549e87df"
              },
              "producer": "external-adapter-example",
              "role": "policy_source",
              "uri": "artifact://examples/external-adapter-finite-state/action/policy-basis.json"
            },
            "statement": "A mismatch is a policy-relative review status, not a certified defect."
          }
        ],
        "policy_contract_version": "2.0",
        "policy_id": "finite-state-review-policy",
        "policy_revision": "finite-state-review-r1",
        "precedence_edges": [],
        "rules": [
          {
            "allowed_dispositions": [
              "Investigate",
              "RequestEvidence"
            ],
            "assessment_kind": "defect_candidate",
            "assessment_note": "A mismatch is a policy-relative review status, not a certified defect.",
            "negative_boundary": [
              "The candidate is not a certified defect, execution command, or recommendation."
            ],
            "rule_id": "mismatch-review",
            "uncertainty_status": "bounded",
            "when": {
              "coordinate_id": "*",
              "op": "coordinate_state_is",
              "predicate_version": "1.0",
              "value": "MISMATCH"
            }
          },
          {
            "allowed_dispositions": [
              "NoAction"
            ],
            "assessment_kind": "no_action_indicated",
            "assessment_note": "Equality on the requested coordinate indicates no action under this policy.",
            "negative_boundary": [
              "Equality does not establish global equivalence or safety."
            ],
            "rule_id": "aligned-no-action",
            "uncertainty_status": "bounded",
            "when": {
              "coordinate_id": "*",
              "op": "coordinate_state_is",
              "predicate_version": "1.0",
              "value": "ALIGNED"
            }
          }
        ],
        "selection_status": "downstream",
        "uncertainty_policy": {
          "incomparable": "propagate_unresolved",
          "no_applicable_rule": "no_disposition",
          "not_declared": "propagate_unresolved",
          "rule_conflict": "unresolved_disposition",
          "unavailable_coordinate": "non_satisfying",
          "unresolved_predicate": "propagate_unresolved",
          "version": "1.0"
        }
      },
      "record_basis": {
        "basis_kind": "protocol_trace",
        "causal_status": "not_claimed",
        "evidence_refs": [
          {
            "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
            "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
            "digest": {
              "algorithm": "sha256",
              "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
            },
            "sofaudit_version": "2.0",
            "validation_receipt": {
              "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
              "digest": {
                "algorithm": "sha256",
                "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
              },
              "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
              "validator_id": "sofaudit.runtime-semantic-validator.v2",
              "validator_version": "2.0"
            }
          }
        ],
        "negative_boundary": [
          "Protocol trace completeness does not establish policy validity or action effectiveness."
        ]
      },
      "record_class": "decision_trace_certificate",
      "record_type": "sofaction",
      "sofaction_version": "2.0",
      "source_audit": {
        "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
        "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
        "digest": {
          "algorithm": "sha256",
          "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
        },
        "sofaudit_version": "2.0",
        "validation_receipt": {
          "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
          "digest": {
            "algorithm": "sha256",
            "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
          },
          "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
          "validator_id": "sofaudit.runtime-semantic-validator.v2",
          "validator_version": "2.0"
        }
      }
    }
  },
  "artifacts": [
    {
      "artifact_id": "sofaction:63be634de4baf64d",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/interpretation/result.sofaction.json",
      "sha256": "63be634de4baf64dc85da3a3ca168933676ba94a2d4b89553da7db18bd03ca4d",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    }
  ]
}
```

### Call 15: sof_validate

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "validation_kind": "sofaction_receipt",
  "artifact": "matrix/agent-a/interpretation/validation-receipt.json",
  "request_id": "matrix-agent-a-validate-action-receipt"
}
```

Result:

```json
{
  "contract_id": "sof-runtime.service-response.v1",
  "request_id": "matrix-agent-a-validate-action-receipt",
  "job_id": "job:634c31b951974c4ea9ba06e75d0e2366",
  "semantic_run_id": "semrun:sha256:bbc77d0b731ab58f66513463137eb14be9a25137dda4207955d5e2be0b321033",
  "workspace_id": "mcp-adopter-20260811a",
  "operation": "validate",
  "status": "succeeded",
  "result": {
    "validation_kind": "sofaction_receipt",
    "validator_result": {
      "action": {
        "action_record_id": "action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
        "artifact": {
          "digest": {
            "algorithm": "sha256",
            "value": "63be634de4baf64dc85da3a3ca168933676ba94a2d4b89553da7db18bd03ca4d"
          },
          "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/result.sofaction.json"
        },
        "sofaction_version": "2.0"
      },
      "artifact_closure": {
        "artifact_count": 3,
        "closure_digest": {
          "algorithm": "sha256",
          "value": "719ddf68ed79f3c735d9ed8320dfda685175b5ecf429ed781bf93e1f96482108"
        },
        "ordered_artifacts": [
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "63be634de4baf64dc85da3a3ca168933676ba94a2d4b89553da7db18bd03ca4d"
              },
              "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/result.sofaction.json"
            },
            "role": "action"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "f64aaf1769054de504fac8c8beefbc2b0e174e2c96cf9f421ec5f68072ec57fe"
              },
              "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/validator/sofaction-validator.py"
            },
            "role": "validator-implementation"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "56e535c97a6370d3e933738b8b356038bd81394aa9c467f8614a1cf0d49db734"
              },
              "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/contracts/sofaction-validation-receipt.schema.json"
            },
            "role": "validation-receipt-contract"
          }
        ]
      },
      "artifact_type": "sofaction_validation_receipt",
      "checks": [
        {
          "check_id": "schema-validation",
          "status": "PASS"
        },
        {
          "check_id": "artifact-digest-closure",
          "status": "PASS"
        },
        {
          "check_id": "action-context-policy-admission",
          "status": "PASS"
        },
        {
          "check_id": "audit-projection-preservation",
          "status": "PASS"
        },
        {
          "check_id": "predicate-replay",
          "status": "PASS"
        },
        {
          "check_id": "candidate-set-regeneration",
          "status": "PASS"
        },
        {
          "check_id": "disposition-closure",
          "status": "PASS"
        },
        {
          "check_id": "authorization-boundary",
          "status": "PASS"
        }
      ],
      "negative_boundaries": [
        "This receipt establishes interpretation and candidate-set protocol conformance only; it does not establish policy correctness, action feasibility, authorization, or causal effect."
      ],
      "receipt_id": "receipt.action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaction-v2",
      "receipt_version": "2.0",
      "status": "PASS",
      "validator": {
        "implementation": {
          "digest": {
            "algorithm": "sha256",
            "value": "f64aaf1769054de504fac8c8beefbc2b0e174e2c96cf9f421ec5f68072ec57fe"
          },
          "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/validator/sofaction-validator.py"
        },
        "receipt_contract": {
          "digest": {
            "algorithm": "sha256",
            "value": "56e535c97a6370d3e933738b8b356038bd81394aa9c467f8614a1cf0d49db734"
          },
          "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/contracts/sofaction-validation-receipt.schema.json"
        },
        "validator_id": "sofaction.runtime-validator.v2",
        "validator_version": "2.0"
      }
    }
  },
  "artifacts": [
    {
      "artifact_id": "sofaction_receipt:447c62bf1a180031",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/interpretation/validation-receipt.json",
      "sha256": "447c62bf1a1800318051907539bc36339974e68df2f2f2ddedf60e4f0cf34fe2",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    }
  ]
}
```

### Call 16: sof_get_artifact

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "path": "matrix/agent-a/interpretation/result.sofaction.json",
  "sha256": "63be634de4baf64dc85da3a3ca168933676ba94a2d4b89553da7db18bd03ca4d"
}
```

Result:

```json
{
  "artifact": {
    "artifact_id": "retrieved_artifact:63be634de4baf64d",
    "media_type": "application/json",
    "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/interpretation/result.sofaction.json",
    "sha256": "63be634de4baf64dc85da3a3ca168933676ba94a2d4b89553da7db18bd03ca4d",
    "schema_id": null,
    "producer": "sof-runtime.service@0.3.0.dev0",
    "input_refs": []
  },
  "content_encoding": "json",
  "content": {
    "action_context": {
      "actor": {
        "actor_id": "domain-reviewer",
        "description": "A domain expert reviewing a finite-state transition comparison.",
        "role": "domain reviewer"
      },
      "authority": {
        "actor_ids": [
          "domain-reviewer"
        ],
        "authority_id": "finite-state-review-authority",
        "description": "Declared review authority for this bounded diagnostic comparison.",
        "scope_ids": [
          "finite-state-comparison-scope"
        ],
        "status": "declared"
      },
      "comparison_role": "diagnostic_comparison",
      "constraints": [
        {
          "constraint_id": "human-review-required",
          "statement": "No candidate is an execution command and no action is authorized by this context.",
          "status": "binding"
        }
      ],
      "context_contract_version": "2.0",
      "context_id": "finite-state-review-context-v1",
      "context_revision": "finite-state-review-r1",
      "contract_status": "nonconforming",
      "evaluator_qualification_note": "Qualification is declared for this finite-state review only; it is not a general domain certificate.",
      "mismatch_direction": "reference_to_target",
      "negative_boundary": [
        "The context does not establish reference truth, severity, action correctness, or authorization."
      ],
      "objective": {
        "objective_id": "review-direct-support",
        "statement": "Determine whether the observed direct-support difference warrants bounded follow-up evidence."
      },
      "scope": {
        "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
        "description": "The declared direct-support coordinate of the external finite-state comparison.",
        "scope_id": "finite-state-comparison-scope"
      },
      "time": {
        "basis": "The two source snapshots bound the comparison.",
        "end": null,
        "kind": "source_snapshot",
        "start": null,
        "timezone": null
      },
      "transformation_contract_refs": [],
      "uncertainty_conditions": [
        "A mismatch is not a certified defect.",
        "Post-action outcomes require a new audit."
      ]
    },
    "action_record_id": "action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
    "audit_projection": {
      "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
      "signature": {
        "operator.support.summary": {
          "certificate_class": null,
          "claim_status": "Computational Observation",
          "claim_target": "comparison_relation",
          "classification_source": "audit_engine",
          "comparison_state": "MISMATCH",
          "coordinate_family": "operator",
          "report_item_binding": {
            "binding_state": "paired",
            "reason": null,
            "reference_item_ref": {
              "artifact_digest": {
                "algorithm": "sha256",
                "value": "166b0de4269bbde554baaac4b07214436942d3a9bfcecd1c073c2ee924c33ae1"
              },
              "item_kind": "claim",
              "report_id": "example.finite-state-adapter.finite-state.transition.reference.sofreport",
              "report_item_id": "report.claim-item.0000",
              "source_output_item_id": "compiler.item.0000"
            },
            "target_item_ref": {
              "artifact_digest": {
                "algorithm": "sha256",
                "value": "bc783aee6c4705ea535a4e8bfd97c696e26b4db3fe81c8d4deb76dbe93dc29dd"
              },
              "item_kind": "claim",
              "report_id": "example.finite-state-adapter.finite-state.transition.target.sofreport",
              "report_item_id": "report.claim-item.0000",
              "source_output_item_id": "compiler.item.0000"
            }
          },
          "result_state": "OBSERVED",
          "source_artifact_ids": [
            "artifact.alignment-evidence"
          ],
          "value": {
            "delta": 1,
            "metric_result": {
              "metric_id": "absolute-difference",
              "status": "computed",
              "value": 1
            },
            "normalized_reference_value": {
              "support_count": 2
            },
            "normalized_target_value": {
              "support_count": 3
            },
            "oracle_ref": null,
            "policy_refs": [],
            "reference_value": {
              "support_count": 2
            },
            "relation": "mismatch",
            "target_value": {
              "support_count": 3
            },
            "unit": "support pairs"
          },
          "value_schema_id": "operator.support.v1"
        }
      }
    },
    "candidate_action_set": {
      "actions": [
        {
          "action_id": "investigate:operator.support.summary",
          "audit_coordinate_refs": [
            {
              "carrier": "operator",
              "comparison_state": "MISMATCH",
              "coordinate_id": "operator.support.summary"
            }
          ],
          "authorization_state": "not_requested",
          "carrier": "operator",
          "context_ref": "finite-state-review-context-v1",
          "declared_risk_considerations": [
            "the candidate may be irrelevant after context or policy review",
            "an observed post-action change would require a new Paper XIII audit"
          ],
          "disposition": "Investigate",
          "evidence_refs": [
            {
              "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
              "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
              "digest": {
                "algorithm": "sha256",
                "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
              },
              "sofaudit_version": "2.0",
              "validation_receipt": {
                "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
                "digest": {
                  "algorithm": "sha256",
                  "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
                },
                "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
                "validator_id": "sofaudit.runtime-semantic-validator.v2",
                "validator_version": "2.0"
              }
            }
          ],
          "intended_diagnostic_consequence": {
            "statements": [
              "obtain evidence relevant to the declared comparison coordinate"
            ],
            "status": "intended_diagnostic_consequence"
          },
          "negative_boundary": [
            "This is a candidate disposition, not an execution command or correctness claim."
          ],
          "policy_rule_refs": [
            "mismatch-review"
          ],
          "preconditions": [
            "the source audit projection and coordinate state remain unchanged",
            "a domain owner confirms the candidate is applicable"
          ],
          "reversibility": "unknown",
          "supported_by_interpretations": [
            "interp:action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport:operator.support.summary"
          ],
          "target": "operator.support.summary"
        },
        {
          "action_id": "requestevidence:operator.support.summary",
          "audit_coordinate_refs": [
            {
              "carrier": "operator",
              "comparison_state": "MISMATCH",
              "coordinate_id": "operator.support.summary"
            }
          ],
          "authorization_state": "not_requested",
          "carrier": "operator",
          "context_ref": "finite-state-review-context-v1",
          "declared_risk_considerations": [
            "the candidate may be irrelevant after context or policy review",
            "an observed post-action change would require a new Paper XIII audit"
          ],
          "disposition": "RequestEvidence",
          "evidence_refs": [
            {
              "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
              "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
              "digest": {
                "algorithm": "sha256",
                "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
              },
              "sofaudit_version": "2.0",
              "validation_receipt": {
                "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
                "digest": {
                  "algorithm": "sha256",
                  "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
                },
                "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
                "validator_id": "sofaudit.runtime-semantic-validator.v2",
                "validator_version": "2.0"
              }
            }
          ],
          "intended_diagnostic_consequence": {
            "statements": [
              "obtain evidence relevant to the declared comparison coordinate"
            ],
            "status": "intended_diagnostic_consequence"
          },
          "negative_boundary": [
            "This is a candidate disposition, not an execution command or correctness claim."
          ],
          "policy_rule_refs": [
            "mismatch-review"
          ],
          "preconditions": [
            "the source audit projection and coordinate state remain unchanged",
            "a domain owner confirms the candidate is applicable"
          ],
          "reversibility": "unknown",
          "supported_by_interpretations": [
            "interp:action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport:operator.support.summary"
          ],
          "target": "operator.support.summary"
        }
      ],
      "count": 2
    },
    "claim_note": "This object records policy-relative interpretation and bounded candidates; it does not select or execute an action.",
    "claim_status": "Computational Certificate",
    "context_admission": {
      "applicability": "applicable",
      "completeness": "complete",
      "contract_validation": "admitted",
      "missing_fields": [],
      "rationale": "ActionContext supplied by the caller.",
      "status": "admitted"
    },
    "disposition_result": {
      "candidate_action_ids": [
        "investigate:operator.support.summary",
        "requestevidence:operator.support.summary"
      ],
      "interpretation_ids": [
        "interp:action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport:operator.support.summary"
      ],
      "kind": "candidate_action_set",
      "reason": "The admitted policy supports bounded candidate dispositions."
    },
    "failure_modes": [
      "difference is not defect, severity, or action without the admitted context and policy",
      "candidate actions are not execution commands, authorization, feasibility, or causal-effect claims",
      "post-action facts require a new Paper XIII audit"
    ],
    "interpretation_records": [
      {
        "assessment_kind": "defect_candidate",
        "assessment_note": "A mismatch is a policy-relative review status, not a certified defect.",
        "audit_coordinate_refs": [
          {
            "carrier": "operator",
            "comparison_state": "MISMATCH",
            "coordinate_id": "operator.support.summary"
          }
        ],
        "context_refs": [
          "finite-state-review-context-v1"
        ],
        "evidence_refs": [
          {
            "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
            "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
            "digest": {
              "algorithm": "sha256",
              "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
            },
            "sofaudit_version": "2.0",
            "validation_receipt": {
              "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
              "digest": {
                "algorithm": "sha256",
                "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
              },
              "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
              "validator_id": "sofaudit.runtime-semantic-validator.v2",
              "validator_version": "2.0"
            }
          }
        ],
        "interpretation_id": "interp:action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport:operator.support.summary",
        "negative_boundary": [
          "The candidate is not a certified defect, execution command, or recommendation."
        ],
        "policy_rule_refs": [
          "mismatch-review"
        ],
        "rationale": "A mismatch is a policy-relative review status, not a certified defect.",
        "supported_dispositions": [
          "Investigate",
          "RequestEvidence"
        ],
        "uncertainty": {
          "reasons": [],
          "status": "bounded"
        }
      }
    ],
    "policy_admission": {
      "applicability": "applicable",
      "completeness": "complete",
      "contract_validation": "admitted",
      "missing_fields": [],
      "rationale": "PolicyProfile supplied by the caller and replayed by the runtime.",
      "status": "admitted"
    },
    "policy_profile": {
      "applicability": {
        "comparison_roles": [
          "diagnostic_comparison"
        ],
        "regimes": [
          "strict_vs_strict"
        ]
      },
      "candidate_families": [
        "Investigate",
        "RequestEvidence"
      ],
      "exceptions": [],
      "normative_basis": [
        {
          "basis_id": "difference-is-not-defect",
          "source_ref": {
            "artifact_id": "finite-state-policy-basis",
            "contract_version": "2.0",
            "digest": {
              "algorithm": "sha256",
              "value": "d4d2e837fd974caccbdde47eccacfad0337d24d3fb9537aac058d76f549e87df"
            },
            "producer": "external-adapter-example",
            "role": "policy_source",
            "uri": "artifact://examples/external-adapter-finite-state/action/policy-basis.json"
          },
          "statement": "A mismatch is a policy-relative review status, not a certified defect."
        }
      ],
      "policy_contract_version": "2.0",
      "policy_id": "finite-state-review-policy",
      "policy_revision": "finite-state-review-r1",
      "precedence_edges": [],
      "rules": [
        {
          "allowed_dispositions": [
            "Investigate",
            "RequestEvidence"
          ],
          "assessment_kind": "defect_candidate",
          "assessment_note": "A mismatch is a policy-relative review status, not a certified defect.",
          "negative_boundary": [
            "The candidate is not a certified defect, execution command, or recommendation."
          ],
          "rule_id": "mismatch-review",
          "uncertainty_status": "bounded",
          "when": {
            "coordinate_id": "*",
            "op": "coordinate_state_is",
            "predicate_version": "1.0",
            "value": "MISMATCH"
          }
        },
        {
          "allowed_dispositions": [
            "NoAction"
          ],
          "assessment_kind": "no_action_indicated",
          "assessment_note": "Equality on the requested coordinate indicates no action under this policy.",
          "negative_boundary": [
            "Equality does not establish global equivalence or safety."
          ],
          "rule_id": "aligned-no-action",
          "uncertainty_status": "bounded",
          "when": {
            "coordinate_id": "*",
            "op": "coordinate_state_is",
            "predicate_version": "1.0",
            "value": "ALIGNED"
          }
        }
      ],
      "selection_status": "downstream",
      "uncertainty_policy": {
        "incomparable": "propagate_unresolved",
        "no_applicable_rule": "no_disposition",
        "not_declared": "propagate_unresolved",
        "rule_conflict": "unresolved_disposition",
        "unavailable_coordinate": "non_satisfying",
        "unresolved_predicate": "propagate_unresolved",
        "version": "1.0"
      }
    },
    "record_basis": {
      "basis_kind": "protocol_trace",
      "causal_status": "not_claimed",
      "evidence_refs": [
        {
          "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
          "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
          "digest": {
            "algorithm": "sha256",
            "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
          },
          "sofaudit_version": "2.0",
          "validation_receipt": {
            "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
            "digest": {
              "algorithm": "sha256",
              "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
            },
            "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
            "validator_id": "sofaudit.runtime-semantic-validator.v2",
            "validator_version": "2.0"
          }
        }
      ],
      "negative_boundary": [
        "Protocol trace completeness does not establish policy validity or action effectiveness."
      ]
    },
    "record_class": "decision_trace_certificate",
    "record_type": "sofaction",
    "sofaction_version": "2.0",
    "source_audit": {
      "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
      "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
      "digest": {
        "algorithm": "sha256",
        "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
      },
      "sofaudit_version": "2.0",
      "validation_receipt": {
        "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
        "digest": {
          "algorithm": "sha256",
          "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
        },
        "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
        "validator_id": "sofaudit.runtime-semantic-validator.v2",
        "validator_version": "2.0"
      }
    }
  }
}
```

### Call 17: sof_get_receipt

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "path": "matrix/agent-a/interpretation/validation-receipt.json",
  "sha256": "447c62bf1a1800318051907539bc36339974e68df2f2f2ddedf60e4f0cf34fe2"
}
```

Result:

```json
{
  "artifact": {
    "artifact_id": "retrieved_artifact:447c62bf1a180031",
    "media_type": "application/json",
    "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/interpretation/validation-receipt.json",
    "sha256": "447c62bf1a1800318051907539bc36339974e68df2f2f2ddedf60e4f0cf34fe2",
    "schema_id": null,
    "producer": "sof-runtime.service@0.3.0.dev0",
    "input_refs": []
  },
  "content_encoding": "json",
  "content": {
    "action": {
      "action_record_id": "action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
      "artifact": {
        "digest": {
          "algorithm": "sha256",
          "value": "63be634de4baf64dc85da3a3ca168933676ba94a2d4b89553da7db18bd03ca4d"
        },
        "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/result.sofaction.json"
      },
      "sofaction_version": "2.0"
    },
    "artifact_closure": {
      "artifact_count": 3,
      "closure_digest": {
        "algorithm": "sha256",
        "value": "719ddf68ed79f3c735d9ed8320dfda685175b5ecf429ed781bf93e1f96482108"
      },
      "ordered_artifacts": [
        {
          "artifact": {
            "digest": {
              "algorithm": "sha256",
              "value": "63be634de4baf64dc85da3a3ca168933676ba94a2d4b89553da7db18bd03ca4d"
            },
            "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/result.sofaction.json"
          },
          "role": "action"
        },
        {
          "artifact": {
            "digest": {
              "algorithm": "sha256",
              "value": "f64aaf1769054de504fac8c8beefbc2b0e174e2c96cf9f421ec5f68072ec57fe"
            },
            "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/validator/sofaction-validator.py"
          },
          "role": "validator-implementation"
        },
        {
          "artifact": {
            "digest": {
              "algorithm": "sha256",
              "value": "56e535c97a6370d3e933738b8b356038bd81394aa9c467f8614a1cf0d49db734"
            },
            "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/contracts/sofaction-validation-receipt.schema.json"
          },
          "role": "validation-receipt-contract"
        }
      ]
    },
    "artifact_type": "sofaction_validation_receipt",
    "checks": [
      {
        "check_id": "schema-validation",
        "status": "PASS"
      },
      {
        "check_id": "artifact-digest-closure",
        "status": "PASS"
      },
      {
        "check_id": "action-context-policy-admission",
        "status": "PASS"
      },
      {
        "check_id": "audit-projection-preservation",
        "status": "PASS"
      },
      {
        "check_id": "predicate-replay",
        "status": "PASS"
      },
      {
        "check_id": "candidate-set-regeneration",
        "status": "PASS"
      },
      {
        "check_id": "disposition-closure",
        "status": "PASS"
      },
      {
        "check_id": "authorization-boundary",
        "status": "PASS"
      }
    ],
    "negative_boundaries": [
      "This receipt establishes interpretation and candidate-set protocol conformance only; it does not establish policy correctness, action feasibility, authorization, or causal effect."
    ],
    "receipt_id": "receipt.action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaction-v2",
    "receipt_version": "2.0",
    "status": "PASS",
    "validator": {
      "implementation": {
        "digest": {
          "algorithm": "sha256",
          "value": "f64aaf1769054de504fac8c8beefbc2b0e174e2c96cf9f421ec5f68072ec57fe"
        },
        "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/validator/sofaction-validator.py"
      },
      "receipt_contract": {
        "digest": {
          "algorithm": "sha256",
          "value": "56e535c97a6370d3e933738b8b356038bd81394aa9c467f8614a1cf0d49db734"
        },
        "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/contracts/sofaction-validation-receipt.schema.json"
      },
      "validator_id": "sofaction.runtime-validator.v2",
      "validator_version": "2.0"
    }
  }
}
```

### Call 18: sof_explain

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "run_directory": "matrix/agent-a/interpretation",
  "request_id": "matrix-agent-a-explain-final"
}
```

Result:

```json
{
  "contract_id": "sof-runtime.service-response.v1",
  "request_id": "matrix-agent-a-explain-final",
  "job_id": "job:342f09992411478e81e7ed1aebdf348c",
  "semantic_run_id": "semrun:sha256:901b991f4aada9b6876d06c6222282cfa438efab843ac3864edc39121059f789",
  "workspace_id": "mcp-adopter-20260811a",
  "operation": "explain",
  "status": "succeeded",
  "result": {
    "explanation": {
      "explanation_version": "1.0",
      "run_id": "agent-a",
      "run_directory": "<server-workspace>\\mcp-adopter-20260811a\\matrix\\agent-a",
      "workflow": "full_pipeline",
      "realizations": [
        {
          "stage": "realization",
          "run_receipt": {
            "uri": "<server-workspace>\\mcp-adopter-20260811a\\matrix\\agent-a\\reference-realization\\run-receipt.json"
          },
          "source": {
            "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/source/input.json",
            "digest": {
              "algorithm": "sha256",
              "value": "3d6e6716653c74a2e4a6a8e22c7b99b8accdf6df2c39ac79aceae0556df5a20d"
            }
          },
          "source_id": "finite-state.transition.reference",
          "eligibility": "canonical_compilable",
          "canonical_compilable": true,
          "adapter": {
            "id": "example.finite-state-adapter",
            "version": "1.0",
            "domain_id": "finite-state-transition-system",
            "declaration": {
              "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/declaration.json",
              "digest": {
                "algorithm": "sha256",
                "value": "7284ed390f68c27f370bc7470ab3e351b0922150145e01e2a89c34bb158b69d4"
              }
            }
          },
          "declared": {
            "carriers": [
              "sectorization",
              "operator_carrier",
              "operator_system"
            ],
            "observables": [
              "thresholded direct support"
            ],
            "capabilities": [
              "complete finite sectorization",
              "labelled transition operators"
            ],
            "unsupported": [
              "route filtration",
              "positive-word depth",
              "Lie/Hall depth",
              "deformation chart"
            ],
            "sectorization_origin": "one-hot basis of the declared finite state set"
          },
          "known_nonclaims": [
            "Realization validation does not establish adapter scientific adequacy.",
            "Only canonical_compilable realizations may enter Manifest, Typed SOF IR, CompilerOutput, or SOFRS assembly."
          ]
        },
        {
          "stage": "realization",
          "run_receipt": {
            "uri": "<server-workspace>\\mcp-adopter-20260811a\\matrix\\agent-a\\target-realization\\run-receipt.json"
          },
          "source": {
            "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/source/input.json",
            "digest": {
              "algorithm": "sha256",
              "value": "a4a46d473151eac268376c3668bb69ad3ba5e2fe5de4d24ddd27be143c467e33"
            }
          },
          "source_id": "finite-state.transition.target",
          "eligibility": "canonical_compilable",
          "canonical_compilable": true,
          "adapter": {
            "id": "example.finite-state-adapter",
            "version": "1.0",
            "domain_id": "finite-state-transition-system",
            "declaration": {
              "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/declaration.json",
              "digest": {
                "algorithm": "sha256",
                "value": "7284ed390f68c27f370bc7470ab3e351b0922150145e01e2a89c34bb158b69d4"
              }
            }
          },
          "declared": {
            "carriers": [
              "sectorization",
              "operator_carrier",
              "operator_system"
            ],
            "observables": [
              "thresholded direct support"
            ],
            "capabilities": [
              "complete finite sectorization",
              "labelled transition operators"
            ],
            "unsupported": [
              "route filtration",
              "positive-word depth",
              "Lie/Hall depth",
              "deformation chart"
            ],
            "sectorization_origin": "one-hot basis of the declared finite state set"
          },
          "known_nonclaims": [
            "Realization validation does not establish adapter scientific adequacy.",
            "Only canonical_compilable realizations may enter Manifest, Typed SOF IR, CompilerOutput, or SOFRS assembly."
          ]
        }
      ],
      "comparison": {
        "stage": "comparison",
        "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
        "artifact": {
          "uri": "<server-workspace>\\mcp-adopter-20260811a\\matrix\\agent-a\\comparison\\result.sofaudit.json"
        },
        "validation": {
          "status": "PASS",
          "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
          "validator_id": "sofaudit.runtime-semantic-validator.v2",
          "validator_version": "2.0",
          "implementation": {
            "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/output/validator/sofaudit-validator.py",
            "digest": {
              "algorithm": "sha256",
              "value": "6664701a28865264bbe1c0ee5107e2bb3b95d7fd8054005d60b40a1a59609880"
            }
          }
        },
        "alignment": {
          "sector": "example.finite-state.identity.sector",
          "observable": "example.finite-state.identity.observable"
        },
        "coordinates": [
          {
            "coordinate_id": "operator.support.summary",
            "state": "MISMATCH",
            "claim_status": "Computational Observation",
            "source_artifacts": [
              "artifact.alignment-evidence"
            ]
          }
        ],
        "why_unresolved_or_unavailable": [],
        "negative_boundary": "This comparison does not establish reference truth, defect status, severity, or action."
      },
      "interpretation": null,
      "known_nonclaims": [
        "This explanation is a structured view of source-addressed artifacts, not an independent scientific conclusion.",
        "Validation PASS establishes the declared contract and artifact closure only.",
        "CandidateAction is not a recommendation, authorization, execution command, or causal-effect certificate."
      ]
    }
  },
  "artifacts": []
}
```

## Conventional final action path completion

The same admitted interpretation was additionally materialized at the conventional `matrix/agent-a/action` child so the provenance explainer could include it. Semantic content and digests were unchanged. The final retrievable locators are therefore:

- `sof-workspace://mcp-adopter-20260811a/matrix/agent-a/action/result.sofaction.json`, SHA-256 `63be634de4baf64dc85da3a3ca168933676ba94a2d4b89553da7db18bd03ca4d`
- `sof-workspace://mcp-adopter-20260811a/matrix/agent-a/action/validation-receipt.json`, SHA-256 `447c62bf1a1800318051907539bc36339974e68df2f2f2ddedf60e4f0cf34fe2`

The final `sof_explain` call then returned the complete source-addressed pipeline including the interpretation and both bounded candidates.

### Additional call 19: sof_interpret

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "audit": "matrix/agent-a/comparison/result.sofaudit.json",
  "receipt": "matrix/agent-a/comparison/validation-receipt.json",
  "context": "case/action/context.json",
  "policy": "case/action/policy.json",
  "out_directory": "matrix/agent-a/action",
  "request_id": "matrix-agent-a-interpret-final"
}
```

Result:

```json
{
  "contract_id": "sof-runtime.service-response.v1",
  "request_id": "matrix-agent-a-interpret-final",
  "job_id": "job:7b08b82d735843cc878e2494aefa68b0",
  "semantic_run_id": "semrun:sha256:96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636",
  "workspace_id": "mcp-adopter-20260811a",
  "operation": "interpret",
  "status": "succeeded",
  "result": {
    "action_record_id": "action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
    "candidate_actions": [
      {
        "action_id": "investigate:operator.support.summary",
        "disposition": "Investigate"
      },
      {
        "action_id": "requestevidence:operator.support.summary",
        "disposition": "RequestEvidence"
      }
    ]
  },
  "artifacts": [
    {
      "artifact_id": "sofaction:63be634de4baf64d",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/action/result.sofaction.json",
      "sha256": "63be634de4baf64dc85da3a3ca168933676ba94a2d4b89553da7db18bd03ca4d",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    },
    {
      "artifact_id": "sofaction_validation_receipt:447c62bf1a180031",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/action/validation-receipt.json",
      "sha256": "447c62bf1a1800318051907539bc36339974e68df2f2f2ddedf60e4f0cf34fe2",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    }
  ]
}
```

### Additional call 20: sof_validate

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "validation_kind": "sofaction",
  "artifact": "matrix/agent-a/action/result.sofaction.json",
  "request_id": "matrix-agent-a-validate-final-action"
}
```

Result:

```json
{
  "contract_id": "sof-runtime.service-response.v1",
  "request_id": "matrix-agent-a-validate-final-action",
  "job_id": "job:765e8702076b4bc3aa6c0db7aa048062",
  "semantic_run_id": "semrun:sha256:92bcae20532d74d21ecbe1582fc25bbaa898f166e95f79cb9a61ac1bb82fef08",
  "workspace_id": "mcp-adopter-20260811a",
  "operation": "validate",
  "status": "succeeded",
  "result": {
    "validation_kind": "sofaction",
    "validator_result": {
      "action_context": {
        "actor": {
          "actor_id": "domain-reviewer",
          "description": "A domain expert reviewing a finite-state transition comparison.",
          "role": "domain reviewer"
        },
        "authority": {
          "actor_ids": [
            "domain-reviewer"
          ],
          "authority_id": "finite-state-review-authority",
          "description": "Declared review authority for this bounded diagnostic comparison.",
          "scope_ids": [
            "finite-state-comparison-scope"
          ],
          "status": "declared"
        },
        "comparison_role": "diagnostic_comparison",
        "constraints": [
          {
            "constraint_id": "human-review-required",
            "statement": "No candidate is an execution command and no action is authorized by this context.",
            "status": "binding"
          }
        ],
        "context_contract_version": "2.0",
        "context_id": "finite-state-review-context-v1",
        "context_revision": "finite-state-review-r1",
        "contract_status": "nonconforming",
        "evaluator_qualification_note": "Qualification is declared for this finite-state review only; it is not a general domain certificate.",
        "mismatch_direction": "reference_to_target",
        "negative_boundary": [
          "The context does not establish reference truth, severity, action correctness, or authorization."
        ],
        "objective": {
          "objective_id": "review-direct-support",
          "statement": "Determine whether the observed direct-support difference warrants bounded follow-up evidence."
        },
        "scope": {
          "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
          "description": "The declared direct-support coordinate of the external finite-state comparison.",
          "scope_id": "finite-state-comparison-scope"
        },
        "time": {
          "basis": "The two source snapshots bound the comparison.",
          "end": null,
          "kind": "source_snapshot",
          "start": null,
          "timezone": null
        },
        "transformation_contract_refs": [],
        "uncertainty_conditions": [
          "A mismatch is not a certified defect.",
          "Post-action outcomes require a new audit."
        ]
      },
      "action_record_id": "action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
      "audit_projection": {
        "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
        "signature": {
          "operator.support.summary": {
            "certificate_class": null,
            "claim_status": "Computational Observation",
            "claim_target": "comparison_relation",
            "classification_source": "audit_engine",
            "comparison_state": "MISMATCH",
            "coordinate_family": "operator",
            "report_item_binding": {
              "binding_state": "paired",
              "reason": null,
              "reference_item_ref": {
                "artifact_digest": {
                  "algorithm": "sha256",
                  "value": "166b0de4269bbde554baaac4b07214436942d3a9bfcecd1c073c2ee924c33ae1"
                },
                "item_kind": "claim",
                "report_id": "example.finite-state-adapter.finite-state.transition.reference.sofreport",
                "report_item_id": "report.claim-item.0000",
                "source_output_item_id": "compiler.item.0000"
              },
              "target_item_ref": {
                "artifact_digest": {
                  "algorithm": "sha256",
                  "value": "bc783aee6c4705ea535a4e8bfd97c696e26b4db3fe81c8d4deb76dbe93dc29dd"
                },
                "item_kind": "claim",
                "report_id": "example.finite-state-adapter.finite-state.transition.target.sofreport",
                "report_item_id": "report.claim-item.0000",
                "source_output_item_id": "compiler.item.0000"
              }
            },
            "result_state": "OBSERVED",
            "source_artifact_ids": [
              "artifact.alignment-evidence"
            ],
            "value": {
              "delta": 1,
              "metric_result": {
                "metric_id": "absolute-difference",
                "status": "computed",
                "value": 1
              },
              "normalized_reference_value": {
                "support_count": 2
              },
              "normalized_target_value": {
                "support_count": 3
              },
              "oracle_ref": null,
              "policy_refs": [],
              "reference_value": {
                "support_count": 2
              },
              "relation": "mismatch",
              "target_value": {
                "support_count": 3
              },
              "unit": "support pairs"
            },
            "value_schema_id": "operator.support.v1"
          }
        }
      },
      "candidate_action_set": {
        "actions": [
          {
            "action_id": "investigate:operator.support.summary",
            "audit_coordinate_refs": [
              {
                "carrier": "operator",
                "comparison_state": "MISMATCH",
                "coordinate_id": "operator.support.summary"
              }
            ],
            "authorization_state": "not_requested",
            "carrier": "operator",
            "context_ref": "finite-state-review-context-v1",
            "declared_risk_considerations": [
              "the candidate may be irrelevant after context or policy review",
              "an observed post-action change would require a new Paper XIII audit"
            ],
            "disposition": "Investigate",
            "evidence_refs": [
              {
                "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
                "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
                "digest": {
                  "algorithm": "sha256",
                  "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
                },
                "sofaudit_version": "2.0",
                "validation_receipt": {
                  "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
                  "digest": {
                    "algorithm": "sha256",
                    "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
                  },
                  "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
                  "validator_id": "sofaudit.runtime-semantic-validator.v2",
                  "validator_version": "2.0"
                }
              }
            ],
            "intended_diagnostic_consequence": {
              "statements": [
                "obtain evidence relevant to the declared comparison coordinate"
              ],
              "status": "intended_diagnostic_consequence"
            },
            "negative_boundary": [
              "This is a candidate disposition, not an execution command or correctness claim."
            ],
            "policy_rule_refs": [
              "mismatch-review"
            ],
            "preconditions": [
              "the source audit projection and coordinate state remain unchanged",
              "a domain owner confirms the candidate is applicable"
            ],
            "reversibility": "unknown",
            "supported_by_interpretations": [
              "interp:action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport:operator.support.summary"
            ],
            "target": "operator.support.summary"
          },
          {
            "action_id": "requestevidence:operator.support.summary",
            "audit_coordinate_refs": [
              {
                "carrier": "operator",
                "comparison_state": "MISMATCH",
                "coordinate_id": "operator.support.summary"
              }
            ],
            "authorization_state": "not_requested",
            "carrier": "operator",
            "context_ref": "finite-state-review-context-v1",
            "declared_risk_considerations": [
              "the candidate may be irrelevant after context or policy review",
              "an observed post-action change would require a new Paper XIII audit"
            ],
            "disposition": "RequestEvidence",
            "evidence_refs": [
              {
                "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
                "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
                "digest": {
                  "algorithm": "sha256",
                  "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
                },
                "sofaudit_version": "2.0",
                "validation_receipt": {
                  "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
                  "digest": {
                    "algorithm": "sha256",
                    "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
                  },
                  "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
                  "validator_id": "sofaudit.runtime-semantic-validator.v2",
                  "validator_version": "2.0"
                }
              }
            ],
            "intended_diagnostic_consequence": {
              "statements": [
                "obtain evidence relevant to the declared comparison coordinate"
              ],
              "status": "intended_diagnostic_consequence"
            },
            "negative_boundary": [
              "This is a candidate disposition, not an execution command or correctness claim."
            ],
            "policy_rule_refs": [
              "mismatch-review"
            ],
            "preconditions": [
              "the source audit projection and coordinate state remain unchanged",
              "a domain owner confirms the candidate is applicable"
            ],
            "reversibility": "unknown",
            "supported_by_interpretations": [
              "interp:action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport:operator.support.summary"
            ],
            "target": "operator.support.summary"
          }
        ],
        "count": 2
      },
      "claim_note": "This object records policy-relative interpretation and bounded candidates; it does not select or execute an action.",
      "claim_status": "Computational Certificate",
      "context_admission": {
        "applicability": "applicable",
        "completeness": "complete",
        "contract_validation": "admitted",
        "missing_fields": [],
        "rationale": "ActionContext supplied by the caller.",
        "status": "admitted"
      },
      "disposition_result": {
        "candidate_action_ids": [
          "investigate:operator.support.summary",
          "requestevidence:operator.support.summary"
        ],
        "interpretation_ids": [
          "interp:action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport:operator.support.summary"
        ],
        "kind": "candidate_action_set",
        "reason": "The admitted policy supports bounded candidate dispositions."
      },
      "failure_modes": [
        "difference is not defect, severity, or action without the admitted context and policy",
        "candidate actions are not execution commands, authorization, feasibility, or causal-effect claims",
        "post-action facts require a new Paper XIII audit"
      ],
      "interpretation_records": [
        {
          "assessment_kind": "defect_candidate",
          "assessment_note": "A mismatch is a policy-relative review status, not a certified defect.",
          "audit_coordinate_refs": [
            {
              "carrier": "operator",
              "comparison_state": "MISMATCH",
              "coordinate_id": "operator.support.summary"
            }
          ],
          "context_refs": [
            "finite-state-review-context-v1"
          ],
          "evidence_refs": [
            {
              "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
              "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
              "digest": {
                "algorithm": "sha256",
                "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
              },
              "sofaudit_version": "2.0",
              "validation_receipt": {
                "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
                "digest": {
                  "algorithm": "sha256",
                  "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
                },
                "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
                "validator_id": "sofaudit.runtime-semantic-validator.v2",
                "validator_version": "2.0"
              }
            }
          ],
          "interpretation_id": "interp:action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport:operator.support.summary",
          "negative_boundary": [
            "The candidate is not a certified defect, execution command, or recommendation."
          ],
          "policy_rule_refs": [
            "mismatch-review"
          ],
          "rationale": "A mismatch is a policy-relative review status, not a certified defect.",
          "supported_dispositions": [
            "Investigate",
            "RequestEvidence"
          ],
          "uncertainty": {
            "reasons": [],
            "status": "bounded"
          }
        }
      ],
      "policy_admission": {
        "applicability": "applicable",
        "completeness": "complete",
        "contract_validation": "admitted",
        "missing_fields": [],
        "rationale": "PolicyProfile supplied by the caller and replayed by the runtime.",
        "status": "admitted"
      },
      "policy_profile": {
        "applicability": {
          "comparison_roles": [
            "diagnostic_comparison"
          ],
          "regimes": [
            "strict_vs_strict"
          ]
        },
        "candidate_families": [
          "Investigate",
          "RequestEvidence"
        ],
        "exceptions": [],
        "normative_basis": [
          {
            "basis_id": "difference-is-not-defect",
            "source_ref": {
              "artifact_id": "finite-state-policy-basis",
              "contract_version": "2.0",
              "digest": {
                "algorithm": "sha256",
                "value": "d4d2e837fd974caccbdde47eccacfad0337d24d3fb9537aac058d76f549e87df"
              },
              "producer": "external-adapter-example",
              "role": "policy_source",
              "uri": "artifact://examples/external-adapter-finite-state/action/policy-basis.json"
            },
            "statement": "A mismatch is a policy-relative review status, not a certified defect."
          }
        ],
        "policy_contract_version": "2.0",
        "policy_id": "finite-state-review-policy",
        "policy_revision": "finite-state-review-r1",
        "precedence_edges": [],
        "rules": [
          {
            "allowed_dispositions": [
              "Investigate",
              "RequestEvidence"
            ],
            "assessment_kind": "defect_candidate",
            "assessment_note": "A mismatch is a policy-relative review status, not a certified defect.",
            "negative_boundary": [
              "The candidate is not a certified defect, execution command, or recommendation."
            ],
            "rule_id": "mismatch-review",
            "uncertainty_status": "bounded",
            "when": {
              "coordinate_id": "*",
              "op": "coordinate_state_is",
              "predicate_version": "1.0",
              "value": "MISMATCH"
            }
          },
          {
            "allowed_dispositions": [
              "NoAction"
            ],
            "assessment_kind": "no_action_indicated",
            "assessment_note": "Equality on the requested coordinate indicates no action under this policy.",
            "negative_boundary": [
              "Equality does not establish global equivalence or safety."
            ],
            "rule_id": "aligned-no-action",
            "uncertainty_status": "bounded",
            "when": {
              "coordinate_id": "*",
              "op": "coordinate_state_is",
              "predicate_version": "1.0",
              "value": "ALIGNED"
            }
          }
        ],
        "selection_status": "downstream",
        "uncertainty_policy": {
          "incomparable": "propagate_unresolved",
          "no_applicable_rule": "no_disposition",
          "not_declared": "propagate_unresolved",
          "rule_conflict": "unresolved_disposition",
          "unavailable_coordinate": "non_satisfying",
          "unresolved_predicate": "propagate_unresolved",
          "version": "1.0"
        }
      },
      "record_basis": {
        "basis_kind": "protocol_trace",
        "causal_status": "not_claimed",
        "evidence_refs": [
          {
            "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
            "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
            "digest": {
              "algorithm": "sha256",
              "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
            },
            "sofaudit_version": "2.0",
            "validation_receipt": {
              "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
              "digest": {
                "algorithm": "sha256",
                "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
              },
              "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
              "validator_id": "sofaudit.runtime-semantic-validator.v2",
              "validator_version": "2.0"
            }
          }
        ],
        "negative_boundary": [
          "Protocol trace completeness does not establish policy validity or action effectiveness."
        ]
      },
      "record_class": "decision_trace_certificate",
      "record_type": "sofaction",
      "sofaction_version": "2.0",
      "source_audit": {
        "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
        "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
        "digest": {
          "algorithm": "sha256",
          "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
        },
        "sofaudit_version": "2.0",
        "validation_receipt": {
          "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
          "digest": {
            "algorithm": "sha256",
            "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
          },
          "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
          "validator_id": "sofaudit.runtime-semantic-validator.v2",
          "validator_version": "2.0"
        }
      }
    }
  },
  "artifacts": [
    {
      "artifact_id": "sofaction:63be634de4baf64d",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/action/result.sofaction.json",
      "sha256": "63be634de4baf64dc85da3a3ca168933676ba94a2d4b89553da7db18bd03ca4d",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    }
  ]
}
```

### Additional call 21: sof_validate

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "validation_kind": "sofaction_receipt",
  "artifact": "matrix/agent-a/action/validation-receipt.json",
  "request_id": "matrix-agent-a-validate-final-action-receipt"
}
```

Result:

```json
{
  "contract_id": "sof-runtime.service-response.v1",
  "request_id": "matrix-agent-a-validate-final-action-receipt",
  "job_id": "job:90fe0827b8974e06a7be181b443120c5",
  "semantic_run_id": "semrun:sha256:bbc77d0b731ab58f66513463137eb14be9a25137dda4207955d5e2be0b321033",
  "workspace_id": "mcp-adopter-20260811a",
  "operation": "validate",
  "status": "succeeded",
  "result": {
    "validation_kind": "sofaction_receipt",
    "validator_result": {
      "action": {
        "action_record_id": "action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
        "artifact": {
          "digest": {
            "algorithm": "sha256",
            "value": "63be634de4baf64dc85da3a3ca168933676ba94a2d4b89553da7db18bd03ca4d"
          },
          "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/result.sofaction.json"
        },
        "sofaction_version": "2.0"
      },
      "artifact_closure": {
        "artifact_count": 3,
        "closure_digest": {
          "algorithm": "sha256",
          "value": "719ddf68ed79f3c735d9ed8320dfda685175b5ecf429ed781bf93e1f96482108"
        },
        "ordered_artifacts": [
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "63be634de4baf64dc85da3a3ca168933676ba94a2d4b89553da7db18bd03ca4d"
              },
              "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/result.sofaction.json"
            },
            "role": "action"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "f64aaf1769054de504fac8c8beefbc2b0e174e2c96cf9f421ec5f68072ec57fe"
              },
              "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/validator/sofaction-validator.py"
            },
            "role": "validator-implementation"
          },
          {
            "artifact": {
              "digest": {
                "algorithm": "sha256",
                "value": "56e535c97a6370d3e933738b8b356038bd81394aa9c467f8614a1cf0d49db734"
              },
              "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/contracts/sofaction-validation-receipt.schema.json"
            },
            "role": "validation-receipt-contract"
          }
        ]
      },
      "artifact_type": "sofaction_validation_receipt",
      "checks": [
        {
          "check_id": "schema-validation",
          "status": "PASS"
        },
        {
          "check_id": "artifact-digest-closure",
          "status": "PASS"
        },
        {
          "check_id": "action-context-policy-admission",
          "status": "PASS"
        },
        {
          "check_id": "audit-projection-preservation",
          "status": "PASS"
        },
        {
          "check_id": "predicate-replay",
          "status": "PASS"
        },
        {
          "check_id": "candidate-set-regeneration",
          "status": "PASS"
        },
        {
          "check_id": "disposition-closure",
          "status": "PASS"
        },
        {
          "check_id": "authorization-boundary",
          "status": "PASS"
        }
      ],
      "negative_boundaries": [
        "This receipt establishes interpretation and candidate-set protocol conformance only; it does not establish policy correctness, action feasibility, authorization, or causal effect."
      ],
      "receipt_id": "receipt.action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaction-v2",
      "receipt_version": "2.0",
      "status": "PASS",
      "validator": {
        "implementation": {
          "digest": {
            "algorithm": "sha256",
            "value": "f64aaf1769054de504fac8c8beefbc2b0e174e2c96cf9f421ec5f68072ec57fe"
          },
          "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/validator/sofaction-validator.py"
        },
        "receipt_contract": {
          "digest": {
            "algorithm": "sha256",
            "value": "56e535c97a6370d3e933738b8b356038bd81394aa9c467f8614a1cf0d49db734"
          },
          "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/contracts/sofaction-validation-receipt.schema.json"
        },
        "validator_id": "sofaction.runtime-validator.v2",
        "validator_version": "2.0"
      }
    }
  },
  "artifacts": [
    {
      "artifact_id": "sofaction_receipt:447c62bf1a180031",
      "media_type": "application/json",
      "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/action/validation-receipt.json",
      "sha256": "447c62bf1a1800318051907539bc36339974e68df2f2f2ddedf60e4f0cf34fe2",
      "schema_id": null,
      "producer": "sof-runtime.service@0.3.0.dev0",
      "input_refs": []
    }
  ]
}
```

### Additional call 22: sof_get_artifact

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "path": "matrix/agent-a/action/result.sofaction.json",
  "sha256": "63be634de4baf64dc85da3a3ca168933676ba94a2d4b89553da7db18bd03ca4d"
}
```

Result:

```json
{
  "artifact": {
    "artifact_id": "retrieved_artifact:63be634de4baf64d",
    "media_type": "application/json",
    "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/action/result.sofaction.json",
    "sha256": "63be634de4baf64dc85da3a3ca168933676ba94a2d4b89553da7db18bd03ca4d",
    "schema_id": null,
    "producer": "sof-runtime.service@0.3.0.dev0",
    "input_refs": []
  },
  "content_encoding": "json",
  "content": {
    "action_context": {
      "actor": {
        "actor_id": "domain-reviewer",
        "description": "A domain expert reviewing a finite-state transition comparison.",
        "role": "domain reviewer"
      },
      "authority": {
        "actor_ids": [
          "domain-reviewer"
        ],
        "authority_id": "finite-state-review-authority",
        "description": "Declared review authority for this bounded diagnostic comparison.",
        "scope_ids": [
          "finite-state-comparison-scope"
        ],
        "status": "declared"
      },
      "comparison_role": "diagnostic_comparison",
      "constraints": [
        {
          "constraint_id": "human-review-required",
          "statement": "No candidate is an execution command and no action is authorized by this context.",
          "status": "binding"
        }
      ],
      "context_contract_version": "2.0",
      "context_id": "finite-state-review-context-v1",
      "context_revision": "finite-state-review-r1",
      "contract_status": "nonconforming",
      "evaluator_qualification_note": "Qualification is declared for this finite-state review only; it is not a general domain certificate.",
      "mismatch_direction": "reference_to_target",
      "negative_boundary": [
        "The context does not establish reference truth, severity, action correctness, or authorization."
      ],
      "objective": {
        "objective_id": "review-direct-support",
        "statement": "Determine whether the observed direct-support difference warrants bounded follow-up evidence."
      },
      "scope": {
        "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
        "description": "The declared direct-support coordinate of the external finite-state comparison.",
        "scope_id": "finite-state-comparison-scope"
      },
      "time": {
        "basis": "The two source snapshots bound the comparison.",
        "end": null,
        "kind": "source_snapshot",
        "start": null,
        "timezone": null
      },
      "transformation_contract_refs": [],
      "uncertainty_conditions": [
        "A mismatch is not a certified defect.",
        "Post-action outcomes require a new audit."
      ]
    },
    "action_record_id": "action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
    "audit_projection": {
      "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
      "signature": {
        "operator.support.summary": {
          "certificate_class": null,
          "claim_status": "Computational Observation",
          "claim_target": "comparison_relation",
          "classification_source": "audit_engine",
          "comparison_state": "MISMATCH",
          "coordinate_family": "operator",
          "report_item_binding": {
            "binding_state": "paired",
            "reason": null,
            "reference_item_ref": {
              "artifact_digest": {
                "algorithm": "sha256",
                "value": "166b0de4269bbde554baaac4b07214436942d3a9bfcecd1c073c2ee924c33ae1"
              },
              "item_kind": "claim",
              "report_id": "example.finite-state-adapter.finite-state.transition.reference.sofreport",
              "report_item_id": "report.claim-item.0000",
              "source_output_item_id": "compiler.item.0000"
            },
            "target_item_ref": {
              "artifact_digest": {
                "algorithm": "sha256",
                "value": "bc783aee6c4705ea535a4e8bfd97c696e26b4db3fe81c8d4deb76dbe93dc29dd"
              },
              "item_kind": "claim",
              "report_id": "example.finite-state-adapter.finite-state.transition.target.sofreport",
              "report_item_id": "report.claim-item.0000",
              "source_output_item_id": "compiler.item.0000"
            }
          },
          "result_state": "OBSERVED",
          "source_artifact_ids": [
            "artifact.alignment-evidence"
          ],
          "value": {
            "delta": 1,
            "metric_result": {
              "metric_id": "absolute-difference",
              "status": "computed",
              "value": 1
            },
            "normalized_reference_value": {
              "support_count": 2
            },
            "normalized_target_value": {
              "support_count": 3
            },
            "oracle_ref": null,
            "policy_refs": [],
            "reference_value": {
              "support_count": 2
            },
            "relation": "mismatch",
            "target_value": {
              "support_count": 3
            },
            "unit": "support pairs"
          },
          "value_schema_id": "operator.support.v1"
        }
      }
    },
    "candidate_action_set": {
      "actions": [
        {
          "action_id": "investigate:operator.support.summary",
          "audit_coordinate_refs": [
            {
              "carrier": "operator",
              "comparison_state": "MISMATCH",
              "coordinate_id": "operator.support.summary"
            }
          ],
          "authorization_state": "not_requested",
          "carrier": "operator",
          "context_ref": "finite-state-review-context-v1",
          "declared_risk_considerations": [
            "the candidate may be irrelevant after context or policy review",
            "an observed post-action change would require a new Paper XIII audit"
          ],
          "disposition": "Investigate",
          "evidence_refs": [
            {
              "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
              "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
              "digest": {
                "algorithm": "sha256",
                "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
              },
              "sofaudit_version": "2.0",
              "validation_receipt": {
                "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
                "digest": {
                  "algorithm": "sha256",
                  "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
                },
                "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
                "validator_id": "sofaudit.runtime-semantic-validator.v2",
                "validator_version": "2.0"
              }
            }
          ],
          "intended_diagnostic_consequence": {
            "statements": [
              "obtain evidence relevant to the declared comparison coordinate"
            ],
            "status": "intended_diagnostic_consequence"
          },
          "negative_boundary": [
            "This is a candidate disposition, not an execution command or correctness claim."
          ],
          "policy_rule_refs": [
            "mismatch-review"
          ],
          "preconditions": [
            "the source audit projection and coordinate state remain unchanged",
            "a domain owner confirms the candidate is applicable"
          ],
          "reversibility": "unknown",
          "supported_by_interpretations": [
            "interp:action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport:operator.support.summary"
          ],
          "target": "operator.support.summary"
        },
        {
          "action_id": "requestevidence:operator.support.summary",
          "audit_coordinate_refs": [
            {
              "carrier": "operator",
              "comparison_state": "MISMATCH",
              "coordinate_id": "operator.support.summary"
            }
          ],
          "authorization_state": "not_requested",
          "carrier": "operator",
          "context_ref": "finite-state-review-context-v1",
          "declared_risk_considerations": [
            "the candidate may be irrelevant after context or policy review",
            "an observed post-action change would require a new Paper XIII audit"
          ],
          "disposition": "RequestEvidence",
          "evidence_refs": [
            {
              "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
              "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
              "digest": {
                "algorithm": "sha256",
                "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
              },
              "sofaudit_version": "2.0",
              "validation_receipt": {
                "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
                "digest": {
                  "algorithm": "sha256",
                  "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
                },
                "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
                "validator_id": "sofaudit.runtime-semantic-validator.v2",
                "validator_version": "2.0"
              }
            }
          ],
          "intended_diagnostic_consequence": {
            "statements": [
              "obtain evidence relevant to the declared comparison coordinate"
            ],
            "status": "intended_diagnostic_consequence"
          },
          "negative_boundary": [
            "This is a candidate disposition, not an execution command or correctness claim."
          ],
          "policy_rule_refs": [
            "mismatch-review"
          ],
          "preconditions": [
            "the source audit projection and coordinate state remain unchanged",
            "a domain owner confirms the candidate is applicable"
          ],
          "reversibility": "unknown",
          "supported_by_interpretations": [
            "interp:action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport:operator.support.summary"
          ],
          "target": "operator.support.summary"
        }
      ],
      "count": 2
    },
    "claim_note": "This object records policy-relative interpretation and bounded candidates; it does not select or execute an action.",
    "claim_status": "Computational Certificate",
    "context_admission": {
      "applicability": "applicable",
      "completeness": "complete",
      "contract_validation": "admitted",
      "missing_fields": [],
      "rationale": "ActionContext supplied by the caller.",
      "status": "admitted"
    },
    "disposition_result": {
      "candidate_action_ids": [
        "investigate:operator.support.summary",
        "requestevidence:operator.support.summary"
      ],
      "interpretation_ids": [
        "interp:action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport:operator.support.summary"
      ],
      "kind": "candidate_action_set",
      "reason": "The admitted policy supports bounded candidate dispositions."
    },
    "failure_modes": [
      "difference is not defect, severity, or action without the admitted context and policy",
      "candidate actions are not execution commands, authorization, feasibility, or causal-effect claims",
      "post-action facts require a new Paper XIII audit"
    ],
    "interpretation_records": [
      {
        "assessment_kind": "defect_candidate",
        "assessment_note": "A mismatch is a policy-relative review status, not a certified defect.",
        "audit_coordinate_refs": [
          {
            "carrier": "operator",
            "comparison_state": "MISMATCH",
            "coordinate_id": "operator.support.summary"
          }
        ],
        "context_refs": [
          "finite-state-review-context-v1"
        ],
        "evidence_refs": [
          {
            "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
            "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
            "digest": {
              "algorithm": "sha256",
              "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
            },
            "sofaudit_version": "2.0",
            "validation_receipt": {
              "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
              "digest": {
                "algorithm": "sha256",
                "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
              },
              "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
              "validator_id": "sofaudit.runtime-semantic-validator.v2",
              "validator_version": "2.0"
            }
          }
        ],
        "interpretation_id": "interp:action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport:operator.support.summary",
        "negative_boundary": [
          "The candidate is not a certified defect, execution command, or recommendation."
        ],
        "policy_rule_refs": [
          "mismatch-review"
        ],
        "rationale": "A mismatch is a policy-relative review status, not a certified defect.",
        "supported_dispositions": [
          "Investigate",
          "RequestEvidence"
        ],
        "uncertainty": {
          "reasons": [],
          "status": "bounded"
        }
      }
    ],
    "policy_admission": {
      "applicability": "applicable",
      "completeness": "complete",
      "contract_validation": "admitted",
      "missing_fields": [],
      "rationale": "PolicyProfile supplied by the caller and replayed by the runtime.",
      "status": "admitted"
    },
    "policy_profile": {
      "applicability": {
        "comparison_roles": [
          "diagnostic_comparison"
        ],
        "regimes": [
          "strict_vs_strict"
        ]
      },
      "candidate_families": [
        "Investigate",
        "RequestEvidence"
      ],
      "exceptions": [],
      "normative_basis": [
        {
          "basis_id": "difference-is-not-defect",
          "source_ref": {
            "artifact_id": "finite-state-policy-basis",
            "contract_version": "2.0",
            "digest": {
              "algorithm": "sha256",
              "value": "d4d2e837fd974caccbdde47eccacfad0337d24d3fb9537aac058d76f549e87df"
            },
            "producer": "external-adapter-example",
            "role": "policy_source",
            "uri": "artifact://examples/external-adapter-finite-state/action/policy-basis.json"
          },
          "statement": "A mismatch is a policy-relative review status, not a certified defect."
        }
      ],
      "policy_contract_version": "2.0",
      "policy_id": "finite-state-review-policy",
      "policy_revision": "finite-state-review-r1",
      "precedence_edges": [],
      "rules": [
        {
          "allowed_dispositions": [
            "Investigate",
            "RequestEvidence"
          ],
          "assessment_kind": "defect_candidate",
          "assessment_note": "A mismatch is a policy-relative review status, not a certified defect.",
          "negative_boundary": [
            "The candidate is not a certified defect, execution command, or recommendation."
          ],
          "rule_id": "mismatch-review",
          "uncertainty_status": "bounded",
          "when": {
            "coordinate_id": "*",
            "op": "coordinate_state_is",
            "predicate_version": "1.0",
            "value": "MISMATCH"
          }
        },
        {
          "allowed_dispositions": [
            "NoAction"
          ],
          "assessment_kind": "no_action_indicated",
          "assessment_note": "Equality on the requested coordinate indicates no action under this policy.",
          "negative_boundary": [
            "Equality does not establish global equivalence or safety."
          ],
          "rule_id": "aligned-no-action",
          "uncertainty_status": "bounded",
          "when": {
            "coordinate_id": "*",
            "op": "coordinate_state_is",
            "predicate_version": "1.0",
            "value": "ALIGNED"
          }
        }
      ],
      "selection_status": "downstream",
      "uncertainty_policy": {
        "incomparable": "propagate_unresolved",
        "no_applicable_rule": "no_disposition",
        "not_declared": "propagate_unresolved",
        "rule_conflict": "unresolved_disposition",
        "unavailable_coordinate": "non_satisfying",
        "unresolved_predicate": "propagate_unresolved",
        "version": "1.0"
      }
    },
    "record_basis": {
      "basis_kind": "protocol_trace",
      "causal_status": "not_claimed",
      "evidence_refs": [
        {
          "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
          "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
          "digest": {
            "algorithm": "sha256",
            "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
          },
          "sofaudit_version": "2.0",
          "validation_receipt": {
            "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
            "digest": {
              "algorithm": "sha256",
              "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
            },
            "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
            "validator_id": "sofaudit.runtime-semantic-validator.v2",
            "validator_version": "2.0"
          }
        }
      ],
      "negative_boundary": [
        "Protocol trace completeness does not establish policy validity or action effectiveness."
      ]
    },
    "record_class": "decision_trace_certificate",
    "record_type": "sofaction",
    "sofaction_version": "2.0",
    "source_audit": {
      "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
      "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
      "digest": {
        "algorithm": "sha256",
        "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
      },
      "sofaudit_version": "2.0",
      "validation_receipt": {
        "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
        "digest": {
          "algorithm": "sha256",
          "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
        },
        "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
        "validator_id": "sofaudit.runtime-semantic-validator.v2",
        "validator_version": "2.0"
      }
    }
  }
}
```

### Additional call 23: sof_get_receipt

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "path": "matrix/agent-a/action/validation-receipt.json",
  "sha256": "447c62bf1a1800318051907539bc36339974e68df2f2f2ddedf60e4f0cf34fe2"
}
```

Result:

```json
{
  "artifact": {
    "artifact_id": "retrieved_artifact:447c62bf1a180031",
    "media_type": "application/json",
    "uri": "sof-workspace://mcp-adopter-20260811a/matrix/agent-a/action/validation-receipt.json",
    "sha256": "447c62bf1a1800318051907539bc36339974e68df2f2f2ddedf60e4f0cf34fe2",
    "schema_id": null,
    "producer": "sof-runtime.service@0.3.0.dev0",
    "input_refs": []
  },
  "content_encoding": "json",
  "content": {
    "action": {
      "action_record_id": "action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
      "artifact": {
        "digest": {
          "algorithm": "sha256",
          "value": "63be634de4baf64dc85da3a3ca168933676ba94a2d4b89553da7db18bd03ca4d"
        },
        "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/result.sofaction.json"
      },
      "sofaction_version": "2.0"
    },
    "artifact_closure": {
      "artifact_count": 3,
      "closure_digest": {
        "algorithm": "sha256",
        "value": "719ddf68ed79f3c735d9ed8320dfda685175b5ecf429ed781bf93e1f96482108"
      },
      "ordered_artifacts": [
        {
          "artifact": {
            "digest": {
              "algorithm": "sha256",
              "value": "63be634de4baf64dc85da3a3ca168933676ba94a2d4b89553da7db18bd03ca4d"
            },
            "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/result.sofaction.json"
          },
          "role": "action"
        },
        {
          "artifact": {
            "digest": {
              "algorithm": "sha256",
              "value": "f64aaf1769054de504fac8c8beefbc2b0e174e2c96cf9f421ec5f68072ec57fe"
            },
            "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/validator/sofaction-validator.py"
          },
          "role": "validator-implementation"
        },
        {
          "artifact": {
            "digest": {
              "algorithm": "sha256",
              "value": "56e535c97a6370d3e933738b8b356038bd81394aa9c467f8614a1cf0d49db734"
            },
            "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/contracts/sofaction-validation-receipt.schema.json"
          },
          "role": "validation-receipt-contract"
        }
      ]
    },
    "artifact_type": "sofaction_validation_receipt",
    "checks": [
      {
        "check_id": "schema-validation",
        "status": "PASS"
      },
      {
        "check_id": "artifact-digest-closure",
        "status": "PASS"
      },
      {
        "check_id": "action-context-policy-admission",
        "status": "PASS"
      },
      {
        "check_id": "audit-projection-preservation",
        "status": "PASS"
      },
      {
        "check_id": "predicate-replay",
        "status": "PASS"
      },
      {
        "check_id": "candidate-set-regeneration",
        "status": "PASS"
      },
      {
        "check_id": "disposition-closure",
        "status": "PASS"
      },
      {
        "check_id": "authorization-boundary",
        "status": "PASS"
      }
    ],
    "negative_boundaries": [
      "This receipt establishes interpretation and candidate-set protocol conformance only; it does not establish policy correctness, action feasibility, authorization, or causal effect."
    ],
    "receipt_id": "receipt.action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaction-v2",
    "receipt_version": "2.0",
    "status": "PASS",
    "validator": {
      "implementation": {
        "digest": {
          "algorithm": "sha256",
          "value": "f64aaf1769054de504fac8c8beefbc2b0e174e2c96cf9f421ec5f68072ec57fe"
        },
        "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/validator/sofaction-validator.py"
      },
      "receipt_contract": {
        "digest": {
          "algorithm": "sha256",
          "value": "56e535c97a6370d3e933738b8b356038bd81394aa9c467f8614a1cf0d49db734"
        },
        "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/contracts/sofaction-validation-receipt.schema.json"
      },
      "validator_id": "sofaction.runtime-validator.v2",
      "validator_version": "2.0"
    }
  }
}
```

### Additional call 24: sof_explain

Arguments:

```json
{
  "workspace_id": "mcp-adopter-20260811a",
  "run_directory": "matrix/agent-a",
  "request_id": "matrix-agent-a-explain-final-chain"
}
```

Result:

```json
{
  "contract_id": "sof-runtime.service-response.v1",
  "request_id": "matrix-agent-a-explain-final-chain",
  "job_id": "job:84cf90e9b0ec4911919888082cc573e8",
  "semantic_run_id": "semrun:sha256:901b991f4aada9b6876d06c6222282cfa438efab843ac3864edc39121059f789",
  "workspace_id": "mcp-adopter-20260811a",
  "operation": "explain",
  "status": "succeeded",
  "result": {
    "explanation": {
      "explanation_version": "1.0",
      "run_id": "agent-a",
      "run_directory": "<server-workspace>\\mcp-adopter-20260811a\\matrix\\agent-a",
      "workflow": "full_pipeline",
      "realizations": [
        {
          "stage": "realization",
          "run_receipt": {
            "uri": "<server-workspace>\\mcp-adopter-20260811a\\matrix\\agent-a\\reference-realization\\run-receipt.json"
          },
          "source": {
            "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/source/input.json",
            "digest": {
              "algorithm": "sha256",
              "value": "3d6e6716653c74a2e4a6a8e22c7b99b8accdf6df2c39ac79aceae0556df5a20d"
            }
          },
          "source_id": "finite-state.transition.reference",
          "eligibility": "canonical_compilable",
          "canonical_compilable": true,
          "adapter": {
            "id": "example.finite-state-adapter",
            "version": "1.0",
            "domain_id": "finite-state-transition-system",
            "declaration": {
              "uri": "runs/.sof-service-cache/40/40341dd55e28c2d0fc558412a57c27a9fc8b27ed5786b1a5111dec28752cb60b/realize/adapter/declaration.json",
              "digest": {
                "algorithm": "sha256",
                "value": "7284ed390f68c27f370bc7470ab3e351b0922150145e01e2a89c34bb158b69d4"
              }
            }
          },
          "declared": {
            "carriers": [
              "sectorization",
              "operator_carrier",
              "operator_system"
            ],
            "observables": [
              "thresholded direct support"
            ],
            "capabilities": [
              "complete finite sectorization",
              "labelled transition operators"
            ],
            "unsupported": [
              "route filtration",
              "positive-word depth",
              "Lie/Hall depth",
              "deformation chart"
            ],
            "sectorization_origin": "one-hot basis of the declared finite state set"
          },
          "known_nonclaims": [
            "Realization validation does not establish adapter scientific adequacy.",
            "Only canonical_compilable realizations may enter Manifest, Typed SOF IR, CompilerOutput, or SOFRS assembly."
          ]
        },
        {
          "stage": "realization",
          "run_receipt": {
            "uri": "<server-workspace>\\mcp-adopter-20260811a\\matrix\\agent-a\\target-realization\\run-receipt.json"
          },
          "source": {
            "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/source/input.json",
            "digest": {
              "algorithm": "sha256",
              "value": "a4a46d473151eac268376c3668bb69ad3ba5e2fe5de4d24ddd27be143c467e33"
            }
          },
          "source_id": "finite-state.transition.target",
          "eligibility": "canonical_compilable",
          "canonical_compilable": true,
          "adapter": {
            "id": "example.finite-state-adapter",
            "version": "1.0",
            "domain_id": "finite-state-transition-system",
            "declaration": {
              "uri": "runs/.sof-service-cache/33/3351436f2103027ee29cfb406c14f3b60f086de79f00c8ebe2ff38cd5db6113e/realize/adapter/declaration.json",
              "digest": {
                "algorithm": "sha256",
                "value": "7284ed390f68c27f370bc7470ab3e351b0922150145e01e2a89c34bb158b69d4"
              }
            }
          },
          "declared": {
            "carriers": [
              "sectorization",
              "operator_carrier",
              "operator_system"
            ],
            "observables": [
              "thresholded direct support"
            ],
            "capabilities": [
              "complete finite sectorization",
              "labelled transition operators"
            ],
            "unsupported": [
              "route filtration",
              "positive-word depth",
              "Lie/Hall depth",
              "deformation chart"
            ],
            "sectorization_origin": "one-hot basis of the declared finite state set"
          },
          "known_nonclaims": [
            "Realization validation does not establish adapter scientific adequacy.",
            "Only canonical_compilable realizations may enter Manifest, Typed SOF IR, CompilerOutput, or SOFRS assembly."
          ]
        }
      ],
      "comparison": {
        "stage": "comparison",
        "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
        "artifact": {
          "uri": "<server-workspace>\\mcp-adopter-20260811a\\matrix\\agent-a\\comparison\\result.sofaudit.json"
        },
        "validation": {
          "status": "PASS",
          "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2",
          "validator_id": "sofaudit.runtime-semantic-validator.v2",
          "validator_version": "2.0",
          "implementation": {
            "uri": "runs/.sof-service-cache/bc/bc5a4c37123416b789ca7a0ee769972ee5b7e0dde5a53df11551c7bc010d92c7/compare/output/validator/sofaudit-validator.py",
            "digest": {
              "algorithm": "sha256",
              "value": "6664701a28865264bbe1c0ee5107e2bb3b95d7fd8054005d60b40a1a59609880"
            }
          }
        },
        "alignment": {
          "sector": "example.finite-state.identity.sector",
          "observable": "example.finite-state.identity.observable"
        },
        "coordinates": [
          {
            "coordinate_id": "operator.support.summary",
            "state": "MISMATCH",
            "claim_status": "Computational Observation",
            "source_artifacts": [
              "artifact.alignment-evidence"
            ]
          }
        ],
        "why_unresolved_or_unavailable": [],
        "negative_boundary": "This comparison does not establish reference truth, defect status, severity, or action."
      },
      "interpretation": {
        "stage": "interpretation",
        "action_record_id": "action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
        "artifact": {
          "uri": "<server-workspace>\\mcp-adopter-20260811a\\matrix\\agent-a\\action\\result.sofaction.json"
        },
        "validation": {
          "status": "PASS",
          "receipt_id": "receipt.action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaction-v2",
          "validator_id": "sofaction.runtime-validator.v2",
          "validator_version": "2.0",
          "implementation": {
            "uri": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/output/validator/sofaction-validator.py",
            "digest": {
              "algorithm": "sha256",
              "value": "f64aaf1769054de504fac8c8beefbc2b0e174e2c96cf9f421ec5f68072ec57fe"
            }
          }
        },
        "context_id": "finite-state-review-context-v1",
        "policy_id": "finite-state-review-policy",
        "interpretations": [
          {
            "interpretation_id": "interp:action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport:operator.support.summary",
            "assessment_kind": "defect_candidate",
            "uncertainty": {
              "reasons": [],
              "status": "bounded"
            },
            "policy_rule_refs": [
              "mismatch-review"
            ],
            "evidence_refs": [
              {
                "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
                "digest": {
                  "algorithm": "sha256",
                  "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
                },
                "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
                "validation_receipt": {
                  "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
                  "digest": {
                    "algorithm": "sha256",
                    "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
                  },
                  "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2"
                }
              }
            ],
            "negative_boundary": [
              "The candidate is not a certified defect, execution command, or recommendation."
            ]
          }
        ],
        "candidate_actions": [
          {
            "action_id": "investigate:operator.support.summary",
            "disposition": "Investigate",
            "authorization_state": "not_requested",
            "evidence_refs": [
              {
                "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
                "digest": {
                  "algorithm": "sha256",
                  "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
                },
                "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
                "validation_receipt": {
                  "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
                  "digest": {
                    "algorithm": "sha256",
                    "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
                  },
                  "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2"
                }
              }
            ]
          },
          {
            "action_id": "requestevidence:operator.support.summary",
            "disposition": "RequestEvidence",
            "authorization_state": "not_requested",
            "evidence_refs": [
              {
                "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit.json",
                "digest": {
                  "algorithm": "sha256",
                  "value": "40125672cfd042eaf8ac737055c9a07dd069b6263aeecab6ce67f31e1a8a95ef"
                },
                "audit_id": "comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport",
                "validation_receipt": {
                  "artifact": "runs/.sof-service-cache/96/96627187f8246d0af53caeb6f9dd8ee1bb4149194260cc175e0e70abca2eb636/interpret/inputs/audit-receipt.json",
                  "digest": {
                    "algorithm": "sha256",
                    "value": "8cb9ccbce7fa6711ff452f3a4c8a818bbb00e35fa2f0eebb573484cbd5e30f07"
                  },
                  "receipt_id": "receipt.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport.sofaudit-v2"
                }
              }
            ]
          }
        ],
        "disposition_result": {
          "candidate_action_ids": [
            "investigate:operator.support.summary",
            "requestevidence:operator.support.summary"
          ],
          "interpretation_ids": [
            "interp:action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport:operator.support.summary"
          ],
          "kind": "candidate_action_set",
          "reason": "The admitted policy supports bounded candidate dispositions."
        },
        "why_unresolved_or_unavailable": [
          {
            "interpretation_id": "interp:action.comparison.example.finite-state-adapter.finite-state.transition.reference.sofreport.example.finite-state-adapter.finite-state.transition.target.sofreport:operator.support.summary",
            "status": "bounded",
            "reasons": []
          }
        ],
        "negative_boundary": [
          "difference is not defect, severity, or action without the admitted context and policy",
          "candidate actions are not execution commands, authorization, feasibility, or causal-effect claims",
          "post-action facts require a new Paper XIII audit"
        ]
      },
      "known_nonclaims": [
        "This explanation is a structured view of source-addressed artifacts, not an independent scientific conclusion.",
        "Validation PASS establishes the declared contract and artifact closure only.",
        "CandidateAction is not a recommendation, authorization, execution command, or causal-effect certificate."
      ]
    }
  },
  "artifacts": []
}
```
