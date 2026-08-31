# File ownership

The template owns the complete website under `.orinoco-lite/site/`, along with
generic workflows, tests, tools, and documentation.

The downstream owns all declarative inputs under `site-specific/`, executable
metadata adapters under `extensions/`, release selection, repository policy,
and generated deployment history.

Ordinary presentation belongs in `site-specific/site.yaml`, content, assets,
and static inputs. A custom layout is supported only as an explicit file under
`site-specific/overrides/layouts/`. Website code under `extensions/` is
invalid, and extension source or runtime products are never copied into a
build.
