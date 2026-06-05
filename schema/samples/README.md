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
  one enforced constraint (empty `obfuscated` → `minLength: 1`, wrong
  `schema_version`, missing `version_code`, bad `app` pattern, a method
  missing its required `signature`, …). If a future schema edit silently
  loosens a constraint, the corresponding sample starts being accepted and
  the `validate.yml` "Schema accepts valid / rejects invalid samples" step
  fails.

The `check-jsonschema` step in `.github/workflows/validate.yml` enforces
both directions. The rosetta-frida (Zod) and rosetta-xposed (Kotlin)
client validators assert the same verdicts in their shared conformance
`validation.json` fixture, so the three hand-maintained copies of the
`schema_version: 2` format stay in lockstep.

## Adding a sample

- A new enforced constraint should get a matching `invalid/<constraint>.json`
  that violates only that constraint (keep everything else valid so the
  rejection is unambiguous), and — if it widens what is allowed — a
  `valid/` sample exercising the new shape.
- Keep samples tiny and provider-neutral (`com.example.app`).
