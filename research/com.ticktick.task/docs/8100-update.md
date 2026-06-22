# TickTick 8.1.0.0 (version_code 8100) — map refresh + new anchors

Findings from refreshing `com.ticktick.task` against a fresh APK
(`versionName 8.1.0.0`, `versionCode 8100`). The real release signing cert
SHA-256 is `80efccbb…578196` (see the signer section below — an earlier
re-bundled sample had mis-set this to a private key). The authoritative
real→obfuscated mapping lives in `maps/com.ticktick.task/8100.json`; the
regex anchors live in `signatures/com.ticktick.task/signatures.yaml`. This doc
only records *what was found*, not the name table.

## Provenance

- APK arrived as a 5-volume RAR (`TickTick_signed.part1–5.rar`, RAR5) — the
  RARLab `unrar` was needed (7-Zip 23.01 / unrar-free choke on the codec /
  multi-volume join) → `TickTick_signed.zip` → `TickTick_signed.apk` (5 dex,
  ~41 MB). NOTE: this sample was re-signed with a private key (see signer
  section); the official build's signer is recorded in the maps.
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

## Member-level pass — 28 method mappings across 9 classes (8100)

A follow-up pass added `methods:` to nine classes already mapped at 8100,
selecting genuinely useful hook points (CRUD chokepoints, the sync commit
steps, the AI/SSE endpoint triggers, the pro/grace-period helpers, crypto key
derivation). All resolve under `sigmatcher analyze` against 8100 with zero
errors; the authoritative obfuscated names + descriptors are in
`maps/com.ticktick.task/8100.json`.

Classes touched: `AiComplete` (4 SSE endpoint triggers — decomposition /
improve / advice / scene), `SyncService` (6 per-entity `commit*` push steps),
`TaskService` (6 task CRUD / sort-order ops), `ProHelper` (5 subscription /
grace-period helpers), `TickTickAccountManager` (`saveUserStatus`,
`isInBilling`, `updateTagListShow`), plus one method each on
`TickTickAuthorizeTask` (`doInBackground`), `ResponseUser` (`toString`),
`PomodoroStateContext` (`changeDuration`), and `AESUtils` (`createKey`).

### Anchoring gotcha #2 — sigmatcher matches the method *body*, not the signature line

The decisive lesson of this pass. sigmatcher applies a method's regex against
each method's **instruction body** and attributes the hit to the enclosing
method — the `.method …(descriptor)` declaration line is **not** part of the
searched text. Consequences:

- A **descriptor fragment** (e.g. `getAccessToken\(\)Ljava/lang/String;`) is a
  bad method anchor: it does not appear in the target method's own body, but it
  *does* appear at every **call site**, so it mis-resolves to a *caller*
  (observed: `getAccessToken` → `getAccessTokenById`) or trips
  "Found too many matches".
- The robust anchor is a **`const-string` literal that occurs in exactly one
  method body** in the class. Every method mapped here is anchored that way.
- Therefore methods with **no string literal in their body cannot be anchored**
  with this dialect and were deliberately dropped rather than guessed:
  `ProHelper.isPro(User)Z` (the gate, but stringless), `SyncService.doSync`,
  the `AESUtils` encrypt/decrypt pairs (their only literal,
  `"AES/ECB/PKCS5Padding"`, is shared by both byte[] variants → ambiguous), and
  native methods on `TitleParserLib` (no body at all).
- Descriptors that reference a **rotating obfuscated type** were also dropped to
  avoid dangling refs — e.g. `PomodoroStateContext`'s `doBeforeUpdateState`
  worker takes the obfuscated inner state type `yb.d$h`. `changeDuration(J)V`
  was mapped instead.

## Signer SHA-256 finding — the value in the maps is a RE-BUNDLED key, not TickTick's

The 8100 APK analysed in this pass was **re-signed with a private key** (not the
official TickTick release cert). Its signing cert SHA-256 is
`44c3bb8c…b29541` — i.e. **identical to the `signer_sha256` already committed in
all three maps** (8080/8081/8100). That confirms the stored value is the
re-bundling key, **not** Google Play's TickTick signing certificate, so any
client checking a Play-Store-installed TickTick against this map would fail the
signer guard.

`signer_sha256` is a functional version/authenticity guard, not derivable from a
re-signed sample. **Now corrected** in all three maps (8080/8081/8100) to the
real Google Play release certificate, read from a device running the official
build:

```
80efccbbbc822a799ff7e787b889d02f3376cc4b829875eaa237adf19e578196
```

The recommended way to read it from a device, given a package name, is to pull
the installed base APK and print the cert digest with `apksigner` (its
"certificate SHA-256 digest" line is already in the canonical bare-lowercase-hex
form the schema wants):

```bash
pkg=com.ticktick.task
adb pull "$(adb shell pm path "$pkg" | sed 's/package://;s/\r//' | grep -m1 base.apk)" /tmp/base.apk \
  && apksigner verify --print-certs /tmp/base.apk | grep -i 'SHA-256'
```

That prints two lines for TickTick:

- `Signer #1 certificate SHA-256 digest: 80efccbb…578196` — the **APK signing
  certificate**; this is what goes in `signer_sha256`.
- `Source Stamp Signer certificate SHA-256 digest: 3257d599…3bbd6d` — the Play
  **source stamp**, a separate provenance marker injected by Google Play. It is
  NOT the app's signing identity and is deliberately **not** stored in the map.

(If `apksigner` isn't handy, `keytool -printcert -jarfile /tmp/base.apk | grep
SHA256` gives the same Signer #1 digest with colons — strip them and lowercase.)

## Coverage expansion — +14 classes, +8 account/Pro methods (8100)

A second member/class pass widened coverage (all verified on 8100 with zero
`sigmatcher analyze` errors; map class count 72 → **86**, methods 28 → **36**).

### New classes (14) — persistence layer

All in the kept `com.ticktick.task.*` carve-out (resolve to themselves).
Inner-class-free classes use the retained SourceFile (`"Foo.java"`) anchor,
verified globally unique; classes whose SourceFile recurs across inner-class
smali are anchored on a class-unique business literal instead (see the YAML
comments for which is which and why).

- **Entities:** `Attachment`, `Comment`, `Filter` (SourceFile); `ChecklistItem`
  (toString-prefix literal — has inner classes).
- **GreenDAO services:** `ChecklistItemService`, `CommentService`,
  `FilterService`, `PomodoroService`, `ReminderService`, `TaskReminderService`,
  `SyncStatusService` (SourceFile); `ProjectService` (SQL-collation fragment),
  `TagService` (helper-name literal), `ColumnService` (delete-by-sid log) — these
  three have inner classes so SourceFile would be `count > 1`.

### New account / Pro methods (8)

- `User.requireDisplayName()String` (the `****@domain` e-mail mask),
  `User.isDidaAccount()Z`.
- `UserProfile.toString()String`.
- `NewGoogleBillingPayment`: `payFor(String,String)V` (launch billing flow),
  `onPurchasesUpdated(BillingResult,List)V` (Play listener),
  `showVerifySubscriptionResult(Purchase)V` (server verify), `destroy()V`.
- `NewGoogleBillingPayUtils.onPurchasesUpdated(Activity,BillingResult,List)V`
  (verify → acknowledge → grant Pro).

Billing-method descriptors reference only `com.android.billingclient.api.*`
(kept library names) and framework types — no dangling obfuscated refs. The
`User`/`UserProfile`/billing classes were already mapped; only `methods:` were
added to them.
