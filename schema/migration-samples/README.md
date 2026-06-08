# Schema-migration worked-example fixtures

These pin the **schema-migration contract** (maps#19, see
`docs/reference/schema-migration.md`) with a concrete, CI-checkable
**hypothetical** `2 -> 3` example. They are fixtures only — the **live**
canonical schema (`schema/rosetta-map.schema.json`) stays `schema_version: 2`.
Nothing here bumps the real schema.

## `v2-to-v3/`

The worked example: a hypothetical v3 that splits the human label `version` from
a bare string into a structured object `{ "name": "..." }`.

- `hypothetical-v3.schema.json` — a fixture-only `schema_version: 3` schema
  (identical to the live v2 schema except the `const: 3` gate and the structured
  `version`). **Never** consumed as canonical; it exists only to make `after`
  checkable.
- `before.v2.json` — a valid v2 map (validates against the **live** v2 schema).
- `after.v3.json` — the same map after the `migrate_v2_to_v3` hop documented in
  `schema-migration.md` (validates against `hypothetical-v3.schema.json`).
- `invalid/not-migrated-still-v2.json` — claims the new `version` shape but left
  `schema_version: 2`; MUST be **rejected** by the v3 schema.
- `invalid/version-left-as-string.json` — bumped to `schema_version: 3` but left
  `version` a bare string (an incomplete migration); MUST be **rejected** by the
  v3 schema.

`.github/workflows/validate.yml` (the "Schema-migration 2->3 worked example"
step) pins all four directions: `before` passes the live v2 schema, `after`
passes the v3 schema, and `before` + both `invalid/` maps are rejected by the v3
schema — so the migrator's "emit-as-v3" gate is demonstrably real.

## Adding another worked example

If the migration contract gains a second hop (e.g. `3 -> 4`), add a sibling
`v3-to-v4/` directory with the same `before` / `after` / `hypothetical-N.schema.json`
/ `invalid/` shape and extend the migration step. Keep fixtures tiny and
provider-neutral (`com.example.app`).
