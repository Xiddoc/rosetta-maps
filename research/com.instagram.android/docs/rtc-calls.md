# RTC — video/audio calls, watch-together, screen-share

Instagram audio/video calling is built on Meta's **RSYS** call engine (native,
reached through `com.instagram.rtc.rsys.models.*` MCF bridge models) with Android
**Telecom** integration and a foreground call service. State models expose real
field names and literal `toString()` prefixes — strong anchors. Logical→
obfuscated names and anchor regexes are in the map + `signatures.yaml`; this is
the behaviour narrative. (Most RTC classes are in dex classes17;
`RtcCallStackImpl` is in classes4.)

## Entry / activity surface

- **`RtcCallActivity`** (`com.instagram.rtc.activity`) is the in-call screen:
  `singleTask`, `showWhenLocked`, `turnScreenOn`, `supportsPictureInPicture`,
  `taskAffinity="com.instagram.android.RtcCallActivity"`. Intent-extra keys
  `rtc_call_activity_arguments_key_notification_trace_id`,
  `rtc_call_activity_arguments_entry_point`; it drives a presenter bridge for the
  call UI. (Anchored on `"launchInternalActivity failed"`.)
- **`RtcCallIntentHandlerActivity`** (same package, `singleInstance`,
  `noHistory`) is the call router: actions
  `…intent_action_open_ongoing_call` / `…create_or_join_call` /
  `…open_ongoing_call_entrypoint`, data scheme `video_call_incoming`, carrying an
  `RtcEnterCallArgs` parcelable. Funnel `rtc_call_launcher`. This is the
  deeplink/notification → call entry (resume ongoing, create/join, incoming).

## System integration & services

- **`RtcConnectionService`** (`com.instagram.rtc.connectionservice`) extends
  `android.telecom.ConnectionService` (manifest permission
  `BIND_TELECOM_CONNECTION_SERVICE`) — bridges Instagram calls into the Android
  system telecom stack (self-managed connections). Bundle keys
  `com.instagram.rtc.connection.connection_id` / `…display_name`; outgoing path
  throws `"Unable to make outgoing call"`.
- **`OngoingCallServiceWithMic`** (`com.instagram.rtc.service`) is the foreground
  call service, **`foregroundServiceType="phoneCall|mediaProjection|microphone"`**
  (`startForeground(20025, …)` on API ≥ 34). It handles
  `ForegroundServiceStartNotAllowedException` and logs `"Failed to start
  foreground service"`. **Hook point:** mic-FGS start/stop = "a call is live".
- **`RtcCallActionIntentHandlerService`** (`…signaling.notifications.service`)
  backs the call/ring-notification action buttons — reads an `RtcConnectionEntity`
  from extra `com.instagram.rtc.notifications.service.entity` and dispatches
  `DISMISS_LIVE_NOTIFICATION` / `DISMISS_MISSED`.

## Engine bridge & orchestration

- **`RtcCallStackImpl`** (`com.instagram.rtc.stack.impl`, dex classes4) is the
  central orchestrator over the RSYS engine: multiway-signaling ingress
  (`"RtcCallStackImpl.receivedMultiwaySignalingMessage"`), enter-call args
  (`com.instagram.rtc.stack.impl.enter_args`), incoming-call dismissal, and
  reject path (`ConnectionService: onReject`). Self-describing string
  `"Call ended/left before participants models set by rsys"`. Prime hook surface
  for call setup/teardown.

## State models (RSYS / MCF)

- **`IgCallModel`** (`com.instagram.rtc.rsys.models`) is the canonical snapshot of
  one call's state (native MCF bridge; `toString` prefix `IgCallModel{inCallState=`).
  Kept fields include `inCallState`, `connectionQuality`, `localCallId`, `linkUrl`,
  `callTrigger`, `initialDirection`, `isAudioOnlyCall`, `e2eeMandated`,
  **`mediaSyncState`** (the watch-together sync state, rsys `MediaSyncState`),
  `participants`, `selfParticipant`, and call lifecycle timestamps.
- **`EngineModel`** (same package; `toString` prefix `EngineModel{state=`) is the
  top-level engine aggregate. It carries `IgCallModel`, `LiveVideoModel`,
  `MosaicGridModel`/`GridModel` (participant grid), `CryptoE2eeModel`,
  **`ScreenShareModel`** (`com.facebook.rsys.screenshare.gen.ScreenShareModel` —
  where screen-share state lives), `EmojiReactionsModel`, `DominantSpeakerModel`,
  `AvatarCommunicationModel`. Delivered to UI via `EngineProxy.stateChangedHandler`.
- **`RtcCallParticipantCellView`** (`…presentation.participants`) is one cell in
  the participant grid (avatar, blurred background `IGVRCellScreenBlurredBackground`,
  video renderer). `ParticipantModel` is the per-participant data element.

## Watch-together & screen-share

- Watch-together (co-watch) sync runs through `IgCallModel.mediaSyncState`
  (rsys `MediaSyncState`), surfaced via `EngineModel`; the content picker is
  Bloks-driven (`RtcCoWatchContentPickerProvider`). Screen-share has no dedicated
  `com.instagram.*` class — its state is the rsys `ScreenShareModel` on
  `EngineModel`, plus the `mediaProjection` FGS type. Both are documented here;
  only the models/services with stable anchors are in the signature set.
