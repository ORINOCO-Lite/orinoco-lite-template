# Getting started

1. Set the site identity and public URL in `site-specific/site.yaml` and
   `orinoco.yaml`.
2. Replace the generic example record under
   `site-specific/metadata/records/` with reviewed site metadata.
3. Add editorial pages, assets, and static inputs only under their
   `site-specific/` directories.
4. Run `pixi run validate`, `pixi run build`, and `pixi run test-all`.
5. Configure repository Pages and curation settings before enabling hosted
   editing.

Projection policy is declarative in `site-specific/projection.yaml`, while its
generic templates and graph producer are template-owned. Do not copy or modify
the framework for ordinary site construction. Use a supported override, fork,
or compatible template when the default website is insufficient.

Metadata acquisition and curation programs may live under `extensions/` and
run through explicit adapter tasks. They must write proposals or reviewed
metadata inputs; the website build never imports or executes them.
