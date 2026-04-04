"""Enrichment polling route."""

from app import limiter

from . import bp
from ._helpers import _get_enrichment_status


@bp.route("/enrichment/status/<job_id>", methods=["GET"])
@limiter.limit("120 per minute")
def enrichment_status(job_id: str):
    """Return current enrichment progress for a job as JSON.

    Supports cursor-based polling via ?since= query param.
    """
    return _get_enrichment_status(job_id)
