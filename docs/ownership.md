# Template source ownership

The Copier source owns the complete generic downstream repository and website.
Its checked rendering is `github-template/`.

The rendered ownership contract distinguishes:

- template-owned website, workflow, tool, test, and documentation files;
- declarative `site-specific/` inputs and supported overrides;
- executable metadata adapters under `extensions/`;
- exact release locks; and
- ignored generated output.

This is the versioned template contract for new downstreams. Migration,
updater behavior, and earlier downstream structures are outside its scope.
