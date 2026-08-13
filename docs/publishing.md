# GitHub-template publication topology

GitHub creates a repository from the files on a template repository's default branch.
The creation form can optionally include all branches, but it cannot select `main:github-template/` as the desired subtree.
GitHub also warns that branches created through a template have unrelated histories.

This repository therefore uses two explicit branch roles:

| Branch | GitHub role | Tree |
| --- | --- | --- |
| `main` | Copier source and maintenance | `copier.yml`, `copier-template/`, tests, tools, and the checked `github-template/` staging render |
| `github-template` | Default branch and template-button source | Exact contents of `main:github-template/` at the branch root |

Version tags such as `v0.1.0` point to reviewed `main` commits because Copier needs the source and questions at that ref.
The publication branch is generated only after that same source commit passes all checks.
Each published tag must have a GitHub Release protected by immutable releases before a consumer update is allowed to use it.

## Local publication

From a clean, committed `main` worktree:

```console
pixi run render
pixi run check
pixi run publish-github-template-branch
pixi run check-github-template-branch
```

The publisher uses `git subtree split`.
It preserves the reviewed source commits' authorship and messages while changing the tree root to the rendered subdirectory.
The verifier compares Git tree object IDs, so the branch cannot contain an extra wrapper directory or a hand-edited file.

## GitHub repository settings

After pushing both reviewed branches:

1. set `github-template` as the repository's default branch;
2. mark the repository as a template repository;
3. protect `github-template` from hand-authored changes;
4. target source pull requests explicitly at `main`;
5. keep release tags on `main` and enable immutable GitHub Releases;
6. publish each supported update tag as an immutable release; and
7. describe the repository as "GitHub template on the default branch; Copier source and releases on main."

The **Use this template** instructions must tell consumers to leave **Include all branches** unchecked.
The resulting repository receives only the ordinary consumer tree.
That tree carries neutral identity defaults.
A new operator follows its checked `docs/getting-started.md` identity bootstrap before adding site content while leaving all recorded release pins unchanged.
The rendered validation and Pages workflows discover the new repository's default branch at runtime, so they remain correct whether GitHub preserves the publication branch name or applies the destination account's configured default-branch name.
Copier updates later use the exact tagged source recorded in `.copier-answers.yml`; they do not merge either template branch.
The updater resolves lightweight and annotated tags to the peeled commit before and after applying an update, rejects a tag that cannot be resolved or moves during the operation, and records the resolved commit in `generated/manifests/framework-update.json`.
That runtime proof avoids the impossible requirement that a release tree contain its own commit ID.

These settings are external publication actions.
The local publication command does not push branches, set the default branch, or enable template status.

GitHub behavior is documented in [Creating a template repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-template-repository) and [Creating a repository from a template](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template).
