# Changelog

## Unreleased

- Use one `orinoco-lite` package version and wheel digest for code and bundled resources.
Rename release locks and Copier answers to `package`, `package_version`, `package_url`, and `package_sha256`.

- Add the optional `pr_previews` Copier question and its single `netlify` provider.
Selecting it renders a pull-request-only `netlify.toml` that installs Pixi and runs the repository's ordinary root-relative build, without touching the canonical GitHub Pages deployment, adding preview-specific tooling, or pinning a second toolchain coordinate.
- Add `pixi run build-sample-site` and a source-CI job that render a sample consumer, build it through the rendered `verify-build`, and upload the built site as a workflow artifact.

Published release history remains available in [GitHub Releases](https://github.com/ORINOCO-Lite/orinoco-lite-template/releases) and Git.
