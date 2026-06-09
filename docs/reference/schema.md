# Map schema

`schema/rosetta-map.schema.json` is the **canonical** JSON Schema (draft-07) for
the `schema_version: 3` map format. It is the single, language-neutral source of
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
  `notes`).
- per-class `source`.
- `signer_sha256` — the lowercase-hex SHA-256 of the signing certificate(s), if
  you read them. This pins publisher authenticity and detects repacks.
  **Format-checked:** each value must match `^[0-9a-f]{64}$` — exactly 64
  lowercase hex chars, **no colon separators** (the canonical on-disk form is
  `abcd…`, not the `AB:CD:…` certificate-fingerprint spelling some tools print).
  It may be a **single string** or a **non-empty array** of such strings (an app
  may present several signing certs; clients match-any). Clients enforce it
  **fail-closed**, so omit the key entirely if you don't have it — don't leave a
  placeholder, which would always `SignerMismatch`.
- `captured_at` — the date you captured the map, as an ISO `YYYY-MM-DD` date.
- `generated_from` — optional `{ "signatures_rev": "<git sha>" }` binding the
  map to the exact signatures revision it was generated from.
- `status` — optional lifecycle marker (`active` / `superseded` / `retracted`;
  absent ⇒ `active`). When `superseded`, set `superseded_by` to the
  `version_code` that replaces this map (the semantic validator enforces this
  pairing).
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

## Anchoring evidence types

A map is *reproduced* from its `signatures/<app>/signatures.yaml`, which pins
each class on the most **rotation-stable** evidence available. The evidence
taxonomy is generic-first — these are the default because they work for any
class:

- **String literals** — endpoint URLs, log tags, `static final String`
  constants, field/key names reached by live code.
- **Superclass / framework parent** — an obfuscated class still extends a
  non-rotating `android` / `androidx` / `java` parent or implements a stable
  interface.
- **Constants** — a `static final` value or magic number.
- **Structural / cross-class** — a resolved class's descriptor referenced
  elsewhere, or a distinctive method-table shape.
- **AIDL / Binder descriptor** — a niche special case *when present*: a `.Stub`
  embeds its binder descriptor verbatim and it never rotates, but most classes
  have no AIDL contract, so it is the exception, not the rule.

This describes the *authoring* evidence, not on-disk schema fields — the format
itself is defined only here in `schema/rosetta-map.schema.json` (this section
adds no fields). See `templates/signatures.template.yaml` and
[CONTRIBUTING.md](../../CONTRIBUTING.md) for the worked authoring flow.

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

Every numeric bound above is pinned in BOTH directions by the curated samples
CI checks (`schema/samples/`): `valid/bounds-at-max.json` exercises the
at-the-limit values (`app`/`version` at 256, `obfuscated` at 512, `sources` at
100, an overload array at 200, `anchors` at 1000) and the `invalid/*-too-long`
/ `invalid/*-too-many` samples each push exactly one of those bounds one over
the limit. The whole-file byte ceiling (`MAX_MAP_BYTES`, the maps-side
equivalent of the clients' input-byte cap) is a CI-workflow guard in
`validate.yml`, since JSON Schema cannot express a total-document-size or
nesting-depth limit; those two remain client-/CI-enforced rather than schema
keywords.
