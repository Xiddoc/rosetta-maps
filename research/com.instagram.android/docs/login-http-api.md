# Instagram — Login HTTP API surface

App: `com.instagram.android`
Version: `433.0.0.47.68` (`version_code` 383909338)
Scope: the private-API endpoints the app calls to authenticate a user, and the
request bodies it builds. Obfuscated class identities and their stable anchors
live in `signatures/com.instagram.android/signatures.yaml`; the resolved
obfuscated↔logical names live in `maps/com.instagram.android/383909338.json`.
This doc records *what the code does*.

## Obfuscation model (important context)

Instagram is built with R8 + Facebook's internal tooling. The result here:

- **Package names are mostly preserved** for first-party feature code
  (`com.instagram.login`, `com.instagram.nux.hybridlogin`,
  `com.instagram.login.credentialmanager`, …). These are *not* name-rotated and
  can be matched by their real FQN.
- **The bulk of logic is flattened into a single synthetic `X` package**
  (`LX/55W;`, `LX/ioi;`, `LX/21G;`, …). Every one of these short tokens
  (`55W`, `ioi`, …) **rotates between releases** and is worthless as an anchor.
- **String literals survive.** API endpoint paths (`accounts/login/`), POST
  field names (`enc_password`, `guid`), analytics event names
  (`instagram_client_password_encryption_encrypt_attempt`) and the hard-coded
  bootstrap public key are all present verbatim. Those are the rotation-stable
  anchors used in the signatures file.

So the research method for IG is: **find the endpoint/field string, then walk
out from the `X/<token>` class that contains it.**

## The login API factory — `X/55W` (logical: `IgAccountsLoginApi`)

`smali_classes9/X/55W.smali` is the single class that constructs every
authentication-related request. Each method returns an `LX/2LZ;` (the IG API
request object) built from an `LX/2k4;`/`LX/17c;` request builder. The methods
and their endpoints:

| method | endpoint | purpose |
|--------|----------|---------|
| `A08`  | `accounts/login/` | **primary username/password login** |
| `A0D`  | `accounts/one_tap_app_login/` | one-tap login with a stored nonce |
| `A03`  | `accounts/account_recovery_code_login/` | login via recovery code |
| `A02`  | `accounts/account_recovery_code_verify/` | verify a recovery code |
| `A01`  | `accounts/assisted_account_recovery/` | assisted account recovery |
| `A06`  | `accounts/send_password_reset/` | trigger password-reset |
| `A0C`  | `accounts/send_recovery_flow_email/` | send recovery email |
| `A07`  | `accounts/google_token_users/` | look up accounts for a Google token (Sign in with Google) |
| `A05`  | `accounts/register_feo2_service/` | FEO2 / encryption-service registration |

(`A04`, `A09`, `A0E`–`A0G` build registration / NUX variants of the same
request shapes; `A0B` returns the cached `adid`.)

### `A08` — the primary login request

Signature:
`A08(LX/2s4; session, String country_codes, String password_value2, String sn_nonce, String sn_result, String guid, String password, String stop_deletion_token, String username, List google_tokens, int login_attempt_count) -> LX/2LZ;`

Body fields added to the `accounts/login/` POST (`smali_classes9/X/55W.smali:611-685`):

- **`enc_password`** — the encrypted password. Built by
  `LX/21G;->A0h(session, plaintextPassword)` (`smali_classes9/X/21G.smali:763`),
  which instantiates `LX/ioi;` and calls `A00(password)`. See
  `password-encryption.md`.
- **username / password keys** — supplied by `LX/281;->A00()` and
  `LX/281;->A01()` (obfuscated string providers that return the literal field
  keys at runtime, e.g. `username`, `phone_id`).
- **`guid`**, **`adid`** (`A0B()`), **`login_attempt_count`** — device + retry
  identity.
- **`google_tokens`** — JSON array, populated from the `List` arg; ties the
  Google-token-users / Smart-Lock path into login.
- **`sn_nonce`**, **`sn_result`** — signal-collection nonce/result
  (anti-automation / integrity signals) added with `A0D` (optional put).
- **`country_codes`**, **`stop_deletion_token`** — optional; the latter lets a
  login cancel a pending account deletion.

The request then runs through the shared IG request post-processors
(`LX/215;->A1J`, `LX/21R;->A0k`, `LX/206;->A0S`) that attach standard IG headers
and the signed body — see `http-signing.md`.

## Where these requests originate

- `com.instagram.nux.hybridlogin` — the NUX (new-user-experience) login UI/VMs.
  `HybridLoginWithQRViewModel` (`smali_classes8/...`) drives QR / cross-device
  login and polls a validation endpoint.
- `com.instagram.login.loggedoutapp` — the logged-out shell
  (`LoggedOutAppActivity`, `IGLoggedOutAppUseCase`).
- Much of the surrounding *flow* (forms, error handling, step routing) is
  server-driven via **Bloks**, so the Java/smali side is mostly the API factory
  plus response models, not screen logic.

## Confidence

`X/55W` identity is **high**: it is uniquely identified by the cluster of
`accounts/*` endpoint string literals it contains (no other class holds this
set). The per-method→endpoint mapping is read directly from the `const-string`
immediately preceding each `LX/2k4;->A08(path)` call.
