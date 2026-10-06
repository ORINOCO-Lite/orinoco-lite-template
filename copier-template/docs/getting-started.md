# Getting started

1. Set the site identity and canonical public URL in `pyproject.toml` (`tool.orinoco.site`).
2. Run `pixi run build` and `pixi run serve` to preview the starter site.
3. Replace the records in `site-specific/metadata/records/` with your own metadata and rebuild.
4. Add optional pages, assets, and appearance overrides under `site-specific/`; see [file ownership](ownership.md).
5. Configure repository Pages and curation settings before enabling hosted editing.

The site record's `associated_with` selects people; a project's `part_of` places it within the site.
Projects name contributors through `associated_with`, and publications name authors through `attributed_to`.
When changing a record's `pid`, update references to it in other records too.

To develop the package, run `pixi run dev-enable` and edit `submodule/orinoco-lite-dev` or its nested dependencies.
The checkout is local and ignored; the switch is not recorded with DataLad.
Return to a fixed package with `pixi run orinoco-lite package update --revision FULL_SHA`, then start a fresh Pixi command.

Use [template updates](template-updates.md) to update the scaffold and package through a GitHub draft pull request or the local CLI.

Use `pixi run orinoco-lite validate` to check inputs without generating a site or projection, and `pixi run orinoco-lite verify-site build/site` to check an existing local build without rebuilding it.
Fixed installs reuse unchanged metadata projections; editable installs recompute them.
`pixi run build --no-cache` repeats projection and semantic checks without fetching new source data.

For GitHub Pages, `pixi run build-pages` builds the website and emits its publication bundle from clean committed inputs.
The workflow deploys the site, then runs `publication record` to retain that successful build outside the source branch.
There is no separate preparation step and no rebuild after deployment.

Metadata acquisition and curation programs may live under `extensions/` and run through explicit adapter tasks.
They must write proposals or reviewed metadata inputs; the website build never imports or executes them.
