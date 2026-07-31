"""Shared analysis request workflow for HTML and JSON routes."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from app.pipeline.models import IOC

from .analysis_modes import DEFAULT_ANALYSIS_MODE, VALID_ANALYSIS_MODES
from .enrichment_jobs import _setup_orchestrator
from .online import OnlineAdmission, _online_admission

ANALYSIS_ERROR_EMPTY_TEXT = "empty_text"
ANALYSIS_ERROR_INVALID_MODE = "invalid_mode"


@dataclass(frozen=True, slots=True)
class AnalysisIntake:
    """Validated analysis input and extracted IOC batch."""

    text: str
    mode: str
    iocs: list[IOC]
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(frozen=True, slots=True)
class AnalysisRequestValues:
    """Raw request values before validation and extraction."""

    text: object
    mode: object


@dataclass(frozen=True, slots=True)
class OnlineStartDecision:
    """Online-mode admission and optional launched job details."""

    admission: OnlineAdmission
    job_id: str | None

    @property
    def registry(self) -> object:
        return self.admission.registry

    @property
    def has_configured_providers(self) -> bool:
        return self.admission.has_configured_providers

    @property
    def rejected_by_limit(self) -> bool:
        return self.admission.rejected_by_limit

    @property
    def fanout_diagnostics(self) -> dict[str, object] | None:
        return self.admission.fanout_diagnostics


def analysis_request_values(
    values: Mapping[str, object],
    *,
    default_mode: str = DEFAULT_ANALYSIS_MODE,
) -> AnalysisRequestValues:
    """Extract raw analyze request fields from form or JSON mappings."""
    return AnalysisRequestValues(
        text=values.get("text", ""),
        mode=values.get("mode", default_mode),
    )


def build_analysis_intake(
    *,
    text: object,
    mode: object,
    has_content: Callable[[str], bool],
    extract_iocs: Callable[[str], list[IOC]],
) -> AnalysisIntake:
    """Validate text/mode once and run IOC extraction only for valid input."""
    if mode not in VALID_ANALYSIS_MODES:
        return AnalysisIntake(
            text=text if isinstance(text, str) else "",
            mode=mode if isinstance(mode, str) else DEFAULT_ANALYSIS_MODE,
            iocs=[],
            error=ANALYSIS_ERROR_INVALID_MODE,
        )
    if not isinstance(text, str) or not has_content(text):
        return AnalysisIntake(
            text="",
            mode=mode,
            iocs=[],
            error=ANALYSIS_ERROR_EMPTY_TEXT,
        )
    return AnalysisIntake(
        text=text,
        mode=mode,
        iocs=extract_iocs(text),
    )


def start_online_analysis(
    *,
    iocs: list[IOC],
    text: str,
    mode: str,
    history_store: object,
    registry: object,
    cache_store: object,
    online_limits: tuple[int, int] | None = None,
    setup_orchestrator: Callable[..., tuple[str, object, object]] = _setup_orchestrator,
) -> OnlineStartDecision:
    """Run shared Online admission and launch enrichment only when allowed."""
    admission = _online_admission(
        iocs,
        registry=registry,
        online_limits=online_limits,
    )
    job_id: str | None = None
    if admission.has_configured_providers and not admission.rejected_by_limit:
        job_id, _, _ = setup_orchestrator(
            iocs,
            text,
            mode,
            history_store,
            admission.configured_providers,
            registry=registry,
            cache=cache_store,
        )
    return OnlineStartDecision(admission=admission, job_id=job_id)
