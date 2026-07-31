"""Stable diagnostic ZIP archive writing."""
from __future__ import annotations

import io
import zipfile
from collections.abc import Iterable

ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def write_stable_zip(entries: Iterable[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_STORED) as archive:
        for path, payload in entries:
            write_zip_entry(archive, path, payload)
    return buffer.getvalue()


def stable_zip_info(path: str) -> zipfile.ZipInfo:
    """Return deterministic ZIP metadata for one archive path."""
    info = zipfile.ZipInfo(filename=path, date_time=ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = 0o600 << 16
    return info


def write_zip_entry(archive: zipfile.ZipFile, path: str, payload: bytes) -> None:
    """Write one archive member with stable metadata."""
    archive.writestr(stable_zip_info(path), payload)
