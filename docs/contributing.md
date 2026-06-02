# Contributing

The canonical, always-current contribution guide is
**[`CONTRIBUTING.md`](https://github.com/Xiddoc/rosetta-maps/blob/master/CONTRIBUTING.md)**
in the repository root. Read it before opening a PR — it covers the full workflow,
the provenance fields to record, and the licensing terms.

This page is a short orientation; the details (and any future changes) live in that
one file so there is a single source of truth.

## The shape of a contribution

Each PR adds (or extends) **one `(app, version_code)` map** so review and
provenance stay legible:

1. **Add or extend the signatures** under `signatures/<app>/signatures.yaml`,
   anchored on rotation-stable evidence so the rules survive a release rotation.
   Start from `templates/signatures.template.yaml`.
2. **Generate the map** for your specific `version_code` from the signatures + the
   APK, and write it to `maps/<app>/<version_code>.json`. If you hand-author, start
   from `templates/map.template.json` and validate locally against the canonical
   schema this repo owns.
3. **Record provenance** on the map using the schema fields — `sources[]`,
   per-class `source`/`confidence`, `signer_sha256`, and `captured_at`.
4. **Open the PR**, keeping it to a single `(app, version_code)` map plus any
   signatures it needs.

See the [trust model](reference/trust-model.md) for *why* the workflow looks like
this and what CI checks, and the [map schema](reference/schema.md) for the field
semantics.

## Licensing

By contributing you agree your signatures and maps are released under this repo's
[MIT license](https://github.com/Xiddoc/rosetta-maps/blob/master/LICENSE).
Contribute only names and structural metadata derived from your own analysis; do
not paste decompiled source. Full terms are in
[`CONTRIBUTING.md`](https://github.com/Xiddoc/rosetta-maps/blob/master/CONTRIBUTING.md).
