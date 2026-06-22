# Instagram sign-up / registration HTTP surface

Findings for `com.instagram.android` **v433.0.0.47.68** (version_code
`383909338`). Obfuscated names below are this build's `LX/…` tokens — they
**rotate every release**, so treat them as illustrative; the durable identity
is the server endpoint path string each class emits (the anchors in
`signatures/com.instagram.android/signatures.yaml`, resolved into
`maps/com.instagram.android/383909338.json`).

All `file:line` references are into the apktool smali tree
(`out/apktool/smali_classes9/…`), which is the ground truth sigmatcher matches
against. The decompiled tree is **not** committed (Hard rule 3).

## How an Instagram API call is built (`IgApi` request-builder primitives)

Every endpoint below is assembled the same way: the app creates a request
builder, sets the path, appends form params, then materialises a request
object. The builder is the obfuscated class **`LX/2k4`** (`smali_classes3`),
with a small, stable method vocabulary worth recognising because every signup
class calls it:

| builder method | meaning |
|----------------|---------|
| `ADN(String key, String val)` | add a POST param unconditionally (the base add) — `2k4.smali:3907` |
| `A0D(String key, String val)` | add the param **only if value != null** (null-guarded) — `2k4.smali:3789` |
| `A0E(String key, boolean)` | add boolean serialised as `"true"`/`"false"` — `2k4.smali:3804` |
| `A0F(String key, boolean)` | add boolean serialised as `"1"`/`"0"` — `2k4.smali:3816` |
| `A0G(String path, Object[] args)` | set a formatted path + args |
| `A08(String path)` | set the endpoint path directly (the most common form — every newly-added builder below calls `2k4->A08("…")`) |
| field `A0G:Ljava/lang/String;` | the **endpoint path** is stored here (e.g. `iput "accounts/create/"`) |
| `A0I()` → `LX/2LZ;` | build the final request object (`LX/2k3.A0I`) |

Some builders set the path through a small static helper instead of calling
`A08` directly — e.g. `LX/21R->A0m(2k4, path, int, int)` (used by the consent
age gate) and `LX/206->A0n(Context, 2k4, path)` (used by the consent flow). The
endpoint string literal still lives in the calling method either way, so it
remains the durable anchor.

`LX/2LZ` is the resolved request; `LX/4br` / `LX/1pp` are the session/handle
types passed into most builders. These are shared infrastructure outside the
signup scope, so the signup map references them by their (rotating) descriptors
rather than mapping them.

## Endpoint → builder class map

Each path string was verified **globally unique** in this build (exactly one
class emits it), which is what makes it a reliable anchor.

| endpoint(s) | logical class (map) | this build |
|-------------|---------------------|------------|
| `accounts/create/`, `accounts/create_validated/` | `AccountCreateApi` | `LX/LMf` |
| `accounts/create_business/` | `AccountCreateBusinessApi` | `LX/O0A` |
| `multiple_accounts/create_secondary_account/` | `CreateSecondaryAccountApi` | `LX/LMh` |
| `accounts/send_signup_sms_code/`, `accounts/send_verify_email/` | `SendSignupSmsCodeApi` | `LX/LUe` |
| `accounts/validate_signup_sms_code/` | `ValidateSignupSmsCodeApi` | `LX/LfL` |
| `accounts/check_confirmation_code/` | `CheckConfirmationCodeApi` | `LX/E4z` |
| `accounts/verify_email_code/` | `VerifyEmailCodeApi` | `LX/Li1` |
| `accounts/check_phone_number/` | `CheckPhoneNumberApi` | `LX/I00` |
| `accounts/username_suggestions/` | `UsernameSuggestionsApi` | `LX/E1z` |
| `accounts/process_contact_point_signals/` | `ProcessContactPointSignalsApi` | `LX/Jt9` |
| `accounts/vetted_phone_reg_login/` | `VettedPhoneRegLoginApi` | `LX/Okp` |
| `fb/facebook_signup/`, `fb/nux_fb_connect/` (+ `accounts/one_tap_app_login/`) | `IgAccountsLoginApi` (login work; see `login-http-api.md`) | `LX/55W` |
| `fb/fb_reg_flag/` | `FbRegFlagApi` | `LX/NmR` |
| `nux/new_account_nux_seen/` | `NewAccountNuxSeenApi` | `LX/JZv` |
| `consent/check_age_eligibility/` | `CheckAgeEligibilityApi` | `LX/Dv3` |
| `consent/get_signup_config/` | `GetSignupConfigApi` | `LX/KXf` |
| `consent/new_user_flow/` | `NewUserFlowApi` | `LX/LBE` |
| `consent/new_user_flow_begins/` | `NewUserFlowBeginsApi` | `LX/JTn` |
| `accounts/prime_app_onboarding_login/` | `IGLoggedOutAppUseCase` (kept name) | `com.instagram.login.loggedoutapp.usecase.IGLoggedOutAppUseCase` |

