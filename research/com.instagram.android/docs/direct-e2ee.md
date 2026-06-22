# Direct messaging — MSYS engine, E2EE, Stella cross-process send

Instagram Direct is backed by Meta's **MSYS** (cross-platform messaging) native
engine reached through thin JNI bridge classes, with an **end-to-end-encrypted**
(Armadillo / "Instamadillo") transport for secure messages. The most stable,
high-value classes are the binder/native-bridge choke points. Logical→obfuscated
names and anchor regexes are in the map + `signatures.yaml`.

## MSYS / MailboxCore bridge

- **`Mailbox`** (`com.facebook.msys.mca`, dex classes4) is the Java↔native MSYS
  mailbox — **the central choke point through which all MSYS-backed Direct data
  flows**. Native methods `deleteDatabaseFilesNative`, `initNativeHolder`; holds
  the `Database` + `NativeHolder`. It registers DB-commit observers with the
  literals `MCIDatabaseCommitNotificationV1` / `…V2` and self-describes via
  `"mDatabase must be initialized in native initNativeHolder() method"`.
  Instrumenting the commit-notification dispatch surfaces every change to the
  messaging store.

## E2EE receive / decrypt landing point

- **`IGMessagePersistencePostProcessorPluginImplPostmailbox`**
  (`…direct.realtime.armadilloexpress.plugins.messagepersistencepostprocessor`,
  dex classes10) extends `Postmailbox` and is the **decrypted-message landing
  point** — the single best place to read plaintext E2EE messages after Meta's
  MEM (Meta Encrypted Messaging) engine decrypts them. It calls
  `MetaEncryptedMessagingMCFBridgejniDispatcher.MEMDecryptedPayloadContextGet*Native(...)`
  (thread mode/type, message id, trace id, offline-queue index) and the
  `MessagePersistenceStoreModelsMCFBridgejniDispatcher.MPS*Native(...)` store
  bridge, then parses a `TransportEvent` protobuf. Stable internal keys include
  `transport_event` and `persist_key_changed`.
- **`IgSecureMessageOverWANotificationService`**
  (`…direct.notifications.armadillo.service`, FGS type `dataSync`) is the
  foreground service that keeps the process alive to receive secure
  (Armadillo/WA-bridged) messages — analytics event
  `ARMADILLO_NOTIFICATIONS_STOP_SERVICE` (reasons `timeout` / `offline_marker`),
  extras `push_notif_id` / `wa_push_id`.

## Stella — cross-process "send a DM from outside the app"

The **Stella** surface is a real cross-process entry point (voice assistant /
other Meta apps) defined by AIDL binder descriptors:

- **`StellaDirectMessagingServiceConnection`** (renamed `X.gev`,
  `com.instagram.direct.stella`) is the client `ServiceConnection` that binds the
  Stella messaging service (binder-type log
  `"onServiceConnected received null or unexpected binder type: "`).
- **`StellaDirectMessagingService$binder$1`** (`com.instagram.direct.stella`) is
  the `Binder` impl: `attachInterface`/`enforceInterface` with descriptor
  `"com.instagram.direct.stella.api.IStellaDirectMessagingService"`. Transaction 1
  reads an `ISendDirectMessageCallback` strong binder and dispatches a send;
  package-mapping string `"Unmapped package name: "`. **Hook point:** every
  cross-process DM send + its success/failure callback crosses this binder.

## Realtime delivery & data model

- Realtime deltas reach the thread store through MSYS **modular-sync** (iris
  deltas via `MDCoreSyncEngineTarget`), not a Direct-package MQTT class;
  `DirectThreadStoreAuthoritativeStoreAdapter`
  (`…direct.realtime.modularsync.adapters`) is the authoritative-store adapter
  that applies them.
- **`Message`** (`com.instagram.direct.model.protobufmodel`, dex classes17) is the
  protobuf message model (`GeneratedMessageLite`). Its `*_FIELD_NUMBER` constants
  derive from the `.proto` and are rotation-stable:
  `ARMADILLO_EXPRESS_DATA_FIELD_NUMBER = 72`, `ENCRYPTED_FIELD_NUMBER = 36`,
  `DECRYPTION_MERGE_ERROR_FIELD_NUMBER = 37`, `IS_FROM_MSYS_FIELD_NUMBER = 49`,
  `IG_THREAD_ID_FIELD_NUMBER = 2`, `CLIENT_CONTEXT_FIELD_NUMBER = 1`. The legacy
  `DirectThreadKey` (`com.instagram.model.direct`, `@Deprecated`) is the old
  thread identity; MSYS now keys on `IG_THREAD_ID`.

## Notes / gaps

- The `DIRECT_APP_THREAD_STORE_SERVICE` permission is declared as a
  `uses-permission` only — Instagram is a **client** of another Meta-family app's
  thread-store provider; no in-APK class hosts it. The in-APK cross-process
  surface is Stella.
- The unified send-entry is split into per-feature mutation factories under
  `…direct.send.mutation.armadilloexpresstransport.*` rather than one class, so
  no single send-pipeline signature is shipped.
