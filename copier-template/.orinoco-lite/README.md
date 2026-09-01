# Orinoco Lite template internals

`.orinoco-lite/presentation/` is a small adapter applied to the upstream
presentation resolved by the verified engine runtime. It contains only
configuration, section-content, and static-file templates needed to map the
generic source to this downstream contract; it is not a standalone website.

`.orinoco-lite/tools/` and `.orinoco-lite/tests/` support deterministic builds,
browser checks, ownership validation, and static curation interfaces.

Downstream data and policy belong under `site-specific/` and `extensions/`.
Generated projection, browser, runtime, and build state is ignored.
