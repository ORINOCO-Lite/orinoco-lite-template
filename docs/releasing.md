# Releasing

1. Start from a clean `main` branch.
2. Render `github-template/` and run `pixi run release-check`.
3. Pass the engine repository's full combined downstream candidate.
4. Update the changelog and exact release coordinates.
5. Commit the release preparation, tag it, and publish an immutable GitHub
   Release.
6. Verify a clean checkout can instantiate the tag without access to the
   engineering repository or German upstream.

Engine and template releases are separate review gates. A downstream selects
its exact template tag and upgrades only by deliberate adoption of another
version, fork, or compatible implementation.
