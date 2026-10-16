"""
config.py — centralized runtime configuration.

Both the CLI (main.py) and the Streamlit dashboard (streamlit.py) need
to (a) point FastF1 at a local cache directory and (b) configure logging.
That setup was previously duplicated; it lives here so behavior stays
consistent and is easy to test.

Environment variables
---------------------
F1_CACHE_DIR   Directory for FastF1's on-disk cache. Default: ./f1_cache
               (created automatically if missing).
F1_LOG_LEVEL   Root log level name (DEBUG/INFO/WARNING/ERROR/CRITICAL).
               Default: WARNING.
"""

import logging
import os

import fastf1

DEFAULT_CACHE_DIR = "f1_cache"
DEFAULT_LOG_LEVEL = "WARNING"

_VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def get_cache_dir() -> str:
    """Return the configured cache directory name (does not create it)."""
    return os.environ.get("F1_CACHE_DIR", DEFAULT_CACHE_DIR)


def get_log_level() -> str:
    """Return a validated log level name, falling back to WARNING.

    An unrecognized ``F1_LOG_LEVEL`` would make ``logging.basicConfig``
    raise at import time; we degrade to the default and warn instead so
    a typo doesn't crash the whole application.
    """
    raw = os.environ.get("F1_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    if raw not in _VALID_LOG_LEVELS:
        # Emit after basicConfig is set up; for now record for the caller.
        logging.getLogger(__name__).warning(
            "Unrecognized F1_LOG_LEVEL=%r, falling back to %s",
            raw,
            DEFAULT_LOG_LEVEL,
        )
        return DEFAULT_LOG_LEVEL
    return raw


def configure_logging(force: bool = False) -> None:
    """Configure root logging once (idempotent unless ``force``)."""
    level = get_log_level()
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=force,
    )


def enable_cache(cache_dir: str | None = None) -> str:
    """Create (if needed) and enable FastF1's on-disk cache.

    Returns the absolute path of the cache directory in use.
    """
    directory = cache_dir or get_cache_dir()
    os.makedirs(directory, exist_ok=True)
    fastf1.Cache.enable_cache(directory)
    return os.path.abspath(directory)


def setup(cache_dir: str | None = None) -> str:
    """One-call bootstrap: configure logging and enable the cache.

    Returns the cache directory path in use.
    """
    configure_logging()
    return enable_cache(cache_dir)
