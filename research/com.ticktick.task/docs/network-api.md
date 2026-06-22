# TickTick — Network / API Layer

- **App:** `com.ticktick.task` (TickTick) — also drives the `cn.ticktick.task`
  (Dida365 / 滴答清单) China sibling from the same code.
- **version_code:** 8081
- **versionName:** 8.0.8.1
- **Subsystem:** HTTP / API surface — base-URL/host config, Retrofit API
  interfaces, the OkHttp client + interceptors, and the sync framework.

All references are to the READ-ONLY decompiled trees:
- jadx Java: `/home/user/apk-workspace/out/jadx/sources/`
- apktool smali: `/home/user/apk-workspace/out/apktool/{smali,smali_classes2..5}/`

Business-logic packages (`com/ticktick/task/*`) keep readable names. The
networking *plumbing* (OkHttp/Retrofit wrappers, interceptors) is in obfuscated
short packages (`w7/`, `y7/`, `x7/`, `vd/`, `td/`, `j7/`) but is easy to anchor
on string literals.

Third-party renames worth knowing:
- `im.*` = OkHttp (`im.w`=`OkHttpClient`, `im.w$a`=`OkHttpClient.Builder`,
  `im.y`=`Request`, `im.y$a`=`Request.Builder`, `im.d0`=`Response`,
  `im.t`=`Interceptor`, `im.v`=`MultipartBody`).
- `ln.*` = Retrofit (`ln.h0`=`Retrofit`, `ln.h0$b`=`Retrofit.Builder`,
  `ln.j0`=`Utils`).
- `on.*` = `retrofit2.http.*` annotations: `@on.f`=`@GET`, `@on.o`=`@POST`,
  `@on.p`=`@PUT`, `@on.b`=`@DELETE`, `@on.a`=`@Body`, `@on.t`=`@Query`,
  `@on.s`=`@Path`, `@on.i`=`@Header`, `@on.w`=`@Streaming`.
- `nn.a` = `GsonConverterFactory`.
- `x7.a` = the custom Retrofit return type (a deferred call wrapper; almost
  every interface method returns `x7.a<T>`), `x7.b` = its custom
  `CallAdapter.Factory`.

---

## 1. Domains and host configuration

### 1.1 `com.ticktick.task.helper.BaseUrl` (classes4.dex)
`/home/user/apk-workspace/out/jadx/sources/com/ticktick/task/helper/BaseUrl.java`

Holds the static domain constants and the live `ServerHostConfig`:

```
BaseUrl.java:28   sServerHostConfig = ServerHostConfig.getRelease();
```

| Constant | Value |
|---|---|
| `TICKTICK_API_DOMAIN` | `https://api.ticktick.com` |
| `TICK_DATA_PLATFORM_DOMAIN` | `https://xapi.ticktick.com` |
| `TICKTICK_SITE_DOMAIN` / `_DOMAIN2` | `https://ticktick.com` |
| `TICKTICK_OLD_DOMAIN` | `https://ticktick.com` |
| `TICKTICK_SUPPORT_DOMAIN` | `https://ticket.ticktick.com` |
| `PULL_TICKTICK_DOMAIN` | `https://pull.ticktick.com` |
| `TICK_DEBUG_COOKIE_DOMAIN` | `https://ticktick.com` |
| `TICK_PATTERN` / `TICK_CER_FILENAME` | `*.ticktick.com` / `ticktick` |
| `DIDA_API_DOMAIN` | `https://api.dida365.com` |
| `DIDA_DATA_PLATFORM_DOMAIN` | `https://xapi.dida365.com` |
| `DIDA_SITE_DOMAIN` / `_DOMAIN2` | `https://dida365.com` |
| `DIDA_SUPPORT_DOMAIN` | `https://support.dida365.com` |
| `PULL_DIDA_DOMAIN` | `https://pull.dida365.com` |
| `DIDA_DEBUG_COOKIE_DOMAIN` | `https://dida365.com` |
| `DIDA_PATTERN` / `DIDA_CER_FILENAME` | `*.dida365.com` / `dida365` |

Selection helpers (all key off `isDidaEnv()`):
- `getApiDomain()` (`BaseUrl.java:30`) → dida vs ticktick API host.
- `getDataTrackerUrl()` (`:34`) → `xapi.*` data-platform host.
- `getSiteDomain()` / `getSiteDomain2()` (`:42`/`:46`) → web host.
- `getLocalModeDomain()` (`:38`) → site host for local (not-signed-in) mode,
  keyed on `j7.a.m()` directly (package = TickTick) rather than account.

`isDidaEnv()` (`BaseUrl.java:50`): returns true if the current `User` is a Dida
account (`user.isDidaAccount()`), **or** local-mode AND not the TickTick package
(`!j7.a.m()`). So the runtime API host is per-account, not just per-build.

### 1.2 `com.ticktick.task.helper.ServerHostConfig` (classes4.dex) — Kotlin data class
`/home/user/apk-workspace/out/jadx/sources/com/ticktick/task/helper/ServerHostConfig.java`

