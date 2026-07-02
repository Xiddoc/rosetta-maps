# MOT mobile ticketing

Moovit (`com.tranzmate`), confirmed against **version_code 1785** (versionName 5.194.0.1785). Classes are referenced by their **logical** name; the obfuscated name for this version is in [`maps/com.tranzmate/1785.json`](../../../maps/com.tranzmate/1785.json) and the regex anchors in [`signatures/com.tranzmate/signatures.yaml`](../../../signatures/com.tranzmate/signatures.yaml).

## Moovit MOT (mass/mobile-on-transit "pay-to-board") ticketing subsystem

MOT is Moovit's "activate a ticket by tapping/scanning at the vehicle or station" flow (heavily used for Israeli transit — bus MOT, train station entrance/exit, and the external **Zuzu** `il.idf.zuzu` wallet). The app code lives under `com.moovit.app.mot.*`; the wire protocol lives under `com.tranzmate.moovit.protocol.ptb.activations.*` (**PTB = Pay-To-Board**), a set of Apache-Thrift structs with kept `MV…` names but obfuscated field accessors.

### Obfuscation reality for this subsystem
Almost every class in scope **keeps its name** (Activities, ViewModels, models, and the `MV*` Thrift structs are all `kept=true`). The value of the map here is (a) pinning class *identity* to rotation-stable anchors so a hook can resolve the class even after R8 shuffles member names, and (b) the anchors themselves double as the best hook targets. Member (method/field) names are almost all renamed to short tokens (`M0`, `P0`, `R0`, `a()`, `j:Z`), so I deliberately added **no** member anchors — every renamed member would rotate. The kept overridden framework methods (`onReady`, `createInitialRequest`, `onInitialRequestSuccessful`) are noted below as hook points but are not class-unique, so they are not encoded as anchors.

### Key data models (`com.moovit.app.mot.model`, `…purchase.model`)
Parcelable models resolved from the PTB responses via obfuscated "coder" helper classes (e.g. `…/model/d`, `g`, `h`, `i`). Anchored on Kotlin `toString()` prefix strings (data classes) or on `b56.v(field,"name")` validation-key strings (classic Parcelables):
- **MotActivation** (core activation record) — has NO globally-unique string (all its field keys `activationTitle`, `agencyName`, `priceReference`, `profileName` are shared verbatim with the `MVPTBActivation` Thrift struct), so it is intentionally **omitted** rather than shipped with a shaky anchor.
- **MotActivationPrice** (price + full price + discount reasons), **MotActivationRegionalFare** (radius + region fares), **MotActivationStationInfo** (origin/destination stop refs), **MotQrCodeActivationFare** (fare + regionFare), **MotQrCodeEstimation** (estimated line + qr codes + source), **MotActivationFailedContact**, **PaymentContactActivationPrice** (per-contact price for group purchases).

### Purchase / pricing flow
- **MotPricesSummaryViewModel** (`…purchase`) drives the "prices summary" screen (`MotPricesSummaryFragment`): fetches the main user's price and each contact's price, merges with the selected `PaymentAccount`, and emits a `MotPricesSummaryViewModel$UiState`. Internal lambdas: `fetchMainUserPrice`, `fetchContactsPrices`, `updatePaymentAccount`, `paymentAccountFlow`, `uiStateFlow`. Anchor is the `calculateUiState(…UserPrices;)…$UiState;` Kotlin function-reference descriptor.
- **ActivationInfo** (`…purchase`) is the per-contact row model (contactId, title, subtitle, price, icon, most-severe profile status) shown in that summary.

