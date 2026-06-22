# TickTick — Premium / Billing / Subscriptions

- **App:** `com.ticktick.task` (TickTick)
- **version_code:** `8081`  **versionName:** `8.0.8.1`
- **Obfuscation:** partial. `com/ticktick/task/*` package + class names mostly
  preserved; helper/library classes (`b8.*`, retrofit impls, lambdas) renamed.
- **Decompiled trees (read-only):**
  - jadx: `/home/user/apk-workspace/out/jadx/sources/`
  - apktool smali: `/home/user/apk-workspace/out/apktool/`

All `file:line` references below are into the jadx tree unless prefixed `smali:`.

---

## 1. Google Play Billing integration

### 1.1 Billing client wrapper — `NewGoogleBillingPayment`

`com/ticktick/task/payfor/billing/NewGoogleBillingPayment.java` is the central
Play Billing wrapper. It is **not** a renamed Play class — it wraps the official
`com.android.billingclient.api.*` (Play Billing Library v6/v7-style: uses
`ProductDetails` / `queryProductDetailsAsync` / `BillingFlowParams`, not the old
SkuDetails API).

- Class signature: `implements b8.b, com.android.billingclient.api.m`
  (line 57). `b8.b` is the app's payment abstraction (`IPayment`); `…api.m` is
  the Play `PurchasesUpdatedListener`.
- Constructor (line 576): builds the `BillingClient` via `c.a(activity)` +
  `aVar.f5934a = new com.android.billingclient.api.j()` (PendingPurchasesParams)
  + `aVar.f5936c = this` (listener), then `aVar.a()`. Also instantiates the
  helper `NewGoogleBillingPayUtils` (line 589).
- `TAG = "NewGoogleBillingPayment"` (line 584) and the literal
  `"BillingClient can only be used once -- closing connection"`
  (`destroy()`, line 784) are unique, rotation-stable anchors.
- Connection is gated through `doAfterClientReady(...)` → `BillingClientKtxKt`
  (line 639) which calls `BillingClientKtxKt.doAfterConnected(...)`.
- Implements the `b8.b` (IPayment) surface: `obtainPrices` (line 844),
  `payFor(freqType, label)` (line 856), `getProductId` (line 833),
  `updateUserInfo` (line 924), `setCallback` (line 870), `dispose` (line 790).
- `onPurchasesUpdated` (line 849) delegates straight to
  `NewGoogleBillingPayUtils.onPurchasesUpdated`.

Nested types worth knowing: `IProgressDialog`, `OnWebPayListener` (web-pay
fallback), `VerifySuccessListener` (callback carrying a `SubscriptionInfo`).

### 1.2 Purchase-flow mechanics — `NewGoogleBillingPayUtils`

`com/ticktick/task/payfor/billing/NewGoogleBillingPayUtils.java` does the actual
Play work. Unique anchor: `"queryProductDetailsAsync productId:"` (line 106).

Flow:
1. **Price fetch** — `checkSkuDetails` → `lambda$checkSkuDetails$0(canFreeTrial)`
   (line 148) selects the server SKU source (see §3) and `checkSkuDetailsNew`
   (line 89) builds a `QueryProductDetailsParams` of `"subs"` products (both
   `productId` and `googleStrikeProductId` per spec) and calls
   `queryProductDetailsAsync`.
2. **Buy** — `payFor(activity, freqType)` (line 433): looks up cached
   `ProductDetails` in `typeProductDetailsMap`, takes the first
   `SubscriptionOfferDetails` offer token, builds `BillingFlowParams`, and calls
   `billingClient.launchBillingFlow(...)`.
3. **Result** — `onPurchasesUpdated` (line 398): on code 0 → `processPurchases`;
   code 1 = user-cancelled; code 3 = billing unavailable → `tryApplyRussiaGift`
   (see §4.3); code 7 (already owned) → `findCurrentUserPurchase`; code 5 =
   developer error. Non-zero codes fire `DataTracker.sendUpgradePurchaseErrorEvent`.
