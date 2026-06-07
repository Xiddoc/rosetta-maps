# maps/

Published, resolved obfuscation maps — the artifacts the Rosetta libraries
consume.

## Layout

```
maps/<app>/<version_code>.json
```

- `<app>` — the Android package name (e.g. `com.example.app`).
- `<version_code>` — the full Android `longVersionCode` (`(versionCodeMajor << 32) | versionCode`), never masked. This is the **authoritative O(1) selection key**,
  so it is the filename; CI rejects a file whose
  name doesn't equal the map's `version_code`.

## Format

Strict JSON, `schema_version: 2`. The canonical schema, field semantics, and
authoring guidance live in `../schema/rosetta-map.schema.json` (owned here) and
its [docs page](https://Xiddoc.github.io/rosetta-maps/reference/schema/).

## Provenance

Carry it on the map itself via `sources[]`, per-class `source` /
`confidence`, `signer_sha256`, and `captured_at`. See `../CONTRIBUTING.md`.

`com.example.app/30405.json` is the worked example — a feature-complete map
exercising AIDL stubs/callbacks, overloads, enums, and fields.
