# Micromobility (bike/scooter)

Moovit (`com.tranzmate`), confirmed against **version_code 1785** (versionName 5.194.0.1785). Classes are referenced by their **logical** name; the obfuscated name for this version is in [`maps/com.tranzmate/1785.json`](../../../maps/com.tranzmate/1785.json) and the regex anchors in [`signatures/com.tranzmate/signatures.yaml`](../../../signatures/com.tranzmate/signatures.yaml).

## Moovit Micromobility (bike/scooter rentals) subsystem

Handles nearby dockless vehicle/station discovery, third‑party provider integration (deep‑link / reserve / unlock), the multi‑step purchase/rental flow, active‑ride tracking, cancellation, and damage reporting. Package paths under `com/moovit/micromobility/**` are preserved; the model/DTO classes keep their `MicroMobility*` names, but the **manager, stores, ride model, request senders, and the map bottom‑sheet are renamed to short tokens** (`zc9`, `gc9`, `qe9`, `com.moovit.micromobility.ride.a`, `sc9`, `vd9`, `yd9`, `cc9`) — those are the high‑value map entries.

### Key components & flow
- **`MicroMobilityManager` (`zc9`)** is the singleton hub (thread pool named `"m-mm"`). It lazily loads and caches two things behind `AtomicReference`s:
  - **user wallet** = active/reserved rides → `MicroMobilityUserWallet` (`qe9`, `toString` = `MicroMobilityUserWallet{rides=…}`). The active status set (`qe9.c`) = `{RESERVED, ACTIVE, PAUSED, PENDING}`.
  - **rides history** → `MicroMobilityRidesHistory` (`gc9`, `toString` = `MicroMobilityRidesHistory{rides=…}`).
  `zc9.c()`/`b()` return `Task`s that fetch these (server call built by `g96`, a shared `Callable`); `zc9.e(ServerId)` resolves a single ride, `zc9.g()` refreshes and fires the LocalBroadcast **`com.moovit.micromobility.action.updated`** (the action string literal lives in the synthetic listener `uc9`). Error codes 40101/40102/40104/43003 trigger account re‑auth.
- **`MicroMobilityRide` (`com.moovit.micromobility.ride.a`)** — the core ride model (implements ordering iface `odg`): `serviceId`, `itemId`, two `ServerId`s, `vehicleTypeName`, provider image, start‑time, `statusInfo` (`pe9`: active flag + `MicroMobilityRide$Status` + `CurrencyAmount`) and `rideInfo` (`ke9`: pickup/dropoff `LocationDescriptor`s, timestamps, vehicle condition, metrics). Priority ordering comes from `MicroMobilityRide$Status` (ACTIVE=1000…EXPIRED=7000). The outer name leaked via the kept inner enums `MicroMobilityRide$Status`/`$VehicleType` even though the outer is renamed to `a`.
- **Discovery / popup**: `MicroMobilityBottomSheetDialog` (`cc9`, extends map base `com.moovit.map.f`) is the map popup for a nearby `MicroMobilityItemInfo`; it embeds `MicroMobilityIntegrationView` and emits analytics `popup_micro_mobility`, `micro_mobility_integration_button_clicked`, `view_ride_clicked`. Its identity is confirmed by the leaked assertion string `"Did you use MicroMobilityBottomSheetDialog.newInstance(...)?"`.
- **Purchase flow**: `MicroMobilityPurchaseActivity` (kept) drives a chain of `MicroMobilityPurchaseStep` subclasses (`…ConfirmationStep`, `…FilterSelectionStep`, `…InputStep`, `…PinCodeStep`, `…QrCodeStep`), each carrying `contextId`/`analyticKey` and a `a(activity, stepId)` that pushes a fragment. Server steps are parsed from Thrift by `jd9.a(...)` (used by response parsers `rd9`/`td9`). Payment is attached to `MVMicroMobilityPurchaseConfirmationRequest.paymentProvider` by `ld9` (cash / clearance‑provider / Google Pay / payment‑method gateway tokens). `MicroMobilityError` maps server error codes 50007‑50011 (WUNDER_ERROR, DOUBLE_ACTIVE_RIDES_ERROR, NO_BIKES_IN_STATION_ERROR, UNRECOVERABLE_ERROR, PENDING_VERIFICATION_ERROR) to dialogs.
- **Active ride**: `MicroMobilityRideActivity` (kept) tracks a live ride — real‑time polling (`startRealTimePolling: rideId=%s` / `stopRealTimePolling`, request `vd9`), cancel‑ride dialog (`cancel_ride_confirmation_dialog_fragment`), and expiration alert; listens for `com.moovit.micromobility.action.updated`.
- **Damage**: `MicroMobilityReportDamageActivity` (kept) submits `MicroMobilityDamageReport`s (request `yd9`), then shows `report_sent_successfully_dialog`; `MicroMobilityReportedDamagesActivity` lists prior reports (request built in `xb9`).

