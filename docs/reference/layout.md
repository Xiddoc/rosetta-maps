# Repository layout

rosetta-maps is **data + CI, not a code library.** It has no build and no runtime
code; the only automation is PR-gated validation.

```
rosetta-maps/
├── maps/<app>/<version_code>.json     ← generated, published, consumed
├── signatures/<app>/signatures.yaml   ← source of truth (sigmatcher dialect)
├── schema/rosetta-map.schema.json     ← CANONICAL schema (this repo owns it)
└── templates/                         ← copy these to start a contribution
```

## `maps/` — published artifacts

Resolved JSON maps, one file per `(app, version_code)`, consumed directly by the
rosetta-frida and rosetta-xposed adapters.

- `<app>` — the Android package name (e.g. `com.example.app`).
- `<version_code>` — the `PackageInfo.versionCode` (or low 32 bits of
  `longVersionCode`). This is the **authoritative O(1) selection key** (RFC 0001
  Decision 3), so it **is** the filename; CI rejects any file whose name does not
  equal the map's `version_code`.

Maps are strict JSON, `schema_version: 2`. Field semantics live with the
[canonical schema](schema.md). Provenance is carried on the map itself via
`sources[]`, per-class `source`/`confidence`, `signer_sha256`, and `captured_at`.

`maps/com.example.app/30405.json` is the worked example — a feature-complete map
exercising AIDL stubs/callbacks, overloads, enums, and fields.

## `signatures/` — source of truth

sigmatcher rules (the offline / host dialect: regex-over-smali) that identify a
class/method across versions. A map under `maps/` is *reproducible* from these
signatures + the APK — which is what makes a contributed map verifiable rather than
just trusted.

```
signatures/<app>/signatures.yaml
```

One file per app. Signatures are **multi-version on purpose**: anchor on
rotation-stable evidence so the same rules resolve across point releases even as
obfuscated names rotate. In rough order of robustness:

1. AIDL descriptor strings (never rotated by R8);
2. stable `static final String` literals reached by live code;
3. stable framework superclass / interface references;
4. cross-class anchors (a resolved class's descriptor referenced elsewhere).

### Two dialects, no third

sigmatcher YAML (here, offline/readable) and DexKit queries (on-device, runtime)
are the only two signature dialects — split by *execution context*, not by app or
framework (RFC 0001 Decision 5). DexKit fingerprints are harvested **one-time**
into this sigmatcher form. Do not propose a new "unified" signature IR — the
convergence point is the resolved **map**, not the signature.

## `schema/` — the canonical map schema

`rosetta-map.schema.json` is the single, language-neutral source of truth for the
`schema_version: 2` format, owned here. See the [map schema](schema.md) page.

## `templates/`

Starting points to copy when authoring a contribution:
`templates/map.template.json` and `templates/signatures.template.yaml`.
