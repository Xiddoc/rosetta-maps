# Instagram — device identity, request signing & auth-token headers

App: `com.instagram.android` v433.0.0.47.68 (`version_code` 383909338)

This is the machinery that identifies and authenticates the client to the IG
server on every request — the layer underneath `login-http-api.md`. All
obfuscated classes below are pinned on globally-unique string literals
(`rg -l` count == 1); obfuscated↔logical names are in the map.

## Outbound: how a request is identified & signed

- **`IgHeaderServiceLayer` (`X/5px`)** — the request interceptor that attaches
  Instagram's custom headers. For `instagram.com` hosts it sets
  `X-IG-Capabilities`, `X-IG-App-ID`, and `X-IG-Connection-Type` (falling back
  to `X-FB-Connection-Type` for other hosts), deriving the connection type from
  `ConnectivityManager`. Anchored on its identity string
  `InstagramSpecificHeaderServiceLayer`. (Header *names* like `X-IG-App-ID`
  appear in dozens of classes — a shared string pool — so they are NOT used as
  anchors; the service-layer identity string is.)

- **`IgSignedGraphQLRequestBuilder` (`X/6yX`)** — builds **signed** request
  bodies for the IG GraphQL endpoints (`/api/v1/wwwgraphql/ig/query/`,
  `/api/v1/ads/graphql/`). It emits the `signed_body` param as `SIGNATURE.<…>`
  plus `strip_nulls` / `strip_defaults` / `vc_policy` / `client_doc_id` /
  `surface`. Anchored on the unique endpoint `/api/v1/wwwgraphql/ig/query/`
  (the `signed_body` / `SIGNATURE.%s` strings are shared with the REST builder
  `X/2k4`, so they are not used as the anchor). The HMAC key itself is not a
  smali literal.

- **`IgGraphQLRequestTask` (`X/6zC`)** — the `Callable` that actually runs a
  GraphQL request, attaching `X-FB-Friendly-Name`, `x-graphql-client-library`,
  and `x-ig-graphql-region-hint`. Anchored on `X-FB-Friendly-Name` (unique).

- **`IgDeviceIdGenerator` (`X/2t3`)** — generates the stable device id
  (`phone_id` / `device_id`). It reads `Settings.Secure.ANDROID_ID`, **rejects
  three well-known bad/emulator ANDROID_IDs** (`9774d56d682e549c`,
  `9d1d1f0dfa440886`, `fc067667235b8f19`), and otherwise derives an `android-…`
  UUID it persists to a file. Anchored on the blacklist constant
  `9774d56d682e549c` (unique).

## Inbound: server-pushed identity & auth tokens

- **`IgAuthHeaderResponseHandler` (`X/6je`)** — parses IG's `*-Set-*` response
  headers and updates local auth/device state:
  - `IG-Set-Authorization` (`Bearer IGT:2:…`) → stores the IG auth token (IGT);
  - `IG-Set-X-MID` → the machine id (MID);
  - the `IG-SET-IG-U-*` family — `…SHBID`, `…SHBTS`, `…DS-USER-ID`, `…RUR`
    (region/routing hint) — session-routing state;
  - `X-IG-Set-WWW-Claim` → the `www_claim` echoed on later requests.

  Anchored on `IG-SET-IG-U-RUR` (unique; the other header names each recur in
  2–3 classes, so they are documented but not used as the anchor).

## Anti-abuse signals (igsignals) — documented, not signatured

The `com.instagram.igsignals.*` package and `IgSignalsCasper` keep their real
names (un-obfuscated). They run an on-device Device-Consistency-Policy (DCP)
predictor — collecting weighted signals (`IgSignalsFeature` = name/weight/value)
into a risk score used for account-abuse/integrity decisions, surfaced into
requests (e.g. the `sn_nonce`/`sn_result` seen on `accounts/login/`). Because
the package is un-obfuscated, it is described here rather than mapped.

## Hook points

- `IgSignedGraphQLRequestBuilder` (`X/6yX`) — observe the pre-signature GraphQL
  body and the resulting `signed_body`.
- `IgHeaderServiceLayer` (`X/5px`) — see/modify the IG headers on every request.
- `IgAuthHeaderResponseHandler` (`X/6je`) — read the freshly-issued IGT / MID /
  www-claim as the server rotates them.

## Confidence

`X/5px`, `X/6yX`, `X/6zC`, `X/2t3`, `X/6je` are **high** — each pinned on a
unique endpoint/identity/blacklist string reached by live code and corroborated
by the surrounding header/endpoint constants. The token-cache helper the agent
flagged (`X/2pi`) had no unique string anchor and is intentionally omitted.