Several already-mapped classes turned out to host **more than one** sign-up
endpoint (one obfuscated builder class, several request methods or a
path-switch). These extra endpoints were folded into the existing class entries
rather than duplicated as new classes:

| existing class | extra endpoint(s) | same method? |
|----------------|-------------------|--------------|
| `AccountCreateBusinessApi` (`O0A`) | `accounts/create_business_validated/` | yes — path switch in `run()V` |
| `CreateSecondaryAccountApi` (`LMh`) | `multiple_accounts/create_secondary_ai_account/` | yes — path switch in the one builder |
| `CheckPhoneNumberApi` (`I00`) | `users/check_email/` | yes — same lookup method |
| `VerifyEmailCodeApi` (`Li1`) | `accounts/verify_sms_code/`, `users/check_username/` | no — three distinct methods (`A00`/`A09`/`A03`) |

## Account creation — `AccountCreateApi` (`accounts/create/`)

`LX/LMf->A00(Context, LX/4br session, RegFlowExtras, Integer mode, String loggedInUserId, String authToken)` → `LX/2LZ`.

The single method builds the whole create payload (`LMf.smali:33`):

- **Path selection** by the `Integer mode` arg (an `LX/008` boxed enum):
  `A00` → `accounts/create/`; `A01` → `accounts/create_validated/`; else empty
  (`LMf.smali:48,267-279`).
- **Device / tracking identity**: `_uuid` and `adid` (device id via
  `LX/2t3->A07`), `google_ad_id` (read from the `google_ad_id` pref, empty if
  absent), and a fresh `waterfall_id` (`LX/5xn->A01`) that ties every event in
  one signup attempt together (`LMf.smali:106-145`).
- **Birthday** pulled from `RegFlowExtras.A02` (a `UserBirthDateImpl`) and split
  into `year` / `month` / `day` params (`LMf.smali:196-251`,
  `UserBirthDateImpl` fields `A02`=year, `A01`=month, `A00`=day).
- **Supervised / teen accounts**: `supervised_user_consent_token` from
  `RegFlowExtras.A0e`, plus `logged_in_user_id` /
  `logged_in_user_authorization_token` (null-guarded via `A0D`) so a guardian's
  session can vouch for the new account (`LMf.smali:170-186`).
- **`do_not_auto_login_if_credentials_match`** toggled from the reg flow type
  (`RegFlowExtras.A02()` vs `LX/IHi.A0B`) (`LMf.smali:155-168`).
- **`intent` / `surface` / `secondary_account_intent`** packed as a nested JSON
  object when `RegFlowExtras.A0V`/`A0W` are present (`LMf.smali:281-297`).

The password is **not** sent here in plaintext — see *Password sealing*.

## Business account creation — `AccountCreateBusinessApi` (`accounts/create_business/`)

`LX/O0A` is a `Runnable`-shaped class; its `run()` builds the request. Beyond
the create fields it adds `enc_password` (sealed, below), `category_id`,
`page_id`, `to_account_type`, `should_show_category`,
`should_show_public_contacts`, and `professional_signup_source_*`
provenance params (`O0A.smali:288-308`).

## Add a second account — `CreateSecondaryAccountApi`

From a logged-in session: `main_user_id` + `main_user_authorization_token`
authenticate the parent account, and the
`should_link_to_main` / `should_cal_link_to_main` /
`should_copy_consent_and_birthday_from_main` flags control whether the new
account inherits the parent's birthday/consent.

## Phone & email confirmation

- **`SendSignupSmsCodeApi`** (`accounts/send_signup_sms_code/`, also
  `accounts/send_verify_email/`): kicks off OTP delivery. Params include
  `phone_id`, `guid`, `waterfall_id`, `android_build_type`, `big_blue_token`,
  `fb_access_token`/`google_tokens` (when continuing from FB/Google),
  `auto_confirm_only`, and a `screen`/`landing` for the originating UI.
- **`ValidateSignupSmsCodeApi`** (`accounts/validate_signup_sms_code/`):
  submits `phone` + the typed code and, notably, reports **SMS-retriever
  telemetry** — `ig_android_sms_retriever_started`,
  `ig_android_sms_retriever_error`, `sms_permission_allowed`, `duration`,
  `error_type` — i.e. whether the Google SMS Retriever auto-read the code.