4. **Server verify + acknowledge** — `processPurchases` → `verifySubscription`
   (line 502): posts purchase fields (`baseOrderId`, `packageName`, `productId`,
   `token`) to `GeneralApiInterface.verifyGoogleSubscription` (see §3), then
   `acknowledgePurchase` (line 50) via `BillingClient.acknowledgePurchase`. On
   network failure it shows a retry dialog (`showRetryVerifyDialog`).
5. **Restore** — `restore` (line 489/324): `queryPurchasesAsync("subs")` → verify
   newest purchase.

### 1.3 Product / SKU identifiers

- **Hard-coded free-trial product IDs** (the only literal SKUs in the APK), in
  `com/ticktick/task/network/sync/payment/model/SubscriptionSpecification.java`:
  - `FREE_TRIAL_7_DAY_PRODUCT_ID = "ticktick_yearly_trial"` (line 24)
  - `FREE_TRIAL_14_DAY_PRODUCT_ID = "ticktick_yearly_trial_v2"` (line 23)
  - helpers `isFreeTrail7Day()` / `isFreeTrail14Day()` (lines 79–85).
- **All other product IDs are server-driven**, not baked into the APK. A
  `SubscriptionSpecification` carries `productId`, `googleStrikeProductId`
  (the struck-through "compare" price SKU), `type` (the price-type key, e.g.
  "month"/"year"), `price`, `trialDay`, `dueDate`, `packageName`. The app fetches
  these from the server (§3) and maps Play `ProductDetails` to them by `productId`.
- `typeProductDetailsMap` keys are the spec `type` string; `payFor(freqType,…)`'s
  `freqType` is that key.
- The free-trial detection in `checkIfAlreadyUsedProTrialAsync`
  (NewGoogleBillingPayment line 593) queries owned "subs" and matches against the
  two literal trial IDs above to decide if the trial was already consumed.

---

## 2. The is-Pro / premium gate

### 2.1 Exact gate

- **`User.isPro()`** — `com/ticktick/task/data/User.java:419`:
  ```java
  public boolean isPro() { return this.proType == 1 || isActiveTeamUser(); }
  ```
  So Pro ⟺ `proType == 1` OR `activeTeamUser == true`.
- **`User` pro state fields** (line 42–48): `proType` (int), `proEndTime` (long),
  `proStartTime` (long), `needSubscribe` (bool), plus `gracePeriod`,
  `noGraceDate`, `subscribeType`, `subscribeFreq`, `teamPro`, `teamUser`,
  `activeTeamUser`. Getters at lines 305–351; `isActiveTeamUser()` line 374.
- **`ProHelper.isPro(User)`** — `com/ticktick/task/helper/pro/ProHelper.java:202`
  is the canonical app-level wrapper:
  `user != null && (user.isPro() || user.isActiveTeamUser())`. This is what
  feature code calls (not `User.isPro()` directly, mostly).

### 2.2 ProHelper responsibilities

`ProHelper` (singleton `INSTANCE`, `TAG="ProHelper"`) also handles:
- Subscribe-type display names (`getSubscribeTypeName`, line 190 — Google Play /
  Apple / Stripe / PayPal / WeChat / Alipay).
- Grace-period warning dialog (`showEnterGracePeriodWarnDialog`, line 213;
  unique log literal `"showEnterGracePeriodWarnDialog needShowDialog FALSE"`).
- Grace-period help URLs (`getGracePeriodUrl`, line 302).
- Pay-success page routing (`showPaySuccessPage`, line 242 → renewal vs upgrade
  vs upgrade-with-proType activities).
- A debug `TestProInfo` override holder (lines 46–164).

### 2.3 Pro-gated features (quota model) — `LimitHelper` + `Limits`

Gating is largely **quota-based**, not boolean per-feature. `LimitHelper`
(`com/ticktick/task/helper/LimitHelper.java`) holds three `Limits` profiles —
free / pro / team — and selects via `ProHelper.isPro(user)` /
`isActiveTeamUser()` (lines 42–57). `Limits` are populated from the server
`LimitsConfig` (`GeneralApiInterface.getLimitsConfig`, endpoint
`api/v2/configs/limits`) in `setLimitsConfig` (line 80), keyed by `accountType`
(0=free, 1=pro, 2=team).

