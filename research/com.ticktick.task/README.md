# com.ticktick.task — research notes

Findings from tearing apart **TickTick** (`com.ticktick.task`) — the
cross-platform task manager / to-do app, which ships a dual back-end for
**TickTick** (international) and **Dida365 / 滴答清单** (China). These are the
human-readable *what-the-code-does* notes that sit behind the machine
artifacts:

- **Authoritative name mapping** → [`maps/com.ticktick.task/<version_code>.json`](../../maps/com.ticktick.task/)
- **Source-of-truth signatures** → [`signatures/com.ticktick.task/signatures.yaml`](../../signatures/com.ticktick.task/signatures.yaml)
- **These notes** → behaviour, flows, API surface, hook points.

Notes reference classes by their **logical** name (e.g. `BaseUrl`,
`LoginApiInterface`); the obfuscated name for a given `version_code` lives in
the map. TickTick is only lightly obfuscated (see
[`docs/orientation.md`](docs/orientation.md)), so most logical names match
the on-device names — the map certifies that for `version_code` 8081 and
will catch future rotations.

## Index

| Doc | Subsystem |
| --- | --- |
| [`docs/orientation.md`](docs/orientation.md) | App shape, obfuscation profile, native libs, TickTick-vs-Dida hosts |
| [`docs/network-api.md`](docs/network-api.md) | The 18 Retrofit API interfaces, endpoint catalog, HTTP client / interceptors / signing, sync framework |
| [`docs/auth.md`](docs/auth.md) | Login / signup / signout, token & cookie lifecycle, third-party OAuth, 2FA/MFA |
| [`docs/premium.md`](docs/premium.md) | Google Play Billing, the is-Pro gate, Pro-gated features, server payment verification, promos |
| [`docs/account.md`](docs/account.md) | The `User` model, account/profile management, settings/config sync, account deletion, local mode |
| [`docs/features.md`](docs/features.md) | Tasks + GreenDAO persistence, sync engine, focus/pomodoro, habits, AI, NL quick-add parser |
| [`docs/8100-update.md`](docs/8100-update.md) | Refresh against `version_code` 8100 (8.1.0.0): rotation results for the 66 rules + 6 new high-value hook anchors |

## Provenance

Produced by the `apk-research` skill: apktool + jadx decompile, search-first
investigation, sigmatcher-verified signatures, peer-reviewed. The signatures
are **multi-version-hardened**: all 66 rules resolve with zero failures on
`version_code` **8081** (8.0.8.1) and **8080** (8.0.8.0) — and again on
**8100** (8.1.0.0), tracked in [`docs/8100-update.md`](docs/8100-update.md)
along with six new hook anchors — which is why there is a map per version
under [`maps/com.ticktick.task/`](../../maps/com.ticktick.task/). Renamed
helpers rotated their obfuscated tokens between releases and the anchors
tracked every one — obfuscated names rotate between releases, the behaviour
and the string-literal anchors are the stable part.
