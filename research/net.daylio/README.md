# net.daylio — research notes

Findings from tearing apart **Daylio** (`net.daylio`) for Rosetta. These are the
human-readable *what-the-code-does* notes that sit behind the machine artifacts:

- **Authoritative name mapping** → [`maps/net.daylio/<version_code>.json`](../../maps/net.daylio/)
- **Source-of-truth signatures** → [`signatures/net.daylio/signatures.yaml`](../../signatures/net.daylio/signatures.yaml)
- **These notes** → behaviour, flows, file formats, hook points.

Notes reference classes by their **logical** name (e.g. `BackupModule`); the
obfuscated name for a given `version_code` lives in the map. Where an obfuscated
token aids navigation it's given in parentheses, pinned to the version stated in
each doc's header.

## Index

| Doc | Subsystem |
| --- | --- |
| [`docs/orientation.md`](docs/orientation.md) | App shape, obfuscation profile, entry points, Room schema |
| [`docs/backups.md`](docs/backups.md) | Google-Drive `.daylio` archive backup/restore + asset sync |
| [`docs/exports.md`](docs/exports.md) | User-facing CSV / PDF data export |
| [`docs/premium.md`](docs/premium.md) | Billing, the is-premium gate, restore, special offers |

## Provenance

Produced by the `apk-research` skill: apktool + jadx decompile, search-first
investigation, sigmatcher-verified signatures, peer-reviewed. Each doc states the
`version_code` it was confirmed against — obfuscated names rotate between
releases, behaviour and anchors are the stable part.

The signatures are **multi-version-hardened**: verified to resolve on both
`version_code` 252 (1.63.12) and 267 (1.65.5), which is why there is a map per
version under [`maps/net.daylio/`](../../maps/net.daylio/). Anchors that couldn't
survive the rotation were re-anchored on stable evidence or dropped (see
[`docs/backups.md`](docs/backups.md)).
