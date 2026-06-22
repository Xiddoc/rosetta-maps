# Realtime / MQTT / FBNS

Instagram's realtime transport: the **MQTT** client to `edge-mqtt.facebook.com`,
GraphQL/Skywalker subscriptions, and **FBNS** push. Class names under
`com.instagram.realtimeclient.*` are kept. Logical→obfuscated names and anchors
are in the map + `signatures.yaml`.

- **`RealtimeClientManager`** (`com.instagram.realtimeclient`) is the central
  MQTT/realtime client — it picks the host (`edge-mqtt.facebook.com` / fallback),
  builds the client with a Thrift payload encoder, and registers event handlers
  (log `error serializing skywalker command`). Hook here for connection lifecycle
  and send.
- **`RealtimeMqttClientConfig`** (same package) builds the MQTT connect config —
  the subscription topic map and connection params (`ig_mqtt_route`, capabilities,
  blacklist). Hook `getConnectionParams` to tamper with connection settings.
- **`RealtimeConstants`** holds the topic registry (`/pubsub` Skywalker,
  `/ig_realtime_sub`, `/ig_message_streaming`, `/ig_send_message`, `/ig_sub_iris`)
  as kept `public static final` field constants.
- **`MainRealtimeEventHandler`** is the inbound payload dispatcher
  (`error parsing realtime event from skywalker`); GraphQL subscriptions are routed
  over `/ig_realtime_sub` by `GraphQLSubscriptionHandler`.
- **`GraphQLSubscriptionID`** is the static table of GraphQL subscription
  query-ids (e.g. `LIVE_REALTIME_COMMENT_QUERY_ID`, in-app notification,
  direct-typing). The numeric ids can rotate per release; the field-name constant
  is the stable part.

Push runs over **FBNS** (`com.facebook.rti.push.service.FbnsService` in the
`:mqtt` process, `InappFbnsService` in `:fbns`), with token registration via
`com.instagram.notifications.push.IgPushRegistrationService` and lifecycle
bootstrapping by `FbnsInitBroadcastReceiver`. Broadcast-channel realtime event
types are defined as `RealtimeProtocol` topic constants (see
`notes-broadcast-channels.md`).
