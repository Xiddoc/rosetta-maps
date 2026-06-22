# Instagram — App Shape, Obfuscation Profile & Anchor Strategy

**App:** `com.instagram.android` (Instagram for Android)
**version_code:** `383909338`  **versionName:** `433.0.0.47.68`
**minSdk:** 28  **targetSdk:** 36
**signer SHA-256:** `44c3bb8c7ea35b3bb11cbfa3c2f5879240df2e49e39816b4437b9856fbb29541`

Decompiled trees analyzed (read-only, never committed — Hard rule 3):
- jadx Java: `/home/user/apk-workspace/out/jadx/sources/` (167,899 `.java`)
- apktool smali: `/home/user/apk-workspace/out/apktool/` — **19 dex files**;
  dex map: `smali` = `classes.dex`, `smali_classes2` = `classes2.dex`, …
  `smali_classes19` = `classes19.dex`.

## Package surface

The APK is enormous: **19 `classes*.dex`**, ~16,400 zip entries, and **257
top-level packages** under `com/instagram/`. The manifest declares **499
activities, 103 services, 65 receivers, 21 content providers**. Roughly 7,160
smali files keep a readable `com/instagram/*` name.

Native libraries (`lib/arm64-v8a/`) include the usual Meta runtime: `libbreakpad`
/ `libfbunwindstack` (crash reporting), `libsuperpack-jni` + `assets/lib/libs.spo`
(Superpack-compressed secondary dex/native payload), `libarcore_sdk_*` (ARCore),
`libgraphics-core`, `liblibyuv`/`libimage_processing_util_jni` (media). Most
feature logic is Java/Kotlin in the dex; the heavy messaging/calling engines are
native (MSYS / RSYS) reached through thin JNI bridge classes.

## Obfuscation profile

Instagram uses **R8 + Meta's redex** with a distinctive posture:

1. **Class names are mostly KEPT.** `com.instagram.*` package and class names
   survive — entry points, repositories, API classes, providers, services,
   models. This makes class *identity* easy to confirm.
2. **Members are rotated to the `A00/A01/A02…` scheme.** Fields and private
   methods become `A0x`; framework overrides (`onCreate`, `onDraw`, `onTransact`,
   `<init>`) keep their real names. So member names are worthless as anchors and
   rotate every release.
3. **A subset of classes is fully renamed into the top-level `X/` package**
   (e.g. `FriendMapFragment → X/T0K`, `MapLocationManager → X/ju1`). These keep
   their original name in a **`__redex_internal_original_name:Ljava/lang/String;`
   static field** — redex writes the real class name there verbatim, which is a
   gold rotation-stable anchor for the renamed layer.
4. **Server-contract strings are everywhere and stable.** GraphQL
   persisted-operation names (`IG…Query`/`…Mutation`) and their `xdt_*` / `xig_*`
   / `xfb_*` doc/API names are compiled in as literals. They cannot rotate — the
   client must send the exact bytes the backend registered — so they are the
   single best anchor class for this app.

## Anchor strategy used (see `signatures.yaml`)

Every signature pins on one of, in rough order of preference:

- **GraphQL operation / doc names** (`"xdt_get_all_presence_points"`,
  `"IGCreateCustomAIVoiceEffectMutation"`) — server contract, never rotates.
- **AIDL / cross-process binder descriptors & fully-qualified action constants**
  (`"com.instagram.direct.stella.api.IStellaDirectMessagingService"`,
  `"com.instagram.rtc.connection.connection_id"`).
- **`__redex_internal_original_name = "…"`** — recovers the `X/`-renamed classes.
- **Full-sentence log/error literals** (`"Unable to make outgoing call"`,
  `"Call ended/left before participants models set by rsys"`).
- **`toString()` prefixes on data models** (`IgCallModel{inCallState=`).
- **SharedPreferences keys** (`"quick_snap_last_updated_app_id"`).

A practical sigmatcher rule learned here: with `count` omitted, a signature must
match **exactly once app-wide**; a literal that repeats in its class needs an
explicit `count`, and a literal shared across classes needs a second AND-ed
anchor or must be dropped. All 48 shipped rules were tuned to resolve to exactly
one class on this APK.

## What is NOT mapped (and why)

- **Members** (methods/fields). They are `A0x`-rotated; mapping them durably
  needs per-member stable anchors that mostly don't exist, and they change every
  release. The map is deliberately **class-level** — that is the verifiable,
  durable identity. Hook points are described in the feature docs by behaviour.
- **Pure-UI / Compose split classes and `X/`-only helpers without a stable
  literal** — identifiable by name in this build but not anchorable across
  versions, so they are documented in prose but kept out of the signatures.
