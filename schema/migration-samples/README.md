# Schema-migration worked-example fixtures

These pin the **schema-migration contract** (maps#19, see
`docs/reference/schema-migration.md`) with a concrete, CI-checkable `2 -> 3`
example. The `2 -> 3` bump has been **executed**: the **live** canonical schema
(`schema/rosetta-map.schema.json`) is now `schema_version: 3`. These fixtures
keep the worked transform checkable against a **frozen** copy of the old v2
schema on the `before` side and the live v3 canonical schema on the `after`
side.

## `v2-to-v3/`

The worked example demonstrates the real v3 transform: bump `schema_version`
`2 -> 3`, drop the removed `confidence` field (top-level `sources[]` and
per-class), and normalize `captured_at` from a free-form string to an ISO
`YYYY-MM-DD` date.

- `frozen-v2.schema.json` — a **frozen** copy of the pre-bump `schema_version: 2`
  canonical schema. It exists only so `before.v2.json` stays checkable now that
  the live canonical schema has moved to v3. **Never** consumed as canonical.
- `before.v2.json` — a valid v2 map (validates against `frozen-v2.schema.json`):
  carries `confidence` fields and a free-form `captured_at`.
- `after.v3.json` — the same map after the `migrate_v2_to_v3` hop documented in
  `schema-migration.md` (validates against the **live** canonical v3 schema):
  `confidence` removed, `captured_at` a real date, `schema_version: 3`.
- `invalid/not-migrated-still-v2.json` — left `schema_version: 2`; MUST be
  **rejected** by the live v3 schema.
- `invalid/confidence-left-in.json` — bumped to `schema_version: 3` but left a
  `confidence` field (an incomplete migration); MUST be **rejected** by the v3
  schema (it is now an unknown key under `additionalProperties: false`).

`.github/workflows/validate.yml` (the "Schema-migration 2->3 worked example"
step) pins every direction: `before` passes the frozen v2 schema, `after`
passes the live v3 schema, `after` is **rejected by the frozen v2 schema** (a v3
artifact does not pass as v2 — the break is real both ways), and `before` + both
`invalid/` maps are rejected by the live v3 schema — so the migrator's
"emit-as-v3" gate is demonstrably real.

## Adding another worked example

If the migration contract gains a second hop (e.g. `3 -> 4`), add a sibling
`v3-to-v4/` directory with the same `before` / `after` / `frozen-N.schema.json`
/ `invalid/` shape and extend the migration step. Keep fixtures tiny and
provider-neutral (`com.example.app`).