- **`CheckConfirmationCodeApi`** (`accounts/check_confirmation_code/`):
  generic email-code check; a `mode`/flag pair distinguishes
  `sign_up_email_code_confirmation` from `recovery_email_code_confirmation`.
- **`VerifyEmailCodeApi`** (`accounts/verify_email_code/`): verifies an email
  code and can ride along profile edits (`first_name`, `biography`, link
  metadata) when reg and profile setup are merged.

## Pre-fill & username

- **`CheckPhoneNumberApi`** (`accounts/check_phone_number/`): pre-reg lookup of
  a phone number; carries one-tap material (`login_nonce_map`, `login_nonces`,
  `big_blue_token`, `qe_id`, `prefill_shown`) so an existing user is steered to
  login instead of signup.
- **`ProcessContactPointSignalsApi`** (`accounts/process_contact_point_signals/`):
  uploads `sim_phone_number` + `google_tokens` + `phone_id` to drive contact
  prefill.
- **`UsernameSuggestionsApi`** (`accounts/username_suggestions/`): asks the
  server for username candidates from `name`/`email`, and **echoes the client's
  own password judgement** as params — `valid_password`, `password_too_short`,
  `password_blacklisted` — alongside `one_page_registration`,
  `nux_contacts_upsell_viewed`, and `is_ci_opt_in` (contact-import opt-in).

## Federated / alternative sign-up entry points

Beyond the e-mail+password and phone reg paths, the app carries several
builders for sign-up routes that start from an existing identity or that gate
account creation:

- **Facebook SSO sign-up** lives on the obfuscated class `LX/55W`, which the
  login work already maps as **`IgAccountsLoginApi`** (the `accounts/*` login /
  recovery factory — see `login-http-api.md`). The sign-up-relevant methods on
  it are `fb/facebook_signup/` (create a brand-new IG account from a Facebook
  access token — the FB-SSO sign-up; the widest param set: FB token, name, and a
  row of boolean flags controlling consent/auto-follow/cross-posting) and
  `fb/nux_fb_connect/` (link a Facebook account during new-user onboarding).
  These two are added as methods on `IgAccountsLoginApi` rather than as a
  separate class, since `accounts/one_tap_app_login/` (same class) was already
  mapped there by the login work.
- **`VettedPhoneRegLoginApi`** (`LX/Okp`) — `accounts/vetted_phone_reg_login/`.
  When a phone number entered during registration already maps to a "vetted"
  device, the flow logs straight into the existing account instead of creating
  a new one. The builder is a Kotlin `Function0` lambda, so the request is
  assembled in its `invoke()`.
- **`FbRegFlagApi`** (`LX/NmR`) — `fb/fb_reg_flag/`. Queries/sets the
  Facebook-registration flag for an FB-linked reg attempt (does this FB user
  already have, or is currently creating, an IG account).
- **`IGLoggedOutAppUseCase`** (kept name) —
  `accounts/prime_app_onboarding_login/`. Pre-warms a login session for the
  logged-out app shell so the first real sign-in is fast. The class keeps its
  real name through R8; only its builder method (`A00`) is obfuscated.

## Age gate, consent & onboarding config

These shape the reg flow before/around account creation rather than creating
the account themselves:

- **`CheckAgeEligibilityApi`** (`LX/Dv3`) — `consent/check_age_eligibility/`.
  The age gate: validates the entered birthday against the minimum-age policy
  before creation proceeds. Path is set via the `LX/21R->A0m` helper.
- **`GetSignupConfigApi`** (`LX/KXf`) — `consent/get_signup_config/`. Fetches
  the server-driven sign-up configuration (which steps/fields this
  client/region must present), i.e. the reg flow is partly server-parameterised.
- **`NewUserFlowApi`** (`LX/LBE`) / **`NewUserFlowBeginsApi`** (`LX/JTn`) —
  `consent/new_user_flow/` and `consent/new_user_flow_begins/`. Drive the
  new-user consent flow (ToS / privacy / data-policy gates) and signal its
  start. `NewUserFlowApi` sets its path via the `LX/206->A0n` helper.
- **`NewAccountNuxSeenApi`** (`LX/JZv`) — `nux/new_account_nux_seen/`. Marks a
  freshly-created account as having seen the new-account NUX, gating
  post-signup education surfaces.

## Endpoints deliberately left unmapped (ambiguous anchors)

