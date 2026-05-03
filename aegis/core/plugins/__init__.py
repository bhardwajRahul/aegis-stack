"""
Plugin-system internals.

The CLI's plugin layer — discovery, spec dataclasses, install /
remove / update orchestration, scaffolding, and forward / reverse
dependency resolution. Each module is a focused concern; this
package is the namespace, not a façade.

Importers should reach for the specific module (``from
aegis.core.plugins.spec import PluginSpec``) rather than re-exporting
through this ``__init__`` — keeps the public surface honest about
where a name lives, and avoids accidental cycles between siblings.
"""
