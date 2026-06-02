# schema/

`rosetta-map.schema.json` is a JSON Schema (draft-07) describing the
`schema_version: 2` map format. It exists for **editor autocompletion and a
fast local first-pass** only.

The **authoritative** validator is the rosetta-frida library's Zod schema
(`src/validate/schema.ts`), which CI runs via `rosetta validate`. This file
mirrors it; when the schema bumps in rosetta-frida, update this file to
match — but the library, not this file, is the source of truth.

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
