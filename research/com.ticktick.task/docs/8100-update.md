# TickTick 8.1.0.0 (version_code 8100) — map refresh + new anchors

Findings from refreshing `com.ticktick.task` against a fresh APK
(`versionName 8.1.0.0`, `versionCode 8100`, signer cert SHA-256
`44c3bb8c…b29541` — unchanged from 8080/8081). The authoritative
real→obfuscated mapping lives in `maps/com.ticktick.task/8100.json`; the
regex anchors live in `signatures/com.ticktick.task/signatures.yaml`. This doc
only records *what was found*, not the name table.

## Provenance

- APK arrived as a 2-volume RAR (`TickTick_signed.part1/2.rar`) → `unar` →
  `TickTick_signed.zip` → `TickTick_signed.apk` (5 dex, ~41 MB).
- Decompiled with apktool 3.0.2 (smali, ground truth for sigmatcher) and
  jadx 1.5.5 (Java, for reading). 109/21970 classes failed in jadx — normal
  for R8 output.

## Map refresh — all 66 prior rules still resolve

`sigmatcher analyze` against 8100 resolved **all 66** original rules with zero
failures/ambiguities. Six obfuscated helpers **rotated their tokens** between
8081 and 8100 — every anchor tracked the rotation, which is the portability
proof the signature set exists for:

| class (real)            | 8081  | 8100  |
| ----------------------- | ----- | ----- |
| `ApiFactoryBase`        | w7.b  | w7.a  |
| `GsonApiFactory`        | w7.c  | w7.b  |
| `LoginHandler`          | j8.m  | j8.l  |
| `TwoFactorLoginHandler` | j8.n  | j8.m  |
| `TickTickAuthorizeTask` | cf.g  | cf.h  |
| `AiComplete`            | q9.x0 | q9.t0 |

Note the shuffle inside the `w7.*` and `j8.*` namespaces: `w7.b` is
`ApiFactoryBase` in 8081 but `GsonApiFactory` in 8100; `j8.m` is `LoginHandler`
in 8081 but `TwoFactorLoginHandler` in 8100. The obfuscated token is worthless
across versions — the in-body anchor is the identity.

## Six new anchors (the "interesting classes")

All six live in the readable `com.ticktick.task.*` carve-out, so they resolve
to themselves on 8100 (kept names). They are not rotation wins; they are
**high-value hook targets** the map now certifies, each anchored on a
rotation-stable in-body literal verified globally unique on 8100. Identity was
confirmed by reading the class, not guessed from a string.

- **`TickTickApplicationBase`** (`com.ticktick.task`) — the app singleton
  (`extends android.app.Application`). `getInstance()` is the process-wide
  handle to the task/account managers and sync; the canonical attach-time hook
  target. Anchored on a widget-broadcast log literal (the `TAG` literal recurs
  as both a `.field` constant and a `const-string`, so it is not a count==1
  anchor).
- **`SettingsPreferencesHelper`** (`.helper`) — central `SharedPreferences`
  façade (`implements OnSharedPreferenceChangeListener`); every app-wide
  toggle/flag funnels through it.
- **`TaskService`** (`.service`) — GreenDAO service for the core `Task2`
  entity; the create/update/delete/query chokepoint, incl. assignee /
  team-project checks.
- **`AttachmentService`** (`.service`) — attachment persistence (local file ↔
  `Attachment` entity, invalid-file cleanup).
- **`AttendeeService`** (`.service`) — attendee / task-sharing persistence.
- **`AESUtils`** (`.utils`) — local AES helper: `AES/ECB/PKCS5Padding`, key
  right-padded with `'0'` to 32 bytes (see `createKey`). A prime hook point for
  reading at-rest plaintext. No inner classes, so its retained SourceFile
  (`"AESUtils.java"`) is a safe count==1 anchor.

### Anchoring gotcha worth remembering

For kept-name classes the retained SourceFile (`"Foo.java"`) is tempting, but
R8 emits the same `.source` directive into every **inner** class smali, so a
SourceFile anchor is ambiguous (`count > 1`) whenever the class has inner
classes. `SettingsPreferencesHelper.java` hit in 11 files,
`TickTickApplicationBase.java` in 14 — both unusable as count==1. The fix used
here: anchor on a business-string literal that occurs exactly once in the
target class. SourceFile is only safe for inner-class-free classes like
`AESUtils`.

Also: a `static final String` constant (e.g. a `TAG`) appears **twice** in
smali — once on the `.field … = "…"` line and again as the inlined
`const-string` at each use site — so it is not a count==1 anchor either. Pick a
literal that is genuinely used once.

## Verification status / follow-ups

- The 66 original rules are verified on 8080, 8081 **and** 8100.
- The 6 new rules are verified on **8100 only** (the sole release on hand when
  authored). They should be back-verified against 8080/8081 when those APKs are
  available; being kept-name classes anchored on stable literals, they are
  expected to resolve to themselves there too.
