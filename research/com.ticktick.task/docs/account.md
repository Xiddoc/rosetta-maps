# TickTick — Account management & user config

- **App:** `com.ticktick.task` (TickTick)
- **version_code:** 8081  **versionName:** 8.0.8.1
- **Obfuscation:** partial — `com/ticktick/task/*` class/method/field names are
  almost entirely preserved in this subsystem (the data models, services,
  managers, and Retrofit API interfaces are NOT renamed). Only generic
  helper/util types (`a0`, `b0`, `f0`, `j`, `m`, `n`, lambda holders, etc.) are
  rotated. This makes the account subsystem very easy to anchor on literal
  class names + string literals.
- All paths below are relative to the jadx tree
  `/home/user/apk-workspace/out/jadx/sources/` unless noted. Smali ground truth
  is under `/home/user/apk-workspace/out/apktool/smali*/`.

---

## 1. The account model

### 1.1 `com.ticktick.task.data.User` — the local persisted account record
File: `com/ticktick/task/data/User.java` (dex: `smali_classes3`)

GreenDAO-backed entity (`User implements Parcelable, Cloneable`), one row per
account in the local DB. This is the *device-side* account record (loaded via
`UserService`/`UserDaoWrapper`), distinct from the network DTO in §2.1.

Notable constants:
- `LOCAL_MODE = "local"` (User.java:20) — username for the no-account user.
- `LOCAL_MODE_ID = "local_id"` (User.java:21) — the `_id` of the local-mode user.
- `FREE_TYPE_NEW_USER = 0`, `FREE_TYPE_PRO_EXPIRED = 1`.

Fields (User.java:23-60), grouped:

| Group | Fields |
|---|---|
| Identity | `_id` (local PK), `sid` (server/remote user id, defaults `"0"`), `username`, `name` (display name), `phone`, `userCode`, `inboxId` |
| Auth | `accessToken`, `password` (deprecated setter), `requestToken` |
| Account kind | `accountType` (int; **4 = local mode**, 7 = Tencent, 8 = Weibo, 9 = WeiXin), `domain` (dida vs ticktick site), `avatar` |
| Pro / subscription | `proType` (1 = pro), `proStartTime`, `proEndTime`, `subscribeType` (e.g. `"google"`, `"order"`), `subscribeFreq` (e.g. year), `needSubscribe`, `teamPro`, `teamUser`, `activeTeamUser`, `gracePeriod`, `noGraceDate`, `errorType` (1 = renewal failed, 2 = duplicate subscribe) |
| Email / verify | `verifyEmail`, `filledPassword` |
| Sync checkpoints | `checkpoint`, `columnCheckPoint`, `settingsBackupPoint`, `listBackupPoint`, `taskBackupPoint`, `modifiedTime`, `createdTime` |
| State | `activity` (1 = the currently-active account), `wake` (1 = active / 0 = frozen/signed-out), `deleted`, `isDisabled` |

Key derived behavior (hook points):
- `isLocalMode()` → `accountType == 4` (User.java:411).
- `isPro()` → `proType == 1 || isActiveTeamUser()` (User.java:419).
- `isDidaAccount()` (User.java:386) — domain comparison against
  `BaseUrl.DIDA_API_DOMAIN` / `DIDA_SITE_DOMAIN`; drives the dida-vs-ticktick
  site split. `getApiDomain()` (User.java:195) maps domain →
  `HttpUrlBuilderBase.DomainType.CHINA_API` / `INTERNATIONAL_API`.
- `isFakeEmail()` (User.java:403) / `setFakeEmail()` (User.java:528) delegate to
  the **`UserProfile`** (the fakeEmail flag lives on the profile, not the User).
- Account-type predicates: `isTencentAccount/ isWeiboAccount / isWeiXinAccount`.
- `getDisplayName()` / `getNickName()` / `requireDisplayName()` — masking logic
  for phone/email (good UI hook points).

Anchor: string literal `"local_id"` (and `"local"`), unique to this class.

### 1.2 `com.ticktick.task.manager.TickTickAccountManager` — the account manager
File: `com/ticktick/task/manager/TickTickAccountManager.java` (dex: `smali_classes4`)

