# Schema evolution & the migration contract

`schema_version` is a **hard gate**, not a hint. The canonical schema pins it
with `"schema_version": { "const": 5 }`, and both client adapters reject any
other value fail-closed (rosetta-frida's Zod `z.literal(5)`, rosetta-xposed's
`MapLoader` `CURRENT_SCHEMA_VERSION` check). A `schema_version: 4` map is not
"old but readable" — it is **rejected**. This page defines the migration
strategy and documents the **executed** `2 -> 3`, `3 -> 4`, and `4 -> 5` bumps,
so that future bumps are a deliberate, reproducible operation rather than an
ad-hoc scramble.

All migrations described below have **already happened**: the live canonical
schema is now `schema_version: 5`. Each PAST hop is exercised against **frozen**
copies of the schemas it bracketed (`frozen-v2.schema.json`,
`frozen-v3.schema.json`, `frozen-v4.schema.json`), so an older worked example no
longer depends on the live schema once a newer version exists.

## The decision: migrate **in place**, at bump time, once

Three strategies were weighed:

| Strategy | What it means | Verdict |
| -------- | ------------- | ------- |
| **(A) On-read migration in clients** | each client keeps a 2→3 (and 1→2, …) upgrader and accepts old maps at load time | **Rejected.** It re-introduces fuzzy multi-version acceptance the `schema_version` hard gate exists to forbid, multiplies the migration logic across the three hand-maintained clients (the exact drift Hard rule 2 fights), and means a map's on-disk version no longer tells you what it is. |
| **(B) Mixed corpus, version-tagged** | the repo holds v2 AND v3 maps side by side; clients pick the newest they understand | **Rejected.** Two live formats in one repo doubles the validation matrix forever and lets a stale v2 silently win selection over a fixed v3. |
| **(C) Migrate in place, repo-wide, at bump time** | a `schema_version: 3` bump is a single repo-wide migration pass that rewrites every map to v3; the repo only ever holds **one** live version | **Chosen.** |

**Decision: (C).** The repo is a *published-artifact* store, not a runtime cache,
so it can afford to hold exactly one canonical version at a time. A version bump
is a one-time, reviewable, reproducible event — the same shape as any other
data-and-schema change — not an ongoing compatibility burden carried in every
client forever.

Concretely, a 2→3 bump is **one PR (or a tight series) that:**

1. bumps `schema/rosetta-map.schema.json` to `"schema_version": { "const": 3 }`
   and makes the format change;
2. **migrates every `maps/**/*.json` in place** to v3 via an explicit, scripted
   migrator (`rosetta migrate`, see below) — never hand-edited per file;
3. updates the drift-guard samples under `schema/samples/{valid,invalid}/` to the
   new shape;
4. lands the matching client bumps (rosetta-frida Zod, rosetta-xposed Kotlin) and
   the shared conformance fixture **together** (Hard rule 2).

After the PR merges, the repo contains **only** v3 maps and a v3 schema; CI
validates a single version; clients accept a single version.

## How the hard gate interacts with the migrator

The `schema_version` gate and the migrator are complementary, not in tension:

- **Inside the repo / on the client**, the gate stays strict: at any commit the
  whole corpus is exactly one version, and a client built for v3 reads v3 only. No
  client ever does on-read migration. This is what keeps a wrong-version map from
  silently corrupting hooks (RFC 0001 Decision 3 / fuzzy-version §3).
- **The migrator is the only thing that reads more than one version**, and it runs
  **at bump time on the developer's machine**, not on the device and not in the
  load path. It reads a v2 map (validating it against the *frozen* v2 schema),
  transforms it, and writes a v3 map (validating it against the v3 schema). It is
  a pure data transform with the schema as its pre/post-condition.

So the gate is never "loosened to allow v2 during migration." Instead the migrator
brackets the transform with **two** gates — accept-as-v2, emit-as-v3 — and the
artifact is v3 the moment it lands.

## Where the migrator lives

The migrator is a **`rosetta migrate` CLI verb** on the developer's machine (the
same place `rosetta convert` / `rosetta pull` live), **not** a runtime path and
**not** in-repo runtime code (this repo is data + CI). For the bump itself it can
run as a one-off script in the bump PR. The contract it must honour:

