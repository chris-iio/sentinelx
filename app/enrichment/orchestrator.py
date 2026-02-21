"""Enrichment orchestrator — stub for TDD RED phase.

All methods raise NotImplementedError. Implementation follows in Task 2.
"""


class EnrichmentOrchestrator:
    """Orchestrates parallel IOC enrichment via ThreadPoolExecutor.

    Stub implementation — methods raise NotImplementedError.
    """

    def __init__(self, adapter, max_workers: int = 4) -> None:
        raise NotImplementedError

    def enrich_all(self, job_id: str, iocs: list) -> None:
        raise NotImplementedError

    def get_status(self, job_id: str) -> dict | None:
        raise NotImplementedError
