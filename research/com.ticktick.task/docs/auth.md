# TickTick — Authentication & Login subsystem

- **App:** `com.ticktick.task` (TickTick)
- **version_code:** `8081`
- **versionName:** `8.0.8.1`
- Decompiled trees analyzed (read-only):
  - jadx Java: `/home/user/apk-workspace/out/jadx/sources/`
  - apktool smali: `/home/user/apk-workspace/out/apktool/`
- Obfuscation: `com/ticktick/task/*` mostly preserved; the network-plumbing
  and login-handler helper classes are R8-renamed into short top-level
  packages (`j8/`, `cf/`, `h8/`, `vd/`, `w7/`, `y7/`, `k8/`, `i8/`).
  jadx keeps the original source-file name in a `// compiled from: X.java`
  comment, which is how the obfuscated helpers below were identified.

All file:line references are into the jadx tree unless prefixed `smali`.

---

## 1. Login / signup / signout API surface

### `LoginApiInterface` (Retrofit interface)
`com/ticktick/task/network/api/LoginApiInterface.java` — loaded from
**classes4.dex**. Return type is `x7.a<T>` (TickTick's renamed `retrofit2.Call`
wrapper; `.d()` = synchronous execute, `.c()` = enqueue). Retrofit annotations
are the renamed `on.*` package (`on.f`=@GET, `on.o`=@POST, `on.p`=@PUT,
`on.t`=@Query, `on.i`=@Header, `on.a`=@Body).

| Method | HTTP | Path | Request | Response |
|---|---|---|---|---|
| `signOn` | POST | `api/v2/user/signon` | `@Body NamePasswordData`, `@Header("x-timestamp")` | `SignUserInfo` |
| `signup` | POST | `api/v2/user/signup` | `@Body NamePasswordData`, `@Query("invitecode")`, `@Header("x-timestamp")` | `SignUserInfo` |
| `signupBySms` | POST | `api/v2/user/signup` | `@Body NamePasswordData`, `@Query("invitecode")`, `@Query("code")`, `@Header("x-timestamp")` | `SignUserInfo` |
| `signout` | GET | `api/v2/user/signout` | — | `qj.c0` (okhttp `ResponseBody`) |
| `signOAuth2` | GET | `api/v2/user/sign/OAuth2` | `@Query("site")`, `@Query("access_token")` | `SignUserInfo` |
| `signOAuth2CN` | GET | `api/v2/user/sign/OAuth2` | `+ @Query("uId")` | `SignUserInfo` |
| `signOAuth2Wechat` | GET | `api/v2/user/sign/OAuth2` | `+ @Query("uId")`, `@Query("refCode")` | `SignUserInfo` |
| `signOAuth2Weibo` | GET | `/api/v2/user/sign/weibo/validate` | `@Query("code")` | `SignUserInfo` |
| `signTwitter` | GET | `api/v2/user/sign/twitter` | `@Query("access_token")`, `@Query("accessTokenSecret")` | `SignUserInfo` |
| `updateGooglePwd` | POST | `api/v2/user/third/changePassword` | `@Header("access_token")`, `@Body ChangePasswordData` | `ApiResult` |
| `getInviteCode` | GET | `api/v2/user/signup/inviteCode` | — | `String` |
| `isJustRegistered` | GET | `api/v2/user/isJustRegistered` | — | `Boolean` |
| `checkSuggestCn` | GET | `api/v2/user/sign/suggestcn` | — | `Boolean` |
| `sendSmsCode` | POST | `api/v2/user/sms/signup/code` | `@Body SmsBindBean` | `c0` |
| `sendBindSmsCode` | POST | `api/v2/user/sms/code` | `@Body SmsBindBean` | `c0` |
| `bindPhone` | POST | `/api/v2/user/sms/phone/bind` | `@Body SmsBindBean` | `c0` |
| `sendEmailVerificationCode` | POST | `/api/v2/user/sendVerifyCode` | `@Query("email")` | `c0` |
| `updateFakeName` | PUT | `/api/v2/user/profile/updateFakedName` | `@Body EmailBindBean` | `c0` |

There is **no separate refresh endpoint**; token "refresh" is re-running the
appropriate sign-in (`signOn` / `signOAuth2`) — see §2.3.

