---
name: manage-orinoco-content
description: Edit and review declarative Orinoco Lite downstream content, assets, identity, presentation choices, or supported overrides under site-specific/. Do not use for metadata adapter execution or curation decisions.
---

# Manage Orinoco content

Keep all website-specific declarative inputs under `site-specific/`:

- edit reviewed semantic records under `site-specific/metadata/`;
- edit Markdown under `site-specific/content/`;
- put assets and static inputs under their named directories;
- change identity, navigation, and supported presentation choices in
  `site-specific/site.yaml`; and
- use `site-specific/overrides/` only when the generic template cannot express
  a required declarative website choice.

Run `pixi run validate`, `pixi run build`, and the relevant browser test. Never
edit generated output or copy template framework files into `site-specific/`.

Use `$operate-orinoco-metadata-adapters` for executables, captured evidence,
candidate metadata, matching policy, and curation decisions under
`extensions/`.
