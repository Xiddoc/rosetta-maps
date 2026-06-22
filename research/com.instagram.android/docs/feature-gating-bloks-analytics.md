# Instagram — feature gating (MobileConfig), Bloks UI & analytics upload

App: `com.instagram.android` v433.0.0.47.68 (`version_code` 383909338)

Three cross-cutting subsystems that shape almost every screen and request.
Most of each framework is either un-obfuscated or generic interpreter
machinery with no unique string anchor; only the genuinely-obfuscated classes
with a verified-unique anchor (`rg -l` count == 1) are mapped.

## Feature gating — MobileConfig

- **`IgMobileConfigFetcher` (`X/2cr`)** — implements
  `com.facebook.mobileconfig.MobileConfigFetcher`; it is the engine that syncs
  and serves the server-driven feature flags / config values the rest of the
  app reads (the `0x81…`-style config ids seen throughout, e.g. in the reel and
  clips request builders, resolve through this). Anchored on
  `mobileconfig_consistency` (unique). This is a high-value hook point: gating
  the whole app's experiment/rollout behaviour passes through here.

## Bloks — server-driven UI

Bloks renders server-defined screens (much of login/NUX/settings). The
framework packages (`com.instagram.bloks`, `com.instagram.common.bloks`,
`com.bloks.foa`) are largely **un-obfuscated** (e.g. `IgBloksScreenConfig`,
`BloksParseResult`, `BloksScreenQueryGenericContainerActivity`), and the
obfuscated interpreter classes (component tree node, evaluator context) mostly
lack unique string anchors. The one obfuscated class worth mapping:

- **`IgBloksActionRegistry` (`X/Adz`)** — the master registry that maps **all
  1816 `bk.action.*` action names** (e.g. `bk.action.array.Append`,
  `bk.action.bloks.AsyncActionWithDataManifestV2`) to integer handler ids; this
  is the dispatch table for every server-defined action the client can execute.
  Anchored on `bk.action.AsyncComponentCacheWrite` (unique). The other Bloks
  internals are documented here but not signatured (no unique anchor / already
  un-obfuscated).

## Analytics upload

Instagram's telemetry funnels through Meta's **Falco / analytics2** stack —
mostly **un-obfuscated** (`FFSingletonJNILogger` is the JNI gateway to the
native Falco queue; `FFAlarmUploadJobService`, `IgAnalytics2TaskBasedUploader`,
`MarkerHealthCounter` for QPL keep their names). The obfuscated piece with a
clean anchor:

- **`IgAnalyticsUploadEndpointBuilder` (`X/5qg`)** — builds the batch-upload URL,
  appending `/logging_client_events` (or `/pigeon_nest`) to the base host. This
  is the POST target for batched client analytics. Anchored on
  `/logging_client_events` (unique).

The obfuscated uploader/queue classes (`X/82d`, `X/81d`, `X/5ww`) are described
in the agent notes but not mapped — their anchors
(`com.facebook.analytics2.logger.UPLOAD_NOW`, the bare `events` JSON key) are
shared across many classes.

## Confidence

`X/2cr`, `X/Adz`, `X/5qg`: **high** — each pinned on a unique, descriptive
string reached by live code, with the surrounding constants confirming role
(`MobileConfigFetcher` interface; the `bk.action.*` cluster; the
`/logging_client_events` + `/pigeon_nest` pair). The un-obfuscated framework
classes are confirmed by preserved FQNs and documented for context only.