Two sign-up-adjacent endpoints were found but **not** given signatures, because
no clean globally-unique single-class anchor exists for them (per the skill's
anchoring rules, a one-version/ambiguous anchor is worse than none):

- **`accounts/contact_point_prefill/`** is emitted by **three** different
  builder classes (this build: `LX/59T`, `LX/DzG`, `LX/JvG`) plus referenced in
  `OnboardingActivity` — three real surfaces calling the same prefill endpoint,
  so a `count: 1` anchor would be ambiguous. The related, stable
  `accounts/process_contact_point_signals/` is mapped instead.
- **`accounts/enable_sms_consent/`** appears both in its builder (`LX/1vT`) and
  in a large path-constants **string table** class (`LX/00B`), so the path
  string alone resolves to two classes. It is a peripheral SMS-consent toggle,
  so it was left out rather than carrying a second disambiguating anchor.

## Password sealing (`enc_password`)

Instagram never posts the raw password during signup; it posts an `enc_password`
string of the form **`#PWD_INSTAGRAM:4:<unix_time>:<base64 sealed box>`**.

- The encryptor is **`LX/ioi`**; `ioi->A00(String plaintext)` returns the
  `enc_password` value and is called right before
  `ADN("enc_password", …)` (`O0A.smali:283-298`).
- The actual sealing is delegated to **`LX/ijJ`**, whose static version field
  `ijJ.A03:I` is set to **`4`** (the `:4:` scheme version) in
  `ioi`'s constructor (`ioi.smali:42-44`). The public key it seals against comes
  from `LX/96x` (the password-encryption keystore, fetched from the server),
  selected by key id.
- The timestamp is the current time formatted with `"%d"`
  (`ioi.smali:120-135`) and becomes the `:<time>:` segment.
- The `#PWD_*` tag family lives in the enum **`LX/fmF`** (`#PWD_INSTAGRAM`,
  `#PWD_ENC`, `#PWD_MSGR`, `#PWD_FB4A`, …) — `fmF.smali:34-59`.

This is the standard Meta "password encryption" (NaCl/libsodium sealed box to a
server-published public key, versioned `4`). `ioi`/`ijJ`/`96x` are shared
login+signup infrastructure; they have no stable string anchor of their own, so
they are documented here but intentionally **not** carried as signatures (an
anchor on a rotating token would break next release — see the skill's anchoring
rules).

## Reg-flow model (`RegFlowExtras`, `UserBirthDateImpl`)

These two keep their real names through R8 (they're (de)serialised), so they're
stable map anchors in their own right:

- **`com.instagram.registration.model.RegFlowExtras`** — the mutable bag carried
  across every reg screen. Fields touched by the builders above include `A02`
  (the `UserBirthDateImpl`), `A0e` (`supervised_user_consent_token`), `A0V`
  (`intent`), `A0W` (`surface`), `A0R` (the plaintext password handed to the
  sealer).
- **`com.instagram.registration.model.UserBirthDateImpl`** — `A02`=year,
  `A01`=month, `A00`=day (ints), split into the `year`/`month`/`day` params.

## Verification status & caveats

- This sign-up work adds **20 new classes** to the shared
  `com.instagram.android` map (which now totals **53**), plus the two FB
  sign-up methods folded into the login work's `IgAccountsLoginApi` (`LX/55W`).
  Every entry **resolves cleanly** under `sigmatcher analyze` against this APK
  (no `Found no matches`, no ambiguity); each API-class anchor was confirmed
  globally unique. The multi-endpoint classes were verified to switch path
  within one method vs. split across distinct methods before being encoded as
  extra anchors vs. extra method entries — so no overload collides. The one
  obfuscated class shared with the login work (`LX/55W`) is mapped once, as
  `IgAccountsLoginApi`, not duplicated.
- **Single-version only.** Per the methodology, true rotation-stability is
  proven by resolving the *same* signatures against a second version. Only
  v433.0.0.47.68 was available here, so cross-version portability is **asserted
  by anchor design** (stable server paths) but **not yet empirically verified**.
  Re-run `sigmatcher analyze` against an adjacent build to close this out.
- The map's tier-1 semantic `referenced-types` sub-check auto-skips for this
  map (a `::warning`, not an error) because Instagram's R8 namespace is the
  dotted `X.` package, from which the validator can't derive a single-segment
  obfuscation alphabet. Shared infra types (`LX/2LZ`, `LX/4br`, …) referenced in
  method descriptors are deliberately left unmapped — out of signup scope.
