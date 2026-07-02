# Premium / Moovit+ / subscriptions

Moovit (`com.tranzmate`), confirmed against **version_code 1785** (versionName 5.194.0.1785). Classes are referenced by their **logical** name; the obfuscated name for this version is in [`maps/com.tranzmate/1785.json`](../../../maps/com.tranzmate/1785.json) and the regex anchors in [`signatures/com.tranzmate/signatures.yaml`](../../../signatures/com.tranzmate/signatures.yaml).

## Moovit+ / Premium subscription subsystem

Moovit's premium tier is **Moovit+**. It is built from three cooperating pieces:

1. **Feature gating** — `com.moovit.app.subscription.premium.packages.*`. An abstract
   base **SubscriptionPackage** (obfuscated on-disk name `com.moovit.app.subscription.premium.packages.a`)
   has one concrete subclass per premium feature, keyed by the **SubscriptionPackageType**
   enum (`AD_FREE`, `SAFE_RIDE`, `SHARE_RIDE`, `TRIP_ON_MAP`, `VEHICLE_ON_MAP`,
   `COMPARE_ON_MAP`, `TRIP_NOTIFICATIONS`, `GREEN_RIDE`, `TRAFFIC_ON_MAP`,
   `TRIP_PLAN_SORT`, `TRIP_PLAN_ADVANCED_ROUTE`, `TRIP_INSIGHTS`, `DEFAULT_TAB`,
   `MUNDIAL`, `ADVANCED_TIME_PICKER`; each carries a lowercase server key such as
   `"safe_ride"`, `"advanced_trip_plan_route_options"`). Each package computes a
   **SubscriptionPackageState** (`INACTIVE`/`OFFER`/`PENDING_ACTIVATION`/`ACTIVE`,
   each with an analytics constant like `"package_state_active"`) inside its
   obfuscated `calculateState` method by reading `com.moovit.payment.account.model.PaymentAccount`
   (the actual entitlement source of truth, owned by the payment subsystem),
   `com.moovit.app.feature.FeatureFlag`, and the `"CONFIGURATION"` app-data part.
   The base class listens for the `"com.moovit.app.action.foreground"` broadcast and
   data-part updates (`SubscriptionPackage$updateBroadcastReceiver$1`,
   `SubscriptionPackage$dataPartsUpdateBroadcastReceiver$1`), then re-runs
   `updateState`→`calculateState` and pushes the result into a `StateFlow` (base field `g`).

2. **Registry / manager** — **SubscriptionPackagesManager** (obfuscated `defpackage.zvd`,
   held via the `qd2` singleton `zvd.d`). It lazily builds a
   `Map<SubscriptionPackageType, SubscriptionPackage>` from the enabled-package list
   `ukg.a().l`, instantiating the concrete package classes (see `awd.a[...ordinal()]`
   switch). Other subsystems (e.g. RideNavigationManager) read package state through this map.

3. **Purchase / entitlement models** (Google Play Billing shapes) —
   `com.moovit.app.subscription.model.*`: **SubscriptionStatus** (Play states
   `ACTIVE`/`CANCELLED`/`EXPIRED`/`IN_GRACE_PERIOD`/`ON_HOLD`/`PAUSED`),
   **SubscriptionOffer** / **SubscriptionOfferAssets** / **SubscriptionBasePlan** /
   **SubscriptionPricingPhase** / **RecurrenceMode** / **SubscriptionOfferType** /
   **SubscriptionPeriod** / **PurchaseDetails** (`productIds`, `purchaseToken`).
   These describe the offers/base-plans shown in the paywall and the resulting purchase.

### Purchase UI flow
`AbstractSubscriptionActivity` (base) → `BlockPaywallActivity`/`BlockPaywallFragment`,
`MoovitPlusActivity`, `MoovitPlusPurchaseFragment`/`MoovitPlusPurchaseOffersFragment`,
`MoovitPlusOnboardingActivity`. The paywall logs analytics
`"purchase_subscription_screen_impression"`. Deep-linking into a package screen is
parsed by **SubscriptionUtils** (obfuscated `com.moovit.app.subscription.c`) from the
intent `"pt"` query param / `"packageType"` / `"onBoardingPackageType"` extras into a
`SubscriptionPackageType`. Purchase vs. restore is modelled by the `SubscriptionAction`
enum (`PURCHASE`/`RESTORE`).

### Referral + benefits (Moovit+ benefits)
Referral: `MoovitPlusReferralActivity`/`MoovitPlusReferralFragment` +
`MoovitPlusRedeemActivity`, backed by **MoovitPlusReferralViewModel** (obfuscated
`com.moovit.app.plus.referral.c`) and **MoovitPlusRedeemViewModel** (obfuscated
`com.moovit.app.plus.referral.b`; both extend the obfuscated ViewModel base `h60` and
carry only the shared coroutine string, so they have no stable unique class anchor and
are omitted from the signatures — identify them by their leaked inner-class names
`MoovitPlusReferralViewModel$sendReferralRequest$1`, `MoovitPlusRedeemViewModel$redeemCouponCode$1`,
etc.). **MoovitPlusReferralParams** is the referral-screen params model.
The wire protocol is Apache-Thrift under
`com.tranzmate.moovit.protocol.moovitplusbenefits`: **MVGetReferralCouponResponse**
(returns `code` + `discountPercents` + `message`), **MVRedeemCouponRequest** (`code`) →
**MVRedeemCouponResponse**; the redeem payload wraps `MVGoogleRedeemData`/`MVAppleRedeemData`
via `MVRedeemCouponData`.

