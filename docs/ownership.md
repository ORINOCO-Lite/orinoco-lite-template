# Template ownership contract

`copier-template/.orinoco-lite/template-ownership.yml` is the machine-readable authority.
The checked render contains the same contract at `github-template/.orinoco-lite/template-ownership.yml`.

| Class | Update behavior | Representative paths |
| --- | --- | --- |
| `template_owned` | Copier three-way update; overlapping downstream edits stop as conflicts | workflows, command facade, updater, ownership verifier, generic adapters, generic contract documentation |
| `initialized_site_owned` | Created once and excluded from later Copier overwrites | `orinoco.yaml`, metadata, `custom/`, site presentation, and source adapters |
| `engine_lock` | Structured replacement by the pinned updater | `orinoco.lock` and the frozen `pixi.lock` |
| `extensions` | Stable site-owned customization hook | `extensions/` |
| `consumer_tests` | Created once, then owned and extended by the site | browser, source-adapter, and offline behavior tests |
| `site_policy` | Always decided by the site | licensing, citation, contribution, and conduct files |
| `generated` | Ignored runtime output | projection under `generated/` |

The updater compares protected site-owned bytes before and after Copier runs.
An undeclared change fails closed.
A semantic migration may cross that boundary only when the operator supplies an explicit migration ID and exact allowed paths; the resulting ledger remains in `human-review` status.

Ownership follows the path contract, not apparent similarity.
A supported customization belongs under `extensions/`; copying a framework file into a site-owned directory does not silently transfer ownership of that framework behavior.

Source adapters and their site-owned tests use only `source-adapters/` and `.orinoco-lite/tests/source-adapters/`, respectively.

This layer never chooses a site's publication identity, content scope, collection policy, authorship, venue, content licensing, or production-cutover semantics.
Those are consumer decisions.
Licensing of the generic template and updater is instead determined by authorized Orinoco Lite rightsholders; a consumer cannot grant rights it does not hold.
Engine behavior remains documented in the [engine repository](https://github.com/con/orinoco-lite-dev); the corresponding consumer view is the rendered [file-ownership guide](../github-template/docs/ownership.md).
