# Testing

Run the source checks with:

```console
pixi run check
```

They verify that the Copier source and checked rendering match, the generic
website is complete and content-neutral, only the declared downstream surfaces
exist, workflows remain pinned, and curation/browser helpers retain their
security contracts.

The engineering repository supplies the authoritative combined proof. Its
quick candidate validates, projects, builds, and runs Chromium against a fresh
rendering. Its full candidate additionally checks deterministic and offline
builds, WebKit, editor/review behavior, layout overrides, extension isolation,
links, assets, and project paths.
