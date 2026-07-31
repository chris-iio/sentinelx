"""Pure settings-page view model helpers."""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.enrichment.setup import build_registry
from app.pipeline.models import IOCType

from .browser_responses import FlashRedirect, apply_flash_redirect
from .template_results import TemplateResult, apply_template_result
from .form_values import stripped_form_value

VIRUSTOTAL_PROVIDER_ID = "virustotal"
API_KEY_EMPTY_MESSAGE = "API key cannot be empty."
UNKNOWN_PROVIDER_MESSAGE = "Unknown provider."
CACHE_CLEARED_MESSAGE = "Cache cleared."
TTL_INVALID_MESSAGE = "TTL must be a positive integer."
MASKED_API_KEY_MESSAGE = "Enter a new API key instead of the masked configured value."

_IOC_TYPE_LABELS = {
    IOCType.IPV4: "IPv4",
    IOCType.IPV6: "IPv6",
    IOCType.DOMAIN: "domain",
    IOCType.URL: "URL",
    IOCType.MD5: "MD5",
    IOCType.SHA1: "SHA1",
    IOCType.SHA256: "SHA256",
    IOCType.EMAIL: "email",
    IOCType.CVE: "CVE",
}
def _mask_key(key: str | None) -> str | None:
    """Return key with all but the last 4 characters replaced by asterisks."""
    if key is None or key == "":
        return None
    key_length = len(key)
    if key_length <= 4:
        return None
    return "*" * (key_length - 4) + key[-4:]


@dataclass(frozen=True, slots=True)
class SettingsActionResult:
    """Result of a settings POST action before Flask applies the redirect."""

    message: str
    category: str
    registry: Any | None = None


def supported_types_text(supported_types: set[IOCType] | frozenset[IOCType]) -> str:
    """Render supported IOC types in the stable settings-page order."""
    text = ""
    text = append_supported_type_text(text, supported_types, IOCType.IPV4)
    text = append_supported_type_text(text, supported_types, IOCType.IPV6)
    text = append_supported_type_text(text, supported_types, IOCType.DOMAIN)
    text = append_supported_type_text(text, supported_types, IOCType.URL)
    text = append_supported_type_text(text, supported_types, IOCType.MD5)
    text = append_supported_type_text(text, supported_types, IOCType.SHA1)
    text = append_supported_type_text(text, supported_types, IOCType.SHA256)
    text = append_supported_type_text(text, supported_types, IOCType.EMAIL)
    return append_supported_type_text(text, supported_types, IOCType.CVE)


def append_supported_type_text(
    text: str,
    supported_types: set[IOCType] | frozenset[IOCType],
    ioc_type: IOCType,
) -> str:
    if ioc_type not in supported_types:
        return text
    label = _IOC_TYPE_LABELS[ioc_type]
    if text:
        return text + " · " + label
    return label


def _provider_status_row(
    info: Mapping[str, Any],
    provider_keys: Mapping[str, str],
    vt_api_key: str | None,
) -> dict[str, Any]:
    provider_id = str(info["id"])
    key = vt_api_key if provider_id == VIRUSTOTAL_PROVIDER_ID else provider_keys.get(provider_id)
    row: dict[str, Any] = {}
    for field in info:
        row[field] = info[field]
    row["masked_key"] = _mask_key(key)
    row["configured"] = key is not None
    return row


def provider_status_rows(
    provider_info: Sequence[Mapping[str, Any]],
    provider_keys: Mapping[str, str],
    vt_api_key: str | None,
) -> list[dict[str, Any]]:
    """Return provider config rows with masked keys and configured flags."""
    rows: list[dict[str, Any]] = []
    for info in provider_info:
        append_provider_status_row(rows, info, provider_keys, vt_api_key)
    return rows


def append_provider_status_row(
    rows: list[dict[str, Any]],
    info: Mapping[str, Any],
    provider_keys: Mapping[str, str],
    vt_api_key: str | None,
) -> None:
    rows.append(_provider_status_row(info, provider_keys, vt_api_key))


def save_provider_key(config_store: Any, provider_id: str, api_key: str) -> None:
    """Persist a provider key through the correct ConfigStore path."""
    if provider_id == VIRUSTOTAL_PROVIDER_ID:
        config_store.set_vt_api_key(api_key)
        return
    config_store.set_provider_key(provider_id, api_key)


def save_provider_key_and_rebuild_registry(
    *,
    config_store: Any,
    provider_id: str,
    api_key: str,
    allowed_hosts: object,
) -> Any:
    """Persist a provider key and return a registry rebuilt from current config."""
    save_provider_key(config_store, provider_id, api_key)
    return build_registry(allowed_hosts=allowed_hosts, config_store=config_store)


