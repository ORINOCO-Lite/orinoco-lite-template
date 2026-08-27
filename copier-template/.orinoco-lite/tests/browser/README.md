# Baseline browser acceptance

These create-once, site-owned tests prove that an ordinary project-path build loads in Chromium and WebKit and keeps local resources under the configured Pages mount.
A complete downstream site should extend this suite to prove that its static `/edit/` route offers **Download bundle** and **Propose via GitHub**, and that the proposal action uses the build-derived repository and selected curation-service coordinates emitted into the editor configuration. It should also prove that a shared `*.github.io` origin requires the explicit in-memory acknowledgment while a dedicated custom domain does not. It should also prove that its static `/review/` route is the source-adapter decision interface and that the central service is only OAuth and GitHub transport.
It may add record, graph, and source-adapter-specific scenarios.
Copier never overwrites the site-owned browser suite after creation.
