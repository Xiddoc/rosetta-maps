# signatures/

The **source of truth**. sigmatcher rules (the offline / host dialect:
regex-over-smali) that identify a class/method across versions. A map under
`../maps/` is *reproducible* from these signatures + the APK — which is what
makes a contributed map verifiable rather than just trusted.

## Layout

```
signatures/<app>/signatures.yaml
```

One file per app. Signatures are **multi-version on purpose**: anchor on
rotation-stable evidence so the same rules resolve across point releases
even as obfuscated names rotate. Generic-first — these work for any class
and are the default:

1. stable `static final String` literals reached by live code;
2. stable framework superclass / interface references;
3. cross-class anchors (a resolved class's descriptor referenced elsewhere);
4. AIDL descriptor strings — a lucky special case *when present* (a `.Stub`
   embeds its binder descriptor verbatim), but most classes have no AIDL
   contract, so it is the exception, not the rule.

This anchoring evidence is **authoring input only** — it identifies a class in
the source, and is not copied into the published map (a pure real→obfuscated
mapping at `schema_version: 5`).

## Two dialects, no third

sigmatcher YAML (here, offline/readable) and DexKit queries (on-device,
runtime) are the only two dialects — split by *execution context*, not by
app or framework. DexKit fingerprints are harvested **one-time** into this
sigmatcher form; the convergence point is the resolved map, not a unified
signature IR.

Start from `../templates/signatures.template.yaml`.

## Validation

CI lints every `signatures/<app>/signatures.yaml` for the minimal
sigmatcher-dialect structure (required top-level keys; known rule, member,
and signature shapes) via `scripts/lint_signatures.py` — the source-of-truth
counterpart to the schema check that guards `../maps/`. It reads only the
committed YAML (never an APK), so it preserves the no-APK CI invariant. Run
it locally before opening a PR:

```bash
python3 scripts/lint_signatures.py signatures/<app>/signatures.yaml
python3 scripts/lint_signatures.py --self-test   # exercise the linter itself
```
