# Publishing the GitHub template branch

The `github-template` branch is a derived consumer distribution for GitHub's
repository-template feature. Versioned Copier tags remain the dependency
coordinate used by downstreams.

Publish only from a clean, reviewed source tag:

```console
pixi run check
pixi run publish-github-template-branch --source-ref vX.Y.Z
pixi run check-github-template-branch --source-ref vX.Y.Z
```

The publisher renders that immutable ref in a temporary directory, writes its
tree directly to the branch, and verifies the branch tree against a second
render of the same ref. It does not add generated files to the source branch or
push any ref.

The resulting branch must expose only the consumer repository root. Copier
configuration, template source topology, and nested publication directories
are rejected.