`Limits` (`com/ticktick/task/data/Limits.java`) quota fields that differ
free↔pro (the de-facto Pro-feature list):
- `projectNumber` (lists), `projectTaskNumber`, `subTaskNumber`,
  `shareUserNumber`, `reminderCount`, `kanbanNumber` (columns),
  `habitNumber`, `countdownNumber`, `timerNumber`, `holidayNumber`,
  `calendarBindNumber`, `urlCalendarNumber`, `googleCalendarNumber`,
  `googleConnectNumber`, `notionWorkspaceNumber`, `notionDatabaseNumber`,
  `visitorNumber`, `taskAttachCount`, `fileCountDailyLimit`, `fileSizeLimit`.

Boolean / capability gates checked via `ProHelper.isPro(...)` are scattered
across helpers (confirmed callers include): `CustomThemeHelper` (premium themes),
`MediaPickerManager` / attachments, `PomodoroPreferencesHelper`,
`CalendarTrial` / `CalendarConnectProjectPickDialogFragment` (calendar sync),
`FilterEditDialogFragment` / `FilterNameInputHelper` (custom filters),
`ProjectEditManager` / `ProjectEditAndDeleteHelper`, `ProjectTemplateHelper`,
`TaskMoveToDialogFragment`, `ColumnMoveToDialogFragment` (kanban). The
pay-wall / privilege comparison UI lives in
`com/ticktick/task/activity/payfor/` (`PayPrivilegeBean`, `PayPrivilegeRowBean`,
`ProFeatureSection`, `ProV6PrivilegeCompareFragment`, `ProV6UiHelper`).

### 2.4 Pay pre-checks — `PayCheckHelper`

`com/ticktick/task/helper/pro/PayCheckHelper.java`:
- `checkInPayBlackList()` → endpoint `/api/v2/payment/isBlacklist`; if user is in
  the pay blacklist, `checkIfInBlackListBeforePay` shows a warning dialog before
  letting the purchase proceed (lines 460–477).
- `checkIfDuplicateSub` / `fetchCurrentSubscribeList` → `querySubscribeList`
  (`/api/v2/subscribe/list`); if the user has ≥2 active subscriptions it shows
  `DuplicateSubscribeFragment` (line 108).

---

## 3. Server-side payment API — `GeneralApiInterface`

`com/ticktick/task/network/api/GeneralApiInterface.java` (a Retrofit interface;
`@f`=GET, `@o`=POST, `@p`=PUT, `@b`=DELETE, `@s`=path, `@t`=query, `@on.a`=body).
The concrete impl is the obfuscated `y7/c` (smali) — both carry the endpoint
literals, so anchor on the URL strings.

Payment / subscription / promo endpoints:

| Method | HTTP | Path | Purpose |
|---|---|---|---|
| `verifyGoogleSubscription` | POST | `api/v2/subscribe/verify/google` | **verify a Play purchase**, returns `SubscriptionInfo` |
| `getSubscriptionSpecifications` | GET | `api/v2/subscribe/subscribe_spec?platform=google` | Google SKU list |
| `getAlipaySubscriptionSpecifications` | GET | `api/v2/subscribe/subscribe_spec?platform=alipay` | Alipay SKU list |
| `getFreeTrialSubscriptionSpecifications` | GET | `api/v2/subscribe/free_trial?platform=google` | free-trial SKUs |
| `getProductListWithFreeTrial` | POST | `/api/v3/subscribe/free_trial_2w` (`platform`,`p`=planCode) | trial+price list (V7 paywall) |
| `getProductList4Local` | POST | `/pub/api/v2/subscribe/free_trial_2w?platform=google` (`noTrial`) | local-mode SKUs |
| `checkTrialAvailable` | GET | `api/v3/subscribe/google/freeTrial` | can this user start a trial |
| `getUserType4FreeTrial` | GET | `/api/v3/subscribe/free_trial/user` | user-type bucket for paywall |
| `querySubscribeList` | GET | `/api/v2/subscribe/list` | active subs (dup-sub check) |
| `cancelSubscribe` | PUT | `/api/v1/payment/cancel/{type}` (`profileId`) | cancel subscription |
| `checkInPayBlackList` | GET | `/api/v2/payment/isBlacklist` | pay-blacklist gate |
| `getOrderSpecifications` | GET | `api/v1/payment/order_spec` | one-time order specs |
| `getAlipayInfo` | GET | `api/v2/payment/alipay_android` (`freq`,`count`) | Alipay order |
| `getAlipaySubscribeInfo` | GET | `/api/v2/payment/alipay/subscribe` | Alipay sub |
| `queryAlipaySubscribeResult` | GET | `/api/v2/payment/alipay/subscribe/check/{id}` | Alipay sub status (`AlipaySubscribeProgress`) |
| `getWeChatPayInfo` | GET | `api/v1/payment/wechat_android` (`freq`,`count`) | WeChat order |
| `getWechatSubscribePreEntrustWebId` | POST | `/api/v2/payment/wxpay/subscribe/android` | WeChat sub entrust |
| `getIntroductoryPrice` | GET | `api/v2/subscribe/introductory_price?platform=google` | intro/discount price |
| `applyGiftCardCode` | POST | `api/v1/giftcard/apply/{code}` | redeem gift card → `ApplyGiftCardCodeResult` |
| `applyGoogleGift` | POST | `/api/v2/freePro/google` | claim free-pro gift → `ProEndInfo` (Russia gift) |
| `getPromotionReport` | GET | `pub/api/v1/promo/year2021` | promo banner → `Promotion` |
| `get7Pro` / `get3Pro` | POST | `/api/v2/trial/7day` / `/api/v2/trial/3day` | claim trial pro → `User7ProModel` |
| `get7ProAvailable` | GET | `/api/v2/trial/7day/available` | trial eligibility |
| `get7ProActionInfo` | GET | `/pub/api/v2/promotion/7pro` | promo action info |
| `getUserStatus` / `getUserProfile` | GET | `api/v2/user/status` / `api/v2/user/profile` | refresh pro state (`SignUserInfo` / `User`) |

Models (`com/ticktick/task/network/sync/payment/model/`): `SubscriptionInfo`
(fields `isPro`, `needSubscribe`, `proEndDate`, `subscribeType`, `userId`,
`userName`), `SubscriptionSpecification` (§1.3), `OrderSpecification`,
`SubscribeListItemDTO`, `AlipaySubscribeProgress`, `SubscribeBaseInfo`.

After a successful verify, `NewGoogleBillingPayment.updateUserInfo` runs a
`wd.b` status task (UpdateUserInfoJob) that re-fetches user status; `isPro`
flips when the server-side `proType` updates.

---

## 4. Promotions / trials

### 4.1 Free-trial paywall — `ProV7TestHelper`

`com/ticktick/task/activity/payfor/ProV7TestHelper.java` (singleton `INSTANCE`,
`TAG="ProV7TestHelper"`) drives the V7 free-trial paywall:
- User-type buckets `USER_NEW/USER_OLD/USER_UPGRADE/USER_ERROR` and plan codes
  `PLAN_O/PLAN_O1/PLAN_A/PLAN_B/PLAN_C/PLAN_N` (string consts).
- `getPlanCode()` feeds `getProductListWithFreeTrial("google", planCode)`.
- `showFreeTrial14Dialog`, `tryShowPayWall`, `checkAndShowPayWall`,
  `getUserType4FreeTrial`, `checkIfAlreadyUsedProTrialInGooglePlay`.
- Persists paywall state via `FreeTrialSaveInfo` / `JobExecuteInfo`
  (kernel appconfig).
- Label `"free_trial_page"` is treated specially in
  `NewGoogleBillingPayment.updateUserInfo` (skips one tracking event).

### 4.2 Promotion banners — `com/ticktick/task/promotion/`

- `PromotionActivity`, `PromotionDispatchActivity` — promo entry UI.
- `Promotion` entity (`network/sync/promo/entity/Promotion.java`) extends
  `com/ticktick/task/network/sync/framework/entity/Entity`; fields: `channel`,
  `count`, `startTime`/`endTime`, `id`, `packageName`, `summary`, `title`,
  `url`, `userType`, `versionFrom`/`versionTo`. Fetched via `getPromotionReport`
  (`pub/api/v1/promo/year2021`).
