"""Generate a domain adapter starter directory."""

from __future__ import annotations

import re
from pathlib import Path


TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "templates" / "expert_adapter_v1"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")
    if not slug:
        raise ValueError("domain must contain at least one letter or number")
    return slug


def _class_name(slug: str) -> str:
    return "".join(part.capitalize() for part in slug.split("-")) + "Adapter"


def init_adapter(domain: str, output_directory: str | Path = ".") -> Path:
    """Create a non-runnable adapter scaffold without overwriting files."""
    slug = _slug(domain)
    destination = Path(output_directory).resolve() / slug
    if destination.exists():
        raise FileExistsError(f"adapter directory already exists: {destination}")

    replacements = {
        "__DOMAIN_SLUG__": slug,
        "__ADAPTER_ID__": f"{slug}.adapter",
        "__SOURCE_ID__": f"{slug}.example",
        "__CLASS_NAME__": _class_name(slug),
    }
    for template in TEMPLATE_ROOT.rglob("*.txt"):
        relative = template.relative_to(TEMPLATE_ROOT)
        target = destination / relative.with_suffix("")
        target.parent.mkdir(parents=True, exist_ok=True)
        content = template.read_text(encoding="utf-8")
        for source, replacement in replacements.items():
            content = content.replace(source, replacement)
        target.write_text(content, encoding="utf-8", newline="\n")
    return destination
