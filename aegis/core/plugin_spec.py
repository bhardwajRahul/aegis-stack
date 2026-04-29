"""
Unified plugin specification — R2 of the plugin system refactor.

Replaces the parallel ``ServiceSpec`` / ``ComponentSpec`` types with a
single ``PluginSpec`` that covers in-tree services, in-tree components,
and (eventually) third-party plugins.

In-tree services and components are first-party plugins (``verified=True``);
external plugins use the same dataclass with ``verified=False``. The
``ServiceSpec`` and ``ComponentSpec`` aliases in
``aegis/core/services.py`` and ``aegis/core/components.py`` preserve
back-compat with pre-R2 call sites — they are subclasses of ``PluginSpec``
that pin ``kind`` to ``SERVICE`` / ``COMPONENT`` by default.

R2 keeps PluginKind narrow (``SERVICE`` / ``COMPONENT``). Additional
kinds (``INTEGRATION``, ``ENHANCEMENT``, ...) are added when a real
plugin needs them, not speculatively.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .file_manifest import FileManifest


class PluginKind(Enum):
    """Top-level role a ``PluginSpec`` plays in an Aegis project."""

    SERVICE = "service"
    """Business-logic plugin (auth, payment, AI, scraping, ...)."""

    COMPONENT = "component"
    """Infrastructure plugin (database, redis, worker, frontend, ...)."""


@dataclass(kw_only=True)
class PluginSpec:
    """Unified specification for components, services, and third-party plugins.

    Field naming notes:

    * ``required_components`` / ``recommended_components`` / ``required_services``
      are the canonical dependency-list fields (matches the pre-R2
      ``ServiceSpec`` convention, which had the higher caller volume).
    * ``requires`` and ``recommends`` exist as **read-only** property aliases
      so legacy ``ComponentSpec``-style attribute access keeps working
      (``component.requires``, ``component.recommends``). Construction via
      those names is intentionally not supported — pass the canonical names.

    The ``type`` field is a sub-classification facet that is meaningful per
    ``kind``: when ``kind=SERVICE`` it carries a ``ServiceType`` (AUTH,
    PAYMENT, ...); when ``kind=COMPONENT`` it carries a ``ComponentType``
    (CORE, INFRASTRUCTURE). Typed as ``Any`` here to avoid a circular
    import; consumers narrow as needed.
    """

    # Identity
    name: str
    kind: PluginKind
    description: str

    # Sub-classification — ServiceType when kind=SERVICE,
    # ComponentType when kind=COMPONENT.
    type: Any = None

    # Dependencies
    required_components: list[str] = field(default_factory=list)
    recommended_components: list[str] = field(default_factory=list)
    required_services: list[str] = field(default_factory=list)
    required_plugins: list[str] = field(default_factory=list)

    # Mutual exclusion
    conflicts: list[str] = field(default_factory=list)

    # Packaging / template
    pyproject_deps: list[str] = field(default_factory=list)
    docker_services: list[str] = field(default_factory=list)
    template_files: list[str] = field(default_factory=list)

    # File ownership for cleanup (R1)
    files: FileManifest = field(default_factory=FileManifest)

    # Bracket-syntax options (R3) — see aegis/core/option_spec.py.
    # ``list[Any]`` rather than ``list[OptionSpec]`` to avoid a runtime
    # circular import; ``OptionSpec`` is only referenced by parsers.
    options: list[Any] = field(default_factory=list)

    # Plugin metadata
    version: str = "0.0.0"
    verified: bool = True

    # ----- Read-only legacy aliases -------------------------------------

    @property
    def requires(self) -> list[str]:
        """Component-style alias for ``required_components``."""
        return self.required_components

    @property
    def recommends(self) -> list[str]:
        """Component-style alias for ``recommended_components``."""
        return self.recommended_components
