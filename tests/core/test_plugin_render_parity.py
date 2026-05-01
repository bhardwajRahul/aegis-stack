"""
Render parity between the legacy ``{% if include_X %}`` path and the new
``{% for p in _plugins | default([]) %}`` path (round 8a foundation).

For each in-tree service, render the same shared template two ways and
assert the rendered byte content is identical:

    legacy:  {include_X: True,  _plugins: []}
    plugin:  {include_X: False, _plugins: [serialize_plugin_to_answer(SERVICES[X])]}

If the new for-loop emits the same imports / mounts as the existing
conditional blocks, the test passes byte-for-byte. If a regression is
introduced (a wiring entry dropped, an alias reordered, whitespace
drift), it will fail with a clear diff.

Round 8a starts with ``app/components/backend/api/routing.py`` only;
remaining shared templates are added as their plugin loops land.
"""

from __future__ import annotations

import pytest
from jinja2 import Environment, FileSystemLoader

from aegis.core.component_files import get_copier_defaults, get_template_path
from aegis.core.plugin_composer import PLUGINS_ANSWER_KEY, serialize_plugin_to_answer
from aegis.core.services import SERVICES

PROJECT_SLUG_PLACEHOLDER = "{{ project_slug }}"


def _jinja_env() -> Environment:
    """Match the env constructed in ``ManualUpdater.__init__``."""
    return Environment(
        loader=FileSystemLoader(str(get_template_path())),
        trim_blocks=False,
        lstrip_blocks=False,
    )


def _render(template_rel_path: str, context: dict) -> str:
    env = _jinja_env()
    template = env.get_template(f"{PROJECT_SLUG_PLACEHOLDER}/{template_rel_path}.jinja")
    return template.render(context)


# Map each service name to the legacy ``include_*`` flag(s) it controls.
# Insights/payment/comms/ai all toggle a single flag; auth happens to
# share the file with three (auth/oauth/auth_org), but only ``include_auth``
# corresponds to "auth as a whole".
SERVICE_INCLUDE_KEY = {
    "auth": "include_auth",
    "ai": "include_ai",
    "comms": "include_comms",
    "insights": "include_insights",
    "payment": "include_payment",
}


@pytest.mark.parametrize("service_name", list(SERVICE_INCLUDE_KEY.keys()))
def test_routing_py_parity(service_name: str) -> None:
    """The legacy path and plugin path render byte-identical routing.py
    for every in-tree service, with all sub-feature flags at default.

    Default project state (memory backend, no oauth/voice/rag, ...) means
    only the unconditional router for each service should survive in
    both paths.
    """
    template = "app/components/backend/api/routing.py"
    spec = SERVICES[service_name]
    include_key = SERVICE_INCLUDE_KEY[service_name]

    defaults = get_copier_defaults()

    # Legacy: the include_X flag is on, no plugin entries.
    legacy_answers = {**defaults, include_key: True, PLUGINS_ANSWER_KEY: []}

    # Plugin: include_X flag is off, plugin entry carries the wiring.
    # serialize_plugin_to_answer applies ``when`` predicates against
    # the merged options dict (defaults here), so only entries that
    # match default project state survive.
    plugin_entry = serialize_plugin_to_answer(
        spec, plugin_options=None, project_answers=defaults
    )
    plugin_answers = {
        **defaults,
        include_key: False,
        PLUGINS_ANSWER_KEY: [plugin_entry],
    }

    legacy_output = _render(template, legacy_answers)
    plugin_output = _render(template, plugin_answers)

    assert legacy_output == plugin_output, (
        f"routing.py parity drift for {service_name}:\n"
        f"--- legacy ---\n{legacy_output}\n"
        f"--- plugin ---\n{plugin_output}\n"
    )
