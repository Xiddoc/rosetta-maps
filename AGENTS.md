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
  resolved `schema_version: 2` JSON consumed directly by rosetta-frida and
  rosetta-xposed.

This repo is **data + CI, not a code library.** It has no build; the only
automation is PR-gated validation.

## Repo layout (invariants)

```
rosetta-maps/
├── maps/<app>/<version_code>.json     ← generated, published, consumed
├── signatures/<app>/signatures.yaml   ← source of truth (sigmatcher dialect)
├── schema/rosetta-map.schema.json     ← editor aid (mirrors the canonical validator)
└── templates/                         ← copy these to start a contribution
```

## Hard rules

1. **Maps are strict JSON, `schema_version: 2`, one per `(app,
   version_code)`.** The filename IS the `version_code` (the authoritative
   O(1) selection key, RFC 0001 Decision 3). `validate.yml` enforces both
   the schema and the filename↔`version_code` match.
2. **Validate against the in-repo JSON Schema; keep it a faithful mirror.**
   CI is self-contained (`ajv` against `schema/rosetta-map.schema.json`) — a
   pure *data* repo shouldn't reach into the library repo at CI time. That
   schema **mirrors** rosetta-frida's canonical Zod validator, which remains
   the schema's source of truth: if it bumps there, update
   `schema/rosetta-map.schema.json` to match (and `const: 2` keeps the
   schema version pinned). It serves double duty as the editor aid.
3. **Never host or upload APKs in CI.** APK-host ToS forbid it and it's a
   copyright liability. Public CI does structural checks only (Decision 4
   tier 1). Correctness-against-the-real-app belongs off public CI
   (attestation / trusted runner / device telemetry — all planned).
4. **Two signature dialects, no third.** sigmatcher YAML (offline, here) +
   DexKit queries (on-device, harvested into sigmatcher form). Do not
   invent a unified signature IR; the convergence point is the *map*
   (RFC 0001 Decision 5).

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
- Don't restate the map schema/format here; cross-link the rosetta-frida
  docs so there is a single source of truth.

## Related repos

- **`rosetta-frida`** — the Frida adapter; canonical schema, validator,
  and RFC 0001.
- **`rosetta-xposed`** — the Xposed/LSPosed/LSPatch adapter; consumes these
  same maps.
