# 🗿 rosetta-maps

> The community knowledge base of **obfuscation maps** for the Rosetta
> tools — an obfuscation-map "CVE database." Contribute the
> real → obfuscated names for an app version once; every
> [rosetta-frida](https://github.com/Xiddoc/rosetta-frida) and
> [rosetta-xposed](https://github.com/Xiddoc/rosetta-xposed) user hooking
> that version gets them for free.

[![Validate](https://github.com/Xiddoc/rosetta-maps/actions/workflows/validate.yml/badge.svg?branch=master)](https://github.com/Xiddoc/rosetta-maps/actions/workflows/validate.yml?query=branch%3Amaster)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Status](https://img.shields.io/badge/status-scaffolding-orange)](#status)

## Why this repo exists

Large obfuscated Android apps rotate their class/method names every minor
release. The Rosetta libraries fix this by decoupling **what you want to
hook** (real name) from **how it's spelled today** (obfuscated name) via
per-version maps. The long-term killer feature is a *shared* place those
maps live, so a hook works against a version its author never tested —
because someone else contributed that version's map.

This repo is that place. It holds two kinds of artifact (RFC 0001
Decisions 4 & 5):

- **`signatures/`** — the **source of truth**. Human-readable sigmatcher
  rules (regex-over-smali) that *identify* a class/method across versions.
  A map is reproducible from its signatures + the APK, which is what makes
  it verifiable.
- **`maps/`** — the **published artifacts**. Resolved
  `schema_version: 2` JSON, one file per `(app, version_code)`, consumed
  directly by Frida script authors and Xposed module authors who won't run
  a matcher or supply an APK.

```
rosetta-maps/
├── maps/<app>/<version_code>.json     ← generated, published, consumed
├── signatures/<app>/signatures.yaml   ← source of truth (sigmatcher dialect)
├── schema/rosetta-map.schema.json     ← editor aid (mirrors the canonical validator)
└── templates/                         ← copy these to start a contribution
```

`version_code` is the authoritative O(1) selection key (RFC 0001
Decision 3), so it **is** the map filename. `signer_sha256`, when present,
guards against applying a map to a repackaged/spoofed build.

## Using a map

Grab the file for your installed `version_code` and load it like any other
Rosetta map:

```typescript
// rosetta-frida
import { rosetta } from 'rosetta-frida';
import map from 'rosetta-maps/maps/com.example.app/30405.json' with { type: 'json' };
rosetta.session({ map });
```

```kotlin
// rosetta-xposed
val rosetta = RosettaXposed.fromMap(MapLoader.fromJson(mapJson), classLoader)
```

(Runtime auto-fetch by `(app, version_code)` is on the libraries' roadmap;
until then, vendor the file you need.)

## Contributing a map

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the full workflow and the
layered trust model. In short:

1. Add/extend `signatures/<app>/signatures.yaml` (the source of truth).
2. Generate `maps/<app>/<version_code>.json` from the signatures + the APK
   (`rosetta convert` / the sigmatcher adapter), or hand-author from the
   template.
3. Open a PR. CI runs **structural validation only — no APK is ever
   uploaded** (APK host ToS / copyright). The bot checks: valid against the
   canonical schema, descriptors parse, `version_code` set and matching the
   filename.

## Status

**Scaffolding.** The layout, the canonical-schema validation CI, the
filename/`version_code` convention check, the JSON Schema editor aid, and a
worked `com.example.app` example (signatures + generated map) are in place.
Planned next (per RFC 0001 Decision 4): signed reproduction attestations,
an optional self-hosted trusted runner that *does* see APKs, device-side
health-check telemetry as the correctness oracle, and a reputation /
web-of-trust gate. None of those host APKs in public CI.

## Related repos

- **[rosetta-frida](https://github.com/Xiddoc/rosetta-frida)** — the Frida
  adapter; canonical home of the map schema, the validator these maps are
  checked against, and RFC 0001.
- **[rosetta-xposed](https://github.com/Xiddoc/rosetta-xposed)** — the
  Xposed/LSPosed/LSPatch adapter; consumes these same maps.

## License

[MIT](LICENSE). Maps and signatures contributed here are released under the
same license; see CONTRIBUTING.md for the provenance expectations.
