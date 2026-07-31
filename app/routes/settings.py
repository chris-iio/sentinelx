"""Settings routes: provider API key management and cache controls."""

from flask import (
    current_app, flash, redirect, render_template, request, url_for,
)

from app import limiter
from app.enrichment.config_store import ConfigStore
from app.enrichment.provider_catalog import PROVIDER_INFO, valid_provider_ids

from . import bp
from app.enrichment.history_diagnostics import get_history_save_diagnostics
from . import settings_view


_VALID_PROVIDER_IDS = valid_provider_ids()


def _set_current_registry(registry) -> None:
    """Replace the app registry after provider-key changes rebuild it."""
    current_app.registry = registry


@bp.route("/settings", methods=["GET"])
@limiter.limit("30 per minute")
def settings_get():
    """Settings page — shows per-provider API key configuration forms."""
    return settings_view.settings_page_route_response(
        cache_store=current_app.cache_store,
        registry=current_app.registry,
        provider_info=PROVIDER_INFO,
        config_store_factory=ConfigStore,
        history_save_diagnostics=get_history_save_diagnostics(),
        render_template=render_template,
    )


@bp.route("/settings", methods=["POST"])
@limiter.limit("10 per minute")
def settings_post():
    """Save a provider API key."""
    return settings_view.provider_key_save_route_response(
        request.form,
        valid_provider_ids=_VALID_PROVIDER_IDS,
        config_store_factory=ConfigStore,
        allowed_hosts=current_app.config.get("ALLOWED_API_HOSTS", []),
        set_registry=_set_current_registry,
        flash_message=flash,
        redirect_to=redirect,
        settings_url=url_for("main.settings_get"),
    )


@bp.route("/settings/cache/clear", methods=["POST"])
@limiter.limit("10 per minute")
def cache_clear():
    """Clear all cached enrichment results."""
    return settings_view.cache_clear_route_response(
        current_app.cache_store,
        set_registry=_set_current_registry,
        flash_message=flash,
        redirect_to=redirect,
        settings_url=url_for("main.settings_get"),
    )


@bp.route("/settings/cache/ttl", methods=["POST"])
@limiter.limit("10 per minute")
def cache_ttl_set():
    """Update cache TTL hours setting."""
    return settings_view.cache_ttl_update_route_response(
        request.form,
        config_store_factory=ConfigStore,
        set_registry=_set_current_registry,
        flash_message=flash,
        redirect_to=redirect,
        settings_url=url_for("main.settings_get"),
    )
