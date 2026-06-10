# Contribution templates

Copy these to start a contribution (see `CONTRIBUTING.md`):

| Template | Copy to | Purpose |
| --- | --- | --- |
| `map.template.json` | `maps/<app>/<version_code>.json` | the published map artifact (strict JSON, `schema_version: 4`) |
| `signatures.template.yaml` | `signatures/<app>/signatures.yaml` | the sigmatcher-dialect source of truth |

## No per-map integrity sidecar

A map is **data, not code**: the resolver only ever returns a member that
already exists in the already-loaded app, so a tampered map is at worst a
wrong-resolution / DoS bug, never code delivery (see
`docs/reference/integrity.md`). Transport integrity already comes from
git-over-HTTPS plus git's content-addressing, so a map needs **no** detached
`.sha256` digest sidecar (the earlier convention was removed in maps#37).

If you want to record a *reproduction* claim — that you rebuilt these exact map
bytes from the signatures + the APK and are willing to sign for it — use the
opt-in attestation sidecar (`<version_code>.json.att.json`, schema
`schema/rosetta-attestation.schema.json`); see
`docs/reference/trust-model.md`. Keep `signer_sha256` inside the map as the
functional version guard it is — it pins the app build the map was authored
against, not a security control.
