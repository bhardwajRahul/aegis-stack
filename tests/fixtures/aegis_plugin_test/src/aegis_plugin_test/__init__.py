"""Fake plugin package for round 8 plugin-distribution tests.

Ships a minimal ``templates/`` tree so ``plugin_template_resolver`` and
``ManualUpdater`` can locate and render its files. The actual code is
empty — what we exercise is the plugin's *file ownership* surface, not
its runtime behaviour.
"""
