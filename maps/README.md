# maps/

Published, resolved obfuscation maps — the artifacts the Rosetta libraries
consume.

## Layout

```
maps/<app>/<version_code>.json
```

- `<app>` — the Android package name (e.g. `com.example.app`).
- `<version_code>` — the `PackageInfo.versionCode` (or low 32 bits of
  `longVersionCode`). This is the **authoritative O(1) selection key**
  (RFC 0001 Decision 3), so it is the filename; CI rejects a file whose
  name doesn't equal the map's `version_code`.

## Format

Strict JSON, `schema_version: 2`. The full schema, field semantics, and
authoring guidance live in the rosetta-frida docs
([map format](https://github.com/Xiddoc/rosetta-frida/blob/master/docs/maps/format.md)).
`../schema/rosetta-map.schema.json` is an editor aid that mirrors the
canonical validator.

## Provenance

Carry it on the map itself via `sources[]`, per-class `source` /
`confidence`, `signer_sha256`, and `captured_at`. See `../CONTRIBUTING.md`.

`com.example.app/30405.json` is the worked example — a feature-complete map
exercising AIDL stubs/callbacks, overloads, enums, and fields.
