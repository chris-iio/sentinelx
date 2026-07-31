"""Provider dispatch setup helpers for enrichment jobs."""

from __future__ import annotations

from threading import Semaphore
from typing import Any

from .diagnostics import _normalize_provider_name
from app.pipeline.models import IOC


def build_dispatch_pairs(adapters: list[Any], iocs: list[IOC]) -> list[tuple[Any, IOC]]:
    """Return every adapter/IOC pair where the adapter supports the IOC type."""
    ioc_count = len(iocs)
    if ioc_count == 0:
        return []
    if ioc_count == 1:
        ioc = iocs[0]
        pairs: list[tuple[Any, IOC]] = []
        append_supported_dispatch_pairs(pairs, adapters, ioc)
        return pairs
    if ioc_count == 2:
        pairs: list[tuple[Any, IOC]] = []
        append_supported_dispatch_pairs(pairs, adapters, iocs[0])
        append_supported_dispatch_pairs(pairs, adapters, iocs[1])
        return pairs
    if ioc_count == 3:
        pairs: list[tuple[Any, IOC]] = []
        append_supported_dispatch_pairs(pairs, adapters, iocs[0])
        append_supported_dispatch_pairs(pairs, adapters, iocs[1])
        append_supported_dispatch_pairs(pairs, adapters, iocs[2])
        return pairs
    if ioc_count == 4:
        pairs: list[tuple[Any, IOC]] = []
        append_supported_dispatch_pairs(pairs, adapters, iocs[0])
        append_supported_dispatch_pairs(pairs, adapters, iocs[1])
        append_supported_dispatch_pairs(pairs, adapters, iocs[2])
        append_supported_dispatch_pairs(pairs, adapters, iocs[3])
        return pairs

    pairs: list[tuple[Any, IOC]] = []
    for ioc in iocs:
        append_supported_dispatch_pairs(pairs, adapters, ioc)
    return pairs


def append_supported_dispatch_pairs(
    pairs: list[tuple[Any, IOC]],
    adapters: list[Any],
    ioc: IOC,
) -> None:
    for adapter in adapters:
        if ioc.type in adapter.supported_types:
            append_dispatch_pair(pairs, adapter, ioc)


def append_dispatch_pair(
    pairs: list[tuple[Any, IOC]],
    adapter: Any,
    ioc: IOC,
) -> None:
    pairs.append((adapter, ioc))


def build_provider_semaphores(
    adapters: list[Any],
    provider_concurrency: dict[str, int] | None,
) -> dict[str, Semaphore]:
    """Return semaphores only for providers that require API keys."""
    concurrency = provider_concurrency or {}
    semaphores: dict[str, Semaphore] = {}
    adapter_count = len(adapters)
    if adapter_count == 0:
        return semaphores
    if adapter_count == 1:
        append_provider_semaphore(semaphores, adapters[0], concurrency)
        return semaphores
    if adapter_count == 2:
        append_provider_semaphore(semaphores, adapters[0], concurrency)
        append_provider_semaphore(semaphores, adapters[1], concurrency)
        return semaphores
    if adapter_count == 3:
        append_provider_semaphore(semaphores, adapters[0], concurrency)
        append_provider_semaphore(semaphores, adapters[1], concurrency)
        append_provider_semaphore(semaphores, adapters[2], concurrency)
        return semaphores
    if adapter_count == 4:
        append_provider_semaphore(semaphores, adapters[0], concurrency)
        append_provider_semaphore(semaphores, adapters[1], concurrency)
        append_provider_semaphore(semaphores, adapters[2], concurrency)
        append_provider_semaphore(semaphores, adapters[3], concurrency)
        return semaphores

    for adapter in adapters:
        append_provider_semaphore(semaphores, adapter, concurrency)
    return semaphores


def append_provider_semaphore(
    semaphores: dict[str, Semaphore],
    adapter: Any,
    concurrency: dict[str, int],
) -> None:
    """Append one keyed provider semaphore using normalized provider naming."""
    raw_name = getattr(adapter, "name", "")
    provider_name = _normalize_provider_name(raw_name)
    if getattr(adapter, "requires_api_key", False):
        limit = concurrency.get(raw_name, concurrency.get(provider_name, 4))
        semaphores[provider_name] = Semaphore(limit)
