# Changelog

## Unreleased

## 0.1.14 - 2026-08-18

- Select the stable Ubuntu archive before Playwright installs Linux WebKit host dependencies, while preserving bounded retries and timeouts.

## 0.1.13 - 2026-08-18

- Prepare Chromium headless-shell and WebKit before either browser suite, avoiding the unused full Chromium download while preserving both engines' acceptance coverage.
- Keep Linux WebKit host-library installation after Chromium while separating it from browser downloads with live phase logs and bounded five- and ten-minute failures.
- Pin the reusable consumer workflow that restores exact browser caches, bounds Linux package-manager network operations, and saves caches only from successful default-branch runs.

## 0.1.12 - 2026-08-18

- Cull generated consumers to the essential downstream interface while keeping implementation support below `.orinoco-lite/`.
- Restore a self-consistent template release identity after the historical v0.1.10 and v0.1.11 publication defects.
- Establish `source-adapters/` as the sole downstream source-adapter surface and align the rendered documentation and agent guidance with upstream importer, enricher, and scraper terms.
- Make `metadata/records/` the sole metadata Things input and establish configuration contract version 2 with `paths.records` and `paths.source_adapters`.
- Treat a fresh render as a content-neutral facade awaiting an explicit site profile; do not place non-Thing placeholders in `metadata/records/` or advertise validation before profile installation.
- Let the fresh facade's test task succeed without placeholder Python tests while continuing to propagate failures from site-owned tests.
- Keep render parity repeatable after local verification by excluding only the declared ignored runtime and cache roots.
- Update the engine, runtime, and reusable workflow to the immutable v0.1.12 release and configuration contract 2.

## 0.1.11 - 2026-08-13

- Make the Pages build wrapper independently testable.
- Retain the historical v0.1.9 embedded release identity; this release is not eligible for Copier-first creation or recopy.

## 0.1.10 - 2026-08-13

- Classify the Pages build wrapper in the template ownership contract.
- Retain the historical v0.1.9 embedded release identity; this release is not eligible for Copier-first creation or recopy.

## 0.1.9 - 2026-08-13

- Pass the configured Pages base URL through a validated argv wrapper so Pixi cannot pass the literal `${ORINOCO_BASE_URL}` expression to Orinoco.

## 0.1.8 - 2026-08-13

- Build one deterministic local artifact with host-neutral root-relative links so previews work through either loopback hostname.
- Verify both loopback hostnames and their same-origin entry-point resources while preserving explicit Pages project-path builds.
- Update the engine, runtime, and reusable workflow to the immutable v0.1.10 release artifacts.

## 0.1.7 - 2026-08-12

- Preserve Playwright 1.62.1 on ordinary platforms while overlaying the revision-compatible 1.61.1 client on macOS 14 only.
- Verify all installed Playwright package versions and preserve the exact consumer-owned browser manifest and lock bytes across installation.

## 0.1.6 - 2026-08-12

- Run Chromium before Playwright changes hosted Linux dependencies, then install WebKit's pinned host dependencies and run WebKit.
This preserves the complete checked browser matrix while avoiding a Chromium teardown hang on Ubuntu.

## 0.1.5 - 2026-08-12

- Install Playwright's pinned Linux host dependencies with Chromium and WebKit so the complete browser gate runs on hosted Ubuntu as well as macOS.

## 0.1.4 - 2026-08-12

- Accept Hugo distribution revision suffixes while preserving the exact Extended 0.154.5 gate.
- Update the engine, runtime, and reusable workflow to the immutable v0.1.9 release artifacts.
- Align local deterministic builds with the root URL served on port 8765 while retaining project-path bases for Pages and browser acceptance.

## 0.1.3 - 2026-08-12

- Update the engine and runtime to immutable v0.1.6 release artifacts.
- Run hosted source smoke tests against the frozen released engine environment.
- Reconcile only three-way-equivalent bootstrap edits and redundant placeholders.
- Require explicit update dispatch and attribute automated framework commits.

## 0.1.2 - 2026-08-12

- Update the engine and runtime to v0.1.4 for complete downstream snapshots.
- Use setup-pixi's v-prefixed version syntax and the reviewed workflow commit.
- Align Copier-first defaults and its frozen lock with the checked render.

## 0.1.1 - 2026-08-12

- Update the engine and runtime to v0.1.3.
- Enforce the runtime-declared Hugo Extended compatibility range during builds.

## 0.1.0 - 2026-08-12

- Establish the content-neutral single-repository contract.
- Add a versioned Copier source and generated GitHub-template default tree.
- Add SHA-pinned validation, Pages, and framework-update workflows.
- Add ownership verification, full-bundle import, and update ledgers.