### Request / response models (all classes4.dex)
- `NamePasswordData` (`network/sync/common/model/NamePasswordData.java`):
  Kotlin, fields `username`, `password`, `phone`, `verCode`, `verKey` (the last
  two carry the captcha answer).
- `SignUserInfo` (`network/sync/common/model/SignUserInfo.java`): the login
  response. Key fields: `token` (the auth/access token), `userId`, `username`,
  `phone`, `inboxId`, `userCode`, `code`, `pro`/`proStartDate`/`proEndDate`,
  `subscribeType`/`subscribeFreq`, `teamUser`, **`authId`** + **`errorType`** /
  `expireTime` (2FA challenge — see §4). Helper `need2FA()` at line 140 returns
  `!TextUtils.isEmpty(authId)`.
- `ChangePasswordData`: `password`, `newPassword1`, `newPassword2`, `code`.
- `SmsBindBean`: `phone`, `password`, `code`, `type` (Companion factories
  `bind(phone)` / `register(phone)`).
- `EmailBindBean`: `id`, `email`, `password`.

---

## 2. Credential / session lifecycle & storage

### 2.1 Token attachment to requests — `Authorization: OAuth <token>` (NOT a cookie)
The auth credential is sent as an **`Authorization` HTTP header**, value
`"OAuth " + accessToken`. There is **no `t` cookie / CookieJar** in this build
— the app uses a stateless bearer header, not a session cookie.

- Request interceptor: `y7/a.java` (`HttpRequestInterceptor`, **classes2.dex**),
  method `b(y.a)` at lines 39-87. Line 68-73:
  ```
  String accessToken = this.f36199b;                       // per-call token, or
  if (accessToken == null)
      accessToken = TickTickApplicationBase.getInstance()
                      .getAccountManager().getAccessToken();  // current user's token
  if (accessToken != null)
      aVar.c("Authorization", "OAuth ".concat(accessToken));
  ```
  Same interceptor also adds `Accept-Language`, `Locale`, `hl`, `X-Device`,
  `User-Agent`, `traceid`, `x-tz`.

### 2.2 Retrofit / OkHttp construction (token plumbing)
- `vd/d.java` (`BaseApi`, classes4.dex) — generic API factory. `f33309c` is the
  built service (created with `token=null`, i.e. uses current-user token via the
  interceptor). `d.a(String token)` (line 65) rebuilds the service bound to an
  **explicit** token.
- `vd/j.java` (`LoginApi`, classes4.dex) = `BaseApi<LoginApiInterface>`;
  `j.b()` returns one bound to `INTERNATIONAL_API`. `new vd.j(domain)` targets a
  specific domain (china vs international, dida).
- `vd/t.java` = `BaseApi<TwoFactorApiInterface>` (constructed in
  `j8/n.java:43` and `LoginTwoFactorAuthFragment.twoFactorApi()`).
- `vd/h.java` = `BaseApi<GeneralApiInterface>` (profile fetch after login).
- `w7/c.java` (`GsonApiFactory`, classes2.dex; singleton `f34215i`) extends
  `w7/b.java` (`ApiFactoryBase`, classes2.dex). `b.a(cls, baseUrl, token, z)`
  at lines 136-186 builds the OkHttp client + Retrofit:
  - When `token == null` the cached shared client (with the default
    interceptor) is reused.
  - When `token != null` the default `httpsRequestInterceptor` is *removed* and
    a fresh `y7.a(headerInfo, token)` is added so that call carries the explicit
    token (lines 162-176).
  - Timeouts 25s connect / 40s read / 40s write (lines 94-96).
  - Response interceptor `y7.b` and logging interceptor are also installed.

