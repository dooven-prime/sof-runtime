from __future__ import annotations

from typing import Any


def compiler_output_markdown(output: dict[str, Any]) -> str:
    lines = [
        "# Compiler Output Inspection",
        "",
        "> Debug serialization only. This document is not a SOFRS report.",
        "",
        f"- Manifest: `{output['manifest_id']}`",
        f"- IR: `{output['ir_record_id']}`",
        f"- Profile: `{output['profile_id']}`",
        "",
    ]
    for item in output["items"]:
        if item["item_kind"] == "claim":
            lines.extend(
                [
                    f"## Claim: {item['claim_id']}",
                    "",
                    f"- Module: `{item['module_id']}`",
                    f"- Result state: `{item['result_state']}`",
                    f"- Claim status: `{item['claim_status']}`",
                    f"- Carriers: {', '.join(f'`{value}`' for value in item['carrier_ids'])}",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    f"## Degradation: {item['module_id']}",
                    "",
                    f"- Action: `{item['action']}`",
                    f"- Reason: `{item['reason_kind']}`",
                    "",
                ]
            )
            lines.extend(f"- {detail}" for detail in item["details"])
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"