### Network request senders (all extend the renamed Moovit request base `kfe`)
- `sc9` → **GetItemInfo** (`MVMicroMobilityItemInfoRequest(serviceId, itemId)`), response `tc9`.
- `vd9` → **RealTimeInfo** (`MVMicroMobilityRealTimeInfoRequest(rideId)`), response `wd9` — the polling call.
- `yd9` → **ReportDamage** (`MVMicroMobilityReportDamageRequest(serviceId, itemId, description, images)`), response `zd9`.
- (Also present but multiplexed into large synthetics, so not signed: purchase‑intent `q78`, confirmation/action `ok1`, cancel‑ride `os8`, damage‑reports‑list `xb9`.)

### Serialization
Model classes use Moovit's custom parcel/codec framework (`t99`/`li4`/`lla.u(...)`) with fixed version indices (e.g. `t99(MicroMobilityRide$Status style)`), not standard `Parcelable` field writes — field order/version numbers are stable per class. Wire types are Thrift `MV…` structs under `com.tranzmate.moovit.protocol.micromobility.*` (kept names).

### Good Frida/Xposed hook points
- **`MicroMobilityManager` (`zc9`)** singleton getter `a()` and the wallet/history loaders `b()`/`c()`/`e(ServerId)` — intercept to read/spoof the user's active rides and history caches.
- **`MicroMobilityRealTimeInfoRequest` sender (`vd9`)** — hook to observe/modify live ride state during polling; pair with `MicroMobilityRideActivity` polling methods.
- **`ld9`** (payment attach) — the choke point where a payment gateway token is bound to the confirmation request; hook to inspect the purchase/payment provider.
- **`MicroMobilityError` `fromErrorCode(int)`** — force/observe the error‑to‑dialog mapping.
- **`MicroMobilityReportDamageRequest` sender (`yd9`)** — observe/alter damage submissions.
- The LocalBroadcast **`com.moovit.micromobility.action.updated`** is the app‑wide "ride state changed" signal to watch.

## Classes identified

| Logical class | Renamed? | Confidence | Identity evidence |
| --- | --- | --- | --- |
| `MicroMobilityManager` | yes | high | Singleton (static volatile d, a()/f() init) that lazily loads and caches the user's micromobility wallet (qe9 MicroMobilityUserWallet) and rides history (gc9… |
| `MicroMobilityRidesHistory` | yes | high | Immutable holder wrapping an unmodifiable List of MicroMobilityRide (rides); its own toString() emits the literal "MicroMobilityRidesHistory{rides=" which na… |
| `MicroMobilityUserWallet` | yes | high | Immutable holder for the user's active micromobility rides; static set qe9.c = EnumSet.of(RESERVED, ACTIVE, PAUSED, PENDING) built from MicroMobilityRide$Sta… |
| `MicroMobilityRide` | yes | high | Core ride model (implements ordering iface odg): fields serviceId, itemId, two ServerIds, vehicleTypeName, provider Image, start timestamp, statusInfo (pe9) … |
| `MicroMobilityBottomSheetDialog` | yes | high | Map bottom-sheet popup for a nearby MicroMobilityItemInfo; embeds MicroMobilityIntegrationView, wires serviceId/itemId, launches MicroMobilityPurchaseActivit… |
| `MicroMobilityError` | no | high | Kept enum mapping micromobility server error codes to dialogs: fromErrorCode() switches 50007->WUNDER_ERROR, 50008->DOUBLE_ACTIVE_RIDES_ERROR, 50009->NO_BIKE… |
| `MicroMobilityReportDamageActivity` | no | high | Kept activity for submitting a micromobility damage report (serviceId/itemId + description + images) via request yd9; on success shows report_sent_successful… |
| `MicroMobilityRideActivity` | no | high | Kept activity for tracking an active ride by rideId: real-time polling (log "startRealTimePolling: rideId=%s" / "stopRealTimePolling", request vd9), cancel-r… |
| `MicroMobilityGetItemInfoRequest` | yes | high | Moovit server request (extends request base kfe) that fetches item info for a nearby micromobility item; constructor takes (RequestContext, serviceId, itemId… |
| `MicroMobilityRealTimeInfoRequest` | yes | high | Moovit server request (extends kfe) for live ride state used by MicroMobilityRideActivity's real-time polling; constructor takes (RequestContext, ServerId ri… |
| `MicroMobilityReportDamageRequest` | yes | high | Moovit server request (extends kfe, implements Callable) that submits a damage report; constructor takes (RequestContext, serviceId, itemId, description, ima… |

