# Releasing

1. Start from a clean `main` branch.
2. Update the changelog and exact engine, runtime, workflow, and template
   release coordinates. The template version must equal the intended tag.
3. Run `pixi run check` and pass the engine repository's combined downstream
   candidate against this working tree.
4. Review and merge the release preparation, then create the immutable tag and
   GitHub Release.
5. Publish and verify the derived branch from that exact tag as described in
   [publishing](publishing.md).
6. Verify a clean checkout can instantiate the tag without access to the
   engineering repository. The engine may resolve the runtime-manifest-pinned
   upstream sources through its normal cache path.

Engine and template releases are separate review gates. A downstream selects
its exact template tag and adopts a later release deliberately.
