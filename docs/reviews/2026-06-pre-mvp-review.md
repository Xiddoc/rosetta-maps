# Pre-MVP Codebase Review — Final Triangulated Findings

**Scope:** `rosetta-maps`, `rosetta-frida`, `rosetta-xposed`
**Date:** 2026-06-06
**Branch (all three repos):** `claude/codebase-review-agents-8RWYg`

## Methodology

This is the **synthesis layer** of a two-phase multi-agent code review run
in preparation for a real-app MVP:

- **Phase 1 — Independent review.** Nine reviewers (CR1–CR9) audited all
  three repositories in parallel. Each produced a stand-alone findings
  document under `review-findings/cr/agent-N.md` with stable IDs
  (e.g. `CR3-001`), severity, file:line evidence, and a suggested fix.
  Total raw findings: **~205**.
- **Phase 2 — Independent verification.** Three verifiers (V1–V3) re-read
  every CR docs and re-checked the source for each claim. Verdicts:
  **UPHELD / PARTIAL / REFUTED**, with explicit notes when a sub-claim
  was wrong. Verifier reports: `review-findings/verify/verifier-{1,2,3}.md`.

After de-duplication across the nine reviewers there are roughly **45
distinct issues**, organised below by severity. Every issue listed here
was upheld by **at least two** verifiers. The four refuted/partial
sub-claims are listed at the end so they are not silently dropped.

Aggregate verdict tally (averaged across V1–V3):

| Verdict   | Count   | Notes                                                                 |
| --------- | ------- | --------------------------------------------------------------------- |
| UPHELD    | ~155–170 | Cited file:line matches; behaviour matches the claim                  |
| PARTIAL   | ~25–30   | Headline correct, a numeric/detail sub-claim was slightly off         |
| REFUTED   | ~1–10    | Mostly small counting errors in CR docs (e.g. "17 classes" → actual 15) |

---

## BLOCKERs — must fix before real-app MVP

These three issues are silent-failure paths against the **exact** class
of app this project is designed for (large commercial Android apps
running multi-threaded JVMs with rotating obfuscation).

### B1. `version_code` int32 cap vs Android `longVersionCode` 64-bit drift

**Severity:** BLOCKER · **Repos:** rosetta-maps, rosetta-frida, rosetta-xposed
**Corroboration:** every reviewer (CR1-001, CR2-001, CR3-003, CR4-001,
CR5-006, CR6-001, CR7-001, CR8-001, CR8-005, CR9-001) — V1+V2+V3 all UPHELD

**Evidence:**
- `rosetta-maps/schema/rosetta-map.schema.json:17` — caps `version_code`
  at `2147483647` (int32 max).
- `rosetta-frida/src/validate/schema.ts:81` and `:268` — Zod enforces the
  same int32 cap.
- `rosetta-frida/src/runtime/auto-detect.ts:127` — reads
  `Number(packageInfo.getLongVersionCode())` with **no masking** to the
  low 32 bits.
- `rosetta-xposed/core/src/main/kotlin/.../model/RosettaMap.kt:158` —
  declares `version_code: Long`.
- `rosetta-xposed/core/.../loader/MapLoader.kt:74` —
  `MAX_VERSION_CODE: Long = 2_147_483_647L`.

**Why it matters:** RFC 0001 Decision 3 explicitly says the runtime selects
maps by `version_code` (PackageInfo.versionCode or the low 32 bits of
`longVersionCode`). Real-world commercial apps routinely set
`versionCodeMajor`, producing a `longVersionCode` above 2³¹. The current
pipeline either rejects the map (schema/Zod) **or** silently truncates to
a JS `number` (Frida side), giving a wrong selection key — a hard-to-debug
silent miss.

**Suggested fix:** Make `version_code` consistently a 64-bit unsigned
quantity end-to-end. Either (a) widen the schema cap to UInt64 (and the
Zod/Kotlin types to match) **or** (b) explicitly mask to the low 32 bits
at *detection time* (`auto-detect.ts` + Android-side reader) and document
that decision in RFC 0001. Add a conformance fixture pinning a
`>2^31` selection case.

