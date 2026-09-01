# Testing

Run the source checks with:

```console
pixi run check
```

They create a fresh disposable consumer with compact custom inputs and verify
substitution, ownership boundaries, the thin presentation adapter, release
locks, publication-tree derivation, and helper behavior. No generated consumer
tree is stored or compared as a snapshot.

The engineering repository supplies the authoritative combined proof. Its
quick candidate validates, projects, builds, and runs Chromium against a fresh
rendering. Its full candidate additionally checks deterministic and offline
builds, WebKit, editor/review behavior, layout overrides, extension isolation,
links, assets, and project paths.
