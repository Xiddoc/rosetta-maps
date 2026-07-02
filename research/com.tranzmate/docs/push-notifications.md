# Push, GCM & Braze

Moovit (`com.tranzmate`), confirmed against **version_code 1785** (versionName 5.194.0.1785). Classes are referenced by their **logical** name; the obfuscated name for this version is in [`maps/com.tranzmate/1785.json`](../../../maps/com.tranzmate/1785.json) and the regex anchors in [`signatures/com.tranzmate/signatures.yaml`](../../../signatures/com.tranzmate/signatures.yaml).

## Push, GCM & Braze subsystem (Moovit / com.tranzmate 5.194.0.1785, version_code 1785)

Moovit is R8 **partially** obfuscated: package paths and most GCM class names are **kept**, but the core Braze classes are renamed to single-letter tokens inside their real packages (`com/moovit/braze/a`, `.../b`, `com/moovit/app/braze/a`, `com/moovit/braze/contentcards/c`). Renamed identities were recovered from leaked synthetic inner-class names (`BrazeInAppMessageHelper$NativeFlowResult`, `BrazeRefresher$refresh$1`, `BrazeRecoveryManager$checkForRecovery$1`) plus in-code log tags. All class anchors below are rotation-stable string/framework literals verified as **globally unique to exactly one class**.

### Key flows

**1. Push receive (FCM entry).** `GcmListenerService extends com.google.firebase.messaging.FirebaseMessagingService` is the single push entry point. Braze-originated pushes are delegated to `com.braze.push.BrazeFirebaseMessagingService`; Moovit pushes are parsed from the `RemoteMessage` (static helpers `c()`/`d()`). It recognizes a fixed **command list** — `ping, metro_update, upload_logs, payment_account_invalidate, tod_rides_invalidate, invalidate_firebase_config, navigation_high_accuracy_required, frequent_entities` — handled inline, and full payloads keyed by `presentation_type` = `notification` / `pop-up` / `message-bar` / `none`. Payloads are wrapped in the `moovit://payload` Uri and rebroadcast via `com.moovit.PAYLOAD_BROADCAST_ACTION`. New FCM tokens arrive at `onNewToken` (log `onNewToken: %s`). Log tag `GcmListenerService`.

**2. Notification build / post / callback.** `GcmNotification` is the `Parcelable` model (title/body/ticker, image, `GcmPayload`, notification id, `MoovitNotificationChannel`); it renders the `android.app.Notification` (icon `ic_notification_alert`, theme `MoovitTheme`). `GcmNotificationPublisher` (a `BroadcastReceiver`, extra key `notification`) posts it. Dismiss/action-button callbacks go to `GcmCallbackIntentService` (IntentService `GcmDismissIntentService`), keyed by `com.moovit.gcm.notification.callback.action.notification_dismiss` / `...notification_action_clicked` with extras `...extra.gcm_notification` / `...extra.notification_id` / `...extra.notification_action`. Notification **taps** open `GcmNotificationActivity`, which resolves the click on a background executor, cancels the notification, and executes the payload via the notification manager. Action buttons are the enum `GcmNotificationAction` (`CARBON_GOOD/CARBON_BAD/CARBON_SKIP` — carbon-footprint rating pushes).

