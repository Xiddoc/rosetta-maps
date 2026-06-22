# Notifications (UX, settings & rendering)

The notification user-experience layer — dismissal, channels, settings, the
in-app Activity Feed — distinct from the MQTT/FBNS *transport* (see
`realtime-mqtt.md`). Class names are mostly kept. Logical→obfuscated names and
anchors are in the map + `signatures.yaml`.

- **`ClearNotificationReceiver`** (`com.instagram.notifications.push`) fires when a
  notification is dismissed/cleared (logs `ig_notification_dismissed`; reads
  `push_id`, `notification_type`, `landing_path`, `bulk_dismiss_id`).
- **`IgPushSdkFbnsReceiverShim`** (`com.instagram.notifications.push.fbns`) is the
  entry shim that takes an FBNS push intent and hands it to the renderer
  (`IgPushSdkFbnsReceiverShim.onReceive`); this is the UX boundary, not the
  transport.
- **`PushChannelType`** (`com.instagram.common.notifications.push.intf`) is the
  enum mapping transport→type (`android_mqtt → FBNS`, `android_fcm → FCM`, `msys`,
  `realtime_local_notification`, …).
- **`NotificationSettingsHandlerActivity`** (`com.instagram.settings.activity`) is
  the deep-link handler into push settings
  (`android.intent.category.NOTIFICATION_PREFERENCES`).

The in-app Activity Feed ("notifications" tab) is backed by
`com.instagram.newsfeed.data.ActivityFeedRepository` (GraphQL op `ActivityFeed`),
and tab/icon badge counts by `com.instagram.notifications.badging.impl.BadgingApiImpl`.
The actual `NotificationManager.notify()` rendering is split across renamed `X/`
classes — a payload parser (`X/1HJ`), a channel-id mapper keyed on push categories
(`direct`/`like`/`comment`/`iglive`/…), and a channel creator — there is no single
kept-name "NotificationManager" class in this build.
