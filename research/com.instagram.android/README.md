# com.instagram.android — research notes

Findings from tearing apart **Instagram for Android** (`com.instagram.android`)
for Rosetta. Started with the **login / authentication HTTP surface** and
**password encryption**, then expanded across the request/identity layer,
secure storage, realtime/push, Direct messaging, and the media pipeline. These
are the human-readable *what-the-code-does* notes behind the machine artifacts:

- **Authoritative name mapping** → [`maps/com.instagram.android/<version_code>.json`](../../maps/com.instagram.android/)
- **Source-of-truth signatures** → [`signatures/com.instagram.android/signatures.yaml`](../../signatures/com.instagram.android/signatures.yaml)
- **These notes** → behaviour, flows, hook points.

Notes reference classes by their **logical** name (e.g. `IgAccountsLoginApi`);
the obfuscated token for a given `version_code` lives in the map. Where an
obfuscated token aids navigation it's given in parentheses (e.g. `X/55W`),
pinned to the version in each doc's header.

## Index

| Doc | Subsystem |
| --- | --- |
| [`docs/login-http-api.md`](docs/login-http-api.md) | Obfuscation model; the `accounts/*` login/recovery API factory (`X/55W`) and the `accounts/login/` request body |
| [`docs/password-encryption.md`](docs/password-encryption.md) | `enc_password` scheme: tag/version/key_id/ciphertext, FB CryptoPub, the bundled bootstrap RSA key, key refresh |
| [`docs/two-factor-and-checkpoint.md`](docs/two-factor-and-checkpoint.md) | 2FA code/SMS/TOTP, trusted-device push approval, checkpoint/challenge routing, login response parser |
| [`docs/alt-login-paths.md`](docs/alt-login-paths.md) | One-tap/saved login + nonce store, Android Credential Manager, Sign-in-with-Google, SmartLock |
| [`docs/http-request-layer.md`](docs/http-request-layer.md) | Shared request-builder/session/signing stack (architecture context; not signatured) |
| [`docs/device-identity-and-signing.md`](docs/device-identity-and-signing.md) | IG header layer, signed GraphQL body, device-id generation, server auth-token (`IGT`/MID/www-claim) header parsing, igsignals |
| [`docs/secure-storage.md`](docs/secure-storage.md) | AndroidKeyStore manager + hardware attestation, JWE cipher, symmetric transformer, keystore key-loader |
| [`docs/realtime-and-push.md`](docs/realtime-and-push.md) | MQTT realtime transport + topic mapper, FBNS push + Flytrap health monitor, presence |
| [`docs/direct-messaging.md`](docs/direct-messaging.md) | MSYS Direct stack, ArmadilloExpress E2EE primitives, Stella AIDL send, mailbox activation (`X/38Z`) |
| [`docs/media-upload.md`](docs/media-upload.md) | Resumable `rupload` + `media/configure*` publish pipeline (photo/video/story/clips/sidecar) |
| [`docs/feature-gating-bloks-analytics.md`](docs/feature-gating-bloks-analytics.md) | MobileConfig feature-flag engine, Bloks server-driven-UI action registry, analytics batch-upload endpoint |
| [`docs/feed-stories-reels.md`](docs/feed-stories-reels.md) | Feed/clips endpoint registry, stories-tray fetch, and the `media/seen/` watched-stories reporter |
| [`docs/signup-http.md`](docs/signup-http.md) | Sign-up / registration HTTP surface: account creation (consumer/business/secondary), SMS+email confirmation, username suggestions, FB sign-up, the age gate & new-user consent flow, contact prefill, and `#PWD_INSTAGRAM:4` password sealing |
| **— feature subsystems (expansion) —** | |
| [`docs/orientation.md`](docs/orientation.md) | App shape, obfuscation profile, dex layout, native libs, anchor strategy |
| [`docs/meta-ai.md`](docs/meta-ai.md) | Meta AI chat threads, AI Studio persona creation, GenAI Imagine, GenAI voices |
| [`docs/quicksnap.md`](docs/quicksnap.md) | QuickSnap / QuickSends — BeReal-style daily dual-camera |
| [`docs/friend-map.md`](docs/friend-map.md) | Instagram Map / Friend Map — live location sharing, audience/privacy |
| [`docs/rtc-calls.md`](docs/rtc-calls.md) | Video/audio calls: RSYS bridge, Telecom, foreground service, watch-together, screen-share |
| [`docs/direct-e2ee.md`](docs/direct-e2ee.md) | Direct E2EE: MSYS engine, decrypt landing point, Stella cross-process send (complements direct-messaging.md) |
| [`docs/reels-creation.md`](docs/reels-creation.md) | Reels/clips creation: drafts provider, teleprompter, music sticker, publish |
| [`docs/stories.md`](docs/stories.md) | Stories: tray/viewer, replies/reactions, interactive stickers, highlights/archive |
| [`docs/close-friends.md`](docs/close-friends.md) | Close Friends: private-stories list API, audience picker, green-ring badge |
| [`docs/shopping-commerce.md`](docs/shopping-commerce.md) | Shopping bag/checkout, product tagging + Branded Content / Paid Partnerships |
| [`docs/live.md`](docs/live.md) | IG Live broadcasting/viewing + monetization (Stars, Badges, gift feed) |
| [`docs/teen-safety-wellbeing.md`](docs/teen-safety-wellbeing.md) | Supervision/parental controls, Family Center, Screen Time / "Take a Break" |
| [`docs/notifications.md`](docs/notifications.md) | Notification UX: dismissal, channels, settings, Activity Feed |
| [`docs/avatars-ar.md`](docs/avatars-ar.md) | Meta Avatars + AR effects (voltron loader, effect gallery, Nametag) |
| [`docs/payments-monetization.md`](docs/payments-monetization.md) | FBPay / W3C payments / payout + creator subscriptions (Fan Club) |
| [`docs/notes-broadcast-channels.md`](docs/notes-broadcast-channels.md) | Instagram Notes ("ambient data") + creator Broadcast Channels |
| [`docs/auth-2fa.md`](docs/auth-2fa.md) | Login/signup/CAA + 2FA fragments/APIs (complements login-http-api / two-factor docs) |
| [`docs/realtime-mqtt.md`](docs/realtime-mqtt.md) | Realtime MQTT client, Skywalker/GraphQL subscriptions, FBNS push (complements realtime-and-push.md) |
| [`docs/comments.md`](docs/comments.md) | Comments: fetch/compose/post, likes, moderation (pin/hide/filter) |
| **— feature subsystems (round 3) —** | |
| [`docs/discovery-search.md`](docs/discovery-search.md) | Explore grid + Search (SERP tabs, typeahead, null-state, suggested users) |
| [`docs/feed-ranking-saved.md`](docs/feed-ranking-saved.md) | Main-feed cache/store + Saved / Collections (CRUD, saved-feed) |
| [`docs/feature-gating-qe-qp.md`](docs/feature-gating-qe-qp.md) | Quick Experiment (QE param read path) + Quick Promotion (megaphone/interstitial framework) |
| [`docs/meta-verified-accounts.md`](docs/meta-verified-accounts.md) | Meta Verified + Authenticity ID upload + account switching / Accounts Center |
| [`docs/stickers-music.md`](docs/stickers-music.md) | Sticker search / GIPHY client + music/audio (search, download, lyrics, original audio) |
| [`docs/inapp-browser-upload.md`](docs/inapp-browser-upload.md) | In-app browser (BrowserLite, link de-shim) + media upload (PendingMedia store/uploader) |
| [`docs/analytics-zero.md`](docs/analytics-zero.md) | Analytics2 batch uploader + Profilo tracing + zero-rating / free-data headers |
| [`docs/lead-ads-tagging.md`](docs/lead-ads-tagging.md) | Lead Ads / lead-gen forms + people/product/collab tagging |
| [`docs/community-notes-fundraisers.md`](docs/community-notes-fundraisers.md) | Community Notes (Bloks-driven) + charitable Fundraisers |
| [`docs/bloks-pando.md`](docs/bloks-pando.md) | Bloks hosting layer + Pando/GraphQL JNI data layer (cross-platform infra) |

