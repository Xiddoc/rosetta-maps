# Backups (Google-Drive `.daylio` archive + asset sync)

Confirmed against **version_code 252 and 267** (signatures verified on both).
Mapped: `BackupModule`, `BackupMetadata`, `BackupPersistenceModule`,
`AssetsSyncModule`, the four `*Worker` classes, `DriveServiceModule`,
`DriveQueryUtil`. **`BackupData` and `DriveBackupService` are documented below
but intentionally NOT mapped** — neither has a rotation-stable, non-obfuscated
anchor that survives across versions (`BackupData` was split between 252 and 267;
`DriveBackupService` is string-poor), so a single-version anchor would be a
liability. See [`maps/`](../../../maps/net.daylio/) and the signatures file.

## Archive format

A Daylio backup is a **ZIP** named `backup_<yyyy_MM_dd>.daylio`. Inside:

- `backup.daylio` — the payload: a JSON object containing **all DB tables plus a
  metadata header**, then **Base64-encoded (UTF-8)** and written as the file body
  (`BackupData.b(File)`). A raw-JSON variant exists (`BackupData.c(File)`).
- an optional `assets/` subtree (photos / audio).

There is **no app-level cryptography** — the only transform is Base64 + JSON.
Confidentiality relies entirely on Google Drive's private `appDataFolder`, not on
encryption. No native `.so` is involved in the backup path.

## Metadata header (`BackupMetadata`, JSON keys)

```
number_of_entries   created_at        is_auto_backup
platform ("android"/"ios")   android_version   ios_version
number_of_photos    photos_size
```

A sentinel empty instance means "no metadata"; restore aborts when it is seen.

## Restore flow (`BackupModule`, a state machine over interface `h8`)

1. Staging dir: `filesDir/backup_file/`. An imported archive is copied to
   `backup_temporary.daylio`.
2. If it is a ZIP it is extracted to `backup_to_import_unzipped/`, which **must**
   contain a `*.daylio` file — else `MalformedBackupException("Unzipped folder do
   not contain daylio file!")`.
3. The inner `*.daylio` is Base64-decoded → JSON; metadata is split off and
   validated. Guards:
   - archive **≥ 100 MiB (104857600)** → rejected (`"Backup file too big!"`)
   - missing metadata → `"Metadata are missing in backup!"`
4. Restore re-imports via `BackupPersistenceModule` (`b(json, cb)`), which
   rebuilds **every table** (moods, tags, entries, goals, reminders, writing
   templates, scales). The "anonymized"/demo export path swaps real media for
   `anonymized.jpeg` / `anonymized.mp4` placeholders.

`BackupPersistenceModule` also owns the `last_backup.json` scratch file and a
"days since last backup" helper.

## Asset (photo/audio) sync to Drive

`AssetsSyncModule` enqueues a WorkManager chain under the work name
**`assets_sync`**: `SyncAssetsWorker` is **always** the mandatory chain head;
`UploadAssetsToCloudWorker` and/or `DownloadAssetsFromCloudWorker` are
**conditionally** chained after it depending on pending up/down-sync flags (so
1–3 workers run, not always 3). Worker class names are **kept** (WorkManager
instantiates by name).

- `SyncAssetsWorker` — reconciles each asset's "in cloud" vs "on device" state,
  setting flags that trigger the upload/download workers.
- `UploadAssetsToCloudWorker` — uploads on-device assets missing from Drive.
- `DownloadAssetsFromCloudWorker` — pulls cloud assets absent on device.
- `AssetsSyncWorkerBase` — shared base: walks the Drive `appDataFolder` `assets/`
  tree via `DriveQueryUtil`, reports foreground-notification progress, and maps
  `GoogleAuthException` / `GoogleAuthIOException` into sign-in-required / retry /
  fail `Result`s.

## Google-Drive plumbing

- `DriveServiceModule` — GoogleSignIn restricted to OAuth scope
  `https://www.googleapis.com/auth/drive.appdata`; builds the Drive client
  labelled `"Daylio"`.
- `DriveQueryUtil` (`of.o3`) — static helpers to resolve/create files & folders
  inside the `appDataFolder` space by name
  (`'<parent>' in parents and name = '<name>'` queries).
- `DriveBackupService` (sole impl of interface `drive.d`) — the full Drive backup
  lifecycle: upload a `BackupData` archive, restore it, list available backups,
  download one by Drive file id, keep the last-backup timestamp, and trigger
  periodic cleanup of old Drive assets. Emits `drive_backup_*cleanup*` analytics.

## Out of scope / next threads

- The per-asset byte-transfer interface `assets.q` is implemented by
  `net.daylio.modules.photos.f` and `net.daylio.modules.audio.n` (photos/audio
  subsystems — not mapped here).
- `AssetsModule` (`assets.i`) — local asset file management; string-poor at the
  top level, so it needs a structural/member anchor (good thread:
  `photos_select_temp` / `photos_capture_temp` / `record_audio_temp` cleanup).
- The obfuscated interfaces (`h8`, `i8`, `drive.d`/`drive.e`, `assets.r`/`.s`/`.q`)
  are stringless; mapping them safely needs cross-class co-resolution with their
  impls.
- `BackupData` (`sd.b`) and `DriveBackupService` (`drive.a`) are **unmapped on
  purpose.** Both were originally pinned on fragile anchors (a cross-obfuscated-
  type conjunction; a method descriptor) that broke on 267 — `BackupData` was
  split into a stringless `{File, BackupMetadata}` holder, and `DriveBackupService`
  carries no top-level string literals. Re-mapping them needs a cross-class
  anchor (e.g. resolving their obfuscated interfaces alongside the impls).
