# Orientation

Confirmed against **version 1.63.12 / version_code 252**.

## App shape

- Package `net.daylio`; minSdk 26, targetSdk 35, compileSdk 36.
- 2 dex (`classes.dex`, `classes2.dex`); 2 ABIs (`arm64-v8a`, `armeabi-v7a`).
- Natives: `amplituda` (ffmpeg-derived `avcodec`/`avformat`/`avutil`/`swresample`
  — audio-waveform rendering for voice-memo entries) + `datastore_shared_counter`.
- 141 activities, 11 services, 30 receivers, 4 providers, 24 permissions.

## Obfuscation profile (R8)

The usual R8 carve-out: classes the framework instantiates by name keep their
names; everything else is renamed to short tokens, but the package **path**
`net.daylio.*` is preserved even where the class name is rotated.

- **Kept names:** `MyApplication`, the `net.daylio.activities.*` activities,
  receivers, WorkManager workers (instantiated by name) — and most third-party
  packages that ship consumer keep-rules (`com.google.*`, `androidx.*`, Glide).
- **Renamed:** the bulk of Daylio's own logic. Even inside `net.daylio.*`, ~182
  of 657 classes have 1–2 letter names. The service layer lives in
  `net.daylio.modules.*` as single-letter classes behind obfuscated interfaces
  (e.g. backup is `m implements h8`). Generated/relocated helpers (ViewBindings,
  etc.) are minified into short top-level packages (`ef`, `kg`, `sd`, `md`, …).

These renamed service classes are why the map exists: their short names rotate
between releases, so we pin them on rotation-stable evidence.

## Entry points

- **Application:** `net.daylio.MyApplication` (named in the manifest).
- **Launcher:** `net.daylio.activities.OverviewActivity` (the home / overview
  screen; MAIN/LAUNCHER).

## Architecture: the `modules` service layer

`net.daylio.modules.*` is a service-locator world. Modules are singletons behind
obfuscated interfaces, fetched through a locator (`vb`, seen as
`vb.b().<accessor>()` at call sites). A Rosetta hook generally wants the concrete
module class (mapped) or the interface method it exposes.

## Persistence — Room (`net.daylio.db.room`)

Abstract `@Database` class `RoomDatabase` + generated `RoomDatabase_Impl`. The
schema (from the generated `CREATE TABLE` statements) is 12 tables:

```
table_entries              table_moods             table_tags
table_tag_groups           table_assets            table_entries_with_assets
table_entries_with_tags    table_scales            table_number_scales
table_text_scales          table_entry_to_scale_value   table_text_scale_value
```

Not mapped as a class: Room repeats the schema strings across ~6 generated
classes, so there is no single clean anchor — the schema is captured here
instead. Useful as orientation for the backup/export serializers, which walk
these same tables.