A 9-field data class `(title, apiHost, webHost, webHost2, cookieHost,
dataPlatformHost, supportHost, aiHost, pullDomain)` plus mutable `socketUrl`,
`isEmpty`, `isTickTick`. Field getters preserved: `getApiHost`,
`getDataPlatformHost`, `getAiHost`, `getPullDomain`, `getSupportHost`,
`getSocketUrl`, etc. `HttpUrlBuilderBase.getAiDomain()` reads
`sServerHostConfig.getAiHost()`.

The named environments are built by `ServerHostConfig$Companion`
(classes4.dex, all `wss://` and title literals live in the Companion smali):

| Factory (`getXxx`) | title | apiHost | webHost | dataPlatformHost | aiHost | socketUrl |
|---|---|---|---|---|---|---|
| `getReleaseTick` | `Tick` | `api.ticktick.com` | `ticktick.com` | `xapi.ticktick.com` | `ai.ticktick.com` | `wss://wssp.ticktick.com/android` |
| `getReleaseDida` | `线上环境` | `api.dida365.com` | `dida365.com` | `xapi.dida365.com` | `ai.dida365.com` | `wss://wssp.dida365.com/android` |
| `getBuildApi` | `Build/Api` | `build.dida365.com` | `api.dida365.com` | `xapi.dida365.com` | `ai.dida365.com` | wss-pomodoro-test |
| `getBuildBuild` | `Build/Build` | `build.dida365.com` | `build.dida365.com` | `xapi.dida365.com` | `ai.dida365.com` | — |
| `getTickBuild` | `Tick Build` | `build.ticktick.com` | `build.ticktick.com` | `xapi.ticktick.com` | `ai.ticktick.com` | (pull=`pull.ticktick.com`, isTickTick=true) |
| `getDevDida` | `Dev环境` | `api-dev.365dida.com` | `dev.365dida.com` | `xapi-dev.365dida.com` | `ai-dev.365dida.com` | wss-pomodoro-dev |
| `getTestDida` | `Test环境` | `api-test.365dida.com` | `test.365dida.com` | `xapi-test.365dida.com` | `ai-test.365dida.com` | wss-pomodoro-test |
| `getFutureDida` | `Future环境` | `api-future-test.365dida.com` | `future-test.365dida.com` | `xapi.dida365.com` | `ai-future-test.365dida.com` | — |

`getRelease()` (`ServerHostConfig.java:55`): `j7.a.m() ? getReleaseTick() :
getReleaseDida()` — i.e. **the shipped host set is chosen purely by package
name at startup**, then per-request host can still flip via `BaseUrl.getApiDomain()`.

Domains by purpose (release): **api** `api.{ticktick,dida365}.com`, **xapi**
(data platform / tracker) `xapi.*`, **ai** `ai.*`, **pull** `pull.*` (push/long-poll
helper domain), **build** `build.*` (internal/QA), **web/site** `{ticktick.com,
dida365.com}`, **support** `ticket.ticktick.com` / `support.dida365.com`,
**socket** `wss://wssp.*/android` (Pomodoro websocket, see §3.4).

### 1.3 `HttpUrlBuilderBase` + Tick/Dida subclasses (all classes4.dex)
`.../helper/HttpUrlBuilderBase.java`, `HttpUrlBuilderTick.java`,
`HttpUrlBuilderDida.java`

- `HttpUrlBuilderBase extends BaseUrl` — abstract; declares the per-flavor URL
  getters (help, support, import, medal, pull, etc.) and a static inner
  `DomainType` holding the four mutable routing constants
  `INTERNATIONAL_SITE/CHINA_SITE/INTERNATIONAL_API/CHINA_API`
  (`HttpUrlBuilderBase.java:9-21`). `BaseUrl.syncData()` re-pins them.
  `getAiDomain()` (`:34`) → `sServerHostConfig.getAiHost()`.
- `HttpUrlBuilderTick` — TickTick(intl) URL set. `getSiteDomain()`
  (`HttpUrlBuilderTick.java:11`) is the runtime *web* host picker: local-mode +
  TickTick package → international; else if signed-in and `user.getDomain()` set
  → that; else uses `SettingsPreferencesHelper.isIpInChina()` / locale
  (`j7.a.o()` = simplified-Chinese, `j7.a.N()`) to fall back to CHINA_SITE vs
  INTERNATIONAL_SITE. Unique anchor: MS-Todo OAuth client id
  `ac15cc06-2732-4101-8587-3e0ac1cbc4c6`.
- `HttpUrlBuilderDida` — Dida(China) URL set; all getters return `dida365`/
  `365dida`/`help.dida365.com` URLs. Unique anchor: MS-Todo client id
  `2ef4d21e-9f3f-45e9-af95-329cd54900b4`.

### 1.4 TickTick(intl) vs Dida365(China) selection — summary

Two independent axes:
1. **Build/package** — `j7.a.m()` (`/home/user/apk-workspace/out/jadx/sources/j7/a.java:350`)
   caches `TextUtils.equals("com.ticktick.task", context.getPackageName())`.
   True = TickTick intl build, false = Dida (`cn.ticktick.task`). This picks the
   `ServerHostConfig` host set at startup (`getRelease`) and the
   `HttpUrlBuilder` subclass.
