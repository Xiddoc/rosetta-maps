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

Strict JSON, `schema_version: 4` — a pure real→obfuscated mapping (the AIDL/Binder
fields and `anchors[]` were removed in v4; finding-evidence lives in the
signatures source). The canonical schema, field semantics, and authoring guidance
live in `../schema/rosetta-map.schema.json` (owned here) and its
[docs page](https://Xiddoc.github.io/rosetta-maps/reference/schema/).

## Provenance

Carry it on the map itself via `sources[]`, per-class `source`,
`signer_sha256`, `captured_at`, and optionally `generated_from`. See
`../CONTRIBUTING.md`.

`com.example.app/30405.json` is the worked example — a feature-complete map
exercising overloads, constructors, enums, fields, and synthetic / anonymous
classes.

> **The example's `signer_sha256` is a placeholder, not a real hash.**
> `com.example.app/30405.json` carries an obviously-fake, well-formed
> `signer_sha256` (`0123456789abcdef…`). It is there only to exercise the
> schema's hex-format constraint; it will **not** match any real signing
> certificate. Clients enforce `signer_sha256` **fail-closed**, so if you
> copy this map and ship it verbatim the signer guard will reject it with a
> `SignerMismatch`. Replace it with your app's real signing-cert SHA-256
> (lowercase, no colons, 64 hex chars), **or** omit the field entirely to use
> the explicitly-unverified construction path (`fromMapUnverified` on the
> Kotlin client; the Frida client likewise skips the guard when the field is
> absent). Never ship a placeholder hash as if it were authentic.
