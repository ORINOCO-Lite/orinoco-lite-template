# Orinoco Lite template internals

`.orinoco-lite/hugo-adapter/` is a small adapter applied to the www-from-model checkout resolved by the selected Orinoco Lite package.
It maps downstream settings, supplies an unbranded homepage and editorial layout, and adds record editing and people-group rendering.
Shared configuration defaults, theme components, and graph rendering come from upstream.

`www-from-model/` is one ignored Git checkout with its Annex object store.
Package changes switch its selected commit and nested dependencies while retaining downloaded objects.
Pages and validation workflows cache this directory between runs; a cache miss downloads the required content again.
Concurrent builds selecting different revisions require separate downstream working directories.
`hugo-adapter/` and these notices remain tracked template files.

The package retrieves required Hugo assets with Git Annex from the same selected checkout and copies ordinary files into the build assembly.

Executable commands are supplied by the installed `orinoco-lite` package and invoked through Pixi tasks.

## Package compatibility

The package supplies reusable rendering functionality, its pinned upstream dependencies, and required framework assets.
The template supplies the Orinoco adaptation and scaffold; site records, pages, and media remain downstream-owned.
Package updates do not import the upstream organisation's content.

This template requires the reusable upstream checkout and asset handling introduced in package commit `6b98af8c16ade43551f4713db21affd268a11a91`.
These changes are not yet released; this commit is the compatibility baseline until a containing release supplies the minimum version.
Select this commit or a descendant retaining that functionality for candidate testing.
A fork must also include that functionality; a higher version number alone does not establish compatibility.

The exact package selection lives in `pixi.toml` and may advance independently of the template.
Raise the minimum only when template adaptations or workflows require new package functionality; routine upstream software or asset updates do not require a template update.
Before publishing this template, replace the unreleased baseline above with the first released package version containing it.
