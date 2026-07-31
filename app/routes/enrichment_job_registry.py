"""Pure route-level enrichment job registry helpers."""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


TerminalStatusBuilder = Callable[[str], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class RegisteredJobState:
    """Live and terminal state for one route-level enrichment job id."""

    orchestrator: Any | None
    terminal: dict[str, Any] | None


def register_orchestrator_state(
    *,
    orchestrators: OrderedDict[str, Any],
    terminal_jobs: OrderedDict[str, dict[str, Any]],
    job_id: str,
    orchestrator: Any,
    max_jobs: int,
    evicted_status: TerminalStatusBuilder,
) -> None:
    """Register a live orchestrator and prune bounded terminal state."""
    orchestrators[job_id] = orchestrator
    terminal_jobs.pop(job_id, None)
    while len(orchestrators) > max_jobs:
        evicted_job_id, _ = orchestrators.popitem(last=False)
        terminal_jobs.pop(evicted_job_id, None)
        terminal_jobs[evicted_job_id] = evicted_status(evicted_job_id)
    while len(terminal_jobs) > max_jobs:
        terminal_jobs.popitem(last=False)


def registered_job_state(
    *,
    lock: Any,
    orchestrators: OrderedDict[str, Any],
    terminal_jobs: OrderedDict[str, dict[str, Any]],
    job_id: str,
) -> RegisteredJobState:
    """Return a live/terminal job snapshot under the route registry lock."""
    with lock:
        return RegisteredJobState(
            orchestrator=orchestrators.get(job_id),
            terminal=terminal_jobs.get(job_id),
        )
