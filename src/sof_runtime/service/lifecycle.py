"""Operational lifecycle coordinator; job state is not SOF evidence."""

from __future__ import annotations

from typing import Any

from .jobs import JobStore


class JobLifecycle:
    def __init__(self, store: JobStore):
        self.store = store

    def begin(self, request: dict[str, Any]) -> dict[str, Any]:
        return self.store.start(self.store.create(request))

    def succeed(
        self,
        job: dict[str, Any],
        response: dict[str, Any],
    ) -> dict[str, Any]:
        return self.store.succeed(job, response)

    def fail(
        self,
        job: dict[str, Any],
        error: dict[str, Any],
    ) -> dict[str, Any]:
        return self.store.fail(job, error)
