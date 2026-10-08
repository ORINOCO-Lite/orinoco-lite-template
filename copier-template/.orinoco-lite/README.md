# Orinoco Lite template internals

`.orinoco-lite/hugo-adapter/` is a small adapter applied to the www-from-model rendering resources supplied by the selected Orinoco Lite package.
It maps downstream settings, supplies an unbranded homepage and editorial layout, and adds record editing and people-group rendering.
Shared configuration defaults, theme components, and graph rendering come from upstream.

Fixed installations bundle the required upstream rendering files, Congo, assets, and notices.
Website builds need no upstream Git/Annex checkout or asset downloads.
Editable installations use the package's nested working checkout, including local changes.

Executable commands are supplied by the installed `orinoco-lite` package and invoked through Pixi tasks.

## Package compatibility

The package supplies reusable rendering functionality, its pinned upstream dependencies, and required framework assets.
The template supplies the Orinoco adaptation and scaffold; site records, pages, and media remain downstream-owned.
Package updates do not import the upstream organisation's content.

This template requires the packaged rendering resources and build output paths supplied by package commit `d573ae1107ae947002ae33b64027b14f1aa83f81`.
These changes are not yet released; this commit is the compatibility baseline until a containing release supplies the minimum version.
Select this commit or a descendant retaining that functionality for candidate testing.
A fork must also include that functionality; a higher version number alone does not establish compatibility.

The exact package selection lives in `pixi.toml` and may advance independently of the template.
Raise the minimum only when template adaptations or workflows require new package functionality; routine upstream software or asset updates do not require a template update.
Before publishing this template, replace the unreleased baseline above with the first released package version containing it.
