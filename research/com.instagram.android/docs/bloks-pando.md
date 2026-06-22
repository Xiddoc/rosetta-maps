# Bloks & Pando / GraphQL (cross-platform infra)

The two Meta cross-platform frameworks that power most of the app: **Bloks**
(server-driven UI) and **Pando** (the GraphQL data layer). These are the most
load-bearing infra surfaces for instrumentation. (Complements master's
`feature-gating-bloks-analytics.md`, which catalogs the Bloks *action registry*;
this doc maps the Bloks *hosting* layer and the Pando *JNI* layer.) The core
interpreter is obfuscated into `X/`; the hosting layer and the native bridge
classes keep their names. Logical→obfuscated names are in the map +
`signatures.yaml`.

## Pando / GraphQL

The native GraphQL request → execute → parse → tree pipeline (all JNI-bridged,
so the native method boundary is the durable hook surface):

- **`PandoGraphQLRequest`** (`com.facebook.pando`) is the request object
  (`pando-graphql-jni`; `queryName`/`schemaName`/`injectionCapabilities`).
  **`PandoGraphQLServiceJNI`** is the native executor.
- **`IgPandoApiFrameworkParserJNI`** (`com.instagram.pando.parsing`) parses
  network bytes into a **`TreeJNI`** response tree (field access by integer
  hashcode); **`TreeWithGraphQL`** is the base of generated typed response models.
- **`PandoConsistencyServiceJNI`** is the normalized store; **`LiveTreeJNI`**
  (`com.instagram.pando.livetree`) is the single-source-of-truth subscription
  layer (`TreeUpdaters returned null!`). **`IGGraphQLLiveQuerySDKProvider`** is the
  realtime live-query provider. **Hook points:** `PandoGraphQLRequest` to capture
  outgoing queries, `IgPandoApiFrameworkParserJNI.parseByteArray` /
  `TreeJNI.asJSONNative` to dump raw responses, `LiveTreeJNI.subscribeToUpdates`
  for live data.

## Bloks (server-driven UI)

`com.bloks.www.*` flow ids appear ~941× app-wide; the lispy interpreter is
obfuscated, but the IG hosting layer keeps its names.

- **`IgBloksScreenConfig`** (`com.instagram.bloks.hosting`) is the Parcelable
  screen config (bundle key `screen_config`, carries app-id + `BloksParseResult`).
  **`IgBloksScreenFragment`** (renamed, recovered by redex name) is the host
  fragment (`runExpression failed on Surface Core.`). **`IgBloksBottomSheetFragment`**
  / **`BloksScreenQueryGenericContainerFragment`** (renamed) are the bottom-sheet
  and screen-query container hosts.
- **`BloksParseResult`** (`com.instagram.common.bloks`) is the parsed payload
  (components + sync/async action containers). **`IgReactBloksNavigationModule`**
  bridges React Native → Bloks. **`BloksNativeHybridShellUrlHandlerActivity`** is
  one of ~15 kept Bloks deep-link entry points. **Hook points:**
  `IgBloksScreenConfig` to capture every screen's app-id + payload,
  `BloksParseResult` to dump parsed component trees. The core interpreter
  (`BloksInterpreterEnvironment`, lispy `Expression`) is fully obfuscated and not
  mapped (would need version-fragile structural fingerprinting).
