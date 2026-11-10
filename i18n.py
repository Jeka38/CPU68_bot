"""Minimal gettext-like translation loader.

One Python module per language lives in ``locales/<code>.py`` and exposes a
``STRINGS`` dict. ``LANGUAGE`` comes from the environment (``.env`` is loaded by
bot.py before this module is imported) and defaults to Russian.
"""

import importlib
import os

DEFAULT_LANGUAGE = "ru"


def normalize_language(value: str) -> str:
    """Turn ``en-US`` / ``EN_us`` into ``en``; empty values become the default."""
    return (value or "").strip().lower().replace("_", "-").split("-")[0]


LANGUAGE = normalize_language(os.getenv("LANGUAGE", DEFAULT_LANGUAGE))
if not LANGUAGE:
    LANGUAGE = DEFAULT_LANGUAGE


def _load_catalog(language: str) -> dict[str, str]:
    try:
        module = importlib.import_module(f"locales.{language}")
    except ModuleNotFoundError as exc:
        if exc.name != f"locales.{language}":
            raise
        module = importlib.import_module(f"locales.{DEFAULT_LANGUAGE}")
    return module.STRINGS


_CATALOG = _load_catalog(LANGUAGE)
_FALLBACK = _load_catalog(DEFAULT_LANGUAGE)


def t(key: str, **kwargs) -> str:
    """Return the translated string for ``key``, formatted with ``kwargs``.

    Missing keys fall back to the default language so a partially translated
    catalog still works; unknown keys raise at call time (caught by tests).
    """
    template = _CATALOG.get(key) or _FALLBACK.get(key)
    if template is None:
        raise KeyError(f"unknown translation key: {key}")
    if not kwargs:
        return template
    return template.format(**kwargs)
