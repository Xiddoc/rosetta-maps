# Contribution templates

Copy these to start a contribution (see `CONTRIBUTING.md`):

| Template | Copy to | Purpose |
| --- | --- | --- |
| `map.template.json` | `maps/<app>/<version_code>.json` | the published map artifact (strict JSON, `schema_version: 2`) |
| `map.template.json.sha256` | `maps/<app>/<version_code>.json.sha256` | the optional detached integrity sidecar (see below) |
| `signatures.template.yaml` | `signatures/<app>/signatures.yaml` | the sigmatcher-dialect source of truth |

## The detached `.sha256` integrity sidecar

A map carries no hash OF ITSELF — a self-hash can't live in the file it hashes,
and a new field would break the strict `additionalProperties: false` clients
(see `docs/reference/integrity.md`). Instead a map's own-bytes integrity is
bound from **outside** the artifact by a detached sidecar that sits next to it:

```
maps/com.example.app/30405.json          ← the canonical, unchanged map
maps/com.example.app/30405.json.sha256   ← the detached digest sidecar
```

**Format** (coreutils `sha256sum`): UTF-8 text, one line ending in a single
`\n`, holding the lowercase 64-hex SHA-256 of the **exact map bytes**, two
ASCII spaces, then the bare map filename (basename, no directory):

```
991b91841128bc28322ed485ad3fa9b4b69ec397ff39809e109170738cd000c5  30405.json
```

This makes `sha256sum -c 30405.json.sha256` work directly from the map's
directory.

**The sidecar is OPTIONAL during rollout.** A map with no sidecar is not a CI
failure; only a *present* sidecar that fails to verify is. The tier is
**transport integrity** (it catches a corrupted/tampered map in transit), not
publisher authenticity — a future detached `.json.sig` signature can be layered
on without changing this format.

**Generate it from the real bytes — never hand-type the digest.** From the
map's directory:

```bash
sha256sum 30405.json > 30405.json.sha256
```

CI verifies every present sidecar with `scripts/verify_map_sidecars.py`, which
implements the exact algorithm the `rosetta pull` clients use; see
`docs/reference/integrity.md`.
