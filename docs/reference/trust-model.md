# Trust model & validation

rosetta-maps follows a layered, provenance-based trust model, in one line:

> **Attest with provenance, CI checks well-formedness, the device confirms
> correctness, reputation accrues over time.**

A contributed map is *verifiable* rather than merely trusted because it is
reproducible from its signatures + the APK. Trust is a gradient that accrues over
time, not a binary stamp.

## What CI checks

Public CI runs **structural validation only** (the first tier of the trust ladder):

- every map is valid against the canonical schema this repo owns
  (`schema/rosetta-map.schema.json`) — CI validates each map against that schema
  directly, with no cross-repo checkout and no drift-prone mirror to keep in sync;
- every `version_code` is present and **matches the filename**
  (`maps/<app>/<version_code>.json`);
- JSON descriptors parse and the file is well-formed — now enforced by the
  tier-1 map semantics check (`scripts/validate_map_semantics.py`), which
  verifies every method `signature` is a well-formed JVM descriptor, every
  app-internal type a descriptor or `field.type` references resolves within the
  same map, no two overloads collide, and the `app` field matches the parent
  directory.

CI also checks the **structure** of two detached sidecars when present (both are
opt-in, and both are separate files, never fields inside the map):

- a [`.sha256` integrity sidecar](integrity.md) binds the map's own bytes
  (`scripts/verify_map_sidecars.py`);
- a `.att.json` **reproduction-attestation** sidecar records and signs that a
  contributor reproduced the map (`scripts/validate_attestations.py`). This is
  the first higher trust tier — see [the trust ladder](#the-trust-ladder-precedence)
  below.

## What CI deliberately does not do

CI **never uploads or hosts an APK.** APK-host terms of service forbid automated
access, and hosting copyrighted APKs is a liability. Correctness against the real
app is established *off* public CI, via the higher tiers below.

### The trust ladder (precedence)

The tiers form a ladder; a higher tier **subsumes** the ones below it (a map that
passes tier 3 is at least as trusted as one that only passes tier 1), and **every
tier preserves the no-APK-in-public-CI invariant**:

| Tier | Name | What it proves | Where it runs |
| ---- | ---- | -------------- | ------------- |
| 0 | **Structural** (schema + semantics + `.sha256`) | the file is well-formed and its own bytes are intact | public CI |
| 1 | **Reproduction + signed attestation** | a human rebuilt these exact bytes from the signatures + APK and signed the claim | authored off-CI; its **structure** is checked in public CI |
| 2 | **Self-hosted trusted runner** | "CI with APK" re-derived the map on a legally-clean machine | a maintainer's runner (FOSS apps / owned devices) — *described, not yet implemented* |
| 3 | **Device-side health-check telemetry** | the adapters' attach-time health check passed against the live app | aggregated device reports — *described, not yet implemented* |

The deliverable here is **tier 1's format + its public-CI structural gate**; tiers
2–3 are described for their ladder position only.

### Tier 1 — reproduction + signed attestation

When a contributor reproduces a map from `signatures/<app>/signatures.yaml` + the
APK and wants to record that correctness claim, they commit a **detached
attestation sidecar** next to the map — **never** a field inside the map (the map
stays a clean `schema_version: 2` artifact; a self-referential trust field is
forbidden by the [AGENTS.md anti-scope](https://github.com/Xiddoc/rosetta-maps)
and would break the strict `additionalProperties: false` clients, exactly as for
the [`.sha256` integrity sidecar](integrity.md)):

```
maps/com.example.app/30405.json            ← the canonical, unchanged map
maps/com.example.app/30405.json.sha256     ← tier 0: bytes-integrity sidecar
maps/com.example.app/30405.json.att.json   ← tier 1: this attestation sidecar
```

**Format** — the canonical schema is
[`schema/rosetta-attestation.schema.json`](https://github.com/Xiddoc/rosetta-maps/blob/master/schema/rosetta-attestation.schema.json)
(`attestation_version: 1`). In one line: it records the map's identity
(`app`, `version_code`), the **`map_sha256`** that binds it to the exact committed
map bytes (the same digest the `.sha256` sidecar carries), `reproduced: true`, an
optional APK identity (**by hash only** — never a URL CI would fetch), and a
non-empty `attestations[]` list. Each attestation entry is a **detached signature
over the `map_sha256` digest** (`minisign` / `ssh-ed25519` / `gpg`) with the
signer's identity and date — so adding an attestor never rewrites the map and
reputation accrues across independent contributors.

**How it composes with the lower tiers** — the attestation's `map_sha256` is the
**same digest** the tier-0 `.sha256` sidecar binds, so the three artifacts chain:
the `.sha256` sidecar proves the bytes are intact, the attestation proves *who
reproduced those exact bytes and signed for it*, and the map itself stays
byte-identical and self-describing. A map may carry any subset (attestation is
**opt-in**); the tiers are independent files that never modify the map.

**What public CI checks (and deliberately does not)** —
[`scripts/validate_attestations.py`](https://github.com/Xiddoc/rosetta-maps/blob/master/scripts/validate_attestations.py)
validates only the sidecar's **structure** and that its `map_sha256` **binds the
committed map bytes** and that its `app`/`version_code` **match the attested map +
filename**. It is APK-free (Hard rule 3): it never fetches or hosts the APK, and
it does **not** cryptographically verify the signatures against a trusted keyring
— *signature-verification-against-a-keyring is itself a higher, off-CI step*.
Public CI thus answers "is this a well-formed attestation that actually binds this
map?", not "is this signer trusted?". A map with no `.att.json` is **skipped**, not
failed (opt-in rollout), and an orphaned `.att.json` (its map renamed/deleted) is
flagged.

### Tiers 2–3 (described only)

- **Optional self-hosted trusted runner** — "CI with APK" on a legally-clean
  machine (FOSS apps, or a maintainer's device). It re-derives the map and can
  emit a tier-1 attestation signed by the runner's key.
- **Device-side health-check telemetry** — the adapters' attach-time health check
  is the correctness oracle; aggregated pass/fail becomes a "verified-on
  `version_code` V" signal.

Each higher tier must preserve the **no-APK-in-public-CI** invariant.

One gap these tiers do not yet close is the map's **own-bytes** integrity (a
map is authenticated against the *app* via `signer_sha256`, never against the
publisher who shipped the file). See [map integrity](integrity.md) for why the
fix is a detached sidecar verified at build time — not a self-hash field inside
the map.

## Schema ownership

This repo owns the **canonical map schema** — the single, language-neutral source
of truth for the `schema_version: 2` format. The format belongs with the data, and
the data lives here. The [rosetta-frida](https://github.com/Xiddoc/rosetta-frida)
(TypeScript) and [rosetta-xposed](https://github.com/Xiddoc/rosetta-xposed)
(Kotlin) adapters are **clients** that track this schema; rosetta-frida is the
first-class client. Changing the format means bumping this schema first, then the
adapters — never a fork or a mirror in the other direction. See the
[map schema](schema.md) page for details.
