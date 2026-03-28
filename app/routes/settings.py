"""Settings routes: provider API key management and cache controls."""

from flask import (
    current_app, flash, redirect, render_template, request, url_for,
)

from app import limiter
from app.enrichment.config_store import ConfigStore
from app.enrichment.setup import PROVIDER_INFO, build_registry

from . import bp
from ._helpers import _mask_key


@bp.route("/settings", methods=["GET"])
@limiter.limit("30 per minute")
def settings_get():
    """Settings page — shows per-provider API key configuration forms."""
    config_store = ConfigStore()
    providers_with_status = []
    for info in PROVIDER_INFO:
        pid = info["id"]
        if pid == "virustotal":
            key = config_store.get_vt_api_key()
        else:
            key = config_store.get_provider_key(pid)
        providers_with_status.append({
            **info,
            "masked_key": _mask_key(key),
            "configured": key is not None,
        })
    cache = current_app.cache_store
    cache_stats = cache.stats()
    cache_ttl = config_store.get_cache_ttl()
    return render_template(
        "settings.html",
        providers=providers_with_status,
        cache_stats=cache_stats,
        cache_ttl=cache_ttl,
    )


@bp.route("/settings", methods=["POST"])
@limiter.limit("10 per minute")
def settings_post():
    """Save a provider API key."""
    provider_id = request.form.get("provider_id", "").strip()
    api_key = request.form.get("api_key", "").strip()

    if not api_key:
        flash("API key cannot be empty.", "error")
        return redirect(url_for("main.settings_get"))

    valid_ids = {p["id"] for p in PROVIDER_INFO}
    if provider_id not in valid_ids:
        flash("Unknown provider.", "error")
        return redirect(url_for("main.settings_get"))

    config_store = ConfigStore()
    if provider_id == "virustotal":
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
    ttl_str = request.form.get("cache_ttl", "").strip()
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
