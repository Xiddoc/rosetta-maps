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
  read it. This pins publisher authenticity and detects repacks.
- `captured_at` — the date you captured the map.