2. **Account / locale at runtime** — `BaseUrl.isDidaEnv()` (account is Dida, or
   local-mode on a non-TickTick package) flips the *API* host per request;
   `HttpUrlBuilderTick.getSiteDomain()` additionally uses
   `user.getDomain()`, `SettingsPreferencesHelper.isIpInChina()`, and locale
   helpers `j7.a.o()` (`a.java:372`, simplified-Chinese) / `j7.a.N()`
   (`a.java:193`, system simplified-Chinese) to route the *web* host.

---

## 2. Endpoint catalog (Retrofit interfaces)

All interfaces live in `com/ticktick/task/network/api/` (jadx) and
`smali_classes4/com/ticktick/task/network/api/` (classes4.dex). Every method
returns `x7.a<…>` (custom call). Paths copied verbatim from the
`@on.f/o/p/b("…")` annotations. `{x}` = `@Path`, query params via `@Query`,
`@Body` bodies noted where useful. Leading-slash inconsistency is in the source.

### AiApiInterface (host: aiHost `ai.*`)
| Method | HTTP | Path | Purpose |
|---|---|---|---|
| `aiTextSummary` | POST | `/ai/api/v2/voice/task/summary` | summarize voice/task text |
| `aiVoiceToText` | POST | `/ai/api/v2/voice/task/transcriptions` | upload audio for STT |
| `getAiVoiceToTextResult` | GET | `/ai/api/v2/voice/task/transcriptions/task` | poll STT result |
| `launchAiVoiceToTextJob` | POST | `/ai/api/v2/voice/task/transcriptions/task` | start STT job |
| `parseTaskFromVoiceText` | POST | `/ai/api/v2/voice/task/extract` | extract task fields from text |
| `getRecommentTaskHistory` | POST | `/ai/api/v2/task/recommend/history` | AI task-recommend history |
| `getRecommentTaskResult` | GET | `/ai/api/v2/task/recommend/task` | poll recommend result |
| `recommendTask` | POST | `/ai/api/v2/task/recommend/task` | request task recommendations |
| `queryAiGenerated` | POST | `/ai/api/v2/generated` | query AI-generated content |

### AppConfigInterface (host: apiHost)
| Method | HTTP | Path | Purpose |
|---|---|---|---|
| `pull` | GET | `pub/api/v1/app/config` | pull remote app config (etag/from) |

### BatchApiInterface (host: apiHost) — core sync batch endpoints
| Method | HTTP | Path | Purpose |
|---|---|---|---|
| `batchCheck` | GET | `api/v2/batch/check/{point}` | full/incremental sync pull (checkpoint) → `SyncBean` |
| `batchUpdateTasks` | POST | `api/v2/batch/task` | push task add/update/delete |
| `batchUpdateProjects` | POST | `api/v2/batch/project` | push project (list) changes |
| `batchUpdateProjectGroups` | POST | `api/v2/batch/projectGroup` | push project group changes |
| `batchUpdateTags` | POST | `api/v2/batch/tag` | push tag changes |
| `batchUpdateFilters` | POST | `api/v2/batch/filter` | push filter changes |
| `batchUpdatePomodoros` | POST | `api/v2/batch/pomodoro` | push pomodoro changes |
| `batchUpdateTiming` | POST | `api/v2/batch/pomodoro/timing` | push timing changes |
| `batchUpdateTaskOrders` | POST | `api/v2/batch/taskOrder` | push task sort orders |
| `batchUpdateTaskParent` | POST | `api/v2/batch/taskParent` | push task parent relations |
| `batchUpdateTaskSortOrders` | POST | `api/v2/batch/taskProjectSortOrder` | push task/project sort order |
| `batchUpdateMoveProjects` | POST | `api/v2/batch/taskProject` | move tasks between projects |
| `batchDeleteTasks` | POST | `api/v2/tasks/delete` | hard/soft delete tasks (`?forever`) |
| `batchRestoreDeletedTasks` | POST | `api/v2/trash/restore` | restore from trash |
| `batchUpdateAssignees` | POST | `api/v2/task/assign` | assign tasks |
| `batchUpdateCalendarEvent` | POST | `/api/v2/calendar/bind/events/batch` | bound-calendar event batch |
| `batchUpdateCalDavCalendarEvent` | POST | `api/v4/calendar/bind/events/batch` | CalDAV event batch |

### CountdownApiInterface (host: apiHost)
| Method | HTTP | Path | Purpose |
|---|---|---|---|
| `getCountdowns` | GET | `/api/v2/countdown/list` | list countdowns (`?status`) |
| `batchUpdate` | POST | `/api/v2/countdown/batch` | batch countdown sync |
| `uploadBackground` | POST(@Streaming) | `/api/v1/attachment/upload/countdown` | upload countdown bg image |
| `downloadBackground` | GET(@Streaming) | `/api/v1/attachment/countdown` | download countdown bg |