The central account manager. Obtained via
`TickTickApplicationBase.getAccountManager()` (TickTickApplicationBase.java:700).
Holds `private User currentUser` (in-memory cache), a `UserService userService`,
and a `UserProfileService userProfileService`.

Core methods (hook points):
- `getCurrentUser()` (TTAM.java:143) — returns cached `currentUser`, else loads
  via `userService.getCurrentUser()` (which falls back to the local-mode user).
- `getCurrentUserId()`, `getCurrentRemoteUserId()` (parses `sid`),
  `getAccessToken()` / `getAccessTokenById()`.
- `getCurrentUserProfile()` (TTAM.java:154) → `UserProfileService.getUserProfileWithDefault(currentUserId)`.
- `isLocalMode()` (TTAM.java:180), `instantLocalUser()` (TTAM.java:165).
- `setCurrentUser(User)` (TTAM.java:354) — switches the active account: freezes
  all accounts if local, else marks active + saves; sets the global request
  domain (`pk.f0.f29198a = domain`) and rebuilds the `RequestManager` HTTP
  client. **This is the account-switch entry point.**
- `saveUserStatus(id, SignUserInfo)` (TTAM.java:296) and
  `saveCurrentUserStatusAndInfo(id, RemoteUserInfoModel)` (TTAM.java:184) —
  merge the server status (pro/team/grace/subscribe/email) into the local
  `User`. These are the **pro-state write paths** (note the
  `Log.e("PaymentUpdateMessage", ...)` literal at TTAM.java:331).
- `saveRefreshTokenResult(...)` (TTAM.java:259), `updateToken()` (TTAM.java:438)
  — token refresh writeback.
- `freezeUser()` / `wakeOrFreezeUser()` (TTAM.java:98) — wake/freeze (sign-out
  marks `wake=0`).
- `signOut(String userId)` (TTAM.java:383) — **the local sign-out / data-wipe
  orchestration** (see §4).
- `updateUserProfile(...)` / `updateUserProfileCache(...)` (TTAM.java:454/466)
  — persist a `UserProfile` and push first-day-of-week into prefs.
- `clearUserCache()` (TTAM.java:108) — drops the in-memory `currentUser`.

Anchor: string literal `"PaymentUpdateMessage"` (only occurrence in class).

### 1.3 `com.ticktick.task.service.UserService` — DB access for `User`
File: `com/ticktick/task/service/UserService.java` (dex: `smali_classes4`)

Thin wrapper over `UserDaoWrapper`
(`getDaoSession().getUserDao()`). Methods: `getCurrentUser()` (the active-user
row, else local), `getLocalModeUser()` (**creates** the local user with
`_id="local_id"`, `username="local"`, `accountType=4`,
`domain=BaseUrl.getLocalModeDomain()` — UserService.java:35), `getUserById`,
`getActiveUserByID`, `saveTickTickAccount`, `freezeUser`/`freezeAllAccount`,
`saveUserActivity` (marks one account active), `updateUserToDB`,
`findExistUser`. Anchor: kept ref `getDaoSession().getUserDao()` /
`UserDaoWrapper` (no class-unique string literal).

---

## 2. Profile management API

### 2.1 `com.ticktick.task.network.api.GeneralApiInterface` — the main user API
File: `com/ticktick/task/network/api/GeneralApiInterface.java` (dex: `smali_classes4`)

