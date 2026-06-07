# Schema drift-guard samples

These are **not** published maps (they live under `schema/`, not `maps/`,
and are excluded from the `maps/**/*.json` validation globs). They exist
solely to pin the canonical schema's enforced constraints in BOTH
directions, closing the systemic drift gap that let earlier divergences
through:

- **`valid/`** — minimal and fuller maps that MUST validate against
  `schema/rosetta-map.schema.json`. If a future schema edit accidentally
  tightens a constraint, one of these starts failing.
- **`invalid/`** — maps that MUST be **rejected**, each violating exactly
  one enforced constraint. The set pins, in both directions, every enforced
  constraint of the canonical schema:
    - empty `obfuscated` → `minLength: 1` (`empty-{class,method,field}-obfuscated`)
    - wrong `schema_version` → the `const: 2` hard gate (`wrong-schema-version`)
    - missing `version_code` (`missing-version-code`)
    - negative `version_code` → `minimum: 0` (`negative-version-code`)
    - over-2^53 `version_code` → `maximum: 9007199254740991` (`version-code-too-large`),
      paired with the 2^32 `valid/version-code-wide.json` accept
    - bad `app` pattern (`bad-app-pattern`)
    - empty `version` → `minLength: 1` (`empty-version`)
    - whitespace-only `version` → the `\S` pattern (`whitespace-version`),
      tightening `version` beyond mere non-emptiness
    - malformed (uppercase-hex) `signer_sha256` → `pattern: ^[0-9a-f]{64}$`
      (`bad-signer-sha256`), paired with the `valid/signer-sha256.json` accept
    - colon-separated `signer_sha256` → same `pattern` rejects the
      `AB:CD:…` certificate-fingerprint form (`signer-sha256-colons`); the
      canonical on-disk form is lowercase, NO colons, exactly 64 hex chars
    - a reserved `classes` key → `propertyNames` rejects `__proto__` /
      `constructor` / `prototype` (`reserved-class-key`)
    - a method missing its required `signature` (`method-missing-signature`)
    - a field missing its required `type` (`field-missing-type`) — the
      symmetric twin of `method-missing-signature`
    - a bad `kind` enum value → `classKind` enum (`bad-class-kind`)
    - a bad `confidence` enum value → `confidence` enum (`bad-confidence`)
    - an unknown / typo'd top-level key → `additionalProperties: false`
      (`unknown-top-level-key`, a `signer_sh256` typo)
    - an unknown / typo'd class-entry key → `additionalProperties: false`
      on `classEntry` (`unknown-class-key`, an `extneds` typo)
    - the `frida_*` hints at the top level → they now live ONLY under
      `client_hints`, so a top-level `frida_min_version` is rejected by
      `additionalProperties: false` (`frida-version-top-level`), paired
      with the `valid/client-hints.json` accept

  If a future schema edit silently loosens a constraint, the corresponding
  sample starts being accepted and the `validate.yml` "Schema accepts valid /
  rejects invalid samples" step fails.

### Constraints intentionally NOT pinned by a per-constraint sample

Some enforced constraints are deliberately **not** given their own
`invalid/` sample here, because doing so would require an unreasonably
bulky fixture and the constraint is already pinned by the client
validators' `bounds.json` parity fixture (carried byte-identical in
rosetta-frida `tests/conformance/fixtures/bounds.json` and rosetta-xposed
`core/src/test/resources/conformance/bounds.json`). Pinning them there
keeps the maps samples tiny while still guarding against drift:

- **`maxLength` caps** on string fields (`app` 256, `version` 256,
  `obfuscated` 512, `signature`/`type`/`notes`/etc. 4096) — a reject
  sample would need a multi-kilobyte string literal.
- **Cardinality caps** — `classes.maxProperties` (50000),
  `methods`/`fields.maxProperties` (5000), `anchors.maxItems` (1000),
  `sources.maxItems` (100), overload-array `maxItems` (200) — a reject
  sample would need to enumerate tens of thousands of entries.

These are scoped out of the maps samples on purpose; the `bounds.json`
parity fixture is the place to extend if a cap changes.

The `check-jsonschema` step in `.github/workflows/validate.yml` enforces
both directions. The rosetta-frida (Zod) and rosetta-xposed (Kotlin)
client validators assert the same verdicts in their shared conformance
`validation.json` fixture, so the three hand-maintained copies of the
`schema_version: 2` format stay in lockstep. (Note: the `signer_sha256`
format is enforced by the full schema and by the Frida Zod / Xposed
`SignerGuard` paths, but NOT by the Xposed `:core` `MapLoader.validate`
that the shared `validation.json` fixture runs through — so the signer
regex is pinned by these maps samples, not by the shared conformance
fixture. The constraints the shared fixture pins are the ones BOTH core
validators enforce: `schema_version`, `app` pattern, `version`
non-empty, `version_code` width, `obfuscated` non-empty, and reserved
keys.)

## Adding a sample

- A new enforced constraint should get a matching `invalid/<constraint>.json`
  that violates only that constraint (keep everything else valid so the
  rejection is unambiguous), and — if it widens what is allowed — a
  `valid/` sample exercising the new shape.
- Keep samples tiny and provider-neutral (`com.example.app`).