### B2. Kotlin `:core` Resolver caches are not thread-safe

**Severity:** BLOCKER · **Repo:** rosetta-xposed
**Corroboration:** CR2-008, CR3-001, CR6-005, CR7-008, CR8-002 — V1+V2+V3 all UPHELD

**Evidence:**
- `rosetta-xposed/core/.../resolver/Resolver.kt:33-55` — every cache
  (`classByReal`, `reverseClassIndex`, `methodCacheByClass`,
  `fieldCacheByClass`) is a plain `mutableMapOf` with no
  `@Synchronized`, `Mutex`, or `ConcurrentHashMap`.
- `grep -E 'Concurrent|synchronized|Mutex' rosetta-xposed/core/src/main` —
  zero hits.

**Why it matters:** Unlike Frida (single-threaded JS host), Xposed/LSPosed
modules run **inside the target app's JVM** and hooks are dispatched on
arbitrary app threads. Concurrent `HashMap` mutation is a documented JVM
crash/livelock hazard (the canonical bug is a write during a rehash
causing an infinite loop). This is not theoretical — any app under
moderate load will hit it.

**Suggested fix:** Replace caches with `ConcurrentHashMap` and use
`computeIfAbsent`. The change is small and surgical. Add a focused stress
test (concurrent `resolveClass` from N coroutines) to the `:core` test
suite.

### B3. Target-namespace guard absent from Kotlin `:core` Resolver

**Severity:** BLOCKER · **Repo:** rosetta-xposed
**Corroboration:** CR7-006 (unique) — V1+V2+V3 all UPHELD with highest confidence

**Evidence:**
- `rosetta-frida/src/resolver/resolver.ts:226,249,438,443` — every public
  resolve path calls `assertTargetAllowed(...)`.
- `rosetta-xposed/core/.../resolver/Resolver.kt` — **zero** calls to
  `assertTargetAllowed`, `TargetGuard`, or `loadGuardedClass`. The guard
  exists only in the `:xposed`-layer `Targets.kt` (`loadGuardedClass`).
- `:core` `Resolver` is declared `public` (V2 verified the public surface).

**Why it matters:** A consumer that uses `:core` directly — which the
module is explicitly designed to allow, since it's `:xposed`-free and
Android-free — gets **zero** target-namespace policy enforcement. The C1
control documented in `TargetPolicy.kt:1-20` is bypassed entirely on the
Kotlin side, while it's enforced on the Frida side. This is a
silent-fail-open regression of an explicitly-documented security control.

**Suggested fix:** Either (a) move `assertTargetAllowed`-equivalent into
`:core/Resolver.kt` so both clients enforce it uniformly, or (b) seal
`:core/Resolver` to `internal` and require consumers to go through a
guarded `:xposed` wrapper. Option (a) matches the Frida shape and the
"Resolver is the choke point" doctrine in RFC 0001 Decision 2.

---

## HIGH — should fix before MVP

### H1. No `rosetta pull` / distribution CLI verb

**Repos:** rosetta-frida, rosetta-maps
**Corroboration:** CR1-008, CR2-010, CR3-009, CR4-006, CR5-008, CR6-010,
CR7-015, CR8-010, CR9-007 — all 9 reviewers, all 3 verifiers UPHELD.

The whole "community maps repo + bundle at build time" value proposition
(documented in `rosetta-frida/AGENTS.md` "Distribution model") rests on a
`rosetta pull` verb that **does not exist**. Current CLI verbs are
`init / validate / convert / patch / extract / inspect`. The example map
itself references a non-existent `merge-bundle` verb (`src/types/map.ts:225`).

**Fix:** Ship `rosetta pull <app>@<version_code>` that fetches the single
verified map from the maps-repo at a pinned commit, verifies the schema,
and writes it under the project's `maps/<app>/` directory. Treat the
maps-repo as the source via plain git/HTTPS (no npm publish needed yet).

