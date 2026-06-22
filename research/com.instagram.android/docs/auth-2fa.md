# Auth / Login & 2FA / Security

The login client surface (CAA-era login, signup, one-tap/saved login, federated
login) and the **two-factor / security** surface (TOTP, SMS, WhatsApp 2FA, trusted
devices, login activity). This is defensive/educational mapping of the public
client surface — class identity only, no secrets. The API caller classes are
renamed `X/` utility classes anchored on their unique REST endpoint strings; the
UI fragments are renamed but recovered via `__redex_internal_original_name`; the
data models keep their FQCN. Logical→obfuscated names are in the map +
`signatures.yaml`.

## Auth / Login

- **`LoginApi`** (renamed `X.55W`) is the central login REST request builder;
  `accounts/login/` is the main auth call and `accounts/one_tap_app_login/` the
  saved-login call. **`SignupApi`** (renamed `X.LMf`) builds `accounts/create/`.
- **`LoginResponseParser`** (renamed `X.GHs`) parses the login response
  (`logged_in_user`, `created_user`, `mac_login_nonce`, `trusted_device_nonce`,
  `session_flush_nonce`) — the session-model + 2FA-required parser.
- UI/flow fragments (renamed, recovered by redex name): `LoginLandingFragment`,
  `OnePageRegistrationFragment`, `CaaLoginOneTapLogOutFragment` (CAA unified
  login), `ManageSavedLoginFragment`, `LoginNotificationApproveFragment` (approve a
  new-device login), plus the `FacebookLoginHelper`/`LoginUtil` helpers.
  `CredentialManagerFetchHelper` (kept) is the Android CredentialManager one-tap
  path.

## 2FA / Security / Trusted devices

- **`TwoFactorApi`** (renamed `X.LbY`) is the 2FA REST caller
  (`accounts/two_factor_login/`, `accounts/account_security_info/`,
  SMS enable/info). **`TrustedDeviceNotifApi`** (renamed `X.LFd`) is the
  trusted-notification (push-approval) polling path
  (`two_factor/check_trusted_notification_status/`).
- UI fragments (renamed, recovered by redex name): `AccountSecurityFragment`
  (2FA/security hub), `TwoFacLandingFragment`, `TwoFacAuthenticatorAppSetupFragment`
  (TOTP setup), `TwoFacLoginVerifyFragment`, `TwoFacTrustedDevicesFragment`, and
  `LoginActivityFragment` (login-sessions list).
- Data models (kept FQCN): **`TwoFactorInfoConfig`** (`com.instagram.login.api`) —
  the full 2FA config dump (`is_totp_two_factor_enabled`,
  `is_whatsapp_two_factor_enabled`, trusted-notification eligibility);
  **`TotpSeedImpl`** (`…twofac.model`) — a TOTP seed (timestamp/name/seed);
  **`TrustedDevice`** (`…twofac.model`) — a trusted device (lat/lng/timestamp/UA/
  active).

Anchoring note: many in-body auth UI strings (`trusted_devices`, `login_activity`,
`arg_backup_codes`) are NOT unique across classes; the durable anchors are the
unique REST endpoint paths and the `__redex_internal_original_name` fields, which
is what the signatures use.