### 2.3 Token invalid / re-auth handling
`y7/b.java` (`HttpResponseInterceptor`, classes2.dex) parses the JSON error body
into `ApiErrorResult` and maps server `errorCode` strings to typed exceptions
(`ud.*`). On `user_not_signon` (`Constants.SyncErrorCode.USER_NOT_SIGN_ON`,
exception `ud.c`) it runs the "token timeout" re-authorize path (lines 558-633):
- `getAuthTokenTimeoutManager()` (`h8/f.java`, log tag
  `AuthTokenTimeoutManagerBase`) freezes the current user
  (`accountManager.freezeUser(id)`) and re-authorizes by **account type**:
  - type **3** (Google web/idtoken) → `k8.h` (`GoogleWebTokenRefreshHelper`)
    using a stored `GOOGLE_REFRESH_TOKEN_TAG_<id>` SharedPref; or `k8.f`
    (`GoogleSysTokenRefreshHelper`) via `GoogleSignIn.getLastSignedInAccount`.
  - type **5** (Facebook) → `k8.d` (`FacebookTokenRefreshHelper`), token from
    SharedPref `FACEBOOK_ACCESSTOKEN_<id>`.
  - type **10** → `k8.m` (`TwitterWebTokenRefreshHelper`).
  - else → `k8.i` (`TickTickTokenRefreshHelper`).
  Each refresh helper re-calls the matching `signOAuth2`/`signTwitter` endpoint
  and writes the new token back onto the `User`.

### 2.4 Persistence — the `User` object
`com/ticktick/task/data/User.java` — **classes3.dex**. This is the persisted
account record (GreenDAO entity, also `Parcelable`). Auth-relevant fields:
`accessToken`, `sid`, `username`, `password`, `requestToken` (third-party
provider token), `domain`, `accountType`, `inboxId`, `userCode`, `_id`.
- `TickTickAccountManager` (`com/ticktick/task/manager/TickTickAccountManager.java`,
  **classes4.dex**) is the account façade:
  - `getCurrentUser()` (line 143) — cached, loaded from `userService`.
  - `getAccessToken()` (line 116) — returns `getCurrentUser().getAccessToken()`;
    this is the value the request interceptor reads.
  - `getAccessTokenById`, `getCurrentUserId`, `getSid`, `saveUserStatus`,
    `freezeUser`, `signOut(id)`.
  - Persistence is through `userService` (DB), not SharedPreferences/MMKV; the
    token lives in the `User` DB row. Provider refresh tokens (Google/Facebook)
    are in default SharedPreferences keyed by user id (see §2.3).
- `h8/m.java` (`ResponseUser`, classes.dex/classes) is the transient
  in-memory login result built from `SignUserInfo` before it is persisted as a
  `User`. Field map (from `toString()`): `f23276a`=userType,
  `f23277b`=name, `f23278c`=username, `f23279d`=password, `f23280e`=authToken,
  `f23281f`=requestToken, `f23282g`=updateToken, `f23286k`=inboxId,
  `f23287l`=domain, `f23288m`=sid, `f23291p`=userCode, `f23295t`=phone,
  `f23296u`=code.
- `h8/l.java` (`RequestUser`, classes) is the login request DTO:
  `f23267a`=username, `f23268b`=password, `f23269c`=phone, `f23270d`=requestToken
  (3rd-party access token), `f23271e`=updateToken, `f23272f`=accountType (int),
  `f23273g`=siteDomain.

`accountType` integer enumeration (observed across handlers): **2** = TickTick
email/username+password, **3** = Google, **5** = Facebook, **10** = Twitter
(others 4/7/8/9 referenced but not in the auth hot-path).

---

## 3. Login orchestration & third-party / OAuth sign-in

### 3.1 LoginHandler hierarchy (`j8/` package, classes.dex)
Abstract base `j8/m.java` (`LoginHandler`) drives every interactive sign-in:
- ctor `(Activity, h8.k callback)`; `h8.k` is the `OnLoginResultListener`.
- Inner `class b extends cf.j<h8.l, h8.m>` (line 118) is the background task.
  Its `a(obj)` (line 134) calls the abstract `k(h8.l, CaptchaValue)` to perform
  the API sign-in, then:
  - if `signUserInfo.need2FA()` → throws `ud.e0(authId, expireTime)` to drive
    the 2FA UI (§4).
  - else builds an `h8.m` from the response, then fetches profile via
    `GeneralApiInterface` (`vd.h(domain).a(token)`): `getFeaturePrompt()`,
    `getUserProfile()`, and (non-china) `getWechatUserInfo()` (lines 168-197).
- `k(...)` is **abstract** — each provider subclass implements it.
- `d(h8.l, Throwable)` (line 242) maps typed exceptions to UI dialogs/toasts
  (wrong password `ud.b2`, user-not-exist `ud.z1`, 2FA-required `ud.e0` →
  `show2FAFragment`, captcha `ud.f0`/`ud.i`, google-bind-conflict `ud.h1`, …).
