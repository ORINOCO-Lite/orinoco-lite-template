# Template release procedure

1. Select an exact reviewed Orinoco engine and runtime release.
2. Review every engine, runtime, template, and workflow coordinate in both
   `.github-template-answers.yml` and the matching `copier.yml` defaults.
   Replace each coordinate that advances with the same immutable reviewed
   value in both files; retain unchanged released components at their existing
   exact coordinates.
3. Update `template_version` and the changelog.
4. Run `pixi run render` and review the generated `copier-template/pixi.lock`; confirm it is byte-identical to `github-template/pixi.lock`.
5. Run `pixi run check` on macOS ARM64 and Linux x86-64.
6. Review the complete `copier-template/` to `github-template/` rendering.
7. Commit the source and generated default tree together and tag that commit on `main` with the declared template version.
8. Run `pixi run publish-github-template-branch` and `pixi run release-check` from the clean release commit.
9. Push the reviewed `main`, version tag, and generated `github-template` branch.
Do not hand-edit the publication branch.
10. Create the GitHub Release for the version tag and require GitHub's immutable-release protection before any consumer updates to that tag.
11. Set `github-template` as GitHub's default branch and template-button source; keep source pull requests and version tags on `main`.
12. Exercise creation with **Include all branches** unchecked and run one update against the full downstream test consumer.
13. Confirm that the created repository root contains `orinoco.yaml` and does not contain `copier.yml`, `copier-template/`, or a nested `github-template/`.
14. Confirm that an updater rehearsal resolves the release tag to the reviewed commit, then recommend the release to other sites.

The release commit is deliberately not embedded in `copier.yml`, the rendered answers, or `orinoco.lock`.
Embedding a commit in the tree whose commit it identifies is self-referential and cannot satisfy the exact `main:github-template/` publication contract.
Instead, the published coordinate is an immutable release tag; the updater resolves that tag immediately before and after Copier runs.
Its detailed diagnostics remain ignored runtime state.

Framework releases do not merge automatically.
Security fixes use the `security` classification in ignored updater state, but still produce an ordinary reviewable pull request.
