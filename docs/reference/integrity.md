# Map integrity & provenance at load

This page documents a known **integrity gap** and the recommended future
approach. It is documentation-led on purpose: the fix must not change the
on-disk map format the strict clients consume (see below).

## The gap

A published map (`maps/<app>/<version_code>.json`) is selected on-device by its
`version_code` and, when present, authenticated against the *app* via
`signer_sha256` — the SHA-256 of the running app's signing certificate. That
guard answers "is this the app the map was authored for?" It does **not**
answer "is this map file itself the one the maintainers published, byte for
byte?"

So a map that is **tampered after publication** — edited in a vendored copy, a
poisoned mirror, or a malicious PR that slips past review — is not caught by any
check that lives *inside* the map. The schema validates shape, the
[tier-1 semantics](trust-model.md) check validates internal consistency, and
`signer_sha256` validates the *app*; none of them bind the map's own bytes to a
trusted publisher.

## Why not a hash field inside the map

The obvious idea — add a `map_sha256` field carrying the file's own hash — is
the wrong shape, for two reasons:

1. **Self-reference (the definitive blocker).** A hash *of the file* cannot
   live *in the file*: adding the field changes the bytes, which changes the
   hash. You would have to define a canonicalisation ("hash everything except
   this field"), which is exactly the fragile, easy-to-get-subtly-wrong
   machinery a self-describing JSON artifact should avoid. This alone rules the
   field out regardless of any schema policy.
2. **It would also break the strict clients (an additional, practical
   constraint).** The top-level map schema and all named object types use
   `additionalProperties: false` (the user-keyed records — `classes`, a class's
   `methods`/`fields` — gate their *values* through a `$ref`, not a literal
   `false`), and the rosetta-frida (Zod) and rosetta-xposed (Kotlin) clients
   track it strictly. A **new field that real maps carry** would be rejected by
   every client that has not yet shipped the matching schema bump — a breaking
   change for a guarantee that does not need to live in the map at all.

## Recommended approach — a detached sidecar

Bind the map's bytes to a trusted publisher from **outside** the artifact, with
a sidecar that travels next to the map but is not part of it:

```
maps/com.example.app/30405.json          ← the canonical, unchanged map
maps/com.example.app/30405.json.sha256   ← (future) detached digest / signature
```

- The sidecar holds either a bare SHA-256 of the map file or, better, a
  **detached signature** (e.g. minisign / `ssh-keygen -Y` / a maintainer GPG
  key) over that digest. A signature additionally proves *who* published it; a
  bare digest only proves the bytes match what the index recorded.
- **A bare `.sha256` committed by the same (untrusted) PR author adds little**
  over just reviewing the map: an attacker who can edit `30405.json` in a PR can
  edit `30405.json.sha256` in the same PR, so the digest only re-states whatever
  bytes they pushed. Real protection requires a **detached signature from a
  trusted party** — a CI signing key or a maintainer key whose private half the
  PR author does not hold — so the binding is to a publisher, not merely to the
  contributed bytes. Treat the bare-digest form as a transport-integrity check
  (catches a corrupted mirror), not an authenticity guarantee.
- It is verified at **build/author time** by the `rosetta pull` CLI on the
  developer's machine — the same place and time the map is fetched and bundled —
  **not on the device**. This keeps the device free of network I/O and crypto it
  does not need, consistent with "maps are acquired and bundled at build time,
  never fetched from the cloud on the device."
- The canonical map stays a **pure, self-describing map**: no self-referential
  hash, no canonicalisation rules, no client-breaking field. Clients that never
  opt into sidecar verification are completely unaffected, because the map bytes
  they parse are identical.

This is a planned tier, not yet implemented; it slots alongside the other
off-CI trust tiers (attestation, trusted runner, device telemetry) described in
the [trust model](trust-model.md), and preserves the same invariants
(no APK in CI; device does no fetching).

## If a schema affordance is ever wanted

If a future phase wants to record provenance *metadata* on the map (e.g. a
source URL or an attestation reference — **not** a self-hash), it must be added
as an **optional** object so existing maps remain valid and strict clients that
do not yet know the key are only affected once they bump. Until a concrete need
exists, prefer the sidecar: it keeps the canonical artifact a clean map and
avoids the self-reference problem entirely.
