# Instagram — alternative login paths (one-tap, Credential Manager, Google, SmartLock)

App: `com.instagram.android` v433.0.0.47.68 (`version_code` 383909338)

Besides username + password (`accounts/login/`, see `login-http-api.md`),
Instagram supports several "no-password" entry paths. This doc maps them.

## One-tap / saved login

After a successful login the server returns one-tap login nonces; on later
launches the app can re-authenticate with just a stored nonce + user id via
`accounts/one_tap_app_login/` (`X/55W.A0D`, see the login API doc).

The nonces and account list are persisted on-device:

- **`IgClientNonceStore` (`X/2vN`, `smali_classes2/X/2vN.smali`)** — the device
  nonce store, anchored on the SharedPreferences key `client_nonces`. Holds
  per-type / per-user nonce maps (read on `A01`, written on `A02`); the login
  API also references `vetted_device_nonces`. This is the only class in this
  area with a globally-unique string anchor, so it is the only one signatured.
- One-tap response handling and account caching are spread across helper
  classes (e.g. the response handler that registers
  `one_tap_login_nonce_callback`, and an account cache backed by an
  E2E-token store keyed `xapp.e2e.tokens`). Those strings are **not** unique
  (2–3 classes each), so those helpers are documented here but not signatured —
  they would need a compound anchor to pin safely.

## Android Credential Manager (passwords + passkeys)

These classes keep their real package names
(`com.instagram.login.credentialmanager.*`, **un-obfuscated**), so the map adds
no name-recovery value for them — they're recorded here for completeness:

- **`CredentialManagerSaveHelper`** — saves the just-used password into the
  system credential store via `androidx.credentials`
  (`CreatePasswordRequest` → `CreatePasswordResponse`).
- **`CredentialManagerFetchHelper`** — fetches a saved password credential to
  pre-fill / auto-login.
- **`SignInWithGoogleLoginFetchHelper`** — "Sign in with Google" via
  `androidx.credentials` + a `GetGoogleIdOption`, using the hard-coded IG web
  OAuth client id `894032761246-…apps.googleusercontent.com`. The resulting
  Google ID token feeds `accounts/google_token_users/` (`X/55W.A07`) to find
  matching IG accounts, then login proceeds.

## Google SmartLock (legacy)

- **`com.instagram.login.smartlock.impl.SmartLockPluginImpl`** (un-obfuscated) —
  the older Google SmartLock-for-Passwords broker integration, still bundled.
  Superseded in practice by Credential Manager above. Holds weak-ref maps of
  pending broker callbacks; delegates the actual broker ops to a base class.

## Why most of these are NOT in the signatures file

Two reasons, both deliberate (see `AGENTS.md` anti-scope):

1. **Already un-obfuscated.** The Credential Manager / SmartLock classes keep
   their real FQNs — sigmatcher would resolve `original == new`, which is a
   finding (recorded here) but not a useful map entry.
2. **No unique anchor.** The one-tap helper strings (`one_tap_login_nonce_callback`,
   `xapp.e2e.tokens`) each appear in 2–3 classes, so a single-string signature
   would be ambiguous and rotation-fragile. Only `X/2vN` (`client_nonces`,
   unique) is signatured.

The login *entry points* for all these paths (`accounts/one_tap_app_login/`,
`accounts/google_token_users/`) are already captured as methods of
`IgAccountsLoginApi` (`X/55W`) in the map.
