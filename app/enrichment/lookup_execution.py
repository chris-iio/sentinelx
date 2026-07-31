"""Retry/backoff execution for one enrichment adapter lookup."""

from __future__ import annotations

import logging
from collections.abc import Callable
from threading import Semaphore
from typing import Any

from .models import EnrichmentError, EnrichmentResult
from .retry_policy import (
    MAX_RATE_LIMIT_RETRIES,
    NON_RATE_LIMIT_RETRY_DELAY,
    is_rate_limit_error,
    rate_limit_backoff_delay,
)
from app.pipeline.models import IOC

AttemptFn = Callable[
    [str, Any, IOC, str],
    EnrichmentResult | EnrichmentError,
]
RecordRetryFn = Callable[[str, str, bool], None]
SleepFn = Callable[[float], None]
RandomUniformFn = Callable[[float, float], float]


def run_attempt_with_semaphore(
    job_id: str,
    adapter: Any,
    ioc: IOC,
    provider_name: str,
    semaphore: Semaphore | None,
    *,
    attempt: Callable[[str, Any, IOC, str], EnrichmentResult | EnrichmentError],
) -> EnrichmentResult | EnrichmentError:
    """Execute one lookup attempt while honoring the optional provider semaphore."""
    if semaphore is None:
        return attempt(job_id, adapter, ioc, provider_name)

    semaphore.acquire()
    try:
        return attempt(job_id, adapter, ioc, provider_name)
    finally:
        semaphore.release()


def run_lookup_with_retries(
    job_id: str,
    adapter: Any,
    ioc: IOC,
    *,
    provider_name: str,
    semaphore: Semaphore | None,
    attempt: AttemptFn,
    record_retry: RecordRetryFn,
    sleep: SleepFn,
    random_uniform: RandomUniformFn,
    logger: logging.Logger,
) -> EnrichmentResult | EnrichmentError:
    """Run one lookup with retry/backoff while keeping sleeps outside semaphores."""
    result = run_attempt_with_semaphore(
        job_id,
        adapter,
        ioc,
        provider_name,
        semaphore,
        attempt=attempt,
    )

    if not isinstance(result, EnrichmentError):
        return result

    if is_rate_limit_error(result):
        for attempt_number in range(1, MAX_RATE_LIMIT_RETRIES + 1):
            record_retry(job_id, provider_name, True)
            delay = rate_limit_backoff_delay(attempt_number, random_uniform)
            logger.warning(
                "Rate limit (429) from %s for %s — backoff attempt %d, sleeping %.1fs",
                provider_name,
                ioc.value,
                attempt_number,
                delay,
            )
            sleep(delay)

            result = run_attempt_with_semaphore(
                job_id,
                adapter,
                ioc,
                provider_name,
                semaphore,
                attempt=attempt,
            )

            if not isinstance(result, EnrichmentError):
                return result
            if not is_rate_limit_error(result):
                break
    else:
        record_retry(job_id, provider_name, False)
        sleep(NON_RATE_LIMIT_RETRY_DELAY)
        result = run_attempt_with_semaphore(
            job_id,
            adapter,
            ioc,
            provider_name,
            semaphore,
            attempt=attempt,
        )

    return result