Benefits: **BenefitViewModel** (email-based benefit registration + instructions) sends a
`GetBenefitInstructions` request and a registration request, validating with the error
`"Invalid benefit."` and using the `"benefit_id"` argument.

Content cards: **MoovitPlusContentCards** (obfuscated `com.moovit.app.plus.a`) picks the
most important premium content card for a given subscription tag and enriches it with
offer pricing (`enrichCard`), logging `"No offers found for subscription tag: "` /
`"Card enrichment is not supported."`.

### Frida / Xposed hook points
- **Force premium ON / read entitlement:** hook the concrete `SubscriptionPackage.calculateState`
  (obfuscated method inside each `.../premium/packages/<feature>/a|b.smali`) or the base
  `updateState` to return `SubscriptionPackageState.ACTIVE`. These package classes are
  obfuscated and carry only `"CONFIGURATION"`, so there is no rotation-stable string
  anchor — target them via `SubscriptionPackagesManager` (`defpackage.zvd`) which holds the
  `Map<SubscriptionPackageType, SubscriptionPackage>` and is reachable from the verified
  `SubscriptionPackageType`/`SubscriptionPackageState` enums.
- **Inspect Play billing state:** watch `SubscriptionStatus`, `SubscriptionOffer`,
  `SubscriptionBasePlan`, `PurchaseDetails`.
- **Referral redemption:** intercept the Thrift structs `MVRedeemCouponRequest`
  (outbound, field `code`), `MVRedeemCouponResponse`, and `MVGetReferralCouponResponse`
  (inbound `discountPercents`).
- **Benefit flow:** hook `BenefitViewModel.calculateUiState` (obf `a`) /
  `sendBenefitInstructionsRequest` (obf `c`).
- **Content-card offer manipulation:** hook `MoovitPlusContentCards.enrichCard` (obf `a`).

### Notable classes lacking a stable anchor (documented, not signed)
`SubscriptionPackage` base (`...premium/packages/a`), `RideNavigationManager`
(`...premium/packages/safety/a`; log tag `"RideNavigationManager"`, but that string also
leaks into its inner receiver/flow classes so it is not class-unique), `SafeRideSubscriptionPackage`
(`...safety/b`), `SubscriptionPackagesManager` (`defpackage.zvd`, no strings),
`SubscriptionUtils` (`...subscription/c`; its intent-extra keys are shared with launchers),
the paywall Activities/Fragments (`purchase_subscription_screen_impression` is shared by
both `BlockPaywallFragment` and `MoovitPlusPurchaseFragment`), and the referral view models
(`...referral/b`,`...referral/c`). All are obfuscated and identified above by their
on-disk names, which are stable only within this `version_code` (1785).

## Classes identified

| Logical class | Renamed? | Confidence | Identity evidence |
| --- | --- | --- | --- |
| `SubscriptionPackageType` | no | high | Kept enum name; @Metadata + $VALUES list all premium package types with their server keys (ad_free, safe_ride, advanced_trip_plan_route_options, ...); consum… |
| `SubscriptionPackageState` | no | high | Kept enum name; values INACTIVE/OFFER/PENDING_ACTIVATION/ACTIVE each carry an analyticsConstant (package_state_offer/pending_activation/active); returned by … |
| `SubscriptionStatus` | no | high | Kept enum mirroring Google Play Billing subscription states (ACTIVE, CANCELLED, EXPIRED, IN_GRACE_PERIOD, ON_HOLD, PAUSED). Anchor string appears twice in-cl… |
| `RecurrenceMode` | no | high | Kept enum for Play Billing pricing recurrence (FINITE_RECURRING, INFINITE_RECURRING, NON_RECURRING); used by SubscriptionPricingPhase. Anchor appears twice i… |
| `SubscriptionPricingPhase` | no | high | Kept Parcelable data class; Kotlin-generated toString prefix 'SubscriptionPricingPhase(cycleCount=' plus fields period/price/recurrenceMode describe one Play… |
| `SubscriptionBasePlan` | no | high | Kept Parcelable model of a Play Billing base plan; carries fields basePlanId, period, price, pricePerMonth, productId. The pricePerMonth field-name string is… |
| `MoovitPlusReferralParams` | no | high | Kept Parcelable params model for the Moovit+ referral screen; Kotlin toString prefix 'MoovitPlusReferralParams(title=' with field showCloseButton. |
| `BenefitViewModel` | no | high | Kept ViewModel (extends obfuscated base h60); drives the Moovit+ benefit registration/instructions flow. Inner classes BenefitViewModel$calculateUiState$1 / … |
| `MoovitPlusContentCards` | yes | high | Obfuscated to plus/a but leaked inner classes MoovitPlusContentCards$enrichCard$1 and MoovitPlusContentCards$getMostImportantContentCardFlow$... reference th… |
| `MVRedeemCouponRequest` | no | high | Kept Apache-Thrift struct (implements TBase) for the Moovit+ referral redeem call; single field 'code'. Thrift toString prefix 'MVRedeemCouponRequest(code:' … |
| `MVRedeemCouponResponse` | no | high | Kept Thrift struct (TBase) for the redeem-coupon response in the Moovit+ benefits protocol; Thrift toString prefix 'MVRedeemCouponResponse(' globally unique. |
| `MVGetReferralCouponResponse` | no | high | Kept Thrift struct (TBase) returning the user's referral coupon: fields code, discountPercents, message. Thrift toString prefix 'MVGetReferralCouponResponse(… |

