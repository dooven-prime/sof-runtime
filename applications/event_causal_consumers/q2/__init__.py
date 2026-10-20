"""Local syntax-wide Q2 tool, not a SOF adapter or canonical compiler module."""

from .engine import check
from .replay import verify_rejection

__all__ = ["check", "verify_rejection"]