### H2. Filename invariant violated end-to-end (`<version>.json` vs `<version_code>.json`)

**Repos:** rosetta-frida, rosetta-maps
**Corroboration:** CR1-004, CR1-007, CR1-017, CR7-007, CR7-022, CR8-008,
CR9-002 — V1+V2+V3 UPHELD.

- `rosetta-frida/maps/com.example.app/3.4.5.json` ships with
  `version_code: 30405` — filename is the **versionName**, not the
  authoritative key.
- `rosetta-frida/cli/commands/init.ts:77,115` scaffolds a new map as
  `<version>.json` with `version_code: 0` — **both** the filename and
  the field are wrong by maps-CI rules.
- `rosetta-maps/.github/workflows/validate.yml:217` enforces
  `filename == version_code.json` — the canonical invariant.

A contributor who follows the documented "rosetta init" path produces a
map that the CI gate will reject. The Frida-side example contradicts the
maps-side invariant.

**Fix:** Rename `rosetta-frida/maps/com.example.app/3.4.5.json` → `30405.json`.
Change `rosetta init` to default the filename to `<version_code>.json`
and require an explicit, non-zero `--version-code`. Add a Frida-side
unit test that asserts the filename invariant on the shipped sample.

### H3. `MethodTarget.member()` only walks `declaredMethods` — no inheritance

**Repo:** rosetta-xposed
**Corroboration:** CR2-015, CR6-002, CR8-006 — V1+V2+V3 UPHELD.

`rosetta-xposed/xposed/.../bind/Targets.kt:181,203` use
`Class.declaredMethods` / `declaredFields`. Members inherited from a
superclass are unfindable. The shipped example map has
`com.example.app.service.RemoteServiceClient extends AbstractServiceClient`
— so even the worked example exercises a path that silently fails.

**Fix:** Walk the parent chain when a member isn't on the declared class
(stop at `java.lang.Object`). Mirror the Frida `resolver.ts` traversal.
Add a conformance case where the binding sits on a parent class.

### H4. Conformance `validation.json` covers ~2 of ~12 schema constraints

**Repos:** rosetta-frida, rosetta-xposed
**Corroboration:** CR1-019, CR2-021, CR3-014, CR5-002, CR6-003, CR7-005,
CR8-004 — V1+V2+V3 UPHELD.

The whole "the three copies of the schema move together" discipline
(`rosetta-maps/AGENTS.md` Testing mandate) rests on the shared
`validation.json` fixture, which currently pins only `minLength: 1` and
`schema_version`. Everything else (signer hash format, `version_code`
int32 cap, `additionalProperties`, the descriptor grammar, etc.) can
drift between Zod/Kotlin/check-jsonschema silently.

**Fix:** Add at least one accept and one reject case for each enforced
constraint listed in `rosetta-map.schema.json`. Run the shared fixture
through all three validators in CI (currently each repo runs only
*its own* validator).

### H5. No fuzzy version matching on Kotlin side

**Repo:** rosetta-xposed
**Corroboration:** CR1-002, CR3-008, CR4-009, CR5-003, CR6-011, CR7-002,
CR8-003, CR9-009 — V1+V2+V3 UPHELD.

- `rosetta-frida/src/runtime/version-match.ts:147-176` implements a
  fuzzy `versionName` fallback (weighted `major*10000 + minor*100 + patch`).
- `rosetta-xposed/core/.../resolver/VersionMatch.kt:100-112` is
  exact-key-only.

The Frida-side fuzzy match has its own sub-issue: weight overflow when
`patch >= 100` (CR3-008 PARTIAL+UPHELD). Either both clients need it or
neither should — and if both, it needs a non-overflow ordering.

**Fix:** Implement a shared semver-aware fallback in `:core` (translate
to Kotlin once, behind the same `allowFuzzyMatch` flag). Replace the
weighted-sum heuristic with proper component-wise lexicographic
comparison (no overflow).

