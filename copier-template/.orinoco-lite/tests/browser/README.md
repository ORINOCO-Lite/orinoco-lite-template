# Baseline browser acceptance

These create-once, site-owned tests prove that an ordinary project-path build loads in Chromium and WebKit and keeps local resources under the configured Pages mount.
A complete downstream site should extend this suite to prove that its static
`/edit/` route offers **Download bundle** and **Propose via GitHub**, and that
the proposal action uses the repository and curation-service coordinates
emitted into the editor configuration. It may also add record, graph, and
source-adapter-specific scenarios.
Copier never overwrites the site-owned browser suite after creation.
