"""
Internationalization support for Aegis Stack CLI.

Usage:
    from aegis.i18n import t

    typer.secho(t("init.title"), fg=typer.colors.BLUE, bold=True)
    typer.echo(t("init.location", path=project_path))

Note: We use ``t`` instead of the conventional ``_`` because ``_`` is
commonly used as a throwaway variable in tuple unpacking throughout the
codebase (e.g., ``result, _ = func()``), which would shadow the import.
"""

from .registry import detect_locale, get_locale, set_locale, translate


def t(key: str, **kwargs: object) -> str:
    """Translate a message key with optional interpolation.

    Fallback chain: current locale -> English -> raw key.

    Args:
        key: Dot-separated message key (e.g., "init.title")
        **kwargs: Values for str.format() interpolation

    Returns:
        Translated string
    """
    return translate(key, **kwargs)


__all__ = ["t", "set_locale", "get_locale", "detect_locale"]
