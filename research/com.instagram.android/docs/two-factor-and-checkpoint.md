# Instagram — two-factor login, trusted-device & checkpoint

App: `com.instagram.android` v433.0.0.47.68 (`version_code` 383909338)

When `accounts/login/` returns `two_factor_required: true` (instead of a
`logged_in_user`), the app enters the 2FA flow. This doc maps the API calls,
the response models, and the trusted-notification ("approve from another
device") path. Obfuscated↔logical names are in the map; this is the behaviour.

## Response routing

The `accounts/login/` JSON is parsed by **`X/GHs`** (logical
`IgLoginResponseParser`, `smali_classes9/X/GHs.smali`). It dispatches on the
top-level keys and decides the next step:

- `logged_in_user` → success.
- `invalid_credentials` (unique to this class — the signature anchor) → wrong
  password.
- `two_factor_required` + `two_factor_info` → hand off to the 2FA sub-parser
  (`X/GI1`, which fills a `TwoFactorInfo` model `X/KTj`).
- `checkpoint_url` / `challenge_required` → checkpoint/challenge flow.

`TwoFactorInfo` (`X/KTj`) carries the method availability flags and routing
data: which second factors are enabled (`sms_two_factor_on`,
`whatsapp_two_factor_on`, `totp_two_factor_on`), the obfuscated phone hint, the
two-factor identifier/nonce, and trusted-notification polling nonces. (These
JSON keys are shared across several parser/model classes, so `X/KTj`/`X/GI1`
are documented here but are NOT given standalone signatures — none has a
globally-unique string anchor; only `X/GHs` does, via `invalid_credentials`.)

## Two-factor API calls

Each of these is its own `X/<token>` class, uniquely anchored on its endpoint
(see the map):

| logical name | endpoint | role |
|--------------|----------|------|
| `IgTwoFactorLoginApi` (`X/LbY`) | `accounts/two_factor_login/` | submit the 2FA code (`verification_code`, `verification_method`, `two_factor_identifier`, `trust_this_device`, `phone_id`, `trusted_notification_polling_nonces`) to complete login |
| `IgTrustedNotificationStatusApi` (`X/LFd`) | `two_factor/check_trusted_notification_status/` | poll whether the user approved the login from a trusted device (push-approval 2FA) |
| `IgTwoFactorSupportApi` (`X/Hd3`) | `two_factor/start_two_fac_support/` | start the 2FA support/help flow when the user is locked out |
| `TwoFacLoginVerifyFragment` (`X/Dw5`) | (UI) + `accounts/send_two_factor_login_sms/` | the code-entry screen; also (re)sends the login SMS. Kept `__redex_internal_original_name = "TwoFacLoginVerifyFragment"` is a second unique anchor. |

### Trusted-notification ("login approved on another device")

`X/LFd` polls `two_factor/check_trusted_notification_status/` with the device
identifier + a set of `trusted_notification_polling_nonces`. While the entry
screen (`X/Dw5`) is open, the app loops this poll; when the status flips to
approved, it completes via `X/LbY` (`accounts/two_factor_login/`) carrying the
matched nonce — so the user never types a code.

## Checkpoint / challenge

A login can also return a **checkpoint** (`checkpoint_url`) or **challenge**
(`challenge_required`) instead of 2FA. These are parsed by the generic API
response/error model (the `checkpoint_url` / `error_type` / `error_reason`
carrier) and route into the server-driven (Bloks) challenge UI. The challenge
flow is overwhelmingly server-driven, so there is little first-party logic to
map beyond the response fields; these classes share their JSON-key strings
across many models and were not given standalone signatures (no unique anchor).

## Confidence

`X/LbY`, `X/LFd`, `X/Hd3`, `X/Dw5`, `X/GHs` are **high** — each is pinned on a
globally-unique endpoint or marker string (verified `rg -l` count == 1). The
response sub-models (`X/KTj`, `X/GI1`, and the checkpoint carriers) are
identified by code/JSON shape but intentionally left out of the signatures
because their string anchors are not unique enough to survive rotation safely.