### H6. Stale-docs cluster — built features still described as "stubbed/planned"

**Repos:** rosetta-xposed (worst), rosetta-frida
**Corroboration:** CR1-014/15/16, CR2-018/19, CR3-017/18, CR4-014/15/16,
CR5-015/16, CR6-013/14, CR7-020/21, CR8-019/20, CR9-014/15/16 — V1+V2+V3 UPHELD.

Three concrete drifts:

1. **Test count.** Multiple AGENTS docs cite *"611 tests / 100% coverage"*;
   `vitest run` reports **`Tests 1056 passed (1056)`** (V1 verified).
2. **DexKit dynamic backend.** `CLAUDE.md` says "Two-module Gradle build"
   and "DexKit is *stubbed*". Reality: three modules
   (`:core / :xposed / :dexkit`, settings.gradle.kts:47);
   `DynamicResolutionBackend.kt` is **344 lines** of actual code,
   `DexKitBackedIndex.kt` is **139 lines**.
3. **Xposed signer enforcement.** RFC 0001 line 196 says
   *"rosetta-xposed enforcement remains planned"* — but
   `RosettaXposed.kt:140,183,220` actually calls `SignerGuard.verify`
   fail-closed.

**Why it matters:** Future maintainers (and the hand-off reviewer) will
either re-implement something that exists or distrust the docs. Both are
costly.

**Fix:** Bulk doc pass — update CLAUDE.md (rosetta-xposed) to "three
modules", remove "stubbed" from DexKit references, update RFC 0001 to
reflect shipped signer enforcement, and replace the stale "611 / 100%"
prose with either the current numbers or a "see CI badge" pointer.

### H7. Three hand-maintained copies of bounds / heuristics, no parity gate

**Repos:** rosetta-maps (schema), rosetta-frida (Zod), rosetta-xposed (BoundsChecker)
**Corroboration:** CR1-005/011/012, CR2-014/16/23, CR3-013/15/23,
CR4-010/11, CR5-012/13, CR6-020/22, CR7-018, CR8-014, CR9-010/11/13 — V1+V2+V3 UPHELD.

Three independent hand-rolled copies of the same logic:

- DoS bounds (max input bytes, max nesting depth, max name length, etc.)
  triplicated.
- `unknownArgTypeOrNull` heuristic byte-identical in
  `rosetta-frida/src/resolver/resolver.ts:101-155` and
  `rosetta-xposed/core/.../resolver/Resolver.kt:339-372` — both with
  identical "KEEP IN SYNC" banners.
- `BoundsChecker.run()` (`MapLoader.kt:211-355`) re-implements much of
  what `rosetta-map.schema.json` already declares; same for Zod.

**Fix:** Either (a) generate constants from the canonical schema at build
time (the source of truth is supposed to be the schema file) and
auto-derive Zod / Kotlin / check-jsonschema clients; or (b) add a
shared-conformance fixture that exhaustively pins the heuristic so any
drift fails CI in both clients. (a) is the right long-term answer; (b) is
the MVP guard.

### H8. `signer_sha256` normalisation drift between schema and SignerGuard

**Repos:** rosetta-xposed, rosetta-frida, rosetta-maps
**Corroboration:** CR2-004, CR8-018 — V1+V2+V3 UPHELD.

- Schema (`rosetta-map.schema.json:19`) and Zod
  (`src/validate/schema.ts:251`) require **strict** `^[0-9a-f]{64}$`.
- `rosetta-xposed/.../SignerGuard.kt:80,123` `normalize()` accepts
  `:`-separated and mixed-case hex.
- `rosetta-frida/src/runtime/signer-detect.ts:181` likewise normalizes.

A map that passes `SignerGuard.normalize` (e.g. with colons) is
**schema-invalid** — so the runtime accepts something the maps CI
rejects. Drift between the published-artifact validation and the
runtime guard.

