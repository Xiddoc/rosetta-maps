# Quick Experiment (QE) & Quick Promotion (QP)

Meta's on-device feature-gating and promo frameworks — high value for
instrumentation. (Complements master's `feature-gating-bloks-analytics.md`, which
covers the MobileConfig fetch endpoint; this doc covers the QE *read path* and
the QP framework.) The QE infra is renamed into `X/`; the QP intf/sdk/model keeps
its `com.instagram.quickpromotion.*` names. Logical→obfuscated names are in the
map + `signatures.yaml`.

## Quick Experiment (QE / mobileconfig)

QE reads A/B parameters layered on **mobileconfig**. The read path is the prime
hook.

- **`QuickExperimentParamStore`** (renamed `X.2fq`) is the parameter store/value
  resolver (log `Caught unsupported type %d for config %s, param %s in IG
  consistency logging`). It wraps the mobileconfig override store
  (reads `mc_overrides.json`). Hook its resolve methods to observe/override every
  QE read.
- **`ExperimentParameter`** (renamed `X.3Bf`) is the param model (id/universe/
  name). **`QuickExperimentDebugStore`** (renamed `X.Qiu`) persists dev overrides.
  **`QuickExperimentInitRunnable`** (renamed `X.2bi`) runs
  `initQuickExperimentManagers` at session start. The mobileconfig launcher
  fetcher (`launcher/mobileconfigqeinfo/`) is mapped on master as `X.2cr`.

## Quick Promotion (QP)

QP is the in-app interstitial/megaphone/tooltip promo framework.

- **`QuickPromotionSurface`** / **`QuickPromotionSlot`** (kept enums) map in-app
  placements (MEGAPHONE/TOOLTIP/INTERSTITIAL/FLOATING_BANNER/…) and slots to
  server values. **`Trigger`** / `QPTooltipAnchor` are the trigger/anchor models.
- **`InstagramQpSdkModule`** (kept) is the per-session QP module that builds the
  surface-controller manager. **`IGSlotFetcher`** (kept) is the fetch/eligibility
  API — GraphQL `QuickPromotionSurfaceQueryV3` rooted at
  `ig_quick_promotion_batch_fetch_root`, sending `surface_triggers`/
  `trigger_context`; logs `No creatives returned for QP`. Eligibility ties QP back
  to QE. **`IgdsPrismMegaphone`** (kept) renders the MEGAPHONE surface; the QP
  action handler runs through Bloks.
