# Testing

Run the source checks with:

```console
pixi run check
```

They create a fresh disposable consumer with compact custom inputs and verify
substitution, ownership boundaries, the thin presentation adapter, release
locks, the licensed materialized-presentation boundary, publication-tree
derivation, and helper behavior. No generated consumer tree is stored or
compared as a snapshot.

The source checks stop at the rendered tree. To prove that a rendered tree
still builds a website, run:

```console
pixi run build-sample-site
```

That renders `tests/sample-site/answers.yml` into ignored build state, overlays
the compact record and editorial fixture beside it, and runs the rendered
consumer's own `verify-build`: two builds, a deterministic comparison, and
host-neutral local-preview verification. Source CI runs it on Linux and uploads
the built site as a workflow artifact, so a template pull request can be
inspected as a website rather than only as a rendered tree.

The fixture is a test input, not a template default. The template deliberately
materializes no record, and a rendered site without one cannot build. The
fixture also supplies an editorial `explore.md`, because the upstream homepage
links `/explore`; a site without that page fails local-preview verification on
that dead link.

The engineering repository supplies the authoritative combined proof. Its
quick candidate validates, projects, builds, and runs Chromium against a fresh
rendering. Its full candidate additionally checks deterministic and offline
builds, WebKit, editor/review behavior, layout overrides, extension isolation,
links, assets, and project paths.