- **Pure + idempotent on its target version.** `migrate(v2) -> v3`; running it on
  an already-v3 map is a no-op (it recognises the current version and returns the
  input unchanged).
- **Schema-bracketed.** It MUST reject input that is not valid against the source
  schema and MUST produce output valid against the target schema; a migration
  that emits an invalid v3 map is a migrator bug, caught by CI's normal schema
  step after the bump.
- **Deterministic bytes.** Same input → same output bytes, so a re-run produces
  a reviewable, identical diff and any future attestation digest is reproducible.
- **One step per major version.** 1→2→3 chained migrators, never a bespoke 1→3
  jump, so each hop is independently testable.

## The three clients move together (Hard rule 2)

A format change is **not done** until all three hand-maintained copies of the
format move in lockstep:

1. **`schema/rosetta-map.schema.json`** (this repo) — the canonical source of
   truth, bumped **first**.
2. **rosetta-frida** Zod validator (`src/validate/schema.ts`) — `z.literal(4)` and
   the new shape.
3. **rosetta-xposed** Kotlin `MapLoader` / model — `CURRENT_SCHEMA_VERSION = 4`
   and the new shape.

…plus the shared conformance fixture (`validation.json`) the two code clients run
through. The canonical schema is bumped first; the clients track it; **never** a
fork or a mirror in the other direction. Until every client has shipped its v3
bump, a v3 corpus would be unreadable by a lagging client — which is exactly why
the bump is one coordinated event, and why on-read migration (strategy A) was
rejected: it would let the clients drift apart silently.

## The executed 2→3 bump

