# Test contract

The template suite proves that:

- a default Copier rendering equals the checked GitHub-template tree;
- the publication branch tree equals the staged rendering tree object exactly and exposes no Copier source or nested wrapper directory;
- an ordinary rendering has no `.gitmodules`, gitlinks, or hidden content;
- site-owned files survive a real two-tag Copier update byte-for-byte;
- a divergent template-owned file produces an explicit conflict;
- workflow action references are full immutable commit SHAs;
- ownership patterns classify every checked consumer file;
- the importer rejects repository metadata and unreviewed overwrites;
- the rendered Pixi facade exposes projection refresh and verification through the locked engine;
- the normal cold-clone gate hydrates declared assets before verifying them, while the denied-network proof warms once and then invokes only asset verification; and
- the complete downstream gate includes exact Hugo Extended 0.154.5, deterministic repeat-build digest comparison, and Chromium/WebKit tests.

Consumer repositories add their complete content, build, browser, integration, and provenance suites.
Template tests are not a substitute for those tests.
