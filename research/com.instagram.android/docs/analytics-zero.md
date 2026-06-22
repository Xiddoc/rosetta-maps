# Analytics / Profilo & Zero-Rating

Meta's telemetry stack (the analytics2 batch uploader + Profilo perf tracing) and
the **zero-rating / free-data** carrier features. Class names under
`com.instagram.analytics.*` / `com.instagram.zero.*` are mostly kept; the core
event logger and the zero-token UI are renamed `X/`. Logical→obfuscated names are
in the map + `signatures.yaml`.

## Analytics / Profilo

- **`IgAnalytics2TaskBasedUploader`** / `IGAnalytics2SimpleUploader`
  (`com.instagram.analytics.analytics2`) both implement the uploader contract —
  the single chokepoint for all batched telemetry leaving the device. The
  destination URL is assembled by a renamed builder (`X.5qg`, `/pigeon_nest` →
  `…/logging_client_events`, mapped on master). Scheduling goes through
  **`GooglePlayUploadService`** (`com.facebook.analytics2.logger`, GMS job
  `com.facebook.analytics2.logger.gms.TRY_SCHEDULE`) + an alarm receiver. Hook the
  uploader entry to observe every telemetry batch.
- **`AnalyticsEventEntry`** (`com.instagram.common.analytics.intf`) is the event
  data record. **`IgProfiloSessionManager`** (`com.instagram.profilo`) wraps
  Profilo BlackBox perf traces tied to a `UserSession` (`No active blackbox trace
  was running`). **`ArirangAnalyticsLogger`** (renamed) is a concrete event-logger
  example.

## Zero-rating / free data

- **`IgZeroMain`** (`com.instagram.zero.main`) is the orchestrator + state model
  (`carrier_id`, `product_alias`, `eligibility_hash`, `is_app_in_basic_mode`,
  `zero_balance_state`; `zero-main-run`); **`IgZeroBalanceStateCache`** persists it
  (`bal_cache_save`).
- **`ZeroNativeRequestInterceptor`** (`com.instagram.service.tigon.interceptors.zerorewritenative`)
  is the native-Tigon `RequestInterceptor` subclass that injects/rewrites the zero
  (free-data) headers onto outbound requests — the on-wire mechanism. Header
  config is fetched/pinged/stored by the `com.instagram.zero.headers.*` classes.
- **`ZeroTokenSummaryFragment`** (renamed) surfaces the zero token (hash, TTL,
  carrier id/name, eligibility hash, FDID). **`IgZeroModuleStatic`** triggers the
  FUP/free-data upsell interstitials.