**3. Payload model.** `GcmPayload` (abstract, `gcmId` + type string via `d()`) has ~26 kept subclasses under `com/moovit/gcm/payload/` (e.g. `TodRidePayload, ServiceAlertPayload, TripPlanPayload, LinePayload, ItineraryPayload, TransitStopPayload, SurveyPayload, RateUsPayload, UserReinstallPayload`). Each implements `a(oo5)` to execute against a handler context. (The abstract base and the leaf payloads have no globally-unique rotation-stable string anchor — the base's only literal `gcmId` also occurs in unrelated classes — so they are intentionally omitted from the signatures; their kept names make them trivially locatable anyway.)

**4. Topic subscription.** `GcmTopicManager extends androidx.work.Worker` subscribes/unsubscribes the device to FCM metro topics `"/topics/android-metro-<metroId>-..."` (also `-info-lang-`, `-percentage-`, `-system` variants) for metro-targeted campaigns, gated on Google Play Services availability and a registration token. Work is parameterized by action/metro_id/user_percentage_bucket data keys.

**5. Braze integration.** `BrazeManager` (`com.moovit.braze.b`, singleton, log tag `BrazeManager`) initializes the Braze SDK (`Initializing Braze SDK`), gated by resource `is_braze_supported` and prefs `braze_user_recovery`/`is_completed`; it registers `BrazeInAppMessageHelper` as the `IInAppMessageManagerListener` and owns the content-cards flow (`com.moovit.braze.contentcards.c` = `BrazeContentCards`, which subscribes to Braze content-card updates — omitted from signatures because its only distinctive refs are Braze-library method descriptors shared with the Braze SDK classes). `BrazeInAppMessageHelper` (`com.moovit.braze.a`) decides whether/when to display Braze in-app messages: it bridges into Moovit's `PopupManager`, supports "native flow" IAMs (e.g. routing to `RateUsBottomSheetDialogFragment`), and logs analytics events `iam_received/iam_display_now/iam_display_later/iam_discard` with attributes IAM_ID/CAMPAIGN/IAM_TYPE/IAM_TP. `BrazeRecoveryManager` (`com.moovit.app.braze.a`) drives `enableBraze()` and the post-login recovery flow. Three `CoroutineWorker`s manage the Braze user: `BrazeUpdateUserWorker` (updates the Braze profile + `alias_braze_unique_id`, pref `com.moovit.braze.profile`), `BrazeUpdateUserAttributesRequestWorker` (server attribute-update request), `BrazeDeleteUserRequestWorker` (deletes the Braze user; part of recovery). The trigger reason is the enum `BrazeUpdateUserAttributesReason` (`PERIODIC_SYNC/DEVICE_ID_CHANGED/BRAZE_UNIQUE_ID_CHANGED`).

### Good Frida / Xposed hook points
- **`GcmListenerService` (message handler method, log `handleRemoteMessage: %s`)** — intercept/inspect every inbound Moovit push before dispatch; the message-bar branch logs `Receiving new GCM message-bar, screen=%s`.
- **`GcmCallbackIntentService.onHandleIntent`** — observe/forge notification dismiss & action-button callbacks.
- **`GcmNotificationActivity`** — intercept notification taps and payload execution.
- **`GcmTopicManager` (subscribe method, log `Subscribe to topic: %s`)** — watch/alter metro FCM topic subscriptions.
- **`BrazeInAppMessageHelper.beforeInAppMessageDisplayed`** — allow/suppress/redirect Braze in-app messages (prime control point); `onInAppMessageButtonClicked` for button taps.
- **`BrazeManager` init / `setInAppMessageEnabled`** — enable/disable Braze wholesale at runtime.
- **`BrazeUpdateUserWorker` (`updateNewBrazeUser()` / `resetBrazeUserLocally()`)** — observe Braze user/alias sync.

### Notes on identity discipline
`GcmNotificationManager` exists as the click/display dispatcher (log tag `GcmNotificationManager`) but is horizontally **class-merged by R8** into the mega-singleton `Lwyf;` (static instances b..j, ~14 merged interfaces), and its tag string is not globally unique — so it is **not** signed as a discrete class. Reference it by behavior only.

## Classes identified

| Logical class | Renamed? | Confidence | Identity evidence |
| --- | --- | --- | --- |
| `GcmListenerService` | no | high | Kept class name + package; extends FirebaseMessagingService; delegates Braze pushes to com.braze.push.BrazeFirebaseMessagingService; parses RemoteMessage; co… |
| `GcmCallbackIntentService` | no | high | Kept name + package; IntentService constructed with name 'GcmDismissIntentService'; onHandleIntent reads extras com.moovit.gcm.notification.callback.extra.* … |
| `GcmNotification` | no | high | Kept name + package; final Parcelable holding title/body/ticker, GcmPayload, notification id and MoovitNotificationChannel; builds the android Notification (… |
| `GcmNotificationActivity` | no | high | Kept name + package; transparent activity launched on notification tap; extras built via getName().concat('.extra').concat('.gcm_notification'/'.notification… |
| `GcmTopicManager` | no | high | Kept name + package; Worker that subscribes/unsubscribes the device to FCM metro topics '/topics/android-metro-<metroId>-...' via FirebaseMessaging, gated on… |
| `BrazeInAppMessageHelper` | yes | high | Renamed to 'a' but leaked via inner enum com.moovit.braze.BrazeInAppMessageHelper$NativeFlowResult; implements IInAppMessageManagerListener; log tag 'BrazeIn… |
| `BrazeManager` | yes | high | Renamed to 'b'; volatile singleton (static instance field + initialize()); log tag 'BrazeManager'; logs 'Initializing Braze SDK'; gated by resource is_braze_… |
| `BrazeRecoveryManager` | yes | high | Renamed to 'a' but leaked via inner com.moovit.app.braze.BrazeRecoveryManager$checkForRecovery$1; log tag 'BrazeRecoveryManager'; enableBraze() enables the B… |
| `BrazeUpdateUserWorker` | no | high | Kept name + package; CoroutineWorker; log tag 'BrazeUpdateUserWorker'; updates the Braze profile and alias_braze_unique_id, pref com.moovit.braze.profile; he… |
| `BrazeUpdateUserAttributesRequestWorker` | no | high | Kept name + package; CoroutineWorker; log tag 'BrazeUpdateUserAttributesRequestWorker'; sends the Braze update-user-attributes request to the Moovit server, … |
| `BrazeDeleteUserRequestWorker` | no | high | Kept name + package; CoroutineWorker; log tag 'BrazeDeleteUserRequestWorker'; sends the Braze delete-user request as part of the recovery flow ('Braze delete… |

