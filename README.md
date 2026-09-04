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

Copier is the only supported creation and update path. Disposable renders are
development and test output, not a second distribution. See
[testing](docs/testing.md) and [releasing](docs/releasing.md).

## Creating a downstream site

A downstream is an ordinary Git repository. Only
[Pixi](https://pixi.sh) 0.76 or newer and a Copier runner are required; the
scaffold pins everything else. The commands below use
[`uv`](https://docs.astral.sh/uv/) to run Copier and DataLad without
installing them.

### 1. Create the repository

```console
uvx datalad create --no-annex my-site
cd my-site
```

DataLad is optional and is used here only to record instantiation provenance;
`git init my-site` is equivalent. The build never requires Git Annex, so
`--no-annex` is the correct mode and no Git Annex installation is needed.

### 2. Instantiate the scaffold

```console
uvx copier copy --trust \
  --vcs-ref v0.2.0rc24 gh:ORINOCO-Lite/orinoco-lite-template .
```

Pass `--vcs-ref` explicitly. Copier resolves a bare `gh:` source to the newest
*stable* tag, so while this template publishes release candidates an
unpinned copy silently instantiates the last 0.1 release instead. Use the
newest tag from
[releases](https://github.com/ORINOCO-Lite/orinoco-lite-template/tags), and
record the instantiation with `datalad run` if the repository is a DataLad
dataset.

Copier asks for four site-identity answers; every release coordinate is
supplied by the template and written to `orinoco.lock`:

| Answer             | Meaning                                                         |
| ------------------ | --------------------------------------------------------------- |
| `project_slug`     | repository and Pages project-path slug                          |
| `project_name`     | human-readable site title                                       |
| `site_description` | short public description                                        |
| `site_base_url`    | canonical public base URL, with project path and trailing slash |

Answers can also be supplied non-interactively with repeated
`--data key=value` options plus `--defaults`, or from a file with
`--data-file answers.yml`.

### 3. Supply the site-owned inputs

Everything a site owns is declarative and lives in two trees:

```text
site-specific/site.yaml              identity, navigation, presentation
site-specific/metadata/records/      Thing YAML records, one entity per file
site-specific/metadata/overlays/annotations/
                                     companion annotations for those records
site-specific/content/               editorial Markdown pages
site-specific/assets/                Hugo asset-pipeline inputs
site-specific/static/                files published verbatim at the site root
site-specific/overrides/{config,layouts,static}
                                     bounded presentation overrides
site-specific/projection.yaml        optional projection contract override
extensions/                          optional metadata-acquisition code
```

Four rules are enforced by the engine and are worth knowing before the first
build:

- Everything below `site-specific/metadata/records/` must be a Thing YAML
  record, and the inventory may not be empty. Delete the scaffold's
  `.gitkeep` and add at least one record — commonly the organization or
  project that the homepage projects from — or the build stops before Hugo
  runs.
- Images referenced from editorial Markdown through Hugo shortcodes such as
  `figure` are resolved through the asset pipeline, so they belong under
  `site-specific/assets/`. `site-specific/static/` is for files that are
  published verbatim and referenced by absolute URL.
- A custom Congo colour scheme is `site-specific/assets/css/schemes/<name>.css`
  named by `presentation.color_scheme`; extra Congo icons are
  `site-specific/assets/icons/<name>.svg`; site CSS is
  `site-specific/assets/css/custom.css`.
- `extensions/` is for executable metadata adapters only. Website functionality
  there is rejected: no `.css`, `.html`, `.js`, `.svg` files and no `assets`,
  `content`, `layouts`, or `static` directories. Presentation belongs in
  `site-specific/overrides/`.

`orinoco.yaml` carries only path selection, and rejects unknown keys. The
recognized paths are `records`, `editorial`, `site`, `generated`,
`extensions`, and `build`; public site identity belongs in
`site-specific/site.yaml`.

#### Example inputs

Published `site-specific/` trees to read before writing your own:

| Example | Contents |
| ------- | -------- |
| [`con-site-specific`](https://github.com/ORINOCO-Lite/con-site-specific) | The Center for Open Neuroscience site: ~220 Things records with annotation overlays, five editorial pages, navigation, and a custom Congo colour scheme. |

An example is a `site-specific/` tree, not a whole downstream, so it can be
copied in or embedded as a submodule or subtree at `site-specific/`.
Embedding keeps the inputs reviewable on their own and lets several
downstreams share one metadata collection. Each example tracks its own
history, so check its README for the template version it currently follows;
older trees may still use conventions the rules above have moved on from.

### 4. Build and preview

```console
pixi install --frozen
pixi run validate
pixi run build
pixi run serve
```

The first build resolves and caches the verified runtime and the exact
upstream presentation, so it needs network access to GitHub and takes longer
than later builds. `pixi run serve` publishes the built site on
<http://127.0.0.1:8765/>, including the static `/edit/` metadata editor.

Before proposing a change, run what CI runs:

```console
pixi run verify-runtime
pixi run verify-hugo
pixi run verify-ownership
pixi run projection-verify
pixi run verify-build
```

`verify-build` builds twice and compares the trees, so it also proves the
site is reproducible.

### 5. Publish

The rendered `.github/workflows/pages.yml` deploys to GitHub Pages. Enable
Pages for the repository with the GitHub Actions source, and keep
`identity.base_url` in `site-specific/site.yaml` equal to the published URL,
including the project path and trailing slash. See
[`docs/custom-domain.md`](copier-template/docs/custom-domain.md) in a rendered
site for the custom-domain variant.

## License

Original scaffold software and the bounded materialized presentation overlay
are MIT licensed; original documentation is CC BY 4.0. Applicable dependency
notices are preserved. See [LICENSES.md](LICENSES.md).
