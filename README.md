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

## Layout

```
rosetta-maps/
├── maps/<app>/<version_code>.json     ← generated, published, consumed
├── signatures/<app>/signatures.yaml   ← source of truth (sigmatcher dialect)
├── schema/rosetta-map.schema.json     ← editor aid (mirrors the canonical validator)
└── templates/                         ← copy these to start a contribution
```

- **`maps/`** holds the **published artifacts** — resolved JSON maps, one
  file per `(app, version_code)`, consumed directly by Frida and Xposed
  authors.
- **`signatures/`** holds the **source of truth** — sigmatcher rules that
  *identify* a class/method across versions, so a map is reproducible from
  its signatures plus the APK.

`version_code` is the authoritative selection key, so it **is** the map
filename. The full map format is documented in the rosetta-frida docs:
[maps/format.md](https://github.com/Xiddoc/rosetta-frida/blob/master/docs/maps/format.md).

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

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the full workflow, the
layered trust model, and what CI does (structural validation only — **no
APK is ever uploaded**). In short: add/extend the signatures, generate the
`maps/<app>/<version_code>.json`, and open a one-map-per-PR change.

## Status

**Scaffolding.** The layout, the canonical-schema validation CI, the
filename/`version_code` convention check, the JSON Schema editor aid, and a
worked `com.example.app` example are in place. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the planned validation tiers
(signed attestations, an optional trusted runner, device telemetry) — none
of which host APKs in public CI.

## Related repos

- **[rosetta-frida](https://github.com/Xiddoc/rosetta-frida)** — the Frida
  adapter; canonical home of the map schema, the validator these maps are
  checked against, and RFC 0001.
- **[rosetta-xposed](https://github.com/Xiddoc/rosetta-xposed)** — the
  Xposed/LSPosed/LSPatch adapter; consumes these same maps.

## License

[MIT](LICENSE). Maps and signatures contributed here are released under the
same license; see [CONTRIBUTING.md](CONTRIBUTING.md) for the provenance
expectations.
