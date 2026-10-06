# Releasing

1. Start from a clean `main` branch.
2. Set the [minimum package requirement](../copier-template/.orinoco-lite/README.md#package-compatibility) to the first released package version containing the functionality the template requires.
   Keep it unchanged when raising only the exact package pin.
   Test the minimum as well as the selected package when the minimum changes.
   Update the changelog and exact package, workflow, and template release coordinates.
   The template version must equal the intended tag.
3. Run `pixi run pytest` and pass the package repository's combined downstream candidate against this working tree.
4. Review and merge the release preparation, then create the immutable tag and GitHub Release.
5. Verify a clean checkout can instantiate the tag without access to the package repository.
   Orinoco Lite may resolve its pinned upstream sources through its normal cache path.

Package and template releases are separate review gates.
A downstream selects its exact template tag and adopts a later release deliberately.
