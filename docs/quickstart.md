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
AIDL stubs/callbacks, overloads, enums, and fields, generated from
`signatures/com.example.app/signatures.yaml`. Copy it (and the matching signatures)
as the starting point for a real contribution.
