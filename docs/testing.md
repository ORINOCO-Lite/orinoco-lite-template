# Testing

Run the source checks with:

```console
pixi run check
```

They create a fresh default consumer and verify that its locked environment installs, its starter site validates and builds, and its same-origin navigation serves without 404s.
They also verify package/template boundaries, the thin presentation adapter, release locks, the licensed materialized-presentation boundary, and helper behavior.
No generated consumer tree is stored or compared as a snapshot.

To exercise a richer record and editorial fixture beyond the deployable default, run:

```console
pixi run build-sample-site
```

That renders `tests/sample-site/answers.yml` into ignored build state, overlays the richer record and editorial fixture, and runs the rendered consumer's own `verify-build`: a website build and host-neutral local-preview verification.
Source CI runs it on Linux without a repository coordinate, so the job builds exactly what a contributor builds locally, and uploads the built site as a workflow artifact, so a template pull request can be inspected as a website rather than only as a rendered tree.

The richer fixture is optional coverage, not required scaffolding for the default render.
The default template carries a small replaceable starter graph and `/explore` page because the upstream homepage links that route.

The engineering repository supplies the combined candidate exercise.
When a template candidate is selected, it renders the template afresh and overlays only the downstream's declared site-owned inputs.
Quick mode runs the rendered downstream's `validate` and `build` tasks.
Full mode also runs `verify-build`.
Browser, source-adapter, offline-cache, and live GitHub behavior require their focused tests or acceptance exercises; neither candidate mode implies them.
