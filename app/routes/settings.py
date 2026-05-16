"""Settings routes: provider API key management and cache controls."""

from flask import (
    current_app, flash, redirect, render_template, request, url_for,
)

from app import limiter
from app.enrichment.config_store import ConfigStore
from app.enrichment.setup import PROVIDER_IDS, PROVIDER_INFO, build_registry
from app.text_utils import stripped_text_or_none

from . import bp
from ._helpers import _mask_key, get_history_save_diagnostics


_VALID_PROVIDER_IDS = frozenset(PROVIDER_IDS)
_VIRUSTOTAL_PROVIDER_ID = "virustotal"


def _stripped_form_value(field_name: str) -> str:
    value = request.form.get(field_name)
    if value is None:
        return ""
    return stripped_text_or_none(value) or ""


@bp.route("/settings", methods=["GET"])
@limiter.limit("30 per minute")
def settings_get():
    """Settings page — shows per-provider API key configuration forms."""
    config_store = ConfigStore()
    provider_keys = config_store.all_provider_keys()
    providers_with_status = []
    for info in PROVIDER_INFO:
        pid = info["id"]
        if pid == _VIRUSTOTAL_PROVIDER_ID:
            key = config_store.get_vt_api_key()
        else:
            key = provider_keys.get(pid)
        providers_with_status.append({
            **info,
            "masked_key": _mask_key(key),
            "configured": key is not None,
        })
    cache = current_app.cache_store
    cache_stats = cache.stats()
    cache_ttl = config_store.get_cache_ttl()
    history_save_diagnostics = get_history_save_diagnostics()
    return render_template(
        "settings.html",
        providers=providers_with_status,
        cache_stats=cache_stats,
        cache_ttl=cache_ttl,
        history_save_diagnostics=history_save_diagnostics,
    )


@bp.route("/settings", methods=["POST"])
@limiter.limit("10 per minute")
def settings_post():
    """Save a provider API key."""
    provider_id = _stripped_form_value("provider_id")
    api_key = _stripped_form_value("api_key")

    if not api_key:
        flash("API key cannot be empty.", "error")
        return redirect(url_for("main.settings_get"))

    if provider_id not in _VALID_PROVIDER_IDS:
        flash("Unknown provider.", "error")
        return redirect(url_for("main.settings_get"))

    config_store = ConfigStore()
    if provider_id == _VIRUSTOTAL_PROVIDER_ID:
        config_store.set_vt_api_key(api_key)
    else:
        config_store.set_provider_key(provider_id, api_key)

    allowed_hosts = current_app.config.get("ALLOWED_API_HOSTS", [])
    current_app.registry = build_registry(allowed_hosts=allowed_hosts, config_store=config_store)

    flash(f"API key saved for {provider_id}.", "success")
    return redirect(url_for("main.settings_get"))


@bp.route("/settings/cache/clear", methods=["POST"])
@limiter.limit("10 per minute")
def cache_clear():
    """Clear all cached enrichment results."""
    current_app.cache_store.clear()
    flash("Cache cleared.", "success")
    return redirect(url_for("main.settings_get"))


@bp.route("/settings/cache/ttl", methods=["POST"])
@limiter.limit("10 per minute")
def cache_ttl_set():
    """Update cache TTL hours setting."""
    ttl_str = _stripped_form_value("cache_ttl")
    try:
        ttl = int(ttl_str)
        if ttl < 1:
            raise ValueError
    except (ValueError, TypeError):
        flash("TTL must be a positive integer.", "error")
        return redirect(url_for("main.settings_get"))
    config_store = ConfigStore()
    config_store.set_cache_ttl(ttl)
    flash(f"Cache TTL set to {ttl} hours.", "success")
    return redirect(url_for("main.settings_get"))
