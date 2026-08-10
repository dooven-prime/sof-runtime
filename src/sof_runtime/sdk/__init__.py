"""Small public SDK surface for domain adapter authors.

The SDK types are JSON-shaped typing aliases. The runtime still owns manifest,
IR, report, audit, action, and validation-receipt construction.
"""

from __future__ import annotations

from typing import Any, TypeAlias

from sof_runtime.adapters.expert import ExpertAdapter

SourceBundle: TypeAlias = dict[str, Any]
RealizationCandidate: TypeAlias = dict[str, Any]
CapabilityDeclaration: TypeAlias = dict[str, Any]

__all__ = [
    "CapabilityDeclaration",
    "ExpertAdapter",
    "RealizationCandidate",
    "SourceBundle",
]
