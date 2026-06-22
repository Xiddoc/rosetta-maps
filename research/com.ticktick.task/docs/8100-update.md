# TickTick 8.1.0.0 (version_code 8100) — map refresh + new anchors

Findings from refreshing `com.ticktick.task` against a fresh APK
(`versionName 8.1.0.0`, `versionCode 8100`). The authoritative
real→obfuscated mapping lives in `maps/com.ticktick.task/8100.json`; the
regex anchors live in `signatures/com.ticktick.task/signatures.yaml`. This doc
only records *what was found*, not the name table.

## Provenance

- APK arrived as a 5-volume RAR (`TickTick_signed.part1–5.rar`, RAR5) — the
  RARLab `unrar` was needed (7-Zip 23.01 / unrar-free choke on the codec /
  multi-volume join) → `TickTick_signed.zip` → `TickTick_signed.apk` (5 dex,
  ~41 MB).
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

### Anchoring gotcha #2 — a bare descriptor fragment matches call sites too

sigmatcher applies a method's regex against the whole method chunk (declaration
line + body — see technique #3 for the exact split). The trap is that a **bare
descriptor fragment** also occurs at every **call site** inside *other* method
chunks. Consequences:

- A fragment like `getAccessToken\(\)Ljava/lang/String;` matches both the real
  getter's declaration AND any method whose body invokes it, so it mis-resolves
  to a *caller* (observed: `getAccessToken` → `getAccessTokenById`) or trips
  "Found too many matches". The fix is technique #3: pin with a leading
  `\.method` so only the declaration line qualifies.
- The robust anchor is a **`const-string` literal that occurs in exactly one
  method body** in the class. Every method mapped here is anchored that way.
- Stringless methods need a different anchor — see technique #3 below (which
  later rescued most of the ones first dropped here). The genuinely
  un-anchorable remainder: the `AESUtils` encrypt/decrypt pairs (their only
  literal `"AES/ECB/PKCS5Padding"` is shared by both byte[] variants → ambiguous
  even by descriptor because the two byte[] overloads share it) and native
  methods on `TitleParserLib` (no body AND no in-class-unique declaration beyond
  the name, which is fine — natives could be added by name if wanted).
- Descriptors that reference a **rotating obfuscated type** were also dropped to
  avoid dangling refs — e.g. `PomodoroStateContext`'s `doBeforeUpdateState`
  worker takes the obfuscated inner state type `yb.d$h`. `changeDuration(J)V`
  was mapped instead.

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

## Anchoring technique #3 — declaration-line anchoring rescues stringless methods

Reading `sigmatcher.analysis.MethodAnalyzer` settled the earlier open question.
It does:

```python
raw_methods = smali.read_text().split(".method")[1:]
methods = {".method" + m for m in raw_methods}
```

So each searched chunk is `.method <decl line>\n<body>….end method` — the
**declaration line is included**, and multiple `signatures:` on one method are
**AND-ed** (`set.intersection_update`). A bare descriptor fragment mis-resolves
only because it also appears at *call sites* inside other chunks. Each chunk
contains exactly one `.method` token (it was the split delimiter), so pinning the
regex with a leading `\.method` targets the declaration line and nothing else:

```yaml
- name: 'getAccessToken'
  signatures:
    - signature: '\.method public getAccessToken\(\)Ljava/lang/String;'
      type: regex
      count: 1
```

This makes any method anchorable by **name + params/return**, with no in-body
literal required — directly capturing the descriptor as identity. The crucial
caveat: it is only robust where the **method name is stable**, i.e. the kept
`com.ticktick.task.*` carve-out. For the renamed/obfuscated classes the name
rotates, so those methods still need a body-string or structural anchor (a bare
`\.method public \w+\(\)Z` would bind the rotating token and is forbidden).

Two further levers exist for the hard cases, not needed yet but worth recording:

- **Field reference instead of method:** map the backing field directly
  (`fields:` capture its `name:type`), which is what a getter/setter actually
  exposes. For kotlinx-serialized DTOs the on-wire JSON key is a string literal
  in the generated `$serializer`, usable as a field/class anchor.
- **Macros:** a method/field regex can interpolate an already-resolved result via
  `${Class.fields.java}` → e.g. `Lf9/s;->a:L…;`. So a stringless method can be
  pinned by the (resolved, possibly-obfuscated) field it reads, rather than by
  its own name — the portable way to anchor obfuscated-class accessors.

### New account / Pro methods enabled by technique #3 (12)

- `User`: `getAccessToken`, `getSid`, `isPro`, `getProType`, `getApiDomain`,
  `getInboxId`, `getUsername` (the token/identity/Pro accessors).
- `ProHelper.isPro(User)Z` — the app-wide Pro gate, previously dropped as
  stringless, now anchored on its declaration line.
- `TickTickAccountManager`: `getCurrentUser`, `getAccessToken`,
  `getCurrentUserId`, `isLocalMode`.

Map totals after this pass: **86 classes, 48 methods** (8100).

### Entity-accessor expansion via technique #3 (User / Task2 / Project)

With method-name stability assumed for the carve-out, the full public accessor
surface (`get*`/`set*`/`is*`) of the three core entities was added by
declaration-line anchoring, auto-derived from 8100 and each verified
`count == 1`:

- `User` +94 (now 103 methods total — incl. `setAccessToken`, `getProEndDate`, …)
- `Task2` +172
- `Project` +118

Overloaded-name setters (`Task2.setStatus`/`setTags`/`setCommentCount`,
`Project.setStatus`/`setDeleted`) are omitted: sigmatcher keys a method
definition by its `name`, so two same-name overloads can't coexist in the
signature set (and the map keys methods by name too). They can be added later as
the schema's array-valued method form if a specific overload is needed.

Map totals after this pass: **86 classes, 432 methods** (8100), 89 KB (well
under the 1 MiB CI ceiling).