A large Retrofit-style interface (annotations `@f`=GET, `@o`=POST, `@p`=PUT,
`@b`=DELETE, `@h`=custom from package `on`; bodies `@on.a`, path `@s`, query
`@t`, header `@i`). Returns `x7.a<T>` (the app's call wrapper). Endpoints
relevant to account/profile (verbatim paths — these are **rotation-stable
anchors**):

Profile / identity:
- `getUserProfile()` → `GET api/v2/user/profile` → `network.sync.common.entity.User` (§2.2). (GAI.java:261)
- `updateName(User)` → `PUT api/v2/user/profile/name`. (GAI.java:348)
- `updateEmail(NamePasswordData)` → `PUT api/v2/user/profile/email`. (GAI.java:339)
- `updateUserFakedUsername(NamePasswordData)` → `PUT api/v2/user/profile/fakedUsername`.
- `changePassword(ChangePasswordData)` → `POST api/v2/user/changePassword` → `ApiResult`. (GAI.java:102)
- `resentVerifyEmail()` → `POST api/v2/user/resentVerifyEmail`.
- `getBindingInfo()` → `GET api/v2/user/userBindingInfo` → `UserBindingInfo`.
- `bindingThirdAccount` / `unBindThirdUser` — third-site binding.
- `getWechatUserInfo()` → `api/v2/user/wechatUser` → `WechatUserProfile`.
- `getUserPublicProfiles(List)` → `POST pub/api/v2/userPublicProfiles` → `List<PublicUserProfile>`.

Avatar:
- `uploadAvatar(v body)` → `POST api/v1/avatar` → Boolean. (GAI.java:360)
- `getAvatar()` → `GET api/v2/avatar/getUrl` → String.

Status / pro / statistics / ranking:
- `getUserStatus()` → `GET api/v2/user/status` → `SignUserInfo` (the pro/team/grace status model). (GAI.java:270)
- `getRanking(detail)` → `GET api/v3/user/ranking` → `Ranking`.
- `getRecentStatisticsRemoteData()` → `api/v3/user/ranking/recently-completed`.
- `getHistoricalStatisticsRemoteData(date)` → `api/v3/user/ranking/history-completed`.
- `getMedals(autoMark)` → `GET /api/v2/badge` → `List<OwnedMedalRecord>`.

Settings/config endpoints (also see §3):
- `getUserSettings()` → `GET api/v2/user/preferences/settings/android` → `UserPreference`. (GAI.java:267)
- `updateUserSetting(UserPreference)` → `PUT api/v2/user/preferences/settings`. (GAI.java:357)
- `getPomodoroConfig`/`updatePomodoroConfig` → `api/v2/user/preferences/pomodoro`.
- `getHabitConfig`/`updateHabitConfig` → `api/v2/user/preferences/habit`.
- `getFeaturePrompt`/`updateFeaturePrompt` → `api/v2/user/preferences/featurePrompt`.
- `getDailyReminder`/`putDailyReminder` → `api/v2/user/preferences/dailyReminder`.
- `getWechatPreferences`/`putWechatPreferences` → `api/v2/user/preferences/wechat`.
- `getSpecialThemePreference()` → `api/v2/user/preferences/themes`.

Account deletion (see §4):
- `deleteAccount(Map)` → `DELETE api/v2/user/deleteAccount`.
- `deleteAccountV2(vid, Map)` → `DELETE api/v2/user/verify/deleteAccount`.
- `deleteAccountV3(vid, Map)` → `DELETE api/v3/user/verify/deleteAccount` (current 2FA-verified path). (GAI.java:135)
- `deleteThirdSiteAccount` / `…V2` / `…V3` — for third-site (e.g. Google) logins.
- `getAutoSignOnToken()` → `api/v1/user/requestSignOnToken`.

Anchor: literal `"api/v2/user/profile"` (or `"api/v3/user/verify/deleteAccount"`),
both unique to this interface.

### 2.2 `com.ticktick.task.network.sync.common.entity.User` — the network profile DTO
File: `com/ticktick/task/network/sync/common/entity/User.java` (dex: `smali_classes4`)

The wire DTO returned by `getUserProfile()` and posted to `updateName`. Extends
`com.ticktick.task.network.sync.framework.entity.BaseEntity`. Fields:
`accountDomain`, `siteDomain`, `email`, `phone`, `username`, `name`,
`givenName`, `familyName`, `gender`, `locale`, `link`, `picture` (avatar URL),
`userCode`, `extenalId` [sic], `password`, `verifiedEmail`, `filledPassword`
(default true), `fakedEmail` (default false), `createdDeviceInfo` (`DeviceInfo`).
`getName()` composites given+family name when `name` is empty.
Anchor: kept superclass ref `BaseEntity` (no class-unique string literal; the
"site domain"/"faked email" semantics live in fields whose names rotate).

### 2.3 Pro/team/grace status model — `SignUserInfo`
File: `com/ticktick/task/network/sync/common/model/SignUserInfo.java` (dex: `smali_classes4`)

Returned by `getUserStatus()`. Source of `isPro()`, `isTeamUser()`,
`isActiveTeamUser()`, `isTeamPro()`, `getGracePeriod()`, `getNoGraceDate()`,
`getErrorType()`, `getSubscribeType()`/`getSubscribeFreq()`,
`getProStartDate()`/`getProEndDate()`, `getNeedSubscribe()`,
`getUserId()`/`getUserCode()`/`getUsername()`/`getPhone()`. Merged into the local
`User` by `TickTickAccountManager.saveUserStatus` (§1.2). The pro/subscription
gate `User.isPro()` is ultimately fed from here.

---

## 3. User config / settings sync

Two distinct sync surfaces:

### 3.1 Per-user app preferences — `UserProfile` + `UserSettingsSyncService`
- **Local model:** `com.ticktick.task.data.UserProfile`
  (`com/ticktick/task/data/UserProfile.java`, dex `smali_classes3`) — a large
  GreenDAO `Parcelable` holding nearly all app settings: list visibility
  (`isShowTodayList`, `isShow7DaysList`, `isShowCompletedList`,
  `isShowScheduledList`, `isShowAssignList`, `isShowTrashList`, `isShowAllList`,
  `isShowTagsList`, `isShowPomodoro`), sort types per smart list
  (`sortTypeOf*`), swipe options (`swipe{LR,RL}{Short,Middle,Long}`),
  reminder/notification config (`defaultReminderTime`, `dailyReminderTime`,
  `notificationMode`, `notificationOptions`, `stickReminder`,
  `supportNotifyOption`), NLP/date/lunar/holiday flags, `quickDateConfig`,
  `calendarViewConf`, `customizeSmartTimeConf`, `mobileSmartProjectMap`,
  `tabBars`, `timeZone`, `locale`, `startDayWeek`, `inboxColor`, `defaultTags`,
  `isFakeEmail`, `etag`, `status` (sync status: `0`=dirty, `2`=done). Factory
  `createDefaultUserProfile(userId)` (UserProfile.java:432). Anchor: toString
  literal `"UserProfile{id="`.
- **Local DB service:** `com.ticktick.task.service.UserProfileService`
  (`com/ticktick/task/service/UserProfileService.java`, dex `smali_classes4`)
  over `UserProfileDaoWrapper` (`getDaoSession().getUserProfileDao()`).
  `getUserProfileWithDefault(userId)` creates+saves a default if absent;
  `saveUserProfile` (create-or-update); `updateSyncStatusDone(userId)` sets
  status `2`. Anchor: kept ref `getUserProfileDao()`.
- **Wire model:** `com.ticktick.task.network.sync.entity.user.UserPreference`
  (`com/ticktick/task/network/sync/entity/user/UserPreference.java`,
  dex `smali_classes4`) — kotlinx-serialized (`@al.f`) DTO mirroring the
  `UserProfile` fields (server field names like `startDayOfWeek`,
  `defaultRemindTime`, `mobileSmartProjects`, `tabBars`, `quickDateConf`,
  `defaultProjectId`, etc.). Has `$serializer`.
- **Sync engine:** `com.ticktick.task.sync.sync.UserSettingsSyncService`
  (`com/ticktick/task/sync/sync/UserSettingsSyncService.java`, dex
  `smali_classes4`). `doSync()` = `pull()` then `push()` then
  `syncDailyReminder()` then `syncShareVip()`.
  - `pull()` (USS.java:79): `generalApi.getUserSettings()` →
    `UserSettingsHandler.mergeToLocal(UserPreference)`.
  - `push()` (USS.java:93): `UserSettingsHandler.describeCommitPreference()` →
    if non-null `generalApi.updateUserSetting(...)` then `markDoneSyncStatus()`.
  - Delegates HTTP to `com.ticktick.task.sync.network.GeneralApi`, the impl that
    wraps `GeneralApiInterface`. Field-merge logic lives in
    `com.ticktick.task.sync.sync.handler.UserSettingsHandler`.
  - Anchor: string literal `"UserSettingsSyncService"` (TAG, repeated).

### 3.2 Extended preferences (kernel) — `PreferenceExInterface`
File: `com/ticktick/task/network/api/PreferenceExInterface.java` (dex `smali_classes4`)

A small key/value preference-bag sync surface for the kernel preference system:
- `pull(@t(PreferenceKey.MTIME) long checkpoint)` → `GET api/v2/user/preferences/ext` → `Map<String,Object>`.
- `commit(Map<String,Object> bean)` → `POST api/v2/user/preferences/ext`.

This is the generic extensible prefs channel (the `KernelManager.getPreferenceApi()`
backend; note `signOut()` calls `KernelManager.getPreferenceApi().reset()`).
Anchor: literal `"api/v2/user/preferences/ext"`.

### 3.3 Remote app config blob — `UserConfigManager`
File: `com/ticktick/task/userconfig/UserConfigManager.java` (dex `smali_classes4`)

Kotlin `object` (`INSTANCE`). `tryRefreshConfig(context)` throttles by
`UserConfig.getMinInterval()` and runs `ConfigLoaderTask`, which GETs a static
JSON at `buildUrl()` =
`httpUrlBuilder.getPullUrl() + "/android/user_config/" + (isDidaAccount ? "dida" : "ticktick") + ".json"`,
parses into `network.sync.sync.model.UserConfig`, and caches via
`UserConfigCache` (offline-webview config). NOT per-user settings — it's a
server-pushed app-config blob, dida/ticktick-split. Related:
`userconfig/UserConfigCache.java`, `userconfig/PullUserConfigEvent.java`,
`userconfig/DailyReminderConfigSchedule.java`. Anchor: TAG literal
`"UserConfigManager"`.

---

## 4. Account deletion / sign-out / data wipe

### 4.1 Sign-out orchestration — `TickTickAccountManager.signOut(userId)`
`com/ticktick/task/manager/TickTickAccountManager.java:383`. The local wipe /
reset performed on sign-out (does NOT itself hit the network):
- Clears child-fragment caches, status-bar/ongoing notifications, pomo status.
- `userService.freezeUser(userId)` (marks the row frozen, `wake=0`).
- `resetCurrentUserForRemoveOrHide(userId)` → if it was the active user, sets
  `currentUser = instantLocalUser()` (drops to local mode).
- Clears calendar/course caches, `covertUserSettingToLocal()` (copies task
  defaults to the `"local_id"` user), hides quick-add ball, resets local theme.
- **Kernel resets:** `KernelManager.getPreferenceApi().reset()` +
  `getAppConfigApi().reset()`.
- Broadcasts pomo-widget update; fires `AccountManagerEventListener.onLoginOut()`
  to all registered listeners (`DatabaseEventCenter.get(AccountManagerEventListener.class)`).

### 4.2 Sign-out UI flow — `AccountSignOutHelper`
File: `com/ticktick/task/manager/AccountSignOutHelper.java` (dex `smali_classes4`)

Drives the user-facing sign-out:
- `showRemoveAccountDialog(activity)` (ASOH.java:183) → confirm → checks twitter-
  login-disable → `mTaskManager.d(currentUser, false, 0)` to **force a final
  sync** before sign-out (5s timeout via `forceSignOutRunnable`).
- On sync done (`onSynchronized`, ASOH.java:151): `signOut()` →
  `removeSyncListener()` → `startLoginActivity()`. On failure:
  `showForceSignOutDialog()` (warns unsynced changes will be lost).
- `signOut()` (ASOH.java:192) runs a background task that: unregisters push
  (`getPushManager().b(id)`), calls **`LoginApiInterface.signout()`** (the
  server-side logout), then `logout()` → `mUser.setActivity(0)` +
  `mAccountManager.signOut(id)` (§4.1) + analytics
  `ta.e.a().h("profile","sign_out")`. Server call is best-effort: on exception it
  still does the local `logout`. Anchor: string literal `"AccountSignOutHelper"`.

### 4.3 Account deletion — `BaseAccountInfoActivity` + `DeleteAccountFragment`
File: `com/ticktick/task/activity/account/BaseAccountInfoActivity.java` (dex `smali_classes3`)

Implements `DeleteAccountFragment.Callback`. `onDeleteAccount(password)` (around
line 117) runs a coroutine flow that calls the delete-account endpoint
(`GeneralApiInterface.deleteAccountV3` / third-site variant), with error mapping
(BAIA.java:176-184): `b2` → wrong-password toast, `a1` → `showSubscribingDialog()`
(must cancel an active subscription first), `r0` → `gotoTransferShareProject()`
(must transfer shared projects first). On success (`onDeleteAccount$4`,
BAIA.java:217) it calls
`ActivityUtils.signOutAndStartLoginActivity(this)`
(`com/ticktick/task/utils/ActivityUtils.java:541`), which performs the same local
wipe as §4.1 and returns to login. 2FA is plumbed via
`TwoFactorAuthHelper`/`TwoFactorVidHolder` (the `x-verify-id` header on the V2/V3
delete endpoints). Concrete UI: `account/AccountInfoActivity.java`,
`activity/account/DeleteAccountFragment.java`,
`activity/account/BaseAccountInfoFragment.java`.

---

## 5. Multi-account, account switching & local mode

- **Local mode (no account):** represented by a real `User` row with
  `_id="local_id"`, `username="local"`, `accountType=4`,
  `domain=BaseUrl.getLocalModeDomain()`. Created lazily by
  `UserService.getLocalModeUser()` (UserService.java:35). Detected via
  `User.isLocalMode()` / `TickTickAccountManager.isLocalMode()`. Sign-out and
  account-deletion both fall the device back to this user.
- **Multi-account / switching:** the DB can hold multiple `User` rows; exactly
  one has `activity==1` (the active account) — enforced by
  `UserService.saveUserActivity(id)` (resets others) and `freezeAllAccount()`.
  `TickTickAccountManager.setCurrentUser(User)` (TTAM.java:354) is the switch
  point: it saves/activates the new account (or freezes all for local), updates
  the in-memory cache, **switches the global API domain** (`pk.f0.f29198a`) and
  rebuilds the `RequestManager` HTTP client, then triggers daily-summary /
  ongoing-notification / auto-sync re-scheduling and clears
  `ViewFilterSidsOperator`. `getAccountById` / `getAccessTokenById` allow
  per-account lookups. Sign-in itself is handled by another subsystem
  (`account/LoginMainActivity`, `network/api/LoginApiInterface`).

---

## Hook-point quick reference (file:line)

- Current user / cache: `TickTickAccountManager.getCurrentUser()` TTAM.java:143;
  `clearUserCache()` TTAM.java:108; `getAccountManager()`
  TickTickApplicationBase.java:700.
- Pro state read: `User.isPro()` User.java:419; write path
  `TickTickAccountManager.saveUserStatus` TTAM.java:296 (status DTO `SignUserInfo`).
- Account switch: `TickTickAccountManager.setCurrentUser` TTAM.java:354.
- Profile fetch/update: `GeneralApiInterface.getUserProfile` GAI.java:261,
  `updateName` GAI.java:348, `updateEmail` GAI.java:339, `changePassword`
  GAI.java:102, `uploadAvatar` GAI.java:360, `getUserStatus` GAI.java:270.
- Settings sync: `UserSettingsSyncService.doSync/pull/push` USS.java:40/79/93;
  `UserProfileService.saveUserProfile` UserProfileService.java:25;
  ext prefs `PreferenceExInterface` (api/v2/user/preferences/ext).
- Sign-out: `TickTickAccountManager.signOut` TTAM.java:383;
  `AccountSignOutHelper.signOut` ASOH.java:192.
- Delete account: `GeneralApiInterface.deleteAccountV3` GAI.java:135;
  `BaseAccountInfoActivity.onDeleteAccount` BAIA.java:117;
  `ActivityUtils.signOutAndStartLoginActivity` ActivityUtils.java:541.
- Local mode: `UserService.getLocalModeUser` UserService.java:35;
  `User.isLocalMode` User.java:411.
