# Trust model & validation

rosetta-maps follows the trust model from
[RFC 0001](https://github.com/Xiddoc/rosetta-frida/blob/master/docs/rfcs/0001-unified-cross-framework-signatures.md)
Decision 4, in one line:

> **Like a CVE database — attest with provenance, CI checks well-formedness, the
> device confirms correctness, reputation accrues over time.**

A contributed map is *verifiable* rather than merely trusted because it is
reproducible from its signatures + the APK. Trust is a gradient that accrues over
time, not a binary stamp.

## What CI checks

Public CI runs **structural validation only** (RFC 0001 Decision 4, tier 1):

- every map is valid against the canonical schema this repo owns
  (`schema/rosetta-map.schema.json`) — CI validates each map against that schema
  directly, with no cross-repo checkout and no drift-prone mirror to keep in sync;
- every `version_code` is present and **matches the filename**
  (`maps/<app>/<version_code>.json`);
- JSON descriptors parse and the file is well-formed.

## What CI deliberately does not do

CI **never uploads or hosts an APK.** APK-host terms of service forbid automated
access, and hosting copyrighted APKs is a liability. Correctness against the real
app is established *off* public CI, via the planned higher tiers:

- **Reproduction + signed attestation** (planned) — independent contributors
  reproduce the map from the signatures and sign the result; only the attestation
  enters the repo, never the APK.
- **Optional self-hosted trusted runner** (planned) — "CI with APK" on a
  legally-clean machine (FOSS apps, or a maintainer's device).
- **Device-side health-check telemetry** (planned) — the adapters' attach-time
  health check is the correctness oracle; aggregated pass/fail becomes a
  "verified-on `version_code` V" signal.

Each higher tier must preserve the **no-APK-in-public-CI** invariant.

## Schema ownership

This repo owns the **canonical map schema** — the single, language-neutral source
of truth for the `schema_version: 2` format. The format belongs with the data, and
the data lives here. The [rosetta-frida](https://github.com/Xiddoc/rosetta-frida)
(TypeScript) and [rosetta-xposed](https://github.com/Xiddoc/rosetta-xposed)
(Kotlin) adapters are **clients** that track this schema; rosetta-frida is the
first-class client. Changing the format means bumping this schema first, then the
adapters — never a fork or a mirror in the other direction. See the
[map schema](schema.md) page for details.
