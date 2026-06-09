# AGENTS.md — rosetta-maps

Guidance for agents and human contributors working in this repo. (For the
user-facing intro, see `README.md`; for the contribution workflow, see
`CONTRIBUTING.md`.)

## What this project is

The **community knowledge base** of obfuscation maps for the Rosetta
tools — an obfuscation-map "CVE database" (RFC 0001 Decision 4, in the
`rosetta-frida` repo under `docs/rfcs/`). It holds two artifacts:

- **`signatures/<app>/signatures.yaml`** — the **source of truth**:
  sigmatcher rules (regex-over-smali) that identify classes/methods across
  versions. A map is *reproducible* from its signatures + the APK, which is
  what makes it verifiable.
- **`maps/<app>/<version_code>.json`** — the **published artifacts**:
  resolved `schema_version: 3` JSON consumed directly by rosetta-frida and
  rosetta-xposed.

This repo is **data + CI, not a code library.** It has no build; the only
automation is PR-gated validation.

## Repo layout (invariants)

```
rosetta-maps/
├── maps/<app>/<version_code>.json     ← generated, published, consumed
├── signatures/<app>/signatures.yaml   ← source of truth (sigmatcher dialect)
├── schema/rosetta-map.schema.json     ← CANONICAL schema (this repo owns it)
└── templates/                         ← copy these to start a contribution
```

## Hard rules

1. **Maps are strict JSON, `schema_version: 3`, one per `(app,
   version_code)`.** The filename IS the `version_code` (the authoritative
   O(1) selection key, RFC 0001 Decision 3). `validate.yml` enforces both
   the schema and the filename↔`version_code` match.
2. **This repo owns the canonical schema; CI validates against it.**
   `schema/rosetta-map.schema.json` is the single, language-neutral source
   of truth for the `schema_version: 3` format — the format belongs with
   the data, and the data lives here. CI validates every map against this
   file directly with a language-neutral JSON Schema checker
   (check-jsonschema — no JS toolchain, no cross-repo checkout). The
   rosetta-frida (TS/Zod)
   and rosetta-xposed (Kotlin) adapters are **clients** that track this
   schema. Changing the format means bumping this file first, then the
   adapters — never a fork or a mirror in the other direction.
3. **Never host or upload APKs in CI.** APK-host ToS forbid it and it's a
   copyright liability. Public CI does structural checks only (Decision 4
   tier 1). Correctness-against-the-real-app belongs off public CI
   (attestation / trusted runner / device telemetry — all planned).
4. **Two signature dialects, no third.** sigmatcher YAML (offline, here) +
   DexKit queries (on-device, harvested into sigmatcher form). Do not
   invent a unified signature IR; the convergence point is the *map*
   (RFC 0001 Decision 5).

## Testing mandate

**Everything that can be tested must be tested; keep CI green; add cases
with every change.** This repo is data + CI, so "tests" are the PR-gated
validation checks in `.github/workflows/validate.yml`, not a unit-test
suite — but the discipline is the same as the rosetta-frida / rosetta-xposed
clients:

- Every change to the canonical schema (`schema/rosetta-map.schema.json`)
  must keep `validate.yml` green AND add/extend the accept/reject samples
  under `schema/samples/` that pin the affected constraint in BOTH
  directions (a `valid/` sample for anything newly allowed, an `invalid/`
  sample for anything newly forbidden). A constraint with no sample
  exercising it can loosen silently — that is the drift the samples exist
  to catch.
- A schema change is not done until the client adapters (frida Zod,
  xposed Kotlin) and, where applicable, the shared conformance
  `validation.json` fixture are updated to match — the three copies of the
  `schema_version: 3` format must move together (Hard rule 2).
- Never weaken or skip a CI check to make a PR pass; fix the data.
- For SEMANTIC (non-schema) constraints — relationships the JSON Schema
  cannot express — a CI check that carries its own in-script `--self-test`
  (accept + reject fixtures pinning each constraint in BOTH directions, the
  way `scripts/validate_map_semantics.py` and `scripts/lint_signatures.py`
  do) satisfies the "pin in both directions" mandate, and is the accepted
  alternative to `schema/samples/`. The `schema/samples/{valid,invalid}/`
  pairs remain the mechanism for SCHEMA constraints.

## When picking up work here

1. **Read RFC 0001 Decisions 3–5** in `rosetta-frida` first — they define
   the identity keys, the trust ladder, and the no-new-format rule this
   repo implements.
2. **Keep CI green and APK-free.** New validation tiers (attestation,
   trusted runner, telemetry) must preserve the "no APK in public CI"
   invariant.
3. **One `(app, version_code)` per PR** so provenance and review stay
   legible (see `CONTRIBUTING.md`).
4. **Keep the example honest.** `maps/com.example.app/30405.json` +
   `signatures/com.example.app/signatures.yaml` are the worked example new
   contributors copy; they must always validate.

## Anti-scope

- No build system, package manifest, or runtime code — this repo is data.
- No new signature format / unified IR (see Hard rule 4).
- No APK fetching, mirroring, or uploading anywhere in this repo or its CI.
- The canonical schema lives in `schema/rosetta-map.schema.json` (this
  repo owns it). Don't duplicate the field-by-field format in prose
  elsewhere; point at the schema so there is a single source of truth.
- No **self-referential map hash field.** A map's own-bytes integrity is
  bound from OUTSIDE the artifact (a detached `<version_code>.json.sha256`
  sidecar verified at build time by `rosetta pull` (planned)), never via a
  hash field inside the map — that would be self-referential AND break the
  strict `additionalProperties: false` clients. See
  `docs/reference/integrity.md` (maps#13 M14).

## Related repos

- **`rosetta-frida`** — the Frida adapter and home of RFC 0001; a client
  of this repo's canonical schema (its Zod validator tracks it).
- **`rosetta-xposed`** — the Xposed/LSPosed/LSPatch adapter; another client
  that consumes these same maps.
