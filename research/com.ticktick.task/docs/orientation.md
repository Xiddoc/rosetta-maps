# TickTick — orientation

App shape, obfuscation profile, entry points, and the network host
foundation. Confirmed against **`version_code` 8081 / versionName 8.0.8.1**
(the APK this research was authored against).

> Obfuscated names rotate between releases; the authoritative
> logical→obfuscated mapping for this `version_code` lives in
> [`maps/com.ticktick.task/8081.json`](../../../maps/com.ticktick.task/8081.json),
> anchored by [`signatures/com.ticktick.task/signatures.yaml`](../../../signatures/com.ticktick.task/signatures.yaml).
> These notes reference classes by their **logical** name.

## App shape

| Property | Value |
| --- | --- |
| Package | `com.ticktick.task` |
| versionName / versionCode | `8.0.8.1` / `8081` |
| minSdk / targetSdk | 21 / 36 |
| Signer cert SHA-256 | `44c3bb8c7ea35b3bb11cbfa3c2f5879240df2e49e39816b4437b9856fbb29541` |
| DEX files | 5 (`classes.dex` … `classes5.dex`) |
| Native ABIs | `arm64-v8a` only |
| Application class | `com.ticktick.task.TickTickApplication` (extends `TickTickApplicationBase`) |

### Native libraries (`lib/arm64-v8a/`)

| `.so` | Role |
| --- | --- |
| `libnative_parser.so` (2.1 MB) | Natural-language quick-add / date parser (see `features.md`). |
| `libmmkv.so` (597 KB) | Tencent **MMKV** key-value store — the app's fast persistence layer alongside GreenDAO. |
| `libsecuritychecknativelib.so` | Native security/integrity checks (`com.ticktick.task.securitychecknativelib`). |
| `libbugsnag-ndk.so`, `libbugsnag-plugin-android-anr.so`, `libbugsnag-root-detection.so` | Bugsnag native crash/ANR/root reporting. |

## Obfuscation profile

TickTick is **R8-minified with a wide carve-out**: the entire
`com.ticktick.task.*` business-logic tree keeps **readable package, class,
and (mostly) member names** — including the Retrofit API interfaces, the
data entities, the account/billing/sync packages, and the `helper.*`
classes. What *is* renamed:

- **Bundled third-party libraries** (OkHttp, Retrofit, Kotlin coroutines,
  Gson, etc.) → short tokens in top-level packages (`a`, `b0`, `kc`, …).
- A minority of **internal helper/lambda classes** (`a.smali`, `i$a.smali`)
  inside otherwise-readable packages.

Consequence for this map: most TickTick classes resolve to **themselves**
(logical name == obfuscated name) and are pinned to a stable string-literal
anchor purely so the map *certifies* the identity for `version_code` 8081.
The map's forward value is catching the day a release finally rotates one of
these names, and pinning the genuinely-obfuscated helpers.

## Dual brand: TickTick (international) vs Dida365 (滴答清单, China)

A single APK ships **both** product back-ends. The brand toggle is
`j7.a.m()` — `true` ⇒ TickTick, `false` ⇒ Dida365 — read throughout the
networking layer (e.g. `ServerHostConfig.Companion.getRelease()` and
`BaseUrl.isDidaEnv()`). `BaseUrl.isDidaEnv()` additionally treats an account
whose `User.isDidaAccount()` is true, or local-mode on the Dida build, as
Dida.

### Host foundation

The host set is centralised in two classes
(`smali_classes4` → `classes4.dex`):

- **`com.ticktick.task.helper.BaseUrl`** — static domain fields + accessors
  (`getApiDomain()`, `getSiteDomain()`, `getDataTrackerUrl()`,
  `isDidaEnv()`).
- **`com.ticktick.task.helper.ServerHostConfig`** — a Kotlin `data class`
  bundling one environment's hosts (`apiHost`, `webHost`, `cookieHost`,
  `dataPlatformHost`, `supportHost`, `aiHost`, `pullDomain`, `socketUrl`).
  Its `Companion` defines every environment: `getReleaseTick()`,
  `getReleaseDida()`, plus dev/test/future/build variants. `getRelease()`
  picks Tick vs Dida via `j7.a.m()`.

**Production hosts:**

| Purpose | TickTick | Dida365 |
| --- | --- | --- |
| REST API (`apiHost`) | `https://api.ticktick.com` | `https://api.dida365.com` |
| Web / site | `https://ticktick.com` | `https://dida365.com` |
| Cookie domain | `https://ticktick.com` | `https://dida365.com` |
| Data platform / analytics (`xapi`) | `https://xapi.ticktick.com` | `https://xapi.dida365.com` |
| Support / ticket | `https://ticket.ticktick.com` | `https://support.dida365.com` |
| AI (`aiHost`) | `https://ai.ticktick.com` | `https://ai.dida365.com` |
| Config/CDN pull | `https://pull.ticktick.com` | `https://pull.dida365.com` |
| Pomodoro WebSocket (`socketUrl`) | `wss://wssp.ticktick.com/android` | `wss://wssp.dida365.com/android` |

Non-production environments referenced in `ServerHostConfig.Companion`
(`*.365dida.com` dev/test/future, `build.ticktick.com`/`build.dida365.com`)
are listed for completeness; they are not used by release builds.

See **`network-api.md`** for the full endpoint catalog and HTTP-client
story built on top of these hosts.

## Where to look (subsystem → docs)

| Doc | Subsystem |
| --- | --- |
| [`network-api.md`](network-api.md) | Host config, the 18 Retrofit API interfaces, HTTP client / interceptors / signing, sync framework |
| [`auth.md`](auth.md) | Login / signup / signout, token & cookie lifecycle, third-party OAuth, 2FA/MFA |
| [`premium.md`](premium.md) | Google Play Billing, the is-Pro gate, Pro-gated features, server payment verification, promos |
| [`account.md`](account.md) | The `User` model, account/profile management, settings/config sync, account deletion, local mode |
| [`features.md`](features.md) | Tasks + GreenDAO persistence, sync engine, focus/pomodoro, habits, AI, NL quick-add parser |

## Provenance

Produced by the `apk-research` skill: apktool (smali + resources + version)
and jadx (readable Java) decompile, search-first investigation,
sigmatcher-verified signatures. APKs and decompiled trees are never
committed (AGENTS.md Hard rule 3).
