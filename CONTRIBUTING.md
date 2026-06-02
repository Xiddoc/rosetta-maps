# Contributing to rosetta-maps

Thank you for helping build the shared obfuscation knowledge base. This
repo follows the trust model from
[RFC 0001](https://github.com/Xiddoc/rosetta-frida/blob/master/docs/rfcs/0001-unified-cross-framework-signatures.md)
Decision 4, in one line:

> **Like a CVE DB — attest with provenance, CI checks well-formedness, the
> device confirms correctness, reputation accrues over time.**

## What goes where

| Path | Artifact | Role |
|---|---|---|
| `signatures/<app>/signatures.yaml` | sigmatcher rules | **source of truth** — reproducible, FOSS-correct |
| `maps/<app>/<version_code>.json` | resolved map | **published artifact** — consumed by Frida & Xposed |
| `templates/` | starting points | copy these |
| `schema/rosetta-map.schema.json` | JSON Schema | **canonical schema** — owned here; CI validates against it |

A map's filename **is** its `version_code` — the authoritative O(1)
selection key (RFC 0001 Decision 3). `maps/com.example.app/30405.json`
holds the map whose `"version_code": 30405`. CI enforces this.

## Submitting a contribution

1. **Add or extend the signatures** for the app under
   `signatures/<app>/signatures.yaml`. Anchor on rotation-stable evidence
   (AIDL descriptor strings, stable string literals, framework superclass
   refs) so the rules survive a release rotation. Start from
   `templates/signatures.template.yaml`.

2. **Generate the map** for the specific `version_code` you have, from the
   signatures + the APK — e.g. with the sigmatcher adapter and
   `rosetta convert` from the rosetta-frida toolchain — and write it to
   `maps/<app>/<version_code>.json`. If you're hand-authoring, start from
   `templates/map.template.json` and validate locally against the canonical
   schema this repo owns:

   ```sh
   npx ajv-cli@5 validate --strict=false \
       -s schema/rosetta-map.schema.json \
       -d maps/<app>/<version_code>.json
   ```

3. **Record provenance** on the map. Use the existing schema fields rather
   than free text where possible:
   - `sources[]` — which tool(s) produced which entries (`tool`, `config`,
     `classes`, `confidence`, `notes`).
   - per-class `source` and `confidence`.
   - `signer_sha256` — the lowercase-hex SHA-256 of the signing
     certificate, if you read it. This pins publisher authenticity and
     detects repacks.
   - `captured_at` — the date you captured it.

4. **Open a PR.** Keep each PR to a single `(app, version_code)` map (plus
   any signatures it needs) so review and provenance stay legible.

## What CI checks (and what it deliberately does not)

CI runs **structural validation only** — RFC 0001 Decision 4, tier 1:

- valid against the canonical schema this repo owns
  (`schema/rosetta-map.schema.json`), checked with `ajv` — no cross-repo
  checkout, no mirror to drift;
- every `version_code` is present and **matches the filename**;
- JSON descriptors parse and the file is well-formed.

CI **never uploads or hosts an APK.** APK-host terms of service forbid
automated access, and hosting copyrighted APKs is a liability. Correctness
against the real app is established *off* public CI:

- **Reproduction + signed attestation** (planned) — independent
  contributors reproduce the map from the signatures and sign the result;
  only the attestation enters the repo, never the APK.
- **Optional self-hosted trusted runner** (planned) — "CI with APK" on a
  legally-clean machine (FOSS apps, or a maintainer's device).
- **Device-side health-check telemetry** (planned) — the rosetta libraries'
  attach-time health check is the correctness oracle; aggregated pass/fail
  becomes a "verified-on `version_code` V" signal. `confidence` is a
  gradient, not a binary.

## Signatures are the source; don't invent a third format

We use exactly two signature dialects, split by execution context (RFC 0001
Decision 5): **sigmatcher YAML** (offline/host, lives here) and **DexKit
queries** (on-device/runtime, harvested one-time into sigmatcher form). Do
not propose a new "unified" signature IR — the convergence point is the
resolved **map**, not the signature.

## Licensing

By contributing you agree your signatures and maps are released under this
repo's [MIT license](LICENSE). Contribute only names and structural
metadata derived from your own analysis; do not paste decompiled source.
