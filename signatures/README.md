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
even as obfuscated names rotate. In rough order of robustness:

1. AIDL descriptor strings (never rotated by R8);
2. stable `static final String` literals reached by live code;
3. stable framework superclass / interface references;
4. cross-class anchors (a resolved class's descriptor referenced elsewhere).

## Two dialects, no third

sigmatcher YAML (here, offline/readable) and DexKit queries (on-device,
runtime) are the only two dialects — split by *execution context*, not by
app or framework. DexKit fingerprints are harvested **one-time** into this
sigmatcher form; the convergence point is the resolved map, not a unified
signature IR.

Start from `../templates/signatures.template.yaml`.
