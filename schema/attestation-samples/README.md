# Attestation-schema drift-guard samples

These pin the canonical **attestation** schema
(`schema/rosetta-attestation.schema.json`) in BOTH directions, exactly like
`schema/samples/` does for the map schema. They are **not** attestation
sidecars for any real map (they live under `schema/`, not `maps/`, and are
excluded from the `maps/**` globs) — they exist solely so a future schema edit
can't silently loosen a constraint.

The attestation sidecar is the **reproduction + signed attestation** artifact
(maps#18): a detached file beside a map (`<version_code>.json.att.json`) that
records that a contributor reproduced the map from its signatures + the APK and
signed the result. It is never a field inside the map (AGENTS.md anti-scope: no
self-referential trust field). See `docs/reference/trust-model.md`.

- **`valid/`** — a `full` sample (multiple attestors, optional `apk` /
  `signatures_sha256`) and a `minimal` sample (only the required keys), both of
  which MUST validate against the attestation schema.
- **`invalid/`** — each violates exactly one enforced schema constraint:
    - `wrong-attestation-version` → the `attestation_version` `const: 1` gate
    - `missing-map-sha256` → required `map_sha256`
    - `bad-map-sha256` → `map_sha256` `pattern: ^[0-9a-f]{64}$`
    - `reproduced-false` → the `reproduced` `const: true` gate
    - `empty-attestations` → `attestations` `minItems: 1`
    - `unknown-method` → the attestation `method` enum
    - `attestation-missing-signature` → required per-attestation `signature`
    - `bad-signed-at` → the `signed_at` date pattern
    - `unknown-top-level-key` → top-level `additionalProperties: false` (a
      trust field that tried to leak into the artifact)
    - `unknown-apk-key` → `apk.additionalProperties: false` (e.g. a download
      `url` CI must never fetch)
    - `apk-missing-sha256` → `apk.required: ["sha256"]` (an `apk` object with
      only `signer_sha256` / `source` and no `sha256`)
    - `apk-not-object` → `apk` `type: object` (a bare string where the object
      is required)
    - `bad-app-pattern` → the `app` dotted-package pattern
    - `negative-version-code` → `version_code` `minimum: 0`

`.github/workflows/validate.yml` enforces both directions (every `valid/` MUST
pass, every `invalid/` MUST be rejected) against
`schema/rosetta-attestation.schema.json`. The SEMANTIC constraints the schema
can't express — that `map_sha256` binds the committed map bytes, and that
`app` / `version_code` agree with the attested map and its filename — are pinned
by `scripts/validate_attestations.py --self-test`.

## Adding a sample

- A new enforced schema constraint should get a matching
  `invalid/<constraint>.json` that violates only that constraint (keep
  everything else valid so the rejection is unambiguous), and — if it widens
  what is allowed — a `valid/` sample exercising the new shape.
- Keep samples tiny and provider-neutral (`com.example.app`).