## Obfuscation profile (TL;DR)

Instagram keeps first-party feature **package** names (`com.instagram.login.*`)
but flattens most logic into a single synthetic **`X` package** (`LX/55W;`,
`LX/ioi;`, …) whose short tokens rotate every release. **String literals
survive** — endpoint paths, POST field names, analytics events, the bundled
public key — so every signature here is anchored on a string verified
**globally unique** across all 19 dex files (`rg -l` count == 1). Because every
obfuscated class lives in package `X` (type refs are always `LX/…;`,
package-qualified), the semantic validator's single-segment "dangling
app-internal reference" check is inherently N/A for this app and is reported as
skipped — that is expected, not a suppressed check.

## Scope & confidence

**313 classes mapped**, each pinned on a unique endpoint / marker string (or a
`__redex_internal_original_name` field) and resolved by `sigmatcher analyze`
against the real APK — every rule resolves to exactly one class, zero
collisions. The map is the **union of two efforts**:

1. The original **login / HTTP / identity** surface (53 → 52 classes): login/auth
   API, sign-up/registration, password encryption, two-factor, one-tap, device
   identity & request signing, keystore secure-storage crypto, realtime/MQTT +
   FBNS push, MSYS Direct mailbox, the media upload/configure pipeline,
   MobileConfig feature gating, the Bloks action registry, analytics
   batch-upload, and the feed/stories/reels HTTP surface.