**Fix:** Normalise at exactly one boundary. Recommend: normalise on
**emit** (`rosetta convert`) so the on-disk artifact is canonical, and
have the runtime guard require the canonical form. The CI is then the
source of truth and the runtime is a thin check.

### H9. `signatures/` directory has no CI validation

**Repo:** rosetta-maps
**Corroboration:** CR4-002, CR6-007, CR7-014 — V1+V2+V3 UPHELD.

`rosetta-maps/AGENTS.md` declares `signatures/<app>/signatures.yaml` the
"source of truth" — a map is reproducible from signatures + APK, which is
"what makes it verifiable." But `.github/workflows/validate.yml` globs
**`maps/**/*.json`** only. `grep signatures validate.yml` → 0 matches.

**Fix:** Add a `signatures/<app>/signatures.yaml` schema/lint step (YAML
parse + sigmatcher dialect linter) to `validate.yml`. Even a minimal
"file parses + has required top-level keys" check would be a step up.

### H10. Trust ladder tiers 2–5 unbuilt; RFC `apk_sha256` references stale

**Repo:** rosetta-maps (CI + docs), rosetta-frida (RFC)
**Corroboration:** CR1-009, CR2-011, CR3-011/19, CR4-008, CR5-009/18,
CR6-012/15, CR7-017, CR8-009/22, CR9-008/17 — V1+V2+V3 UPHELD.

- RFC 0001 Decision 4 describes a 5-tier trust ladder. Only tier-1
  (structural CI) is implemented.
- RFC 0001 lines **179, 197, 206** still reference `apk_sha256` as a live
  field, but the schema dropped it for `signer_sha256` (Decision 3
  refinement).
- `SignerGuard.kt:3-4` cites *"Decision 4"* — but app identity is
  Decision 3.

**Fix (MVP)**: Update the RFC to remove `apk_sha256` and fix the
`SignerGuard` citation. Tiers 2–5 can stay deferred — but the RFC should
mark them as "deferred to V2" instead of describing them as the design.

---

## MEDIUM — post-MVP track, fix opportunistically

(One-liners; see CR docs for evidence/cite each.)

- **M1.** Registry collision policy diverges — Frida first-wins
  (`version-match.ts:92` `!index.has`), Kotlin last-wins
  (`VersionMatch.kt:67`). Pick one. (CR1-003, CR3-006, CR7-011)
- **M2.** Reverse-class-index collision policy *also* diverges — this
  time Kotlin first-wins (`Resolver.kt:62` `putIfAbsent`), Frida last-wins
  (`resolver.ts:199` `.set()`). Distinct from M1. (CR7-003 — unique)
- **M3.** All-zeros `signer_sha256: "00...00"` placeholder in worked
  example. With `SignerGuard` fail-closed default, a contributor who
  copies the example ships a map that always raises
  `SignerMismatchException`. (CR2-007, CR5-004, CR6-004, CR9-020)
- **M4.** Worked-example `sources[].config: "signatures/example.json"`
  points at a non-existent file (real file is
  `signatures/com.example.app/signatures.yaml`). (CR4-021, CR5-017)
- **M5.** `RosettaXposed` companion exposes 4 near-parallel
  factories (`fromMap`, `fromMapUnverified`, `fromRegistry`,
  `fromMapWithDiscovery`) with subtly different security postures —
  notably `fromMapWithDiscovery` skips signer if `identity == null`
  (`RosettaXposed.kt:220`). Either rationalise into one builder or
  document the trade-off matrix prominently. (CR4-012, CR5-014, CR7-019,
  CR8-015, CR9-012)
- **M6.** Schema lacks `additionalProperties: false`; Zod uses
  `.strip()`; Kotlin uses `ignoreUnknownKeys = true` — typos in map
  fields are silently dropped. (CR2-005, CR4-004)
- **M7.** No persistent on-device discovery cache — `DiscoverySink`
  default is `NOOP`. WaEnhancer-style SharedPreferences caching would
  amortise dynamic resolution across app restarts. (CR5-010, CR9-006)
