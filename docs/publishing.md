# Publishing the GitHub template branch

`pixi run publish-github-template-branch` renders the reviewed Copier source
and publishes the result to the `github-template` branch. The branch is a
creation convenience, while versioned Copier tags remain the dependency
coordinate used by downstreams.

Before publishing, require a clean source tree, a passing `pixi run check`, and
the reviewed release commit. Verify the resulting branch contains the complete
`.orinoco-lite/site/` website and only `site-specific/` and `extensions/` as
downstream input surfaces.