The `2 -> 3` bump was a real, batched change (issues #19, #43, #39, #38/#32,
#36, #40). The field-by-field shape lives **only** in the canonical schema
(`schema/rosetta-map.schema.json`) — see the [map schema](schema.md) page rather
than re-listing it here. In summary, v3:

- bumps the hard gate to `"schema_version": { "const": 3 }`;
- **removes** `confidence` entirely (the per-class and `sources[]` field);
- tightens `captured_at` from a free-form string to an ISO `YYYY-MM-DD` date;
- lets `signer_sha256` be **either** a single 64-hex string **or** a non-empty
  array of them (match-any across signing certs);
- adds optional `generated_from` (`{ signatures_rev }`), `status`
  (`active` / `superseded` / `retracted`, absent ⇒ active), and `superseded_by`
  (a `version_code`). The `status` ⟷ `superseded_by` relationship is enforced by
  the semantic validator (`scripts/validate_map_semantics.py`), not the schema.

### `generated_from` design notes

Two deliberate choices about `generated_from` are recorded here so they are not
re-litigated:

- **`signatures_rev` is an intentionally-unverified provenance hint.** It is
  validated as a hex *shape* only (`^[0-9a-f]{7,40}$`); a fabricated rev passes
  silently. There is **no** repo-internal git-existence check, and one will not be
  added — a map may legitimately be authored where the signatures rev is not a
  commit in *this* repo. This is deliberately asymmetric with `sources[].config`,
  which semantic check 5 *does* bind to a committed file: a config path names a
  file that must exist here, whereas a signatures rev is just a backwards-pointing
  breadcrumb to wherever the signatures lived when the map was generated.
- **`generated_from` is map-level, not `sources[].rev`.** A map is generated from a
  single signatures revision, so the rev belongs once at the top level; per-source
  provenance stays in `sources[]`, which also carries hand-authored and
  runtime-discovered entries that have no git rev at all. (This is why issue #36's
  per-source-`rev` alternative was not chosen.)

The migrator hop is then:

```text
migrate_v2_to_v3(map):
    assert map.schema_version == 2          # accept-as-v2 gate
    map.schema_version = 3
    drop map.confidence and source.confidence (removed in v3)
    normalize map.captured_at -> "YYYY-MM-DD"
    return map                               # emit-as-v3 gate (validate vs v3 schema)
```

A **before/after fixture pair** demonstrating exactly this transform lives under
[`schema/migration-samples/v2-to-v3/`](https://github.com/Xiddoc/rosetta-maps/tree/master/schema/migration-samples/v2-to-v3):

- `before.v2.json` — a valid v2 map (validates against the **frozen** v2 schema
  kept beside it, `frozen-v2.schema.json`): carries `confidence` and a free-form
  `captured_at`.
- `after.v3.json` — the same map after `migrate_v2_to_v3` (validates against the
  **frozen v3** schema, `../v3-to-v4/frozen-v3.schema.json` — the live schema has
  since moved to v4).
- `invalid/` — an `after` that did **not** complete the migration (still carries
  `schema_version: 2`) and one that left a `confidence` field in: both MUST be
  **rejected** by the frozen v3 schema, pinning that the migrator's emit-as-v3 gate
  is real in both directions.

These fixtures are exercised by the `validate.yml` "Schema-migration 2->3 worked
example" step, so the *contract* stays CI-pinned. The frozen schemas are **not**
the canonical schema — they are fixtures that exist only to keep the worked
examples checkable now that the live `schema/rosetta-map.schema.json` is
`const: 5`.

## The executed 3→4 bump

The `3 -> 4` bump finished a change that the v3 bump **stranded** (see *Lessons*
below): issues **#35** (de-emphasize AIDL / generalize the schema fields) and the
schema slice of **#41** (anchoring strategy). v4 makes the published map a **pure
real→obfuscated mapping**. The field-by-field shape lives **only** in the canonical
schema — in summary, v4:

- bumps the hard gate to `"schema_version": { "const": 4 }`;
- **removes** the AIDL/Binder-specific fields — `classEntry.aidl_descriptor`,
  `methodEntry.aidl_txn`, and the `aidl_stub` / `aidl_callback` values from the
  `classKind` enum (so `kind` is purely structural again);
- **removes** the descriptive `anchors[]` array from `classEntry`.

**Why these came out.** No resolver ever read them — both static resolvers
(rosetta-frida `src/resolver/`, rosetta-xposed `core/.../resolver/`) translate
purely off `obfuscated` + a method `signature`. `anchors` had a single consumer
(rosetta-frida's attach-time health check) and the AIDL fields had none. They were
*finding-evidence* — how a class is identified — which belongs in the
`signatures/<app>/signatures.yaml` **source**, not in the resolved artifact. The
generic structural fields (`extends`, the remaining `kind` values, `dex`) stay:
they describe a Java class generically rather than privileging an Android API
family.

**Runtime self-verification (the health check) is deliberately out of scope for
v4** and tracked as a separate follow-up issue. Re-asserting signature evidence at
attach time can produce **false** staleness — an AIDL descriptor or a log string
can change between two releases while the class is still the right hook target —
so a richer self-verification design needs more thought than a reflexive
anchor-match. With the AIDL/anchor fields gone, the frida health check degrades to
"the mapped obfuscated class loads" (plus the target-namespace guard).

The migrator hop is:

```text
migrate_v3_to_v4(map):
    assert map.schema_version == 3          # accept-as-v3 gate
    map.schema_version = 4
    drop class.aidl_descriptor, class.anchors, method.aidl_txn (removed in v4)
    remap kind aidl_stub|aidl_callback -> class|interface (removed enum values)
    return map                               # emit-as-v4 gate (validate vs v4 schema)
```

A **before/after fixture pair** lives under
[`schema/migration-samples/v3-to-v4/`](https://github.com/Xiddoc/rosetta-maps/tree/master/schema/migration-samples/v3-to-v4):

- `frozen-v3.schema.json` — a frozen copy of the pre-bump v3 canonical schema
  (shared: it is also the `after` schema of the 2→3 hop).
- `before.v3.json` — a valid v3 map carrying `aidl_descriptor`, `aidl_txn`,
  `anchors`, and a `kind: aidl_stub` (validates against `frozen-v3.schema.json`).
- `after.v4.json` — the same map after `migrate_v3_to_v4` (validates against the
  frozen v4 schema, `../v4-to-v5/frozen-v4.schema.json`). This `after` validated
  against the *live* schema until the `4 -> 5` bump; now that v5 is live, the
  executed 3→4 contract is pinned against the frozen v4 copy so it no longer
  shifts when the live schema moves on.
- `invalid/` — an `after` still at `schema_version: 3`, and one that left an
  `aidl_descriptor` in: both MUST be **rejected** by the frozen v4 schema, pinning
  the emit-as-v4 gate in both directions.

These are exercised by the `validate.yml` "Schema-migration 3->4 worked example"
step.

## The executed 4→5 bump

The `4 -> 5` bump finishes the same "an artifact field must have a reader"
cleanup that v4 applied to the AIDL/anchor fields, this time for the last
free-form provenance field. In summary, v5:

- bumps the hard gate to `"schema_version": { "const": 5 }`;
- **removes** the `sources[].notes` string — the only free-text field left in
  the map.

**Why it came out.** `notes` was human prose ("rebuilt from signatures.yaml @
deadbeef", "verified via Frida runtime trace") that **no resolver reads** — both
static resolvers translate purely off `obfuscated` + a method `signature`, and
never look at `sources[]` beyond counting provenance. It was *authoring
narrative* — why/how a contributor produced the map — which belongs in a comment
at the top of `signatures/<app>/signatures.yaml` (the **source**), not in the
resolved artifact. In practice the committed maps that carried it were already
restating provenance their `signatures.yaml` header documented in full, so the
removal lost nothing. The structured provenance fields that a tool can act on
(`tool`, `config`, `classes`, per-class `source`, `signer_sha256`) stay.

The migrator hop is:

```text
migrate_v4_to_v5(map):
    assert map.schema_version == 4          # accept-as-v4 gate
    map.schema_version = 5
    for src in map.sources: drop src.notes  (removed in v5)
    return map                               # emit-as-v5 gate (validate vs v5 schema)
```

A **before/after fixture pair** lives under
[`schema/migration-samples/v4-to-v5/`](https://github.com/Xiddoc/rosetta-maps/tree/master/schema/migration-samples/v4-to-v5):

- `frozen-v4.schema.json` — a frozen copy of the pre-bump v4 canonical schema
  (shared: it is also the `after` schema of the 3→4 hop).
- `before.v4.json` — a valid v4 map carrying a `sources[].notes` (validates
  against `frozen-v4.schema.json`).
- `after.v5.json` — the same map after `migrate_v4_to_v5` (validates against the
  **live** canonical v5 schema).
- `invalid/` — an `after` still at `schema_version: 4`, and one that left a
  `notes` field in: both MUST be **rejected** by the live v5 schema, pinning the
  emit-as-v5 gate in both directions.

These are exercised by the `validate.yml` "Schema-migration 4->5 worked example"
step.

## Lessons from the v3 bump (why v4 was needed)

The `3 -> 4` bump exists because the `2 -> 3` bump **stranded** work that two open
issues had explicitly said would "ride the v3 bump (#19)." The v3 commit listed
six issues and silently omitted #35 and #41's schema slice; only #35's
no-schema-change docs rebalance landed, so the breaking field removal needed a
second migration right behind v3. Durable lessons, so it does not recur:

1. **Breaking-version windows are scarce — batch them deliberately.** Before
   cutting any schema bump, sweep **all** open issues for ones tagged
   schema-breaking and explicitly *include or consciously exclude each in the bump
   PR description*. A `schema-breaking` label + a "pending breaking changes"
   checklist keeps an issue from missing the train.
2. **An artifact field must have a reader.** `aidl_descriptor` / `aidl_txn` /
   `anchors` accreted as speculative metadata that no resolver consumed. A field
   enters the **published** map only when a runtime consumer reads it; evidence
   that only *produces* the map belongs in `signatures.yaml`.
3. **Separate source from artifact.** `signatures/<app>/signatures.yaml` is *how
   to find* a class (evidence, may rotate); `maps/<app>/<version_code>.json` is
   *what we found* (resolved real→obf). Don't duplicate finding-evidence into the
   artifact "just in case."
4. **Don't freeze a taxonomy before a consumer needs it.** #41's typed-anchor
   union was *not* built speculatively — the right call. Prove a taxonomy on a real
   map and a real consumer before committing the format to it.

## Anti-scope

- No on-device migration, ever — the device reads exactly the version it was built
  for (RFC 0001: maps are bundled at build time, no device-side transforms).
- No mixed-version corpus — at any commit the repo is exactly one `schema_version`.
- No bespoke skip-a-version migrators — only chained single-major-version hops.
- The canonical schema is bumped first; the clients (rosetta-frida Zod,
  rosetta-xposed Kotlin) and the shared conformance fixture track it — never a
  fork or a mirror in the other direction.
