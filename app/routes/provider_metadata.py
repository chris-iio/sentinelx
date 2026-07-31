"""Provider metadata helpers for analysis result templates."""
from __future__ import annotations

from app.json_utils import encode_json_object
from app.pipeline.models import IOC, IOCType

PROVIDER_COUNT_IOC_TYPES = (
    IOCType.IPV4,
    IOCType.IPV6,
    IOCType.DOMAIN,
    IOCType.URL,
    IOCType.MD5,
    IOCType.SHA1,
    IOCType.SHA256,
    IOCType.EMAIL,
)


def provider_counts_json(registry) -> str:
    """Return provider-count metadata without allocating provider lists."""
    return encode_json_object({
        "ipv4": registry.provider_count_for_type(IOCType.IPV4),
        "ipv6": registry.provider_count_for_type(IOCType.IPV6),
        "domain": registry.provider_count_for_type(IOCType.DOMAIN),
        "url": registry.provider_count_for_type(IOCType.URL),
        "md5": registry.provider_count_for_type(IOCType.MD5),
        "sha1": registry.provider_count_for_type(IOCType.SHA1),
        "sha256": registry.provider_count_for_type(IOCType.SHA256),
        "email": registry.provider_count_for_type(IOCType.EMAIL),
    })


def provider_coverage(registry, configured=None) -> dict[str, int]:
    """Return registered/configured provider coverage without copying all providers."""
    registered_count = registry.registered_count()
    configured_providers = registry.configured() if configured is None else configured
    configured_count = len(configured_providers)
    return {
        "registered": registered_count,
        "configured": configured_count,
        "needs_key": registered_count - configured_count,
    }


def _provider_count_for_type_cached(
    counts_by_type: dict[IOCType, int],
    registry,
    ioc_type: IOCType,
) -> int:
    if ioc_type not in counts_by_type:
        counts_by_type[ioc_type] = registry.provider_count_for_type(ioc_type)
    return counts_by_type[ioc_type]


def enrichable_count(iocs: list[IOC], registry) -> int:
    """Return total provider fanout while counting each IOC type once."""
    ioc_count = len(iocs)
    if ioc_count == 0:
        return 0
    if ioc_count == 1:
        return registry.provider_count_for_type(iocs[0].type)
    if ioc_count == 2:
        first_type = iocs[0].type
        second_type = iocs[1].type
        first_count = registry.provider_count_for_type(first_type)
        if second_type == first_type:
            return first_count + first_count
        return first_count + registry.provider_count_for_type(second_type)
    if ioc_count == 3:
        first_type = iocs[0].type
        second_type = iocs[1].type
        third_type = iocs[2].type
        first_count = registry.provider_count_for_type(first_type)
        total = first_count
        if second_type == first_type:
            second_count = first_count
        else:
            second_count = registry.provider_count_for_type(second_type)
        total += second_count
        if third_type == first_type:
            return total + first_count
        if third_type == second_type:
            return total + second_count
        return total + registry.provider_count_for_type(third_type)
    if ioc_count == 4:
        first_type = iocs[0].type
        second_type = iocs[1].type
        third_type = iocs[2].type
        fourth_type = iocs[3].type
        first_count = registry.provider_count_for_type(first_type)
        total = first_count
        if second_type == first_type:
            second_count = first_count
        else:
            second_count = registry.provider_count_for_type(second_type)
        total += second_count
        if third_type == first_type:
            third_count = first_count
        elif third_type == second_type:
            third_count = second_count
        else:
            third_count = registry.provider_count_for_type(third_type)
        total += third_count
        if fourth_type == first_type:
            return total + first_count
        if fourth_type == second_type:
            return total + second_count
        if fourth_type == third_type:
            return total + third_count
        return total + registry.provider_count_for_type(fourth_type)

    counts_by_type: dict[IOCType, int] = {}
    total = 0
    for ioc in iocs:
        total += _provider_count_for_type_cached(counts_by_type, registry, ioc.type)
    return total
