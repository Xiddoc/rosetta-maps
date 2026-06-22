# 🗿 rosetta-maps

> The community knowledge base of Android **obfuscation maps** — a
> shared, searchable database of obfuscated app internals.

[![Validate](https://github.com/Xiddoc/rosetta-maps/actions/workflows/validate.yml/badge.svg?branch=master)](https://github.com/Xiddoc/rosetta-maps/actions/workflows/validate.yml?query=branch%3Amaster)
[![Docs](https://github.com/Xiddoc/rosetta-maps/actions/workflows/pages.yml/badge.svg?branch=master)](https://iliketo.party/rosetta-maps/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

rosetta-maps is a shared, PR-gated repository of per-app, per-version obfuscation
maps — the `real → obfuscated` names for an app version. Contribute a map once and
every consumer of that version gets it for free. The maps are consumed directly by
the [rosetta-frida](https://github.com/Xiddoc/rosetta-frida) and
[rosetta-xposed](https://github.com/Xiddoc/rosetta-xposed) adapters, and each map
is *reproducible* from the signatures it was generated from plus the APK — so a
contribution is verifiable, not just trusted.

This repo is **data + CI**: strict JSON maps, the sigmatcher signatures they come
from, and the validation that gates them. It owns the **canonical, language-neutral
map schema**; the adapters are clients that track it (rosetta-frida is the
first-class client).

## What a contribution looks like

A pull request adds (or extends) **one `(app, version_code)` map**:

- `signatures/<app>/signatures.yaml` — the **source of truth** (sigmatcher rules).
- `maps/<app>/<version_code>.json` — the **published artifact**, resolved from
  those signatures + the APK.

CI validates every map against the canonical schema and checks the filename against
the map's `version_code`. No APK is ever uploaded. See
**[CONTRIBUTING.md](CONTRIBUTING.md)** for the full workflow.

## Documentation

Full docs are at **[iliketo.party/rosetta-maps](https://iliketo.party/rosetta-maps/)**:

- [Quickstart](https://iliketo.party/rosetta-maps/quickstart/) — grab a map and load it.
- [Contributing](https://iliketo.party/rosetta-maps/contributing/) — how to add a map.
- [Repository layout](https://iliketo.party/rosetta-maps/reference/layout/) — what lives where.
- [Trust model & validation](https://iliketo.party/rosetta-maps/reference/trust-model/) — the trust ladder and what CI does.
- [Map schema](https://iliketo.party/rosetta-maps/reference/schema/) — the canonical schema this repo owns.

## Related repos

- **[rosetta-frida](https://github.com/Xiddoc/rosetta-frida)** — the Frida adapter
  and first-class **client** of the map schema.
- **[rosetta-xposed](https://github.com/Xiddoc/rosetta-xposed)** — the
  Xposed/LSPosed/LSPatch adapter; another **client** that consumes these maps.

This repo owns the **canonical map schema** (`schema/`); the adapters above consume it.

## License

[MIT](LICENSE). Maps and signatures contributed here are released under the same
license; see [CONTRIBUTING.md](CONTRIBUTING.md) for the provenance expectations.
