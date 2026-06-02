# schema/

`rosetta-map.schema.json` is a JSON Schema (draft-07) describing the
`schema_version: 2` map format. It serves double duty: **editor
autocompletion** and **this repo's CI gate** (`validate.yml` runs `ajv`
against it, so the data repo validates itself without reaching into the
library repo).

The **schema source of truth** is the rosetta-frida library's Zod schema
(`src/validate/schema.ts`). This file *mirrors* it; when the schema bumps in
rosetta-frida, update this file to match — the library, not this file,
defines the format.

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
