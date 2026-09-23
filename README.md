# Orinoco Lite downstream template

This repository publishes a thin Copier scaffold for Orinoco Lite downstreams.
It supplies repository structure, workflows, helper tools, a small Orinoco Hugo adapter, and a bounded licensed overlay for required Hugo assets.
It does not distribute the reusable website.

The selected `orinoco-lite` package revision is the single authority for the exact German [`www-from-model`](https://hub.psychoinformatics.de/www/www-from-model) revision and official Congo dependency.
At build time the package resolves those sources and composes them with:

```text
.orinoco-lite/hugo-adapter/  small template-owned adaptation
.orinoco-lite/materialized-hugo-assets/upstream/
                             required ordinary-file asset overlay
site-specific/               declarative downstream inputs and overrides
extensions/                  optional metadata acquisition and curation code
```

The source branch contains maintainable inputs and behavioral tests.
Render into ignored build state and run the source checks:

```console
pixi run render
pixi run pytest
```

Copier is the only supported creation and update path.
Disposable renders are development and test output, not a second distribution.
See [testing](docs/testing.md) and [releasing](docs/releasing.md).

## Creating a downstream site

A downstream is an ordinary Git repository.
Only [Pixi](https://pixi.sh) 0.76 or newer and a Copier runner are required; the scaffold pins everything else.
CI always installs the latest Pixi and sets `PIXI_LOCKED=true` to reject stale locks without rewriting them.
For the same local default, run `export PIXI_LOCKED=true` in your shell.
For deliberate dependency updates, run `env -u PIXI_LOCKED pixi lock`, then review and commit the changes.
The commands below use [`uv`](https://docs.astral.sh/uv/) to run Copier and DataLad without installing them.

### 1. Create the repository

```console
uvx datalad create --no-annex my-site
cd my-site
```

DataLad is optional and is used here only to record instantiation provenance; `git init my-site` is equivalent.
The build never requires Git Annex, so `--no-annex` is the correct mode and no Git Annex installation is needed.

### 2. Instantiate the scaffold

```console
uvx copier copy --trust \
  --vcs-ref v0.3.0rc3 gh:ORINOCO-Lite/orinoco-lite-template .
```

Pass `--vcs-ref` explicitly.
Copier resolves a bare `gh:` source to the newest *stable* tag, so while this template publishes release candidates an unpinned copy silently instantiates the last 0.1 release instead.
Use the newest tag from [releases](https://github.com/ORINOCO-Lite/orinoco-lite-template/tags), and record the instantiation with `datalad run` if the repository is a DataLad dataset.

Copier asks for site identity and preview settings.
Package coordinates are maintained defaults in [`copier.yml`](copier.yml), not interactive questions.
They may be overridden explicitly to select the official repository or a fork, at a release tag or exact commit:

| Answer             | Meaning                                                         |
| ------------------ | --------------------------------------------------------------- |
| `project_slug`     | repository and Pages project-path slug                          |
| `project_name`     | human-readable site title                                       |
| `site_description` | short public description                                        |
| `site_base_url`    | canonical public base URL, with project path and trailing slash |
| `package_repository` | Git repository containing the Python project at its root      |
| `package_revision` | release tag or exact package commit                              |

Answers can also be supplied non-interactively with repeated `--data key=value` options plus `--defaults`, or from a file with `--data-file answers.yml`.

### 3. Review the starter site and supply site-owned inputs

Everything a site owns is declarative and lives in two trees:

```text
site-specific/site.yaml              identity, navigation, appearance
site-specific/metadata/records/      Thing YAML records, one entity per file
site-specific/metadata/overlays/machine-provenance-annotations/
                                     companion annotations for those records
site-specific/content/               editorial Markdown pages
site-specific/assets/                Hugo asset-pipeline inputs
site-specific/static/                files published verbatim at the site root
site-specific/overrides/{config,layouts,static}
                                     bounded Hugo overrides
site-specific/projection.yaml        optional projection contract override
extensions/                          optional metadata-acquisition code
```

Four rules are enforced by Orinoco Lite and are worth knowing before the first build:

- Everything below `site-specific/metadata/records/` must be a Thing YAML record, and the inventory may not be empty.
  The scaffold provides a small starter record graph and `/explore` page so its first build works.
  Replace those clearly labeled starter inputs with reviewed site metadata and editorial content before publishing a real site.
- Images referenced from editorial Markdown through Hugo shortcodes such as `figure` are resolved through the asset pipeline, so they belong under `site-specific/assets/`.
  `site-specific/static/` is for files that are published verbatim and referenced by absolute URL.
- A custom Congo colour scheme is `site-specific/assets/css/schemes/<name>.css` named by `appearance.color_scheme`; extra Congo icons are `site-specific/assets/icons/<name>.svg`; site CSS is `site-specific/assets/css/custom.css`.
- `extensions/` is for executable metadata adapters only.
  Website functionality there is rejected: no `.css`, `.html`, `.js`, `.svg` files and no `assets`, `content`, `layouts`, or `static` directories.
  Hugo overrides belong in `site-specific/overrides/`.

`orinoco.yaml` carries only path selection, and rejects unknown keys.
The recognized paths are `records`, `editorial`, `site`, `generated`, `extensions`, and `build`; public site identity belongs in `site-specific/site.yaml`.

#### Example inputs

Published `site-specific/` trees to read before writing your own:

| Example | Contents |
| ------- | -------- |
| [`con-site-specific`](https://github.com/ORINOCO-Lite/con-site-specific) | The Center for Open Neuroscience site: ~220 Things records with annotation overlays, five editorial pages, navigation, and a custom Congo colour scheme. |

An example is a `site-specific/` tree, not a whole downstream, so it can be copied in or embedded as a submodule or subtree at `site-specific/`.

For **Propose via GitHub** with a `site-specific` submodule, use an absolute GitHub HTTPS or SSH URL and deploy its current default-branch commit.
Install the curation App on both repositories and give the curator write access to both.
The existing curation App authorizes the exact trusted workflow through GitHub Actions OIDC and supplies short-lived access limited to the metadata repository.
No second App or downstream App private key is required.
The service rejects changed proposal heads, expired authorization, and workflows that do not match the authenticated submission.
The workflow validates the composed site before replacing the two handoffs.
Merge the metadata draft first, preserving its validated commit (use a merge commit, not a squash or rebase), then merge the website gitlink proposal.
If one update fails, inspect both draft heads before retrying; neither reviewed default branch is changed automatically.
For source adapters, the `curation-review.yml` workflow coordinates proposal and finalization drafts with the same App.
Initialize both repositories as DataLad datasets without Annex before running it.
Provide `extensions/source-adapters/<adapter>/review.py` in the trusted website default branch with a `build_candidate_plan(root, *, trusted_root, metadata_base)` function returning the package's `CandidatePlan`.
The adapter reads captured source and mapping policy from the immutable base checkout at `root`; executable adapter code comes from `trusted_root`.
Dispatch the workflow with that adapter name, follow its downstream review link, and submit one explicit decision for every candidate.
The package owns repository coordination, DataLad recording, composed validation, and temporary App access through `orinoco-lite curation validate`, `publish`, and `complete`.
The workflow supplies the event, permissions, locked environment, and GitHub artifact upload.
A stale head or lost access stops the write; a failure after the metadata push reports the partial result for inspection.
Neither draft is merged automatically.

Embedding keeps the inputs reviewable on their own and lets several downstreams share one metadata collection.
Each example tracks its own history, so check its README for the template version it currently follows; older trees may still use conventions the rules above have moved on from.

### 4. Build and preview

```console
pixi install --frozen
pixi run build
pixi run serve
```

The first build resolves and caches the exact www-from-model checkout, so it needs network access to GitHub and takes longer than later builds.
`pixi run serve` publishes the built site on <http://127.0.0.1:8765/>, including the static `/edit/` metadata editor.

Before proposing a change, run what CI runs:

```console
pixi run build && pixi run orinoco-lite verify-site build/site
```

`orinoco-lite verify-site` checks the locally built site before it is published.

Pixi installs the downstream-selected package dependency declared in `pixi.toml`.
A downstream may retain the generated `pixi.lock` for the complete resolved environment; no Orinoco-specific release lock is required.
Copier records the template selection in `.copier-answers.yml`; workflows contain their pinned action references.
Resources and specifications required to build or operate Orinoco Lite are internal to that package and share its version and integrity boundary.

### 5. Publish

The rendered `.github/workflows/pages.yml` deploys to GitHub Pages.
Enable Pages for the repository with the GitHub Actions source, and keep `identity.base_url` in `site-specific/site.yaml` equal to the published URL, including the project path and trailing slash.
See [`docs/custom-domain.md`](copier-template/docs/custom-domain.md) in a rendered site for the custom-domain variant.

## License

Original scaffold software and the bounded materialized Hugo asset overlay are MIT licensed; original documentation is CC BY 4.0.
Applicable dependency notices are preserved.
See [LICENSES.md](LICENSES.md).