### CourseApiInterface (host: apiHost) — timetable/course
| Method | HTTP | Path |
|---|---|---|
| `batchUpdateSchedule` | POST | `api/v1/course/batch/timetable` |
| `checkImageOrcLimit` | GET | `/api/v1/course/upload/check` |
| `copyTimetable` | POST | `/api/v1/course/share/copy/{timetableShareId}` |
| `getPreviewTimetable` | GET | `/api/v1/course/share/preview/{timetableShareId}` |
| `getTimetableShareInfo` | GET | `/api/v1/course/share/{timetableId}` |
| `getTimetables` | GET | `/api/v1/course/timetable` |
| `parseApplyTimetable` | POST | `/api/v1/course/parseApply` |
| `parseTimetable` | POST | `/api/v1/course/parse/{schoolId}` |
| `postArchivedCourse` | POST | `/api/v1/course/archived` |
| `pullArchivedCourse` | GET | `/api/v1/course/archived` |
| `postSchoolUrl` | POST | `/api/v1/course/courseUrl` |
| `queryImageOrcResult` | GET | `/api/v1/course/{id}/ocr` |
| `uploadImage4ImportTimetable` | POST | `/api/v1/course/attachment/upload` |

### GeneralApiInterface (host: apiHost) — the big catch-all (~95 endpoints)
Full method list is long; representative endpoints by area:
- **Subscription / payment:** `getProductList4Local` POST `/pub/api/v2/subscribe/free_trial_2w?platform=google`; `getProductListWithFreeTrial` POST `/api/v3/subscribe/free_trial_2w`; `getAlipayInfo` GET `api/v2/payment/alipay_android`; `getWeChatPayInfo` GET `api/v1/payment/wechat_android`; alipay subscribe GET `/api/v2/payment/alipay/subscribe`; wxpay subscribe POST `/api/v2/payment/wxpay/subscribe/android`; `cancelSubscribe` PUT `/api/v1/payment/cancel/{type}`; verify google POST `api/v2/subscribe/verify/google`; `getSubscribeList` GET `/api/v2/subscribe/list`; blacklist GET `/api/v2/payment/isBlacklist`.
- **Trials/promo:** POST `/api/v2/trial/3day`, `/api/v2/trial/7day`; GET `/api/v2/trial/7day/available`, `/pub/api/v2/promotion/7pro`, `pub/api/v1/promo/year2021`; `freePro` POST `/api/v2/freePro/google`; functionTrial POST `/api/v2/functionTrial/create`.
- **User / profile / preferences:** `getUserProfile` GET `api/v2/user/profile`; `getUserStatus` GET `api/v2/user/status`; `changePassword` POST `api/v2/user/changePassword`; preferences pull/push GET/PUT `api/v2/user/preferences/{settings/android, habit, pomodoro, dailyReminder, wechat, themes, featurePrompt}`; profile updates PUT `api/v2/user/profile/{email,name,fakedUsername}`; `getUserRegTime` GET `/api/v2/user/regTime`.
- **Notifications/badge/medal:** `getNotification` GET `api/v2/notification`; unread GET `api/v2/notification/unread`; `markNotificationRead` PUT `api/v2/notification/markRead`; delete `@DELETE api/v2/notification/delete/{notificationIds}`; `getMedals` GET `/api/v2/badge`; unmark GET `/api/v2/badge/unmark`.
- **Ranking/stats:** `getRanking` GET `api/v3/user/ranking`; history `api/v3/user/ranking/history-completed`, `recently-completed`.
- **Push register:** `registerPush` POST `api/v2/push/register`; `unregisterPush` `@DELETE api/v2/push/unregister/{id}`; cancel POST `api/v2/push/cancel`.
- **Third-party binding:** POST `api/v2/user/third/binding`; `unBindThirdUser` `@DELETE api/v2/user/unbinding`; deleteThirdSiteAccount `@DELETE api/v2/user/{,verify/}deleteThirdSiteAccount` (v2/v3); notion connect POST `/api/v2/connect/notion`.
- **Data collection:** `updateDevice` POST `datacollect/device/update`; event upload POST `datacollect/event/upload`; google_play stats POST `pub/api/v1/stats/google_play`.
- **Templates/referral/avatar/captcha/gift:** project templates GET `/api/v2/projectTemplates/all`; apply template POST `api/v2/templates/project/{id}/apply`; refer code/barcode/rewards GET `api/v2/refer/*`; avatar POST `api/v1/avatar` + GET `api/v2/avatar/getUrl`; captcha GET `/pub/captcha`; giftcard POST `api/v1/giftcard/apply/{code}`.

Unique anchor literals present: `datacollect/device/update`, `datacollect/event/upload`, `/api/v2/badge`.

### HabitApiInterface (host: apiHost)
| Method | HTTP | Path |
|---|---|---|
| `batchUpdateHabits` | POST | `api/v2/habits/batch` |
| `getHabits` | GET | `api/v2/habits` |
| `batchUpdateHabitCheckins` | POST | `api/v2/habitCheckins/batch` |
| `getHabitCheckIns` | GET | `api/v2/habitCheckins` |
| `batchUpdateHabitRecords` | POST | `/api/v2/habitRecords` |
| `getHabitRecords` | GET | `/api/v2/habitRecords` |
| `batchUpdateHabitSections` | POST | `/api/v2/habitSections/batch` |
| `getHabitSections` | GET | `api/v2/habitSections` |

