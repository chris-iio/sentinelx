"""IOC extraction pipeline package.

The pipeline consists of pure functions with no Flask context dependencies,
no HTTP calls, and no side effects. This guarantees testability and enforces
the offline/online boundary in route handlers (not in business logic).

Pipeline components (added in Plans 02-03):
- extractor.py  — extract_iocs(text: str) -> list[dict]
- normalizer.py — normalize(raw: str) -> str
- classifier.py — classify(normalized: str, raw: str) -> IOC | None
- models.py     — IOCType enum, IOC frozen dataclass, group_by_type utility
"""
