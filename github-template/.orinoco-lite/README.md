# Orinoco Lite template internals

`.orinoco-lite/site/` is the complete versioned website implementation.
`.orinoco-lite/tools/` and `.orinoco-lite/tests/` support deterministic builds,
browser checks, ownership validation, and static curation interfaces.

Downstream data and policy belong under `site-specific/` and `extensions/`.
Generated projection, browser, runtime, and build state is ignored.
