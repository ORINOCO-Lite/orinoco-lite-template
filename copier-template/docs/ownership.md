# File ownership

The template owns the downstream scaffold, generic workflows and tools,
documentation, and a small adaptation under `.orinoco-lite/presentation/`.
The engine runtime resolves the upstream website and theme; they are not part
of this repository.

The downstream owns all declarative inputs under `site-specific/`, executable
metadata adapters under `extensions/`, create-once acceptance tests, release
selection, repository policy, and generated deployment history.

Ordinary presentation belongs in `site-specific/site.yaml`, content, assets,
and static inputs. A custom layout is supported only as an explicit file under
`site-specific/overrides/layouts/`. Website code under `extensions/` is
invalid, and extension source or runtime products are never copied into a
build.