- `j(h8.l, CaptchaValue)` (line 411) shows the progress dialog and starts the
  task thread.

Provider subclasses of `j8/m` (jadx `// compiled from:` names):
| Obf class | Source name | Provider | `k()` call |
|---|---|---|---|
| `j8/e.java` | `AccountLoginTickTickHandler` | email/username + password | `signOn(NamePasswordData, SecurityHelper.getTimestamp())` (line 39) |
| `j8/a.java` | `AccountLoginFacebookHandler` | Facebook | `signOAuth2("facebook.com", requestToken)` (line 20) |
| `j8/b.java` | `AccountLoginGoogleSystemhandler` | Google (system account) | `signOAuth2(GOOGLE_SITE_DOMAIN, requestToken)`; sets `accountType=3` (lines 101,111) |
| `j8/c.java` | `AccountLoginGoogleWebHandler` | Google (web idToken) | `signOAuth2(GOOGLE_SITE_DOMAIN, requestToken)` (line 20) |
| `j8/n.java` | `TwoFactorLoginHandler` (Kotlin) | 2FA verify-during-sign-in | `verifyCodeWhenSign(authId, VerifyBody)` (line 43) |
| `j8/l.java` | `LoginHandler` inner task | Google post-login set-password | `updateGooglePwd(token, ChangePasswordData)` (line 64) |

`Constants.SiteDomain.GOOGLE_SITE_DOMAIN = "google.com"`,
`FACEBOOK_SITE_DOMAIN = "facebook.com"` (`Constants.java:1778-1780`).

### 3.2 Non-interactive authorize task
`cf/g.java` (`TickTickAuthorizeTask`, classes4.dex) re-authorizes a stored
`User` (used by re-sync / token refresh). `doInBackground()` (lines 23-45)
switches on `user.getAccountType()`: 2→`signOn`, 5→Facebook `signOAuth2`,
3/6→Google `signOAuth2`. Result token copied into an `h8.m`.

### 3.3 Sign-in entry / Activities
- `com/ticktick/task/account/LoginMainActivity.java` (extends
  `BaseLoginMainActivity`, implements `GoogleApiClient.OnConnectionFailedListener`)
  — Google sign-in `onActivityResult` (line 61), log tag `"GoogleLoginHelper"`
  (a unique anchor for this class).
- `com/ticktick/task/activity/account/BaseLoginMainActivity.java` — base; has
  `show2FAFragment(requestUser, authId, expireAt)` invoked from `j8.m.d`.
- `com/ticktick/task/activity/account/LoginAccountHelper.java` (classes3.dex,
  Kotlin `object`, TAG `"LoginAccountHelper"`) — `show2FAFragment(...)` routes
  to the WeChat 2FA fragment or the generic 2FA fragment based on the queried
  methods (`query2FactorMethodsWhenSign`).
- Email/phone register + password UI: `activity/fragment/login/`
  (`EmailRegisterFragment`, `PhoneRegisterFragment`, `PasswordInputFragment`,
  `RegisterInputAccountFragment`, `CaptchaFragment`, `BasePhoneVerificationFragment`).
- Google OAuth plumbing: `i8/` package (`GoogleApiClient`, `GoogleOAuth2Utils`,
  `GoogleSysClient`, `GoogleTokenReauthorizeTask`).

### 3.4 Provider coverage in THIS (international) build
- **Email/username + password** — full (`j8/e`).
- **Google** — full, two variants (system account `j8/b`, web idToken `j8/c`).
- **Facebook** — full (`j8/a`), uses `com.facebook.AccessToken`.
- **Twitter** — token-refresh helper present (`k8/m`); endpoint `signTwitter`.
- **WeChat / Weibo (China / Dida)** — endpoints exist in `LoginApiInterface`
  (`signOAuth2Wechat`, `signOAuth2CN`, `signOAuth2Weibo`) and WeChat appears as
  a 2FA channel, but the interactive WeChat/Weibo sign-in *Activity* is part of
  the China (Dida) flavor and is not wired in this international APK's login
  handlers.
- **Apple** — no native Apple sign-in present.
- Third-party profile entity: `network/sync/common/entity/thirdsiteuserprofile/WechatUserProfile.java`.

