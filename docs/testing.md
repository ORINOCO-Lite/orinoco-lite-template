# Testing

Run the source checks with:

```console
pixi run check
```

They create a fresh disposable consumer with compact custom inputs and verify substitution, package/template boundaries, the thin presentation adapter, release locks, the licensed materialized-presentation boundary, and helper behavior.
No generated consumer tree is stored or compared as a snapshot.

The source checks stop at the rendered tree.
To prove that a rendered tree still builds a website, run:

```console
pixi run build-sample-site
```

That renders `tests/sample-site/answers.yml` into ignored build state, overlays the compact record and editorial fixture beside it, and runs the rendered consumer's own `verify-build`: a website build and host-neutral local-preview verification.
Source CI runs it on Linux without a repository coordinate, so the job builds exactly what a contributor builds locally, and uploads the built site as a workflow artifact, so a template pull request can be inspected as a website rather than only as a rendered tree.

The fixture is a test input, not a template default.
The template deliberately materializes no record, and a rendered site without one cannot build.
The fixture also supplies an editorial `explore.md`, because the upstream homepage links `/explore`; a site without that page fails local-preview verification on that dead link.

The engineering repository supplies the combined candidate exercise.
When a template candidate is selected, it renders the template afresh and overlays only the downstream's declared site-owned inputs.
Quick mode runs the rendered downstream's `validate` and `build` tasks.
Full mode also runs `verify-hugo`, `verify-release-selection`, and `verify-build`.
Browser, source-adapter, offline-cache, and live GitHub behavior require their focused tests or acceptance exercises; neither candidate mode implies them.