- **M8.** No Kotlin equivalent of `src/session/health-check.ts`.
  An on-attach sanity check would catch most "wrong map / right app"
  mis-bindings before the first hook fires. (CR2-013, CR8-012)
- **M9.** `frida_min_version` / `frida_max_version` in the
  language-neutral schema are unused at runtime by either client — a
  "neutral schema" leaking client-specific fields. Either move them to a
  `client_hints` sub-object or document the consumer. (CR4-003, CR6-008,
  CR7-013)
- **M10.** Resolvers do not translate / walk `extends` — the schema ships
  it but no resolver consumes it. Combined with H3, the entire
  inheritance story is unwired. (CR7-010, CR6-002)
- **M11.** Tier-1 CI does not implement referenced-types-resolvable,
  overload-distinctness, descriptor parse, or app-dir/app-field match —
  all promised by RFC 0001 Decision 4 as part of tier 1.
  (CR3-004, CR5-005/21, CR9-003)
- **M12.** No on-device `version_code` / `signer_sha256` reader helper
  for Xposed — `AppIdentity` is a value class the consumer has to fill
  themselves from `PackageManager`. (CR3-010, CR7-016)
- **M13.** `:dexkit` module excluded from kover coverage gate
  (`build.gradle.kts:93-94` only aggregates `:core` + `:xposed`); also in
  the default build path despite docs saying it's opt-in. (CR1-006,
  CR2-020, CR3-021, CR4-019, CR8-011)
- **M14.** No map provenance / integrity check at load time — a tampered
  bundled map is detected only via `signer_sha256` of the *app*, never
  the map itself. (CR1-010)
- **M15.** No packaging / publishing — `package.json` is
  `"version": "0.0.0-dev"`, no npm publish config, no Maven Central
  publication for `:core`. Maps cannot actually be distributed yet.
  (CR2-024, CR3-022, CR6-031)
- **M16.** `MapSource.tool` enum vocabulary drift — Frida `map.ts:14`
  emits `rosetta-frida-runtime-discovered`; Kotlin
  `RosettaMap.kt:67` documents `rosetta-runtime-discovered`. Pick one.
  (CR5-019, CR7-023)
- **M17.** `version: min(1)` (Zod / schema) vs `isBlank()` (Kotlin) — a
  whitespace-only `version` passes Zod / schema but fails Kotlin.
  (CR2-003, CR7-004)
- **M18.** `DynamicResolutionBackend` records only a single overload per
  method name (`DynamicResolutionBackend.kt:166-175`) — an obfuscated app
  with method overloads loses all but the last harvested one. (CR6-006)

---

## LOW — cleanup; doesn't block MVP

- **L1.** `zodPathToString` dead branch — both branches at
  `src/validate/schema.ts:332` collapse to `String(segment)`. (CR2-017, CR8-017)
- **L2.** `DynamicResolutionBackend.resolveField` (`:dexkit`,
  line 218–222) is a deliberate dead call — either implement or delete.
  (CR6-021, CR8-016)
- **L3.** `<init>` magic string vs `is_constructor: true` flag — the
  schema has the field, `Targets.kt:170` ignores it and dispatches on the
  name. (CR8-007)
- **L4.** `MapLoader.kt:138` double-scans the input — allocates
  `text.toByteArray(...).size` then re-scans the string. (CR2-023)
- **L5.** `frida-only` `RESERVED_RECORD_KEYS` defined in Frida only — the
  rejection is correct, but Kotlin should have parity. (CR2-025)
