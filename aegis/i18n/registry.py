"""Locale registry and message resolution."""

import os

_current_locale: str = "en"
_messages: dict[str, dict[str, str]] = {}


def set_locale(locale: str) -> None:
    """Set the active locale."""
    global _current_locale
    normalized = _normalize_locale(locale)
    _current_locale = normalized
    _load_locale(normalized)


def get_locale() -> str:
    """Get the active locale code."""
    return _current_locale


def detect_locale() -> str:
    """Detect locale from environment.

    Priority: AEGIS_LANG env var -> system locale -> 'en'
    """
    env_lang = os.environ.get("AEGIS_LANG")
    if env_lang:
        return _normalize_locale(env_lang)

    import locale as locale_mod

    try:
        system_locale, _ = locale_mod.getlocale()
    except Exception:
        system_locale = None

    if system_locale:
        return _normalize_locale(system_locale)

    return "en"


def _normalize_locale(raw: str) -> str:
    """Normalize locale string to a supported code.

    Maps zh_CN, zh-Hans, zh_TW, zh -> 'zh'
    Maps en_US, en-GB, en -> 'en'
    Unsupported locales fall back to 'en'
    """
    code = raw.lower().replace("-", "_").split("_")[0]
    from .locales import AVAILABLE_LOCALES

    if code in AVAILABLE_LOCALES:
        return code
    return "en"


def _load_locale(locale: str) -> None:
    """Lazily load a locale's messages into the registry."""
    if locale in _messages:
        return

    if locale == "zh":
        from .locales.zh import MESSAGES

        _messages["zh"] = MESSAGES
    elif locale == "ko":
        from .locales.ko import MESSAGES

        _messages["ko"] = MESSAGES

    # Always ensure English is available as fallback
    if "en" not in _messages:
        from .locales.en import MESSAGES as EN_MESSAGES

        _messages["en"] = EN_MESSAGES


def translate(key: str, **kwargs: object) -> str:
    """Look up a message key and interpolate.

    Fallback chain: current locale -> English -> raw key.
    """
    _load_locale(_current_locale)
    _load_locale("en")

    msg = _messages.get(_current_locale, {}).get(key)
    if msg is None:
        msg = _messages.get("en", {}).get(key)
    if msg is None:
        return key

    if kwargs:
        try:
            return msg.format(**kwargs)
        except (KeyError, IndexError):
            return msg
    return msg