2. The **feature-subsystem expansion** (149 classes across 26 product
   subsystems): Meta AI/AI Studio, QuickSnap, Friend Map, Direct/MSYS/E2EE, RTC
   calls, Reels/clips, Stories, Close Friends, Shopping/Commerce, Branded
   Content, IG Live, Live monetization, Supervision, Family Center,
   Wellbeing/Screen Time, Notifications, Avatars, AR effects, Payments/FBPay,
   Creator subscriptions, Notes, Broadcast Channels, Auth/Login, 2FA/Security,
   Realtime/MQTT, Comments.

The two efforts independently agreed on the obfuscated names of the 6 shared
login/2FA classes (`X.55W`, `X.GHs`, `X.LbY`, `X.LFd`, `X.LMf`, `X.Dw5`) — a
useful cross-check. One class (`X.E1z`) was relabeled during the merge from
`UsernameSuggestionsApi` to its authoritative redex name
`OnePageRegistrationFragment` (the registration fragment calls the
`accounts/username_suggestions/` endpoint inline, which is why the old
endpoint-anchor resolved to it).

Many adjacent classes are documented in prose but deliberately **not**
signatured, for two recurring reasons: (a) their string anchors are shared
across several classes (not unique → rotation-fragile), or (b) the class is
**already un-obfuscated** (much of `realtimeclient`, `com.facebook.rti.*`,
`com.instagram.direct.*`, MSYS, Credential Manager, SmartLock keep real FQNs),
so a map entry would be `original == new`. See each doc's "Confidence" /
"why not signatured" section.

## Provenance

Produced by the `apk-research` skill: apktool + jadx decompile, search-first
investigation, sigmatcher-verified signatures.

- **Confirmed against `version_code` 383909338 (433.0.0.47.68)** only.
- APK signer SHA-256: `44c3bb8c…fbb29541` (see the map's `signer_sha256`).
- **Not yet cross-version verified.** Anchors were uniqueness-checked against
  this single release; the real portability test (resolving the same
  signatures against a second version, per the skill) needs a second APK and is
  the obvious next step before relying on these across point releases.