### LiveActivityApiInterface (host: apiHost) — vendor live-activity/push
| Method | HTTP | Path |
|---|---|---|
| `addLiveToVivo` | POST | `api/v2/live/activity/vivo` |
| `addLiveToXiaomi` | POST | `api/v2/live/activity/xiaomi` |
| `cancelLiveToVivo` | DELETE | `api/v2/live/activity/vivo/push` |
| `cancelLiveToXiaomi` | DELETE | `api/v2/live/activity/token/push` |
| `deleteLiveToVivo` | DELETE | `api/v2/live/activity/vivo` |
| `deleteLiveToXiaomi` | DELETE | `api/v2/live/activity/token` |

### LoginApiInterface (host: apiHost / site for OAuth)
| Method | HTTP | Path |
|---|---|---|
| `signup` / `signupBySms` | POST | `api/v2/user/signup` (`@Header x-timestamp`) |
| `signOn` | POST | `api/v2/user/signon` (`@Header x-timestamp`) |
| `signout` | GET | `api/v2/user/signout` |
| `signOAuth2` / `…CN` / `…Wechat` | GET | `api/v2/user/sign/OAuth2` |
| `signOAuth2Weibo` | GET | `/api/v2/user/sign/weibo/validate` |
| `signTwitter` | GET | `api/v2/user/sign/twitter` |
| `bindPhone` | POST | `/api/v2/user/sms/phone/bind` |
| `sendBindSmsCode` | POST | `api/v2/user/sms/code` |
| `sendSmsCode` | POST | `api/v2/user/sms/signup/code` |
| `sendEmailVerificationCode` | POST | `/api/v2/user/sendVerifyCode` |
| `checkSuggestCn` | GET | `api/v2/user/sign/suggestcn` |
| `getInviteCode` | GET | `api/v2/user/signup/inviteCode` |
| `isJustRegistered` | GET | `api/v2/user/isJustRegistered` |
| `updateFakeName` | PUT | `/api/v2/user/profile/updateFakedName` |
| `updateGooglePwd` | POST | `api/v2/user/third/changePassword` (`@Header access_token`) |

### PreferenceExInterface (host: apiHost)
| Method | HTTP | Path |
|---|---|---|
| `commit` | POST | `api/v2/user/preferences/ext` |
| `pull` | GET | `api/v2/user/preferences/ext` (`?mtime`) |

### PushTestApiInterface (host: apiHost)
| Method | HTTP | Path |
|---|---|---|
| `pushArrives` | POST | `api/v2/push/stats/arrive` |

### TaskApiInterface (host: apiHost) — task/project/collab/calendar/pomodoro (~95 methods)
Representative (full set in jadx file lines 90–380):
- **Tasks:** `getTask` GET `api/v2/task/{taskId}`; `getTaskWithChildren` GET `api/v2/task/{taskId}?withChildren`; closed/completed POST `api/v2/tag/completedTask`; etags GET `api/v2/project/{id}/taskEtags`; search GET `/api/v2/search/all`; activity GET `api/v1/project/{projectId}/task/{taskId}/activity`; activity count POST `/api/v2/task/activity/count`.
- **Trash:** GET `api/v2/project/all/trash/pagination` & `…/page`; `@DELETE api/v2/trash/empty`, `api/v2/trash/cleanUp`; restore POST `api/v2/trash/restore`.
- **Projects/lists:** archive POST `api/v2/project/{projectId}/close`; PUT `/api/v2/project`; duplicate POST `/api/v2/project/{projectId}/duplicate`; barcode share POST/GET `api/v2/project/{projectId}/barcode`, `/api/v2/project/barcode/{barcodeId}`.
- **Sharing/collaboration:** apply/accept/refuse PUT `api/v2/project/collaboration/{apply,accept,refuse}`; permission PUT `api/v2/project/permission/{accept,refuse}` & POST `…/{projectId}/permission/apply`; invite POST/DELETE `api/v2/project/{projectId}/collaboration/invite`; shares GET/POST `api/v2/project/{projectId}/shares`; share contacts GET/DELETE `api/v2/share/{contacts,shareContacts}`.
- **Comments:** POST `api/v2/project/{projectId}/task/{taskId}/comment`; GET comments; `@DELETE …/comment/{commentId}`.
- **Agenda / task-attend:** GET `api/v2/task-attend/{taskAttendId}/attendees`; create invite GET `api/v2/task-attend/invitation/create`; owner allow PUT `api/v2/task-attend/invitation/closed/{taskAttendId}`; delete attendee `@DELETE api/v2/task-attend/{projectId}/attendees/{taskAttendId}`.
- **Calendar bind/connect:** bind POST `api/v4/calendar/bind`, GET `api/v2/calendar/bind?channel=android`; iCloud POST `api/v4/calendar/bind/icloud`; exchange POST `api/v2/calendar/bind/exchange`; connect GET `api/v2/calendar/connect?channel=android`; events GET/POST `api/v2/calendar/bind/events/{id,all,outlook}`; subscribe POST `api/v2/calendar/subscribe`, `api/v2/calendar/batch/subscribe`; subscription GET `api/v2/calendar/subscription`.
- **Pomodoro/focus:** GET `api/v2/pomodoros`, `/api/v2/pomodoros/timeline`, `/api/v2/pomodoros/timing`; bind POST `/api/v2/pomodoro/{habit,task}/bind`, `/api/v2/pomodoro/timing/{habit,task}/bind`; delete `@DELETE /api/v2/pomodoro/all`, `/api/v2/pomodoro/{id}`, `/api/v2/pomodoro/timing/{id}`; filter POST `/api/v2/pomodoro/filter`; record GET `/api/v2/pomodoro/record/{checkPoint}`.
- **Attachments:** GET `api/v1/attachment/{projectId}/{taskId}/{attachmentId}` and comment variant; daily limit GET `api/v1/attachment/dailyLimit`.
- **Misc:** favorite location GET/POST/DELETE `api/v2/user/favLocation`; tag merge PUT `api/v2/tag/merge`; page show GET `api/v2/page/show`.

