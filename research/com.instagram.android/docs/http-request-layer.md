# Instagram — the API request / signing layer (architecture notes)

App: `com.instagram.android` v433.0.0.47.68 (`version_code` 383909338)

Context for the login docs: every `accounts/*` call in `login-http-api.md` is
built on a shared request stack. This doc records that architecture so the
login flows make sense. **None of these classes are in the signatures file** —
they are anchored only on strings shared across many classes (`signed_body`,
`SIGNATURE.%s`, `X-IG-App-ID`) or on structural traits, so a single-string
sigmatcher rule cannot pin them uniquely/stably. They are documented, not
mapped.

## The request builder stack (all in package `X`, names rotate)

- **Request builder base** (`X/2k4`-family) — the mutable builder the login API
  factory talks to. Methods seen from `X/55W`:
  - `A08(path)` sets the endpoint (`accounts/login/`),
  - `ADN(key, value)` / `A0D(key, value)` add required / optional POST params,
  - the builder is finalised into the request object via the `X/215`/`X/21R`
    post-processors.
- **Request object** (`X/2LZ`) — what every `X/55W` login method returns. It is
  the executable request whose response is later parsed (e.g. by `X/GHs`).
- **Session types** — login methods take a session arg:
  - a logged-out / device session wrapper (carrying the
    `IgSessionManager.LOGGED_OUT_TOKEN`) for pre-auth calls, and
  - `com.instagram.common.session.UserSession` (un-obfuscated, kept) for
    authenticated calls like `register_feo2_service`.

## Request signing

Instagram signs request bodies: the builder emits a `signed_body` parameter of
the form `SIGNATURE.<payload>` (the literal format string `SIGNATURE.%s` is
present). Standard IG headers (`X-IG-App-ID`, `X-IG-Capabilities`, device
descriptors) are attached by the shared post-processors (`X/215;->A1J`,
`X/21R;->A0k`, `X/206;->A0S`) invoked from `X/55W.A08`. The `signed_body` /
`SIGNATURE.%s` strings live in more than one class (the builder and a GraphQL
variant), which is exactly why they are not usable as unique anchors.

## Practical takeaway for the adapters

To observe a login request end-to-end at runtime, the stable, uniquely-pinned
hook points are in the map:

1. `IgPasswordEncrypter.encryptPassword` (`X/ioi.A00`) — plaintext in,
   `enc_password` out (see `password-encryption.md`).
2. `IgAccountsLoginApi.login` (`X/55W.A08`) — assembles the `accounts/login/`
   body (`enc_password`, `guid`, `adid`, nonces, …).
3. `IgLoginResponseParser` (`X/GHs`) — parses the response and branches to
   success / 2FA / checkpoint.

The request-builder/signing classes above sit between (2) and the socket but
are best reached by hooking the pinned endpoints rather than by name, given
their rotation-fragile anchors.
