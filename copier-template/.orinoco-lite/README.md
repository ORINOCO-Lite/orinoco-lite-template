# Orinoco Lite template internals

`.orinoco-lite/hugo-adapter/` is a small adapter applied to the www-from-model checkout resolved by the selected Orinoco Lite package.
It maps downstream settings, supplies an unbranded homepage and editorial layout, and adds record editing and people-group rendering.
Shared configuration defaults, theme components, and graph rendering come from upstream.

The package retrieves required Hugo assets with Git Annex from the same selected checkout and copies ordinary files into the build assembly.

Executable commands are supplied by the installed `orinoco-lite` package and invoked through Pixi tasks.