Unique anchors present: `/api/v2/search/all`, `api/v2/task-attend/invitation/create`.

### TaskTemplateApiInterface (host: apiHost)
| Method | HTTP | Path |
|---|---|---|
| `getAllTaskTemplate` | GET | `/api/v2/templates` |
| `postAllNoteTemplate` | POST | `/api/v2/templates/note` |
| `postAllTaskTemplate` | POST | `/api/v2/templates/task` |

### TeamApiInterface (host: apiHost)
| Method | HTTP | Path |
|---|---|---|
| `acceptJoinTeam` | PUT | `api/v2/team/collaboration/{accept}` |
| `getAllTeams` | GET | `api/v2/teams` |
| `getTeamMembers` | GET | `api/v2/team/{teamId}/members` |
| `getTeamUserShareContacts` | GET | `api/v2/team/{teamId}/share/shareContacts` |
| `getRecentProjectUsers` | GET | `api/v2/project/share/recentProjectUsers` |
| `getTeamRecentProjectUsers` | GET | `api/v2/project/team/share/recentProjectUsers` |
| `changeListOwner` | POST | `api/v2/project/{projectSid}/transfer` |
| `upgradeProject` | PUT | `api/v2/project/{projectId}/upgrade` |
| `downgradeProject` | PUT | `api/v2/project/{projectId}/degrade` |
| `handleTeamJoinInvitation` | POST | `api/v2/team/accept/invite` |

### TestApiInterface (host: xapi/data-platform) — A/B testing
| Method | HTTP | Path |
|---|---|---|
| `getPlanType` | POST | `datacollect/pub/v1/ab/group` |
| `getTestPlanResults` | POST | `datacollect/pub/v1/ab/group/result` |
| `postEvent` | POST | `datacollect/pub/v1/ab/event` |

### TicketApiInterface (host: support / data-platform)
| Method | HTTP | Path |
|---|---|---|
| `ticket` | POST | `/api/v1/ticket` |

### TimerApiInterface (host: apiHost) — focus timers
| Method | HTTP | Path |
|---|---|---|
| `batchUpdate` | POST | `/api/v2/timer` |
| `getAllTimers` | GET | `/api/v2/timer` |
| `getOverview` | GET | `/api/v2/timer/overview/{timerId}` |
| `getStatistics` | GET | `/api/v2/timer/statistics/{timerId}/{startDay}/{endDay}/{interval}` |
| `getTimeline` | GET | `/api/v2/timer/timeline/{timerId}` |

### TwoFactorApiInterface (host: apiHost) — MFA
| Method | HTTP | Path |
|---|---|---|
| `query2FactorMethods` | GET | `api/v2/user/mfa/setting` |
| `query2FactorMethodsWhenSign` | GET | `api/v2/user/sign/mfa/setting` (`@Header x-verify-id`) |
| `sendCode` | POST | `api/v2/user/mfa/code` |
| `sendCodeWhenSign` | POST | `api/v2/user/sign/mfa/code` (`@Header x-verify-id`) |
| `verifyCode` | POST | `/api/v2/user/mfa/code/verify` |
| `verifyCodeWhenSign` | POST | `/api/v2/user/sign/mfa/code/verify` (`@Header x-verify-id`) |
| `verifyOAuth2Token` | GET | `api/v2/user/mfa/OAuth2` |

---

## 3. The networking stack (OkHttp + Retrofit + interceptors)

### 3.1 `w7.b` = `ApiFactoryBase.kt` (classes2.dex) — builds the client + Retrofit
`/home/user/apk-workspace/out/jadx/sources/w7/b.java`

- Holds the interceptors and a lazy `OkHttpClient`:
  - `f34206b` = `y7.a` (request header interceptor, "httpsRequestInterceptor"),
  - `f34205a` = `y7.b` (response interceptor, "responseInterceptor"),
  - `f34208d` = `b2.e` (the "headerInfo" / `RequestHeaderInfo` provider, `Locale`),
  - `f34207c` = `im.o` (`Dns`), `f34209e` = `im.n` (`ConnectionPool`).
