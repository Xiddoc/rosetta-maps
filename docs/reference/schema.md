# Map schema

`schema/rosetta-map.schema.json` is the **canonical** JSON Schema (draft-07) for
the `schema_version: 2` map format. It is the single, language-neutral source of
truth for the format — this repo owns it because this repo owns the data it
describes.

CI validates every map under `maps/` against this file. It is also the reference
for field semantics when authoring a map by hand.

## Clients track this schema

The adapters that consume these maps are **clients** of the schema, not owners of
it:

- **[rosetta-frida](https://github.com/Xiddoc/rosetta-frida)** (TypeScript) — the
  first-class client. It carries a validator that tracks this schema and is
  contract-tested against it.
- **[rosetta-xposed](https://github.com/Xiddoc/rosetta-xposed)** (Kotlin) —
  consumes the same format on-device.

Changing the format means bumping **this** schema first, then updating the client
adapters to match — never the other way around.

## Editor setup (optional)

In VS Code, point your settings at the schema for files under `maps/` to get
autocompletion and inline validation:

```jsonc
// .vscode/settings.json
{
    "json.schemas": [
        {
            "fileMatch": ["maps/**/*.json"],
            "url": "./schema/rosetta-map.schema.json"
        }
    ]
}
```

The canonical artifacts intentionally omit a `$schema` key so they stay
byte-faithful with the maps rosetta-frida emits.

## Provenance fields

Record provenance on the map itself rather than in free text:

- `sources[]` — which tool(s) produced which entries (`tool`, `config`, `classes`,
  `confidence`, `notes`).
- per-class `source` and `confidence`.
- `signer_sha256` — the lowercase-hex SHA-256 of the signing certificate, if you
  read it. This pins publisher authenticity and detects repacks. **Format-checked:**
  it must match `^[0-9a-f]{64}$` — exactly 64 lowercase hex chars, **no colon
  separators** (the canonical on-disk form is `abcd…`, not the `AB:CD:…`
  certificate-fingerprint spelling some tools print). Clients enforce it
  **fail-closed**, so omit the key entirely if you don't have it — don't leave a
  placeholder, which would always `SignerMismatch`.
- `captured_at` — the date you captured the map.
- `client_hints` — an optional sub-object for **advisory**, client-specific hints
  that the core resolver ignores (`frida_min_version`, `frida_max_version`). They
  live under `client_hints` rather than at the top level so the top-level
  identity keys stay clean and the hints read as non-authoritative. `client_hints`
  is itself **closed** (`additionalProperties: false`): adding a new hint key is a
  deliberate schema change (bump this schema, then the client adapters), not a
  silent extension — an unrecognised key is rejected rather than ignored.

The top-level object, `sources[]` entries, and every class / method / field
entry are **closed** (`additionalProperties: false`): an unknown or misspelled
key (e.g. `extneds`, `signer_sh256`) is rejected rather than silently dropped.

## Input bounds and key safety

The schema imposes defensive caps so a malformed or hostile map can't blow up a
client. These exact limits are mirrored by the rosetta-frida (Zod) and
rosetta-xposed clients and must stay in lockstep:

- **Sizes:** `classes` ≤ 50000 entries; per-class `methods` and `fields` ≤ 5000
  each; a method-overload array is 1–200 entries; `anchors` ≤ 1000; `sources` ≤
  100.
- **String lengths:** obfuscated / short names ≤ 512; `signature` ≤ 4096; `app`
  and `version` ≤ 256; other free-text strings ≤ 4096.
- **Identifier shapes:** `app` must match
  `^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$` (a dotted Java package
  id — every segment must start with a letter, so `com.2example` is rejected);
  `version_code` is an integer ≥ 0; `version` must be non-blank — the
  guarantee comes from two complementary constraints: `minLength: 1` rejects
  the empty string `""` and the `\S` pattern rejects an all-whitespace label
  like `"   "`; `signer_sha256` matches `^[0-9a-f]{64}$`.
- **Reserved-key rejection:** the `classes`, `methods`, and `fields` objects
  reject the keys `__proto__`, `constructor`, and `prototype` (prototype-pollution
  guard for JS clients).
