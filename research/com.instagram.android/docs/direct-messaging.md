# Instagram — Direct messaging (MSYS) & message encryption

App: `com.instagram.android` v433.0.0.47.68 (`version_code` 383909338)

Instagram Direct is built on Meta's **MSYS** (Meta System) messaging stack with
the **ArmadilloExpress** encrypted transport. Notably, almost the entire DM
subsystem keeps its **real package names** — so this is mostly a prose map with
one obfuscated class signatured.

## Architecture (un-obfuscated framework)

- **`com.instagram.direct.*`** — the IG-side Direct API, models, and send
  mutations:
  - `DirectThreadApi` (`com.instagram.direct.request`) — the Direct HTTP API;
    holds `direct_v2/…` endpoints (e.g. `direct_v2/send_direct_invite/`, unique)
    and builds thread/message payloads (`client_context`, `ig_thread_id`,
    `item_id`, `eb_device_id`, `igd_request_log_tracking_id`).
  - `StellaDirectMessagingService` (`com.instagram.direct.stella`) — an **AIDL**
    service that lets authorised companion apps send DMs over IPC (guarded by
    permission `com.instagram.android.fbpermission.MANAGE_MESSAGING`), routing
    into MSYS. Its callback `ISendDirectMessageCallback` is an AIDL interface.
  - `com.instagram.direct.send.mutation.*` — per-type send mutations (text,
    media, animated media) over ArmadilloExpress.
- **`com.facebook.msys.*`** — the MSYS mailbox/database engine.
- **`com.instagram.direct.msys.encryptedbackup.EncryptedBackupCrypto`** — a
  native crypto bridge exposing `createHmac(...)` and an Olm-style client-map
  operation; this is the Signal/Olm-derived E2EE primitive layer used for
  encrypted backups / secure message state.
- **`com.facebook.rsys.crypto.gen.CryptoContextHolder`** — RSYS crypto session
  state (keys/device ids) for E2EE calls.

These are described here, not signatured: their FQNs are not obfuscated, so a
map entry would be `original == new`.

## Mapped (obfuscated)

- **`MsysMailboxActivationCallback` (`X/38Z`)** — the obfuscated consumer
  callback fired when the MSYS **mailbox is activated** ("Mailbox activated"),
  i.e. when the encrypted-messaging database/session is ready and the offline
  message processors + encryption plugins are wired to the `UserSession`. This
  is the gate every DM send/receive passes once, so it's a useful hook point
  for "is messaging live yet?". Anchored on `Mailbox activated` (unique).

## Send flow (high level)

1. UI / `StellaDirectMessagingService` requests a send.
2. MSYS mailbox is activated if needed → `MsysMailboxActivationCallback` (`X/38Z`).
3. `DirectThreadApi` builds the payload (`client_context`, `ig_thread_id`,
   `eb_device_id`).
4. ArmadilloExpress transport encrypts (via `EncryptedBackupCrypto` native HMAC
   / Olm client-map).
5. Publish over MQTT `/ig_send_message`; response on `/ig_send_message_response`
   (see `realtime-and-push.md`).

## Confidence

`X/38Z`: **high** (unique "Mailbox activated" string in the activation
callback, corroborated by the MSYS mailbox APIs it touches). The framework
classes are confirmed by their preserved FQNs / AIDL descriptors. No
`labyrinth` codename string was found; the E2EE primitives present are
Olm/Signal-style via `EncryptedBackupCrypto`.