def is_masked_api_key(value: str) -> bool:
    """Return whether a value matches the legacy masked-key display format."""
    return len(value) > 4 and value[:-4].count("*") == len(value) - 4


def provider_key_save_action(
    *,
    provider_id: str,
    api_key: str,
    valid_provider_ids: frozenset[str],
    config_store_factory: Any,
    allowed_hosts: object,
) -> SettingsActionResult:
    """Validate and execute a provider-key save request."""
    if not api_key:
        return SettingsActionResult(API_KEY_EMPTY_MESSAGE, "error")

    if is_masked_api_key(api_key):
        return SettingsActionResult(MASKED_API_KEY_MESSAGE, "error")

    if provider_id not in valid_provider_ids:
        return SettingsActionResult(UNKNOWN_PROVIDER_MESSAGE, "error")

    registry = save_provider_key_and_rebuild_registry(
        config_store=config_store_factory(),
        provider_id=provider_id,
        api_key=api_key,
        allowed_hosts=allowed_hosts,
    )
    return SettingsActionResult(api_key_saved_message(provider_id), "success", registry)


def provider_key_save_action_from_form(
    form: Mapping[str, object],
    *,
    valid_provider_ids: frozenset[str],
    config_store_factory: Any,
    allowed_hosts: object,
) -> SettingsActionResult:
    """Normalize a provider-key form and execute the save request."""
    return provider_key_save_action(
        provider_id=stripped_form_value(form, "provider_id"),
        api_key=stripped_form_value(form, "api_key"),
        valid_provider_ids=valid_provider_ids,
        config_store_factory=config_store_factory,
        allowed_hosts=allowed_hosts,
    )


def provider_key_save_route_response(
    form: Mapping[str, object],
    *,
    valid_provider_ids: frozenset[str],
    config_store_factory: Any,
    allowed_hosts: object,
    set_registry: Callable[[Any], object],
    flash_message: Callable[[str, str], object],
    redirect_to: Callable[[str], object],
    settings_url: str,
) -> object:
    """Apply a provider-key save form through the shared settings action response path."""
    return apply_settings_action_response(
        provider_key_save_action_from_form(
            form,
            valid_provider_ids=valid_provider_ids,
            config_store_factory=config_store_factory,
            allowed_hosts=allowed_hosts,
        ),
        set_registry=set_registry,
        flash_message=flash_message,
        redirect_to=redirect_to,
        settings_url=settings_url,
    )


def cache_ttl_update_action(
    *,
    raw_ttl: str,
    config_store_factory: Any,
) -> SettingsActionResult:
    """Validate and execute a cache-TTL update request."""
    ttl = positive_cache_ttl_hours(raw_ttl)
    if ttl is None:
        return SettingsActionResult(TTL_INVALID_MESSAGE, "error")

    config_store = config_store_factory()
    config_store.set_cache_ttl(ttl)
    return SettingsActionResult(cache_ttl_saved_message(ttl), "success")


def cache_ttl_update_action_from_form(
    form: Mapping[str, object],
    *,
    config_store_factory: Any,
) -> SettingsActionResult:
    """Normalize a cache-TTL form and execute the save request."""
    return cache_ttl_update_action(
        raw_ttl=stripped_form_value(form, "cache_ttl"),
        config_store_factory=config_store_factory,
    )


def cache_ttl_update_route_response(
    form: Mapping[str, object],
    *,
    config_store_factory: Any,
    set_registry: Callable[[Any], object],
    flash_message: Callable[[str, str], object],
    redirect_to: Callable[[str], object],
    settings_url: str,
) -> object:
    """Apply a cache-TTL update form through the shared settings action response path."""
    return apply_settings_action_response(
        cache_ttl_update_action_from_form(
            form,
            config_store_factory=config_store_factory,
        ),
        set_registry=set_registry,
        flash_message=flash_message,
        redirect_to=redirect_to,
        settings_url=settings_url,
    )


def cache_clear_action(cache_store: Any) -> SettingsActionResult:
    """Clear cached enrichment results and return the settings action result."""
    cache_store.clear()
    return SettingsActionResult(CACHE_CLEARED_MESSAGE, "success")


def cache_clear_route_response(
    cache_store: Any,
    *,
    set_registry: Callable[[Any], object],
    flash_message: Callable[[str, str], object],
    redirect_to: Callable[[str], object],
    settings_url: str,
) -> object:
    """Apply a cache-clear request through the shared settings action response path."""
    return apply_settings_action_response(
        cache_clear_action(cache_store),
        set_registry=set_registry,
        flash_message=flash_message,
        redirect_to=redirect_to,
        settings_url=settings_url,
    )