### QR-code activation flow
- **MotQrCodeScanActivity** — camera scanner (`android.permission.CAMERA`); reports analytics `QR_scan_tap`, `mot_on_qr_code_scanned`; calls `get_mot_nearby_bus` to resolve nearby lines; guards on mocked/unknown location.
- **MotQrCodeActivationActivity** — the request-backed activation screen (extends the app's `MoovitAppActivity` request framework: `createInitialRequest` → `onInitialRequestSuccessful`). Consumes `MotQrCodeEstimation`s, supports `autoSkipByPrediction`/`skipScan`, `manual_fare_selection`, and requires the `MOT_SUPPORT_VALIDATOR` app-data part. `R0(MotQrCodeActivationFare, TransitLine, ServerId, boolean)` performs the actual per-fare activation. Static factory is `M0(...)` (the "createStartIntent" the guard string names).

### Station entrance/exit flow
- **MotStationActivationAbstractActivity** — abstract base for `MotStationEntranceActivationActivity` / `MotStationExitActivationActivity` / `MotStationEntranceOnlyActivationActivity`. Emits analytics `mot_station_impression`, `mot_station_error_try_again_clicked`.

### Wallet / home-screen widgets (`com.moovit.app.mot.wallet.widget`)
Each widget is a `MoovitComponentWidget` + a Kotlin `ViewModel` that combines an `AppDataParts`/`Configuration` + `PaymentAccount` flow into a `…UiState` via a `calculateUiState(...)` function reference (the anchor):
- **MotActivationWalletPurchaseViewModel** → `UiState` (loads route-type data, `MotActivationWalletPurchaseWidget`).
- **MotWalletInfoBoxViewModel** → `MotWalletInfoBoxUiState` (loads `MotWalletInfoBox`, listens to `activeWalletInfoBoxUpdatesReceiver`).
- **SmartCardWalletWidgetViewModel** → `SmartCardUiState` (`deleteCard`, `setPrimary`, `SmartCardWalletWidget`).
- **ZuzuWalletViewModel** → integrates the external **Zuzu** app (`il.idf.zuzu`); logs `The zuzu app is not installed!` / `Failed to calculate the ui state!`.

### Wire protocol (`com.tranzmate.moovit.protocol.ptb.activations`, Thrift)
57 `MV*` structs. Highest-value request/response cycle included as signatures (anchored on the generated `toString()` `"MVPTB…(field:"` prefix, which is globally unique per struct):
- **MVPTBSetActivationRequestV2 / MVPTBSetActivationResponse** — the actual purchase/activation call (response carries `activationsGroup` + `failedContacts`).
- **MVPTBGetUserActivationsResponse** — the wallet's list of active tickets (`activations` + `info` + `routeTypeData`).
- **MVPTBActivation** — the core activation struct the app `MotActivation` model is decoded from.
Other notable structs (not signed, but same anchor recipe applies): `MVPTBGetActivationPriceRequest/ResponseV2`, `MVPTBGetContactsPricesRequest/Response`, `MVPTBSetActivationByLocationRequest`, `MVPTBRetryActivationProcessRequest`, `MVPTBQrCodeEstimation`, `MVPtbGetNearByTransitTypesRequest/Response`, `MVPTBBillingStatementResponse`.

### Recommended Frida/Xposed hook points
- **Activation happens here:** `MotQrCodeActivationActivity.R0(...)` (per-fare QR activation) and the request built in `MotQrCodeActivationActivity.createInitialRequest()` / delivered to `onInitialRequestSuccessful(List)`; for station flows hook `MotStationActivationAbstractActivity`.
- **Observe/patch prices:** `MotPricesSummaryViewModel` (its `calculateUiState`/`fetchMainUserPrice` lambdas) and the models `MotActivationPrice`, `PaymentContactActivationPrice`, `ActivationInfo`.
- **Wallet contents:** parse `MVPTBGetUserActivationsResponse` / `MVPTBActivation` at the protocol layer, or hook the `calculateUiState` of the four wallet ViewModels to read/alter what the widgets render.
- **Purchase call:** intercept construction of `MVPTBSetActivationRequestV2` or the `MVPTBSetActivationResponse` read to see activation results.
Because names are kept, resolve each class by its anchor string, then walk to the renamed members (they rotate between versions — do not hard-code `R0`/`M0`).

## Classes identified

| Logical class | Renamed? | Confidence | Identity evidence |
| --- | --- | --- | --- |
| `MotQrCodeEstimation` | no | high | Kotlin data class implementing Parcelable with fields estimatedLine(MotQrCodeLinePrediction), qrCodes(List), source(String); generated toString prefix 'MotQr… |
| `PaymentContactActivationPrice` | no | high | Kotlin data class (contact + activationPrice) for per-contact group-purchase pricing; unique toString prefix 'PaymentContactActivationPrice(contact='. .class… |
| `MotActivationFailedContact` | no | high | Kotlin data class (contactId + name) representing a contact that failed group activation; unique toString prefix 'MotActivationFailedContact(contactId='. .cl… |
| `MotActivationStationInfo` | no | high | Parcelable holding origin/destination TransitStop DbEntityRefs; constructor validates b56.v(dbEntityRef,"originStopRef") — that literal is globally unique to… |
| `MotActivationRegionalFare` | no | high | Parcelable model (radius + list of region fares); constructor validation key 'regionFares' is globally unique. .class line kept. |
| `MotActivationPrice` | no | high | Parcelable price model (priceAmount, fullPriceAmount CurrencyAmount, discountReasons List) with nested DiscountReason; validation key 'fullPriceAmount' is gl… |
| `MotQrCodeActivationFare` | no | high | Parcelable fare selected during QR activation (fare + regionFare); validation key 'regionFare' is globally unique. Consumed by MotQrCodeActivationActivity.R0… |
| `ActivationInfo` | no | high | Kotlin data class for a prices-summary row (contactId, name, title, subtitle, price, icon, mostSevereProfileStatus); unique toString prefix 'ActivationInfo(c… |
| `MotPricesSummaryViewModel` | no | high | Kotlin ViewModel behind MotPricesSummaryFragment; lambdas fetchMainUserPrice/fetchContactsPrices/updatePaymentAccount/paymentAccountFlow/uiStateFlow. Anchor … |
| `MotActivationWalletPurchaseViewModel` | no | high | Kotlin ViewModel for MotActivationWalletPurchaseWidget; loads route-type data, combines AppDataParts + PaymentAccount + list into a UiState. Anchor is the un… |
| `MotWalletInfoBoxViewModel` | no | high | Kotlin ViewModel for MotWalletInfoBoxWidget; loadInfoBox/infoBoxFlow, listens to activeWalletInfoBoxUpdatesReceiver. Anchor is the unique calculateUiState(Ap… |
| `SmartCardWalletWidgetViewModel` | no | high | Kotlin ViewModel for SmartCardWalletWidget; deleteCard/setPrimary/paymentAccountFlow. Anchor is the unique calculateUiState(Configuration, PaymentAccount) ->… |
| `ZuzuWalletViewModel` | no | high | Kotlin ViewModel integrating the external Zuzu app (package il.idf.zuzu) into the wallet; logs 'The zuzu app is not installed!' (globally unique) and 'Failed… |
| `MotQrCodeActivationActivity` | no | high | Request-backed activation Activity (createInitialRequest/onInitialRequestSuccessful; static factory M0=createStartIntent; R0(MotQrCodeActivationFare,...) act… |
| `MotQrCodeScanActivity` | no | high | Camera QR scanner Activity (android.permission.CAMERA); analytics QR_scan_tap / mot_on_qr_code_scanned; resolves nearby lines via 'get_mot_nearby_bus' (globa… |
| `MotStationActivationAbstractActivity` | no | high | Abstract base for station entrance/exit activation Activities (MotStationEntrance/Exit/EntranceOnly...); analytics 'mot_station_impression' + 'mot_station_er… |
| `MVPTBSetActivationRequestV2` | no | high | Thrift request struct for performing an MOT activation/purchase (fields context, scanLocation, fareInfo, ...); generated toString prefix 'MVPTBSetActivationR… |
| `MVPTBSetActivationResponse` | no | high | Thrift response for an MOT activation (fields activationsGroup, failedContacts); unique toString prefix 'MVPTBSetActivationResponse(activationsGroup:'. Thrif… |
| `MVPTBGetUserActivationsResponse` | no | high | Thrift response carrying the user's active MOT tickets for the wallet (fields activations, info, routeTypeData); unique toString prefix 'MVPTBGetUserActivati… |
| `MVPTBActivation` | no | high | Core Thrift activation struct (activationId, activationTime, activationTitle, agencyName, profileName, priceReference, ...) that the app MotActivation model … |