- **OkHttpClient build** (`w7.b$C0481b.invoke`, `b.java:83-133`):
  - SSL: `SSLContext.getInstance("TLS")`.
  - timeouts: connect 25s, read 40s, write 40s (`b.java:94-96`).
  - interceptor order added: `y7.a` (request headers) → `y7.c`
    (`PayPathRequestInterceptor`) → `y7.b` (response) → `wm.a`
    (OkHttp `HttpLoggingInterceptor`, level `a.EnumC0487a.f34583a` = `NONE`).
  - dispatcher `maxRequests` set to 10 (`b.java:127-131`).
- **Retrofit build** in `<S> S a(Class<S>, apiBaseUrl, token, boolean useC)`
  (`b.java:136-186`):
  - `ln.h0$b` = `Retrofit.Builder`; `callbackExecutor` = `w7.a` (a main-thread
    executor); call-adapter factories `x7.b` (custom → returns `x7.a`) **and**
    `mn.g` (RxJava2 `CallAdapter.Factory`); `baseUrl(apiBaseUrl)`; converter =
    `b()` or `c()` (Gson, via subclass).
  - Per-`(domain, interfaceClass)` instances cached in static `f34204h`
    (`HashMap`). When a per-request `token` is supplied, it rebuilds the client
    removing the shared `y7.a` and adding a fresh `new y7.a(headerInfo, token)`
    so the override token is used (`b.java:159-176`).
- `b()`/`c()` are abstract → `nn.a` (`GsonConverterFactory`).

### 3.2 `w7.c` = `GsonApiFactory.kt` (classes2.dex) — singleton concrete factory
`/home/user/apk-workspace/out/jadx/sources/w7/c.java`
- `c extends w7.b`; singleton `f34215i`.
- `b()` → `nn.a.c(a8.n.b())`, `c()` → `nn.a.c(a8.n.c())` — two Gson configs
  (`a8.n` is the Gson holder). `b()` is the default, `c()` the alternate
  (selected by the `boolean` arg, often for date-tolerant parsing).

### 3.3 `y7.a` = `HttpRequestInterceptor.kt` (classes2.dex) — request headers / signing
`/home/user/apk-workspace/out/jadx/sources/y7/a.java`
The single place all standard headers are injected (`a.b(Request.Builder)`,
`a.java:39-87`):
| Header | Value / source |
|---|---|
| `Accept-Language` | from `RequestHeaderInfo` locale, e.g. `xx-YY, xx;q=0.8, en-US;q=0.6, en;q=0.4`, fallback `en-US, en;q=0.4` |
| `LOCALE` (`Constants.PK.LOCALE`) | `locale.toString()`, fallback `en_US` |
| `hl` | `j7.a.b().toString()` (app locale) |
| `X-Device` | `TickTickUtils.getDeviceInfoWithCampaign()` (JSON device descriptor) |
| `Authorization` | `"OAuth " + accessToken` (override token, else `AccountManager.getAccessToken()`) |
| `User-Agent` | `TickTickUtils.getAppMessage() + ' ' + j7.a.h()` (app build string + version code) |
| `traceid` | `Utils.generateObjectId()` (per-request 24-hex ObjectId) |
| `x-tz` | `TimeZone.getDefault().getID()` |

No HMAC/body signing — auth is the bearer `OAuth <token>` header. Anchor
literals: `hl`, `X-Device`, `traceid`, `x-tz`, `OAuth `, `en-US, en;q=0.4`.

### 3.4 `y7.c` = `PayPathRequestInterceptor.kt` (classes2.dex)
`/home/user/apk-workspace/out/jadx/sources/y7/c.java`
For a fixed allow-list of payment paths (e.g. `/api/v1/payment/alipay_android`,
`/api/v2/payment`, `/api/v2/subscribe/verify/google`, …), if the static
`f36201b` data-label is set, adds header `X-Data-Label`. Anchors:
`/api/v1/payment/alipay_android`, `X-Data-Label`.

### 3.5 `y7.b` = `HttpResponseInterceptor.kt` (classes2.dex) — error handling
`/home/user/apk-workspace/out/jadx/sources/y7/b.java`
- `implements im.t`; field `f36200a` = `td.c`.
- Reads `traceid` off responses for logging (`b.java:187`), inspects
  `Authorization` (`:558`), maps error bodies to
  `com.ticktick.task.network.sync.sync.model.ApiErrorResult`, and dispatches a
  large family of typed exceptions from package `ud.*` (`ud.a0`..`ud.z2` —
  the per-error-code exception hierarchy) imported at the top. Logs under tag
  `"NETWORK"`. Handles 401/lock (`LockManager`) and triggers re-auth
  (Google sign-in import present).

### 3.6 `td.f` (classes4.dex) — Pomodoro WebSocket (not Retrofit)
`/home/user/apk-workspace/out/jadx/sources/td/f.java`
`extends im.j0` (`WebSocketListener`), connects to `ServerHostConfig.socketUrl`
(`wss://wssp.*/android`). Builds the handshake `Request` with the same auth
trio — `Authorization: OAuth <token>`, `x-device`, `hl` (`td/f.java:148-156`) —
plus the standard `Sec-WebSocket-*` headers. Fan-out to a `HashSet<WebSocketListener>`.

