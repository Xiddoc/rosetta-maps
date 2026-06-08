# Schema evolution & the migration contract

`schema_version` is a **hard gate**, not a hint. The canonical schema pins it
with `"schema_version": { "const": 2 }`, and both client adapters reject any
other value fail-closed (rosetta-frida's Zod `z.literal(2)`, rosetta-xposed's
`MapLoader` `CURRENT_SCHEMA_VERSION` check). A `schema_version: 1` map is not
"old but readable" — it is **rejected**. This page defines what happens the day
the format must move to `schema_version: 3`, so that bump is a deliberate,
reproducible operation rather than an ad-hoc scramble.

This is a **strategy + a worked hypothetical example**. The live canonical schema
stays `schema_version: 2`; nothing here bumps it.

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
3. re-emits each map's **`.sha256` sidecar** (the bytes changed, so the digest
   must too) via `scripts/verify_map_sidecars.py --emit`;
4. updates the drift-guard samples under `schema/samples/{valid,invalid}/` to the
   new shape;
5. lands the matching client bumps (rosetta-frida Zod, rosetta-xposed Kotlin) and
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
- **Deterministic bytes.** Same input → same output bytes, so the re-emitted
  `.sha256` sidecars are reproducible and reviewable.
- **One step per major version.** 1→2→3 chained migrators, never a bespoke 1→3
  jump, so each hop is independently testable.

## The three clients move together (Hard rule 2)

A format change is **not done** until all three hand-maintained copies of the
format move in lockstep:

1. **`schema/rosetta-map.schema.json`** (this repo) — the canonical source of
   truth, bumped **first**.
2. **rosetta-frida** Zod validator (`src/validate/schema.ts`) — `z.literal(3)` and
   the new shape.
3. **rosetta-xposed** Kotlin `MapLoader` / model — `CURRENT_SCHEMA_VERSION = 3`
   and the new shape.

…plus the shared conformance fixture (`validation.json`) the two code clients run
through. The canonical schema is bumped first; the clients track it; **never** a
fork or a mirror in the other direction. Until every client has shipped its v3
bump, a v3 corpus would be unreadable by a lagging client — which is exactly why
the bump is one coordinated event, and why on-read migration (strategy A) was
rejected: it would let the clients drift apart silently.

## Worked hypothetical: a 2→3 bump

This is **illustrative only** — it does not describe a real planned change. Say v3
splits the human label `version` into a structured object:

- **v2:** `"version": "3.4.5"` (a plain string).
- **v3 (hypothetical):** `"version": { "name": "3.4.5" }` (an object; the gate
  becomes `"schema_version": { "const": 3 }`).

The migrator hop is then:

```text
migrate_v2_to_v3(map):
    assert map.schema_version == 2          # accept-as-v2 gate
    map.schema_version = 3
    map.version = { "name": map.version }    # string -> { name: string }
    return map                               # emit-as-v3 gate (validate vs v3 schema)
```

A **before/after fixture pair** demonstrating exactly this transform lives under
[`schema/migration-samples/v2-to-v3/`](https://github.com/Xiddoc/rosetta-maps/tree/master/schema/migration-samples/v2-to-v3):

- `before.v2.json` — a valid v2 map (validates against the **live** v2 schema).
- `after.v3.json` — the same map after `migrate_v2_to_v3` (validates against the
  **hypothetical** v3 schema kept beside it, `hypothetical-v3.schema.json`).
- `invalid/` — an `after` that did **not** complete the migration (still carries
  `schema_version: 2`) and one that left `version` a bare string: both MUST be
  **rejected** by the v3 schema, pinning that the migrator's emit-as-v3 gate is
  real in both directions.

These fixtures are exercised by the existing `validate.yml` sample steps' sibling
pattern (a dedicated migration-samples step), so the *contract* is CI-pinned even
though the live schema stays v2. The hypothetical v3 schema is **not** the
canonical schema — it is a fixture that exists only to make the worked example
checkable; the canonical `schema/rosetta-map.schema.json` remains `const: 2`.

## Anti-scope

- No on-device migration, ever — the device reads exactly the version it was built
  for (RFC 0001: maps are bundled at build time, no device-side transforms).
- No mixed-version corpus — at any commit the repo is exactly one `schema_version`.
- No bespoke skip-a-version migrators — only chained single-major-version hops.
- This does **not** bump the live schema; it defines the contract for when a bump
  happens. The canonical schema stays `schema_version: 2`.