### 3.5 Sign-up & sign-out
- Sign-up task: `cf/k.java` (`TickTickSignUpTask`, Kotlin) → `signup` /
  `signupBySms`. Extra post-signup work in
  `activity/account/SignUpExtraWork.java`.
- Sign-out: `com/ticktick/task/manager/AccountSignOutHelper.java` (classes4.dex).
  `signOut()` (line 192) runs a background task that calls
  `LoginApiInterface.signout().c()` (line 214) then locally
  `mAccountManager.signOut(userId)` / `logout(id)` regardless of network result
  (line 222 logs out even on failure).

---

## 4. Two-factor auth (2FA / MFA)

### `TwoFactorApiInterface`
`com/ticktick/task/network/api/TwoFactorApiInterface.java` — **classes4.dex**.

| Method | HTTP | Path | Request | Response |
|---|---|---|---|---|
| `query2FactorMethods` | GET | `api/v2/user/mfa/setting` | — | `UserTwoFactorSetting` |
| `query2FactorMethodsWhenSign` | GET | `api/v2/user/sign/mfa/setting` | `@Header("x-verify-id")` authId | `UserTwoFactorSetting` |
| `sendCode` | POST | `api/v2/user/mfa/code` | `@Body SendCodeBody` | `SendCodeResult` |
| `sendCodeWhenSign` | POST | `api/v2/user/sign/mfa/code` | `@Header("x-verify-id")`, `@Body SendCodeBody` | `SendCodeResult` |
| `verifyCode` | POST | `/api/v2/user/mfa/code/verify` | `@Body VerifyBody` | `VerifyCodeResult` |
| `verifyCodeWhenSign` | POST | `/api/v2/user/sign/mfa/code/verify` | `@Header("x-verify-id")`, `@Body VerifyBody` | `SignUserInfo` |
| `verifyOAuth2Token` | GET | `api/v2/user/mfa/OAuth2` | `@Query site/access_token/uId/type` | `VerifyCodeResult` |

`...WhenSign` variants are the **login-time challenge** (carry the
`x-verify-id` = `authId`); the bare variants are post-login (managing 2FA in
settings).

### Flow
1. A normal sign-in (`signOn` / `signOAuth2`) returns a `SignUserInfo` with
   **no `token`** but a non-empty **`authId`** ⇒ `need2FA()` true.
2. `j8.m$b.a` throws `ud.e0(authId, expireTime)`; `j8.m.d` calls
   `BaseLoginMainActivity.show2FAFragment(requestUser, authId, expireAt)` (or
   posts `Need2FAEvent`).
3. `LoginAccountHelper.show2FAFragment` calls
   `query2FactorMethodsWhenSign(authId)` → `UserTwoFactorSetting` to learn the
   enabled channels, then opens the WeChat 2FA fragment or the generic 2FA
   fragment.
4. The chosen fragment (e.g. `LoginTwoFactorAuthFragment`, classes3.dex):
   - "send code": `sendCodeWhenSign(authId, new SendCodeBody("mail"/"phone", …))`
     (`LoginTwoFactorAuthFragment.java:295,305`).
   - "verify": builds a `VerifyBody(oid, method, code, type)` and runs
     `j8/n.java` (`TwoFactorLoginHandler`) → `verifyCodeWhenSign(authId,
     VerifyBody)` (`j8/n.java:43`) which returns a real `SignUserInfo` with a
     `token`, completing login through the same `j8.m` pipeline.

### 2FA entities (all classes4.dex, `network/sync/entity/mfa/`)
- `SendCodeBody`: `method` (`"mail"`/`"phone"` consts `METHOD_MAIL`/
  `METHOD_PHONE`), `type`.
- `VerifyBody`: `oid`, `method`, `code`, `type`.
- `SendCodeResult`, `VerifyCodeResult`.
- `UserTwoFactorSetting`: `mfaEnabled` + per-channel `TwoFactorOption`:
  `phoneOption`, `mailOption`, `wechatOption`, `appOption` (TOTP, exposes
  `secret`), `backupOption`. Method `toModel()` (lines 51-73) maps to
  `TwoFactorOptionModel` using method strings `"phone"`, `"mail"`,
  `AccountVerificationMethod.METHOD_WECHAT/METHOD_APP/METHOD_BACKUP`.
- `TwoFactorOption`: `enabled`, `name`, `secret`.

