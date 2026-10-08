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

This template requires Orinoco Lite `0.3.0` or a later version retaining its packaged rendering resources and build output paths.
A fork must also include that functionality; a higher version number alone does not establish compatibility.

The exact package selection lives in `pixi.toml` and may advance independently of the template.
Raise the minimum only when template adaptations or workflows require new package functionality; routine upstream software or asset updates do not require a template update.
