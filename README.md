# Orinoco Lite site template

This repository is the versioned source for ordinary, single-repository Orinoco Lite sites.
It deliberately has two branch roles:

- `main` contains the authoritative Copier source, release tags, tests, and a checked staging render at `github-template/`; and
- `github-template` contains only that rendered consumer tree at its branch root and is the GitHub repository's default branch.

GitHub's template button copies the default branch, not an arbitrary subdirectory.
The dedicated publication branch is therefore required; the `github-template/` directory on `main` is never itself exposed as a nested directory to a newly created consumer.

The default tree contains no organization records, editorial claims, assets, publication data, or inherited site history.
A complete reviewed site bundle can be imported into its site-owned paths without making that content part of the template.

## Maintainer commands

```console
pixi run render
pixi run check
pixi run publish-github-template-branch
pixi run check-github-template-branch
pixi run release-check
```

`render` replaces the checked default tree from the Copier source and `.github-template-answers.yml`.
It also refreshes `copier-template/pixi.lock` when reviewed release coordinates change, then proves a second rendering leaves that lock byte-identical.
This ships the same frozen environment through both Copier-first creation and the GitHub template button.
`check-render` fails when the checked tree has drifted.
Release the template from a clean commit tagged with a PEP 440 compatible tag such as `v0.1.0`; Copier records that exact tag in each consumer's answers file.
The tag must belong to an immutable GitHub Release.
During every update, the updater resolves the tag to its peeled 40-hex commit both before and after Copier runs and records that commit in the review ledger.

The default answers carry the exact engine, runtime, and workflow coordinates reviewed for the current template release.
Rendering also resolves a frozen cross-platform `pixi.lock`; a publishable update must refresh and verify all of those coordinates together.

`publish-github-template-branch` uses `git subtree split` to publish the exact committed `main:github-template` tree at the root of the local `github-template` branch.
It does not push or change GitHub settings.
`release-check` is the post-publication gate and therefore requires that local branch to exist already.

See [ownership](docs/ownership.md), [release procedure](docs/releasing.md), [publication topology](docs/publishing.md), and [test contract](docs/testing.md).