2FA UI fragments: `com/ticktick/task/activity/fragment/twofactor/`
(`LoginTwoFactorAuthFragment`, `ActionTwoFactorAuthFragment`,
`SafetyVerifyAuthFragment`, `VerifySelectionFragment`, `TwoFactorAuthHelper`,
`BaseAuthFragment`).

---

## 5. Password handling & rules

- Login sends the **plaintext password** in `NamePasswordData.password` over
  HTTPS to `signon` (`j8/e.java:31-39`). No client-side hashing.
- `signOn`/`signup` carry an `x-timestamp` header from
  `SecurityHelper.getTimestamp()`; server returns `time_mismatch` (`ud.i1`,
  `Constants.SyncErrorCode.TIME_MISMATCH`) if the clock is off
  (`j8/m.java:289`).
- **Password length rule: 6–64 chars.** Enforced in
  `EmailRegisterFragment.java:216`, `PasswordInputFragment.java:247`,
  `BasePhoneVerificationFragment.java:324`, and in the Google set-password
  dialog `j8/m.java:364` (`text.length() < 6 || text.length() > 64`
  → `R$string.toast_password_invalid_length`). Max input cap of 64 also at the
  EditText level (`...:289/316/291`).
- Captcha: when the server demands it (`need_recaptcha` `ud.f0` /
  `captcha_wrong` `ud.i`) the `CaptchaValue` (key+code) is put into
  `NamePasswordData.verKey`/`verCode` (`j8/e.java:35-37`). Captcha image is a
  base64 data URL decoded in `CaptchaFragment.java:141`.
- Google "mail already registered" path lets the user set a password via
  `updateGooglePwd` (`changePassword`) — `j8/m.java:329-392`, `j8/l.java:64`.

---

## 6. Hook points (quick reference)

| Purpose | Class (obf → logical) | file:line |
|---|---|---|
| Attach `Authorization: OAuth <token>` | `y7/a` → HttpRequestInterceptor | `y7/a.java:68-73` |
| Read current token | `TickTickAccountManager.getAccessToken` | `manager/TickTickAccountManager.java:116` |
| Email/pw sign-in API call | `j8/e` → AccountLoginTickTickHandler.k | `j8/e.java:39` |
| Google sign-in API call | `j8/b`,`j8/c` | `j8/b.java:101`, `j8/c.java:20` |
| Facebook sign-in API call | `j8/a` | `j8/a.java:20` |
| Build session from response | `j8/m$b.a` → LoginHandler task | `j8/m.java:134-205` |
| 2FA branch (need2FA) | `j8/m$b.a` throws `ud.e0` | `j8/m.java:137-138` |
| 2FA verify-during-sign-in | `j8/n` → TwoFactorLoginHandler.k | `j8/n.java:43` |
| 2FA send code | `LoginTwoFactorAuthFragment` | `.../LoginTwoFactorAuthFragment.java:295,305` |
| Token-invalid re-auth | `y7/b` → HttpResponseInterceptor | `y7/b.java:558-633` |
| Sign-out API + local logout | `AccountSignOutHelper.signOut` | `manager/AccountSignOutHelper.java:192-214` |

---

## 7. Notes on anchors (for signatures.yaml authoring — kept out of this doc)

- `LoginApiInterface` and `TwoFactorApiInterface` each contain their full set of
  unique endpoint path string literals (e.g. `api/v2/user/signon`,
  `api/v2/user/sign/mfa/setting`) — verified globally unique to their class in
  smali; ideal rotation-stable anchors.
- `y7/a` (request interceptor) is uniquely anchored by the literal `"OAuth "`
  combined with `"Authorization"` + `"traceid"`/`"x-tz"` in one method (`"OAuth "`
  alone also appears in `td/f`).
- `LoginMainActivity` carries the unique log tag `"GoogleLoginHelper"`.
- The `j8/`, `cf/`, `h8/`, `vd/` helper class **names are R8-rotated** and must
  be re-anchored each version on string literals / kept-type descriptors, never
  on the short member names. The endpoint-string anchors above are the durable
  entry points; the handlers are best reached structurally (subclasses of the
  abstract `LoginHandler` whose `k()` returns `SignUserInfo`, calling a
  `LoginApiInterface`/`TwoFactorApiInterface` method).