def apply_settings_action(
    action: SettingsActionResult,
    *,
    set_registry: Callable[[Any], object],
) -> SettingsActionResult:
    """Apply any runtime mutation requested by a settings action."""
    if action.registry is not None:
        set_registry(action.registry)
    return action


def apply_settings_action_response(
    action: SettingsActionResult,
    *,
    set_registry: Callable[[Any], object],
    flash_message: Callable[[str, str], object],
    redirect_to: Callable[[str], object],
    settings_url: str,
) -> object:
    """Apply a settings action and return the shared Flask redirect response."""
    applied = apply_settings_action(action, set_registry=set_registry)
    return apply_flash_redirect(
        FlashRedirect(settings_url, applied.message, applied.category),
        flash_message=flash_message,
        redirect_to=redirect_to,
    )


def api_key_saved_message(provider_id: str) -> str:
    """Return the settings flash message for a saved provider API key."""
    return f"API key saved for {provider_id}."


def cache_ttl_saved_message(ttl: int) -> str:
    """Return the settings flash message for a saved cache TTL."""
    return f"Cache TTL set to {ttl} hours."


def positive_cache_ttl_hours(value: str) -> int | None:
    """Return a positive cache TTL hour value, or None when invalid."""
    try:
        ttl = int(value)
    except (TypeError, ValueError):
        return None
    if ttl < 1:
        return None
    return ttl


def provider_health_rows(registry: Any) -> list[dict[str, str]]:
    """Return secret-free local provider health rows for the settings dashboard."""
    rows: list[dict[str, str]] = []
    for provider in registry.all():
        append_provider_health_row(rows, provider)
    return rows


def append_provider_health_row(rows: list[dict[str, str]], provider: Any) -> None:
    rows.append(_provider_health_row(provider))


def _provider_health_row(provider: Any) -> dict[str, str]:
    requires_key = bool(provider.requires_api_key)
    configured = bool(provider.is_configured())
    if not requires_key:
        key_status = "Not required"
    elif configured:
        key_status = "Configured"
    else:
        key_status = "Missing"
    return {
        "name": provider.name,
        "key_status": key_status,
        "readiness": "Ready" if configured else "Needs API key",
        "readiness_class": "ready" if configured else "needs-key",
        "supported_ioc_types": supported_types_text(provider.supported_types),
        "reachability": "Not checked",
        "last_checked": "Never",
        "last_error": "None",
    }


def settings_page_context(
    *,
    provider_info: Sequence[Mapping[str, Any]],
    config_store: Any,
    cache_store: Any,
    registry: Any,
    history_save_diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the complete settings page template context."""
    provider_keys = config_store.all_provider_keys()
    return {
        "providers": provider_status_rows(
            provider_info,
            provider_keys,
            config_store.get_vt_api_key(),
        ),
        "provider_health_rows": provider_health_rows(registry),
        "cache_stats": cache_store.stats(),
        "cache_ttl": config_store.get_cache_ttl(),
        "history_save_diagnostics": history_save_diagnostics,
    }


def settings_route_context(
    *,
    cache_store: Any,
    registry: Any,
    provider_info: Sequence[Mapping[str, Any]],
    config_store_factory: Any,
    history_save_diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    """Return settings page context using the current app dependencies."""
    return settings_page_context(
        provider_info=provider_info,
        config_store=config_store_factory(),
        cache_store=cache_store,
        registry=registry,
        history_save_diagnostics=history_save_diagnostics,
    )


def settings_page_result(
    *,
    cache_store: Any,
    registry: Any,
    provider_info: Sequence[Mapping[str, Any]],
    config_store_factory: Any,
    history_save_diagnostics: Mapping[str, Any],
) -> TemplateResult:
    """Return the settings page render decision from current app dependencies."""
    return TemplateResult(
        "settings.html",
        settings_route_context(
            cache_store=cache_store,
            registry=registry,
            provider_info=provider_info,
            config_store_factory=config_store_factory,
            history_save_diagnostics=history_save_diagnostics,
        ),
        200,
    )


def settings_page_route_response(
    *,
    cache_store: Any,
    registry: Any,
    provider_info: Sequence[Mapping[str, Any]],
    config_store_factory: Any,
    history_save_diagnostics: Mapping[str, Any],
    render_template: Callable[..., Any],
) -> Any:
    """Apply the settings page render decision for route-supplied dependencies."""
    return apply_template_result(
        settings_page_result(
            cache_store=cache_store,
            registry=registry,
            provider_info=provider_info,
            config_store_factory=config_store_factory,
            history_save_diagnostics=history_save_diagnostics,
        ),
        render_template=render_template,
    )