### 3.7 `nm.a` (classes-level, OkHttp internal) — default UA fallback
`/home/user/apk-workspace/out/jadx/sources/nm/a.java:64-65` sets
`User-Agent: okhttp/4.12.0` only if none present (confirms OkHttp 4.12.0).

---

## 4. Sync framework / how interfaces are invoked

### 4.1 `vd.d` = `BaseApi.kt` (`com.ticktick.task.network.restful.BaseApi`, classes4.dex)
`/home/user/apk-workspace/out/jadx/sources/vd/d.java`
Generic `class d<T>` — the bridge from a domain string + interface class to a
live Retrofit proxy:
- ctor `d(String domain, boolean useAltGson)` (`d.java:53`): resolves `T` from
  its parameterized superclass and calls `w7.c.f34215i.a(interfaceClass, domain,
  null, useAltGson)` → cached proxy stored in `f33309c`.
- `a(String token)` (`d.java:65`): same but with a per-call override token
  (forces a token-scoped client per §3.1).
- Static `d.a.a(File)` builds a `multipart/form-data` body (`v` / MultipartBody)
  for attachment uploads.

Per-interface subclasses extend `d<SpecificApiInterface>`, e.g.
`vd.m extends d<TaskApiInterface>` (`vd/m.java:14`, `TaskApi.kt`). Callers do
`new vd.m(apiDomain, false).f33309c` to get a `TaskApiInterface` and invoke
endpoints. `apiDomain` comes from
`AccountManager.getCurrentUser().getApiDomain()` (e.g. `z9/a.java:42-44`), i.e.
the per-account API host from §1.

### 4.2 Batch sync entities
The `BatchApiInterface` request bodies (`SyncTaskBean`, `SyncProjectBean`,
`SyncBean`, `BatchUpdateResult`, etc.) live under
`com/ticktick/task/network/sync/` (model/entity/sync subtrees). The sync result
helper `ApiResult` is at
`com/ticktick/task/network/sync/framework/api/ApiResult.java` (constant
`ApiResult.TOKEN = "token"`, used by `LiveActivityApiInterface`).
`batchCheck(point)` (GET `api/v2/batch/check/{point}`) is the incremental pull
(checkpoint), and the `batchUpdate*` POSTs are the push side — these are the
core of the sync loop.

---

## 5. Hook points (class : member — file:line)

Base-URL / host:
- `com.ticktick.task.helper.BaseUrl.getApiDomain()` — BaseUrl.java:30 (per-request API host)
- `com.ticktick.task.helper.BaseUrl.isDidaEnv()` — BaseUrl.java:50 (Dida vs Tick selector)
- `com.ticktick.task.helper.ServerHostConfig$Companion.getRelease()` — ServerHostConfig.java:55 (build host set)
- `com.ticktick.task.helper.HttpUrlBuilderTick.getSiteDomain()` — HttpUrlBuilderTick.java:11 (web host routing)
- `j7.a.m()` — j7/a.java:350 (package=TickTick test), `j7.a.o()` — j7/a.java:372 (zh-CN locale)

HTTP client / interceptors:
- `w7.b.a(Class, String, String, boolean)` — w7/b.java:136 (Retrofit proxy factory + cache)
- `w7.b$C0481b.invoke()` — w7/b.java:88 (OkHttpClient build: timeouts + interceptor chain)
- `w7.c` (GsonApiFactory singleton `f34215i`) — w7/c.java:14
- `y7.a.b(Request.Builder)` — y7/a.java:39 (ALL request headers / auth injection)
- `y7.c.a(Interceptor.Chain)` — y7/c.java:21 (X-Data-Label for payment paths)
- `y7.b.a(Interceptor.Chain)` — y7/b.java:110 (response error handling)
- `td.f.g()` — td/f.java:135 (Pomodoro WebSocket connect + auth headers)

Sync entry:
- `vd.d.<init>(String, boolean)` — vd/d.java:53 ; `vd.d.a(String)` — vd/d.java:65 (interface proxy resolution)
- e.g. `vd.m` (`TaskApi.kt`) — vd/m.java:14 (`d<TaskApiInterface>`)
- `BatchApiInterface.batchCheck` / `batchUpdateTasks` — sync pull/push core

---

## 6. Notes for signature authoring
- The 18 API interfaces are PRESERVED-name interfaces in classes4.dex; anchor
  each on a unique endpoint **path string literal** present in its smali (these
  are rotation-stable — server contract, not obfuscated members). Suggested
  unique anchors are listed per-interface in §2.
- The plumbing classes (`w7.b/c`, `y7.a/b/c`, `vd.d`) are obfuscated short
  names that WILL rotate; anchor on the verified string literals (`hl`,
  `X-Device`, `traceid`, `x-tz`, `httpsRequestInterceptor`, `headerInfo`,
  `X-Data-Label`, `/api/v1/payment/alipay_android`) and on kept
  framework supertype/interface refs (`im.t` = OkHttp Interceptor) rather than
  member names.
- `BaseUrl`/`ServerHostConfig`/`HttpUrlBuilder*` are PRESERVED names in
  classes4.dex; anchor on the domain string constants.
