# Getting started

1. Set the site identity and canonical public URL in `pyproject.toml` (`tool.orinoco.site`).
2. Replace the starter records and `/explore` page with reviewed site metadata and editorial content before publishing.
3. Add further editorial pages, assets, and static inputs only under their `site-specific/` directories.
4. Run `pixi run build`; it validates the inputs as part of building the site.
5. Configure repository Pages and curation settings before enabling hosted editing.

Run `pixi run build` before replacing the examples to explore the starter site.
The default pages and relationships come from metadata; authored pages and layout overrides are optional.
In `site-specific/metadata/records/`, the site record associates the example person through `associated_with`, the project belongs to the site through `part_of` and names its contributor through `associated_with`, and the publication names its author through `attributed_to`.
These relationships follow the selected upstream projection: people are selected through the site's associations and projects through membership in the site.
When replacing examples, update both their `pid` identifiers and the records that reference them; adding an unrelated record does not necessarily create a page or listing entry.

To test local package edits, run `pixi run dev-enable ../orinoco-lite-dev`; restore the preceding package selection with `pixi run dev-disable`.
Both tasks record the package selection, lockfile, and development link with DataLad, leaving unrelated site edits uncommitted.
The recorded editable connection still depends on that local checkout.

Use [template updates](template-updates.md) to update the scaffold and package through a GitHub draft pull request or the local CLI.

Orinoco Lite supplies the default projection and resolves the www-from-model checkout selected by its packaged resources.
Ordinary site construction should use declarative inputs and the supported small overrides under `site-specific/overrides/`, not copy the upstream Hugo components into this repository.

Use `pixi run orinoco-lite validate` to check inputs without generating a site or projection, and `pixi run orinoco-lite verify-site build/site` to check an existing local build without rebuilding it.
Builds reuse unchanged metadata projections; `pixi run build --no-cache` repeats projection and semantic checks without fetching new source data.

For GitHub Pages, `pixi run build-pages` builds the website and emits its publication bundle from clean committed inputs.
The workflow deploys the site, then runs `publication record` to retain that successful build outside the source branch.
There is no separate preparation step and no rebuild after deployment.

The template's required materialized Hugo assets are ordinary files under `.orinoco-lite/materialized-hugo-assets/upstream/`.
Site-specific assets belong under `site-specific/`; downstream tasks never hydrate either tree with Git Annex.

Metadata acquisition and curation programs may live under `extensions/` and run through explicit adapter tasks.
They must write proposals or reviewed metadata inputs; the website build never imports or executes them.
