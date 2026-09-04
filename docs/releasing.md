# Releasing

1. Start from a clean `main` branch.
2. Update the changelog and exact package, workflow, and template release coordinates.
The template version must equal the intended tag.
3. Run `pixi run check` and pass the package repository's combined downstream candidate against this working tree.
4. Review and merge the release preparation, then create the immutable tag and GitHub Release.
5. Publish and verify the derived branch from that exact tag as described in [publishing](publishing.md).
6. Verify a clean checkout can instantiate the tag without access to the engineering repository.
The package may resolve its pinned upstream sources through its normal cache path.

Package and template releases are separate review gates.
A downstream selects its exact template tag and adopts a later release deliberately.
