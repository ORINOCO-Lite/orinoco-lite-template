# Test contract

The template suite proves that:

- a default Copier rendering equals the checked GitHub-template tree;
- the publication branch tree equals the staged rendering tree object exactly and exposes no Copier source or nested wrapper directory;
- an ordinary rendering has no `.gitmodules`, gitlinks, or hidden content;
- site-owned files, including explicit strict reference and graph policies, survive a real two-tag Copier update byte-for-byte;
- a divergent template-owned file produces an explicit conflict;
- workflow action references are full immutable commit SHAs;
- ownership patterns classify every checked consumer file;
- Pages derives curation repository identity from the trusted runner rather than a repeated site setting, while the central service remains the configuration-free default;
- the rendered Pixi facade generates ignored projection output before validation and builds;
- the normal cold-clone gate hydrates declared assets before verifying them, while the denied-network proof warms once and then invokes only asset verification; and
- the complete downstream gate includes exact Hugo Extended 0.161.1, deterministic repeat-build digest comparison, and Chromium/WebKit tests.

The browser gate installs the locked Playwright client, then prepares Chromium headless-shell and WebKit before either suite begins.
It uses Playwright's `--only-shell` mode so the unused full Chromium binary is not downloaded, while preserving the exact four-test matrix.
Warm browser caches remain valid: the preparation command verifies each required browser and downloads only missing payloads.
The generated browser artifact uses only its project-path base; the dynamically allocated static test server remains authoritative for the loopback host and port.

Browser downloads have a ten-minute bound and finish before Chromium runs.
After Chromium finishes, Linux WebKit host-library installation runs as its own phase with inherited live output and a five-minute bound; WebKit runs only after that succeeds.
This retains the established Ubuntu ordering in which WebKit host changes never precede the Chromium suite.
Each phase has explicit start, completion, and failure messages, and a timeout terminates the phase's process group.
The Linux host-library phase still runs on a browser-cache hit because browser binaries and runner packages have different lifecycles.
macOS skips host-library installation and keeps the exact macOS 14 Playwright 1.61.1 compatibility overlay before preparing both browsers.

Consumer repositories add their content, build, browser, source-adapter, and site-behavior suites.
Template tests are not a substitute for those tests.
