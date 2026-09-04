# Template source ownership

The Copier source owns the downstream scaffold, a small Orinoco presentation adapter, a bounded licensed materialized-presentation overlay, generic workflows and tools, documentation, and exact release coordinates.
It does not own the reusable website.
The released package resolves the exact upstream presentation and theme.
Optional downstream acceptance tests remain site-owned.

The rendered ownership contract distinguishes:

- template-owned scaffold, adapter, materialized asset, workflow, tool, and documentation files;
- optional site-owned acceptance tests;
- declarative `site-specific/` inputs and supported overrides;
- executable metadata adapters under `extensions/`;
- exact release locks; and
- ignored generated output.

The source branch does not store a rendered consumer.
Disposable renders test composition, while the derived `github-template` branch exists only as a GitHub repository-creation distribution.

This is a forward-looking contract for new downstreams.
Earlier structures and automated migration are outside its scope.
