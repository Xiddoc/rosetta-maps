# Schema-migration worked-example fixtures

These pin the **schema-migration contract** (maps#19, see
`docs/reference/schema-migration.md`) with concrete, CI-checkable worked
examples. The **live** canonical schema (`schema/rosetta-map.schema.json`) is now
`schema_version: 4`. Each PAST hop is checked against **frozen** copies of the
schemas it bracketed, so an older worked example no longer depends on the live
schema once a newer version exists.

## `v2-to-v3/`

The worked example demonstrates the real v3 transform: bump `schema_version`
`2 -> 3`, drop the removed `confidence` field (top-level `sources[]` and
per-class), and normalize `captured_at` from a free-form string to an ISO
`YYYY-MM-DD` date.

- `frozen-v2.schema.json` — a **frozen** copy of the pre-bump `schema_version: 2`
  canonical schema. It exists only so `before.v2.json` stays checkable. **Never**
  consumed as canonical.
- `before.v2.json` — a valid v2 map (validates against `frozen-v2.schema.json`):
  carries `confidence` fields and a free-form `captured_at`.
- `after.v3.json` — the same map after the `migrate_v2_to_v3` hop documented in
  `schema-migration.md`. It validates against the **frozen v3** schema
  (`../v3-to-v4/frozen-v3.schema.json`), not the live canonical — the live schema
  has since moved to v4.
- `invalid/not-migrated-still-v2.json` — left `schema_version: 2`; MUST be
  **rejected** by the frozen v3 schema.
- `invalid/confidence-left-in.json` — bumped to `schema_version: 3` but left a
  `confidence` field (an incomplete migration); MUST be **rejected** by the
  frozen v3 schema (it is now an unknown key under `additionalProperties: false`).

## `v3-to-v4/`

The worked example demonstrates the real v4 transform: make the published map a
**pure real->obfuscated mapping** by dropping the AIDL/Binder-specific fields
(`classEntry.aidl_descriptor`, `methodEntry.aidl_txn`, the
`aidl_stub`/`aidl_callback` `kind` values) and the descriptive `anchors[]` array.
Finding-evidence (string literals, AIDL descriptors) is authoring input that
stays in `signatures/<app>/signatures.yaml`, never the emitted artifact.

- `frozen-v3.schema.json` — a **frozen** copy of the pre-bump `schema_version: 3`
  canonical schema. Shared: it is the `after` schema of the 2->3 hop AND the
  `before` schema of this hop. **Never** consumed as canonical.
- `before.v3.json` — a valid v3 map (validates against `frozen-v3.schema.json`):
  carries `aidl_descriptor`, `aidl_txn`, `anchors`, and a `kind: aidl_stub`.
- `after.v4.json` — the same map after the `migrate_v3_to_v4` hop (validates
  against the **live** canonical v4 schema): the AIDL fields and `anchors` are
  gone, `kind` is the generic `class`.
- `invalid/not-migrated-still-v3.json` — left `schema_version: 3`; MUST be
  **rejected** by the live v4 schema.
- `invalid/aidl-field-left-in.json` — bumped to `schema_version: 4` but left an
  `aidl_descriptor` on a class (an incomplete migration); MUST be **rejected** by
  the v4 schema (now an unknown key under `additionalProperties: false`).

`.github/workflows/validate.yml` (the "Schema-migration 2->3 / 3->4 worked
example" steps) pins every direction for both hops, so each migrator's
"emit-as-target" gate is demonstrably real.

## Adding another worked example

If the migration contract gains a further hop (e.g. `4 -> 5`), add a sibling
`v4-to-v5/` directory with the same `before` / `after` / `frozen-N.schema.json`
/ `invalid/` shape, freeze the v4 schema beside it, repoint the previous hop's
`after` side at the new frozen schema, and extend the migration step. Keep
fixtures tiny and provider-neutral (`com.example.app`).
