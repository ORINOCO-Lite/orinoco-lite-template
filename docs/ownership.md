# Template ownership contract

`copier-template/template-ownership.yml` is the machine-readable authority.
The template distinguishes these classes:

- **template-owned** files form the small command, workflow, updater, and documentation facade.
  Copier updates them with three-way conflict handling.
- **initialized site-owned** files and directories are created once, then excluded from every Copier overwrite.
  They include canonical metadata, editorial content, assets, presentation overlays, integrations, extensions, and `orinoco.yaml`.
- **engine lock** data in `orinoco.lock` is changed only by the pinned updater and remains reviewable as structured YAML.
- **generated** files may be replaced after all declared inputs validate.
- **semantic migrations** may touch site-owned content only when an explicit migration identifier and changed paths appear in the update ledger.

The update command hashes every site-owned file before and after Copier runs.
An undeclared change fails closed.
A supported extension belongs under `extensions/`; copying a framework file into a site-owned directory does not silently transfer ownership of that framework behavior.

The template never chooses publication identity, content scope, collection policy, authorship, venue, licensing, or production-cutover semantics.
