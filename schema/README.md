# schema/

`rosetta-map.schema.json` is the **canonical** JSON Schema (draft-07) for
the `schema_version: 5` map format. It is the single, language-neutral
source of truth for the format — this repo owns it because this repo owns
the data it describes.

CI validates every map under `maps/` against this file (see
`.github/workflows/validate.yml`). Editors can also point at it for
autocompletion (below).

The adapters that consume these maps are **clients** of this schema, not
owners of it:

- **rosetta-frida** (TypeScript) carries a Zod validator
  (`src/validate/schema.ts`) for attach-time use; it tracks this schema
  and is contract-tested against it.
- **rosetta-xposed** (Kotlin) consumes the same format on-device.

Changing the format means bumping **this** schema first, then updating the
client adapters to match — never the other way around.

## Editor setup (optional)

VS Code, point your settings at it for files under `maps/`:

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
