# Instagram — realtime (MQTT) transport & FBNS push

App: `com.instagram.android` v433.0.0.47.68 (`version_code` 383909338)

Instagram keeps a persistent connection for live events (DMs, presence,
typing, feed/realtime subscriptions) over **MQTT**, and receives wake-ups via
**FBNS** (Facebook Notification Service). Most of this subsystem keeps its real
package names; the two obfuscated classes with unique anchors are mapped, the
rest are documented here.

## MQTT transport (mostly un-obfuscated)

The core lives under `com.instagram.realtimeclient.*` with **real names**:

- `RealtimeClientManager` — the MQTT client lifecycle/owner; holds the topic→
  handler map and the connection state. Identity string
  `edge-mqtt-fallback.facebook.com` (the fallback broker host) is unique to it.
- `RealtimeConstants` — the MQTT topic constants: `/ig_realtime_sub` (GraphQL
  realtime subscribe), `/pubsub` (Skywalker), `/ig_sub_iris` (Iris message
  sync), `/ig_message_streaming`, `/ig_send_message` + `/ig_send_message_response`.
- `GraphQLSubscriptionHandler`, `RealtimePayloadParser`,
  `MainRealtimeEventHandler` — subscription routing and payload demux.

These are described here (not signatured) because their FQNs are not obfuscated.

### Mapped (obfuscated)

- **`IgMqttTopicMapper` (`X/SRe`)** — the obfuscated SparseArray that maps MQTT
  topic **ids** to topic **strings** (`/buddy_list`, `/graphql`,
  `/orca_presence`, `/push_notification`, …). MQTT publishes/subscribes use the
  numeric id on the wire; this class is the id↔route table. Anchored on
  `/buddy_list` (unique).

## FBNS push (Facebook Notification Service)

The push stack lives under `com.facebook.rti.*` (mostly un-obfuscated):
`FbnsAIDLService` (the AIDL push IPC, binder descriptor
`com.facebook.push.fbns.ipc.IFbnsAIDLService`), `FbnsServiceDelegateV2`, and the
NotifGateway DGW client. These keep their names.

### Mapped (obfuscated)

- **`FbnsFlytrapHealthMonitor` (`X/mFZ`)** — the obfuscated "Fbnslite Flytrap"
  health/diagnostics monitor for the FBNS-lite connection (schedules health
  snapshots via a `ScheduledExecutorService`). Anchored on `Fbnslite_Flytrap`
  (unique).

## Presence & typing

Presence/typing runs over a **DistribGW** stream (not MQTT) — stream name
`presence` (`PresenceStreamHandler`, `IgDgwPresenceClientImpl`, both
un-obfuscated). Documented for completeness; not mapped.

## Why mostly prose, not signatures

Instagram leaves the realtime/push framework packages (`realtimeclient`,
`com.facebook.rti.*`, DistribGW) **un-obfuscated**, so sigmatcher would resolve
them `original == new` — no name to recover. The topic-string constants
(`/ig_realtime_sub`, `/pubsub`) are also spread across 8–14 handler classes, so
they are not unique anchors. Only the two genuinely-obfuscated classes with a
unique string (`X/SRe`, `X/mFZ`) are in the map.

## Confidence

`X/SRe` and `X/mFZ`: **high** (unique anchor + corroborating topic/health
strings). The un-obfuscated framework classes are confirmed by their preserved
FQNs and AIDL descriptors.