- `promotion/google/data/IntroductoryPrice` — Google introductory price model:
  `discountRate`, `periods`, `version`, `productId`, `type`,
  `startTime`/`endTime` (fetched via `getIntroductoryPrice`).

### 4.3 Russia gift flow — `payfor/billing/russia/`

When Play billing is unavailable (`onPurchasesUpdated` code 3),
`NewGoogleBillingPayUtils.tryApplyRussiaGift` (line 346) calls
`RussiaGiftPayment.apply(activity, productDetails)`. `RussiaGiftPayment`
(anchor literal `"RUB"`, smali line 374) plus `ApplyFreeDialog` /
`ApplyGiftSuccessFragment` give Russian users free pro via
`applyGoogleGift` (`/api/v2/freePro/google`).

### 4.4 Other redemption

- Gift-card codes: `applyGiftCardCode` (`api/v1/giftcard/apply/{code}`),
  UI via `RedeemListener` in `activity/payfor/`.
- 3/7-day trial pro: `get3Pro` / `get7Pro` endpoints (§3).

---

## 5. Pricing tiers / what Pro unlocks

- **Tiers:** Free (`proType==0`/`accountType 0`), **Pro** (`proType==1`,
  `accountType 1`), **Team** (`activeTeamUser`/`accountType 2`). There is no
  separate baked-in price table — prices come from the server
  `SubscriptionSpecification`s and Play `ProductDetails`. Billing frequencies
  observed: `year` / `month` (`ProHelper.getSubscribeFreqName`, line 326).
- **Subscribe channels** (`Constants.SubscribeType`,
  `com/ticktick/task/constant/Constants.java:2365`): `google`, `apple`,
  `paypal_subscribe`, `stripe_subscribe`, `wxpay_subscribe`,
  `alipay_subscribe`, `order`. (Android in-app path is `google`; others are
  cross-platform / web-pay states.)
- **What Pro unlocks:** the higher `Limits` quotas in §2.3 (more lists, tasks,
  subtasks, reminders, kanban columns, habits, countdowns, attachments,
  calendar/Notion connections, sharing) plus boolean capabilities gated by
  `ProHelper.isPro` (premium themes, calendar sync, custom filters/smart-lists,
  task templates, advanced pomodoro). Exact numbers are server-config
  (`getLimitsConfig`), not in the APK.

---

## 6. Hook points (quick reference)

| What | Where (`file:line`) |
|---|---|
| Is-Pro decision | `data/User.java:419` (`isPro`), `helper/pro/ProHelper.java:202` (`ProHelper.isPro`) |
| Pro state fields | `data/User.java:46-48` (`proEndTime`/`proStartTime`/`proType`), `:374` (`isActiveTeamUser`) |
| BillingClient build | `payfor/billing/NewGoogleBillingPayment.java:576-589` |
| launchBillingFlow | `payfor/billing/NewGoogleBillingPayUtils.java:482` |
| onPurchasesUpdated | `payfor/billing/NewGoogleBillingPayUtils.java:398` |
| Server verify | `payfor/billing/NewGoogleBillingPayUtils.java:502` → `GeneralApiInterface.java:369` |
| Trial SKU consts | `network/sync/payment/model/SubscriptionSpecification.java:23-24` |
| Quota gate | `helper/LimitHelper.java:42-57`, `:80` |
| Pay blacklist / dup-sub | `helper/pro/PayCheckHelper.java:460,448` |
| Free-trial paywall | `activity/payfor/ProV7TestHelper.java` |
| Russia free-pro | `payfor/billing/NewGoogleBillingPayUtils.java:346`, `payfor/billing/russia/RussiaGiftPayment.java` |

> Naming/regex anchors are kept in `signatures.yaml`, not here. Most powerful
> rotation-stable hook for "force Pro" is `ProHelper.isPro(User)` /
> `User.isPro()` — overriding the latter to always return `true` flips the gate;
> `proType` is the underlying integer.
