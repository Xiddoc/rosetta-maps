# Network & server protocol

Moovit (`com.tranzmate`), confirmed against **version_code 1785** (versionName 5.194.0.1785). Classes are referenced by their **logical** name; the obfuscated name for this version is in [`maps/com.tranzmate/1785.json`](../../../maps/com.tranzmate/1785.json) and the regex anchors in [`signatures/com.tranzmate/signatures.yaml`](../../../signatures/com.tranzmate/signatures.yaml).

## Moovit Network & Server Protocol subsystem

Moovit runs **two parallel network stacks**:

### 1. Classic `HttpURLConnection` request framework (primary, most RPCs)
The base request/response pair still drives the bulk of server calls. R8 moved
these out of `com.moovit.commons.request` into the default package and renamed
them to single tokens:

- **`pac` = BaseServerRequest** (abstract). Builds the target `Uri` from a
  server-path string resource + `Backend`, appends query params
  (`F/D/E` → `setUrlParameter`, guarded by *"Can't set a URL parameter after the
  connection has been opened"*), opens a `FirebasePerfUrlConnection`-instrumented
  `HttpURLConnection`, and injects headers in two methods:
  - `I` (**addRequestHeaders**): sets `Access-Token` (from `DeviceAuthManager`/
    `lr5.e(context)`) and `Authorization: Bearer <token>` (from
    `PaymentAccountAuthManager` / `iva`), guarded by `R()`/`Q()` (both true only
    for `app4/app5 …/services-app/services/` hosts).
  - `J` (**addAppHeaders**): only for `*.moovitapp.com` hosts — sets
    `CLIENT_VERSION`, `PHONE_TYPE`, `API_KEY`, `USER_KEY` (from the cached
    `USER_CONTEXT`), and `Metro-Revision-Metro-Id` / `Metro-Revision-Number` /
    `Gtfs-Language` (from the cached `METRO_CONTEXT`).
  - `L` maps HTTP 307→`RedirectException`, 401→`UnauthorizedException`.
  - `W` (**onServerException**): reacts to server auth-error codes
    `CLIENT_DEVICE_ACCESS_TOKEN_INVALID`, `CLIENT_ACCOUNT_REFRESH_TOKEN_INVALID`,
    `CLIENT_ACCOUNT_ACCESS_TOKEN_INVALID` (clears/refreshes device + account
    tokens).
  - `T`/`a0`/`d0`/`e0` create and read the response via `this.d.newInstance()`
    (the response `Class` passed to the ctor) and support multi-response
    (`S()`, subclass `p12`). gzip/identity decoding in `K`.
- **`fec` = BaseServerResponse** (abstract). `d` (**readHeaders**) parses
  `X-Android-Response-Source` (cache source) + `ETag`; `c`/`b` throw on non
  200/201/204 (*"… returned response code …"*). Holds a back-reference to its
  `pac`.

Coroutine wrappers live in `com.moovit.commons.request.a` (`RequestExtKt`,
`execute`/`executeMulti`). Request env is `com.moovit.request.RequestContext`
(kept: Context + user + `AnalyticsFlowKey`) and `RequestOptions` (kept).

### 2. Newer Ktor stack under `com.moovit.core.network`
Used by the repository-layer (`com.moovit.data.*.remote`) flows:

- **`com.moovit.core.network.a` = HttpClientUtils / request-routing attributes**
  (abstract). Defines three Ktor `AttributeKey`s that select how each request is
  issued: `backend-attribute` (a `Backend`), `path-attribute` (String),
  `auth-attribute` (Boolean = requires auth). Also `asFlow` /
  `asListResourceResponse` response helpers.
- **`com.moovit.core.network.b` = network Logging HttpClientPlugin** (implements
  the client-plugin interface `od6`). Wires request/response/exception logging
  (`Logging$setupRequestLogging`, `…setupResponseLogging`, `…logExceptions`),
  default logger format `Request[*]`, CURL dump.
- **`com.moovit.core.network.e` = NetworkModule user-error parser**
  (`NetworkModule$Companion$parseUserError`). Casts the response body to
  `MVErrorMessage` and reads `errorCode`/`shortDescription`/`longDescription`
  (`a()I`, `c()`, `b()`) to build the `UserRequestError`.
- **`com.moovit.core.network.f` = ThriftSerializationConverter** (implements Ktor
  `ContentConverter` `ov2`) — the wire (de)serializer: reads/writes
  `org.apache.thrift.TBase`/`TUnion` bodies via `TCompactProtocol`-style
  transport (`ThriftSerializationConverter$serialize`). *Not signed:* it holds no
  rotation-stable string; identify it as the only Ktor `ContentConverter`
  touching `TBase`/`TUnion`. High-value hook for dumping every Thrift
  request/response.
- **Auth (Ktor):** `com.moovit.core.network.auth.a` = **AccessTokenAuthProvider**
  (adds `Access-Token` header via the token holder; refresh via
  `AccessTokenAuthProvider$refreshToken`), backed by
  `com.moovit.core.network.auth.b` = **AuthTokenHolder** (double
  `AtomicReference<Deferred>` single-flight token load/refresh —
  `AuthTokenHolder$loadTokens`/`$setToken`). *Not signed:* no unique in-class
  string; identify via the leaked synthetic names + `com.moovit.data.auth.provider.a`.
- **App headers (Ktor):** `com.moovit.app.request.b` = **AppHeadersProvider**
  (`AppHeadersProvider$configureHeaders`) — mirrors `pac.J`, sets
  `CLIENT_VERSION`=`5.194.0.1785`, `API_KEY`=`moovit_2751703405`, `USER_KEY`,
  `Metro-Revision-*`. *Not signed:* every candidate string is shared across ≥9
  files. `com.moovit.app.request.c` = **AppCallRequestExceptionHandler** and
  `MetroIdMismatchExceptionHandler` handle metro-id/revision mismatches
  (re-fetch metro, copy favorites).

### Server configuration / endpoints
- **`com.moovit.core.network.Backend`** (kept enum) — the Ktor-side endpoint set:
  `APP_SERVER https://app5.moovitapp.com/services-app/services/`,
  `APP_SECURED_SERVER app4`, `CDN_SERVER app4cdn`,
  `CDN_RESOURCES static…/v4/`, `OFFLINE_RESOURCES static…/offlineData/`,
  `TVM https://anonymousstream.moovitapp.com/`, `SDK sdk.moovitapp.com`.
- **`com.moovit.data.core.environment.backend.a` = BackendEnvironments** — the
  full prod/qa/stg URL matrix keyed by `app`/`secureApp`/`cdn`/`search`/
  `resources`/`offlineResources`/`tvm`/`tvmNew`/`sdk`, plus `kinesisEnvironment`
  and the `prod`/`stg`/`qa` selector (*"Unknown environment: "*). The classic
  `pac` path instead resolves hosts from string resources
  `server_path_app_server_url` / `…_secured_url`.

### Thrift protocol structs (`com.tranzmate.moovit.protocol.*`)
**2,496** generated `MV*` classes across ~60 subpackages
(`tripplanner`, `users`, `ticketingV2`, `payments`, `metroinfo`, `gtfs`,
`carpool`, `tod`, …). **Class names are kept** (`MV*`), so they are trivially
known — but every field/method is renamed to short tokens, and the structs carry
**no self-name const-string** (Thrift descriptor strings are stripped), so
per-struct anchoring adds little map value and is intentionally omitted here.
Key RPC message types by kept name:
- **Trips:** `…tripplanner.MVTripPlanRequest`, `MVTripPlanSectionedResponse`.
- **Account/users:** `…users.MVCreateUserRequest`/`MVCreateUserResponse`,
  `MVChangeUserMetroAreaRequest`, `MVUserRegistrationStateResponse`,
  `MVFirebaseCustomTokenResponse`; errors as `…common.MVErrorMessage`.
- **Tickets:** `…ticketingV2.MVPurchaseItineraryRequest`,
  `MVActivateTicketRequest`, `MVExternalPaymentV2Request`,
  `MVUserRefreshTicketsStatusResponse`, `MVUserRecommendedFaresResponse`.

### Exceptions (kept names, `com.moovit.commons.request` / `com.moovit.request`)
`ServerException` (base), `UnauthorizedException` (carries the server auth code),
`RedirectException`, `BadResponseException`, and `UserRequestError` (extends
`ServerException`; `errorCode` + short/long description). `MetroIdMismatchException`
/ `MetroRevisionMismatchException` / `ServerBusyException`. These have no
in-class string anchors and their names are already un-obfuscated, so they are
documented rather than signed.

### Best Frida/Xposed hook points
- **Dump every classic RPC:** hook `BaseServerRequest.c0`/`e0` (send) and
  `BaseServerResponse.readResponse` (`fec.d`) — gives raw URL, headers, and the
  decoded stream for all `pac` subclasses.
- **See/insert auth headers:** hook `BaseServerRequest.addRequestHeaders`
  (`pac.I`, anchor *"Failed to add access token header!"*) to observe/override
  `Access-Token` + `Bearer` injection; hook `pac.onServerException` (`W`) to
  watch token-invalidation flow.
- **Ktor path:** hook `ThriftSerializationConverter` (`com.moovit.core.network.f`)
  `a`(deserialize)/`b`(serialize) to intercept every Thrift `TBase` on the Ktor
  client; hook `AuthTokenHolder` (`auth.b`) `loadTokens`/`setToken` for the
  Access-Token session; hook NetworkModule user-error parser
  (`com.moovit.core.network.e`) to read server `MVErrorMessage` codes.
- **Redirect endpoints:** patch `Backend.getBaseUrl` / `BackendEnvironments` to
  point traffic at a proxy.

## Classes identified

| Logical class | Renamed? | Confidence | Identity evidence |
| --- | --- | --- | --- |
| `BaseServerRequest` | yes | high | Abstract base of the classic HttpURLConnection request framework: builds Uri from a server-path string resource + server config, appends query params (setUrl… |
| `BaseServerResponse` | yes | high | Abstract base of the classic response hierarchy, paired with pac (holds a back-ref field 'a:pac', instantiated via pac.T() this.d.newInstance()). readHeaders… |
| `Backend` | no | high | Kept enum of the Ktor-stack server endpoints; each constant carries a baseUrl: APP_SERVER=https://app5.moovitapp.com/services-app/services/, APP_SECURED_SERV… |
| `BackendEnvironments` | yes | high | Full prod/qa/stg backend URL matrix: enumerates every environment's app/secureApp/cdn/search/resources/offlineResources/tvm/tvmNew/sdk endpoint (prod app5/ap… |
| `NetworkModule.parseUserError` | yes | high | Enclosing class (this$0) of the leaked synthetic NetworkModule$Companion$parseUserError$1; its static a(e, je6, Continuation) casts the Ktor response body to… |
| `NetworkLoggingPlugin` | yes | high | Ktor HttpClientPlugin (implements od6 with getKey/install/prepare) that installs request/response/exception logging by wiring the kept-named Logging$setupReq… |
| `NetworkRequestAttributes` | yes | high | Abstract holder (from HttpClientUtils.kt) defining the three Ktor request AttributeKeys that route each Ktor call: 'backend-attribute' typed as Backend, 'pat… |

