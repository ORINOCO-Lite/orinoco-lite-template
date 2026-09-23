# Testing

Run the source tests with:

```console
pixi run pytest
```

By default, pytest excludes integration tests.
Source tests check the rendered scaffold, package/template boundaries, the thin Hugo adapter, licensed materialized assets, and workflow behavior without installing or building a downstream.
Use test paths or pytest selection flags for focused checks:

```console
pixi run pytest tests/test_template_architecture.py
```

No generated consumer tree is stored or compared as a snapshot.

Run the website-build integration test explicitly:

```console
pixi run pytest -m integration
```

It creates a disposable default downstream, installs its locked environment, validates and builds the starter site, then runs `orinoco-lite verify-site build/site`.
That verification checks the homepage and its direct references, not every route or browser interaction.
See [source CI](../.github/workflows/source-ci.yml) for the platforms that run each check.

For package or template development, use the package's [ordinary downstream workflow](https://github.com/ORINOCO-Lite/orinoco-lite-dev#engineering-workflow).
From the engineering checkout, `pixi run orinoco-lite dev setup --template /path/to/template` creates a downstream with the selected template and site inputs; setup stops before projection and building.
Preserve existing downstreams and use their `pixi run orinoco-lite dev enable` connection instead of routinely recreating them.
Exercise the downstream's normal `pixi run orinoco-lite build` and `pixi run orinoco-lite verify-site build/site` commands when a website build is in scope.
Browser, source-adapter, offline-cache, and authenticated GitHub behavior require their separate focused tests or acceptance exercises.
