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
    - malformed (uppercase-hex) `signer_sha256` → `pattern: ^[0-9a-f]{64}$`
      (`bad-signer-sha256`), paired with the `valid/signer-sha256.json` accept
    - a reserved `classes` key → `propertyNames` rejects `__proto__` /
      `constructor` / `prototype` (`reserved-class-key`)
    - a method missing its required `signature` (`method-missing-signature`)

  If a future schema edit silently loosens a constraint, the corresponding
  sample starts being accepted and the `validate.yml` "Schema accepts valid /
  rejects invalid samples" step fails.

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