- **L6.** Schema-version mismatch error is generic — diagnostics could
  point a user at `rosetta migrate` (which doesn't exist; see M11).
  (CR7-012, CR9-004)
- **L7.** `boundedRecord` triple-cast (`schema.ts:106-142`) — Zod
  typing escape hatch. Functional but a smell. (CR3-015)
- **L8.** `SignerGuard.kt:3-4` cites *"Decision 4"*; app identity is
  Decision 3. (CR3-020, CR8-023)
- **L9.** Frida lacks the pre-parse byte/depth guard that Kotlin
  `MapLoader.kt:112-187` has (`MAX_INPUT_BYTES`, `MAX_NESTING_DEPTH`).
  Add parity. (CR6-032, CR7-025)
- **L10.** `rosetta-maps/.github/workflows/` has two similarly-named files
  (`pages.yml` "Deploy docs" and `validate.yml` "Validate maps"). Cosmetic.
  (CR1-018)
- **L11.** Maps CI triggers only on `master` — works if the default branch
  is `master`; flag for future rename. (CR4-017, CR7-024)
- **L12.** `rosetta-frida` `rosetta.session(...)` uses a module-level
  singleton; re-attach semantics under concurrent `Java.perform`
  callbacks not investigated. (CR9-019)
- **L13.** `unknownArgTypeOrNull` heuristic is also duplicated by value
  in `DEFAULT_DENY_PREFIXES` — same fragile-sync problem. (CR7-018)

---

## Refuted / partially refuted findings (kept for the record)

These were caught by the verifiers and **should not** be in the fix-list:

- **CR9-014 sub-claim "the sample has 17 class entries"** — **REFUTED**.
  Verified by both V1 and V2 with `len(json.load(...)['classes'])` → 15
  classes in both `rosetta-maps/maps/com.example.app/30405.json` and
  `rosetta-frida/maps/com.example.app/3.4.5.json`. The parent finding
  ("611 tests" stale) stays in H6 above.
- **CR7-020 sub-claim "879 it/test calls"** — **PARTIAL**. The grep
  approach undercounts dynamically generated suite cases. V1 ran
  `vitest run` and saw 1056. The parent stale-prose finding stays.
- **CR3-008 sub-claim about fuzzy weight overflow** — **UPHELD** but
  worth calling out as an *additional* fact under H5: the formula
  `major*10000 + minor*100 + patch` produces collisions for any
  `patch >= 100` (e.g. `1.0.142` ranks the same as `1.1.42`).
- **CR2-022, CR4-018, CR5-020, CR6-030, CR9-018 — "gradle build is
  fragile"** — **PARTIAL / environmental.** Multiple reviewers hit Kotlin
  daemon incremental-cache issues. V1 ran
  `./gradlew :core:test --no-daemon -Dkotlin.compiler.execution.strategy=in-process -Dkotlin.incremental=false`
  → `BUILD SUCCESSFUL`. **Not a code defect**; document the workaround in
  CONTRIBUTING.

---

## Prioritised do-next list

Concrete order to tackle these for MVP:

1. **B1, B2, B3** — the three BLOCKERs. Surgical fixes, all under a day each.
2. **H6** (stale docs) — opportunity bundle; do alongside the BLOCKER PRs
   so the doc churn is one diff.
3. **H1** (`rosetta pull`) — the most user-visible MVP gap.
4. **H2** (filename invariant) + **H4** (conformance fixture) — these
   together close the "three copies drift silently" hole.
5. **H3** (inheritance walk) + **M10** (`extends` translation) — pair
   them; same code path.
6. **H5** (fuzzy parity) + **H7** (parity gate) — pair them.
7. **H8, H9, H10** — doc + small CI extension, batchable.
8. **M / L bands** — opportunistically as touched.

The three BLOCKERs alone unblock real-app testing; everything below is
quality-of-life that prevents future drift but doesn't gate the MVP.

---

## Pointers

- Raw CR docs: `review-findings/cr/agent-{1..9}.md` (~3,163 lines / 9 docs)
- Verifier reports: `review-findings/verify/verifier-{1..3}.md` (~1,800 lines / 3 docs)
- Branch: `claude/codebase-review-agents-8RWYg` on all three repos
- See RFC 0001 in `rosetta-frida/docs/rfcs/` for the design context that
  most of these findings reference.
