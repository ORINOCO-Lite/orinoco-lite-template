# Orinoco Lite downstream template

This repository publishes a thin Copier scaffold for Orinoco Lite downstreams.
It supplies repository structure, workflows, helper tools, exact release
coordinates, a small Orinoco presentation adapter, and a bounded licensed
overlay for required presentation assets. It does not distribute the reusable
website.

The verified engine runtime is the single authority for the exact German
[`www-from-model`](https://hub.psychoinformatics.de/www/www-from-model)
revision and official Congo dependency. At build time the engine resolves
those sources and composes them with:

```text
.orinoco-lite/presentation/  small template-owned adaptation
.orinoco-lite/materialized-presentation/upstream/
                             required ordinary-file asset overlay
site-specific/               declarative downstream inputs and overrides
extensions/                  optional metadata acquisition and curation code
```

The source branch contains maintainable inputs and behavioral tests. A local
render goes to ignored build state:

```console
pixi run render
pixi run check
```

The `github-template` branch is a derived distribution for GitHub's repository
template feature. It is rendered from an exact source tag and is not used as a
test fixture. See [testing](docs/testing.md),
[publishing](docs/publishing.md), and [releasing](docs/releasing.md).

## License

Original scaffold software and the bounded materialized presentation overlay
are MIT licensed; original documentation is CC BY 4.0. Applicable dependency
notices are preserved. See [LICENSES.md](LICENSES.md).
