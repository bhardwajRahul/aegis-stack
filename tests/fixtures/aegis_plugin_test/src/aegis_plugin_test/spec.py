"""PluginSpec for the fake test plugin.

The entry point ``aegis.plugins`` points at :func:`get_spec`, which
``aegis.core.plugin_discovery.discover_plugins`` calls to materialize
the spec at runtime.
"""

from aegis.core.file_manifest import FileManifest
from aegis.core.plugins.spec import PluginKind, PluginSpec


def get_spec() -> PluginSpec:
    return PluginSpec(
        name="test_plugin",
        kind=PluginKind.SERVICE,
        description="Fake plugin shipped with aegis-stack tests.",
        version="0.0.1",
        verified=False,
        # Files this plugin owns in the target project. ``aegis remove``
        # walks this list (via ``iter_cleanup_paths(spec, selected=False)``)
        # to clean up after itself.
        files=FileManifest(primary=["app/services/test_plugin"]),
    )
