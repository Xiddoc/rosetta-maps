# rosetta-maps

**The community knowledge base of Android obfuscation maps — a shared, searchable database of obfuscated app internals.**

rosetta-maps is a shared, PR-gated repository of per-app, per-version
obfuscation maps: the `real → obfuscated` names for an app version. Contribute a
map once and every consumer of that version gets it for free. The maps are
consumed directly by the [rosetta-frida](https://github.com/Xiddoc/rosetta-frida)
and [rosetta-xposed](https://github.com/Xiddoc/rosetta-xposed) adapters, and each
map is *reproducible* from the signatures it was generated from plus the APK — so
a contribution is verifiable, not just trusted.

This repo is **data + CI**: strict JSON maps, the sigmatcher signatures they come
from, and the validation that gates them. It owns the **canonical, language-neutral
map schema**; the adapters are clients that track it.

## What a contribution looks like

A pull request adds (or extends) one `(app, version_code)` map:

- `signatures/<app>/signatures.yaml` — the **source of truth** (sigmatcher rules
  that identify classes/methods across versions).
- `maps/<app>/<version_code>.json` — the **published artifact**, resolved from
  those signatures + the APK and consumed by the adapters.

CI validates every map against the canonical schema and checks that the filename
matches the map's `version_code`. No APK is ever uploaded. The full workflow lives
in the [contribution guide](contributing.md).

## Where to go next

<div class="grid cards" markdown>

- :material-rocket-launch: **[Quickstart](quickstart.md)**
  Grab a map and load it in Frida or Xposed.

- :material-source-pull: **[Contributing](contributing.md)**
  How to add a map, the PR shape, and provenance fields.

- :material-folder-outline: **[Repository layout](reference/layout.md)**
  What lives where: `maps/`, `signatures/`, `schema/`, `templates/`.

- :material-shield-check: **[Trust model & validation](reference/trust-model.md)**
  The trust ladder and what CI does (and deliberately does not).

- :material-code-json: **[Map schema](reference/schema.md)**
  The canonical, language-neutral schema this repo owns.

</div>

## Related repositories

- **[rosetta-frida](https://github.com/Xiddoc/rosetta-frida)** — the Frida adapter
  and first-class client of the map schema; its validator
  tracks this repo's canonical `schema/rosetta-map.schema.json`.
- **[rosetta-xposed](https://github.com/Xiddoc/rosetta-xposed)** — the
  Xposed/LSPosed/LSPatch adapter; another client that consumes these same maps.

This repo owns the **canonical map schema**; the adapters above consume it.
