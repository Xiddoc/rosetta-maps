# Quickstart — using a map

Each map is one file per `(app, version_code)`. The `version_code` is the
authoritative selection key, so it **is** the filename:

```
maps/<app>/<version_code>.json
```

Grab the file for your installed `version_code` and load it like any other Rosetta
map.

## rosetta-frida (TypeScript)

```typescript
import { rosetta } from 'rosetta-frida';
import map from 'rosetta-maps/maps/com.example.app/30405.json' with { type: 'json' };

rosetta.session({ map });
```

## rosetta-xposed (Kotlin)

```kotlin
val rosetta = RosettaXposed.fromMap(MapLoader.fromJson(mapJson), classLoader)
```

Runtime auto-fetch by `(app, version_code)` is on the adapters' roadmap; until
then, vendor the file you need.

## Finding your version_code

`<version_code>` is the full Android `longVersionCode` (`(versionCodeMajor << 32) | versionCode`), never masked. If a map for your exact version is missing, that is the cue to
[contribute one](contributing.md): extend the signatures, regenerate, and open a
PR.

## The worked example

`maps/com.example.app/30405.json` is a feature-complete example map — it exercises
overloads, enums, fields, and (as one special case) AIDL stubs/callbacks, generated
from `signatures/com.example.app/signatures.yaml`. Copy it (and the matching
signatures) as the starting point for a real contribution.

## Anchoring evidence types

Signatures pin each class on the most **rotation-stable** evidence available, so
the same rule resolves across adjacent point releases even as obfuscated names
rotate. The taxonomy is generic-first — these work for any class and are the
default:

- **String literals** — endpoint URLs, log tags, `static final String`
  constants, field/key names reached by live code. The everyday anchor.
- **Superclass / framework parent** — an obfuscated class still `extends` a
  non-rotating `android` / `androidx` / `java` parent (or implements a stable
  interface).
- **Constants** — a `static final` value or magic number a class carries.
- **Structural / cross-class** — a resolved class's descriptor referenced
  elsewhere, or a distinctive method-table shape.
- **AIDL / Binder descriptor** — a niche special case *when present*: a `.Stub`
  embeds its binder descriptor string verbatim and it never rotates, but most
  classes have no AIDL contract, so it is the exception, not the rule.

This is authoring guidance, not a format spec — the on-disk fields live in the
[map schema](reference/schema.md), the single source of truth.
