"""Low-level config file persistence helpers for ConfigStore."""
from __future__ import annotations

import configparser
import os
import tempfile
import threading
from pathlib import Path

_CONFIG_LOCKS_GUARD = threading.Lock()
_CONFIG_LOCKS: dict[Path, threading.RLock] = {}


def config_lock_for_path(path: Path) -> threading.RLock:
    """Return the shared in-process lock for one config path."""
    key = path.resolve(strict=False)
    with _CONFIG_LOCKS_GUARD:
        lock = _CONFIG_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _CONFIG_LOCKS[key] = lock
        return lock


def copy_config(cfg: configparser.ConfigParser) -> configparser.ConfigParser:
    """Return a mutable copy so failed writes do not poison the read cache."""
    copied = configparser.ConfigParser(interpolation=None)
    for section in cfg.sections():
        append_config_section(copied, cfg, section)
    return copied


def append_config_section(
    copied: configparser.ConfigParser,
    source: configparser.ConfigParser,
    section: str,
) -> None:
    copied.add_section(section)
    source_section = source[section]
    for option in source_section:
        append_config_option(copied, section, source_section, option)


def append_config_option(
    copied: configparser.ConfigParser,
    section: str,
    source_section: configparser.SectionProxy,
    option: str,
) -> None:
    copied.set(section, option, source_section[option])


def write_config_atomic(path: Path, cfg: configparser.ConfigParser) -> None:
    """Atomically write config to disk with owner-only permissions."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temp_path = Path(temp_name)
    try:
        os.chmod(temp_path, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            cfg.write(fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
