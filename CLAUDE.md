# CLAUDE.md — rosetta-maps

@../CLAUDE.md

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

## Hard rules

1. **Maps are strict JSON, `schema_version: 2`, one per `(app,
   version_code)`.** The filename IS the `version_code` (the authoritative
   O(1) selection key, RFC 0001 Decision 3). `validate.yml` enforces both
   the schema and the filename↔`version_code` match.
2. **Reuse the canonical validator, never fork it.** CI checks maps with
   the rosetta-frida library's own Zod validator (`rosetta validate`, run
   from a transient checkout). `schema/rosetta-map.schema.json` is an
   editor aid that *mirrors* it — if the schema bumps in rosetta-frida,
   update that file too, but the library remains the source of truth.
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

## Related repos

- **`rosetta-frida`** — the Frida adapter; canonical schema, validator,
  and RFC 0001.
- **`rosetta-xposed`** — the Xposed/LSPosed/LSPatch adapter; consumes these
  same maps.
