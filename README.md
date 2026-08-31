# Orinoco Lite template

This repository publishes the complete versioned website template for an
Orinoco Lite downstream. The template owns Hugo configuration, layouts,
navigation, projection templates, workflows, browser tests, and useful generic
defaults.

A rendered downstream has one forward-looking composition boundary:

```text
.orinoco-lite/site/   complete template-owned website
site-specific/        declarative metadata, content, assets, identity, choices,
                      and supported overrides
extensions/           optional metadata acquisition and curation executables
```

The website is generalized from the exact German `www-from-model` baseline
selected by the engineering repository. It contains no German records,
editorial content, identity, or site assets.

## Development

```console
pixi run render
pixi run check
```

`github-template/` is the checked rendering used to verify the default tree.
The engine repository performs combined candidate tests with injected
site-specific inputs before release.

See [testing](docs/testing.md), [publishing](docs/publishing.md), and
[releasing](docs/releasing.md).

## License

Template code is MIT licensed. Vendored Congo theme files retain their upstream
license in `.orinoco-lite/site/themes/congo/LICENSE`.
