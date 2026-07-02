# Transit-on-demand / ride hailing

Moovit (`com.tranzmate`), confirmed against **version_code 1785** (versionName 5.194.0.1785). Classes are referenced by their **logical** name; the obfuscated name for this version is in [`maps/com.tranzmate/1785.json`](../../../maps/com.tranzmate/1785.json) and the regex anchors in [`signatures/com.tranzmate/signatures.yaml`](../../../signatures/com.tranzmate/signatures.yaml).

## Transit-on-Demand / Ride-Hailing (TOD) subsystem — Moovit 5.194.0.1785 (com.tranzmate, vc 1785)

### What it does
The TOD subsystem books and tracks **on-demand passenger rides** (ride-hailing / taxi-style and autonomous-vehicle rides) and **shuttle** rides. It covers the full lifecycle: booking flow (pick a pickup + drop-off inside a service zone), placing an order, waiting for driver/vehicle assignment, live vehicle tracking, in-ride actions (flash lights / beep / PIN / QR), destination change, rating, and cancellation (with cancel-fee quoting). Code lives entirely under `com.moovit.app.tod.*`. Package **paths are preserved**; most domain classes keep **descriptive names** (`TodRide`, `TodOrder`, `TodRidesProvider`, activities, view-models) so `kept=true`, but their **fields/methods are renamed to single tokens** (`a`, `b`, `g()`), which is exactly what the map recovers. A few internal/facade classes are renamed to short tokens (e.g. the Kotlin realtime facade `TodRideRealtimeProviderExtKt` collapses to `com/moovit/app/tod/a.smali`, which has no string anchor and is not reported).

### Core data model
- **`TodRide`** — the central active-ride aggregate: `rideId`, `orderTime`, `TodRideStatus`, `TodRideJourney`, `TodRideVehicle`, price (`CurrencyAmount`), provider id/name/icons, rating/ratable, reservation flags, `hasPaymentIssue`, `dropOffTime`, `itineraryGuid`. Parcelable; identified by its `toString` prefix `TodRide{rideId='`.
- **`TodRideStatus`** (enum) — FUTURE / ACTIVE / CANCELLED / COMPLETED / PASSENGER_NOT_SHOWN / DECLINED, each carrying icon/text/color resource ids + a `priority` used for ordering. Persisted via an `li4` CODER. Its Thrift twin is `MVTodPassengerRideStatus`; the app enum is told apart by its Android string-resource refs (`tod_passenger_ride_status_*`).
- **`TodJourneyStatus`** (enum) — live vehicle progress: HEADING/ARRIVING/ARRIVED × PICKUP/DROP_OFF. Drives the bottom-sheet state views. Distinguished from Thrift `MVTodJourneyStatus` by its `tod_passenger_ride_real_time_*` resource refs.
- **`TodRideJourney`** — origin / destination `LocationDescriptor`s, pickup & drop-off points, walking times, map bounds (`toString` prefix `TodRideJourney{origin=`).
- **`TodOrder` / `TodOrderAssignment`** — an order (ServerId, expiration ms, list of assignments, `TodPaymentInfo`) and one driver/vehicle assignment (`assignmentId`, journey, provider images). `TodOrder` itself is a thin data holder with no unique string and is not reported; `TodOrderAssignment` is anchored on its `providerMapImage` ctor validation string.
- **`TodRideVehicleColorBar`** — vehicle-identification color bar (find-my-ride). Part of the vehicle-action set (`TodRideVehicleAction` = AUDIO/BEEP/COLOR_BAR/FLASH, `TodPassengerActionRequiredInfoType` = NONE/PIN_CODE/QR_CODE); those two enums leak their names into Thrift twins and lack app-unique anchors, so only ColorBar is reported.

### Booking flow
- **`TodBookingOrderViewModel`** — the booking state machine. Uses a `SavedStateHandle` with keys `pickup_location`, `drop_off_location`, `pickup_loading`, `drop_off_loading`, `order_info`, `USER_CONTEXT`; loads user context then resolves pickup/drop-off service areas. Produces an `OrderInformation` consumed by `TodOrderActivity`.
- **`TodLocation`** — a chosen booking location (`snapshotId` + `LocationDescriptor`).
- **`TodBookingPickupInformation` / `TodBookingDropOffInformation`** — per-zone pickup/drop-off rules: allowed shapes, stops, service-area flag, pickup-confirmation-required flag, explanation URLs, drop-off restrictions. (Note the `toString` tags say `TodBookingOrderPickupInformation[...]` / `TodBookingOrderDropOffInformation[...]` — the on-disk class names are the shorter `TodBookingPickupInformation` / `TodBookingDropOffInformation`.)
- **`TodZoneShape`** — a polygon (`shapeId` + point list) defining a TOD service zone boundary.

### Cancellation
- **`TodCancelFeeDialogInfo`** — the cancel-fee confirmation dialog payload (image, title, message, options list, close-button text). Id wrappers `TodOrderId`/`TodRideId`/`TodSubscriptionId`/`TodCancelOption` are trivial 1–2 field holders with no stable string anchor and are not reported.

### Controllers / lifecycle
- **`TodRidesProvider`** — the app-wide **rides repository / manager** (`volatile` singleton, `BroadcastReceiver`). Registers for GCM topic `tod_ride` and for local broadcasts `com.moovit.tod_rides_provider.action.{book,cancel_ride,login,ride_status_change,reassign,ride_rating,cancel_subscription}`. On any of these it invalidates a 5-minute cache and re-fetches via server request `api_path_tod_rides_request` (obfuscated request wrapper `kqe`, response `lqe` which parses Thrift `MVTodPassengerRides` into ride + subscription lists), then notifies registered `hqe` listeners. This is the single hub for "rides changed".
- **`TodRideActivity`** — the live active-ride screen (map + `TodRideBottomSheet` state views). Handles new-ride intents, cancel-ride dialog, rating, support validator, TOD Lottie prefetch.
- **`TodOrderActivity`** — the order/checkout screen: builds and sends the order request, disables the pay button while in-flight, keeps a valid current order until expiry, and can stop the active order.

### Serialization / formats
- On-device models are **Android Parcelable** (custom `aje`/`bge` `CREATOR`s indexed by an int; versioned reader/writers `khe`/`li4` for evolving fields).
- The **network layer is Apache Thrift** (`com.tranzmate.moovit.protocol.tod.passenger.MV*` and `...tod.shuttles.MV*`): e.g. `MVTodPassengerRides`, `MVTodOrderResponse`, `MVTodRideUpdateOffer`, `MVTodJourneyStatus`. App models are converted from these MV structs inside the obfuscated `lqe`-style response wrappers. Those MV structs are a separate (protocol) subsystem and are only referenced here, not signed.

### Good Frida / Xposed hook points
- **`TodRidesProvider.requestRidesUpdate` (renamed `g()Z`)** — hook to observe/force ride-list refreshes; return value gates whether a network fetch fires. `TodRidesProvider.notifyRidesUpdated` (static, renamed `a(...)`) fires on every update/error — hook to intercept the resolved ride list.
- **`TodRidesProvider.onReceive`** — central choke point for all TOD push/broadcast events (`intent.getAction()` is the event name).
- **`TodRide` constructor / `TodRideStatus`** — hook `TodRide.<init>` or read `TodRide.c` (status) to watch ride state transitions; `TodRideStatus.getPriority`/fields expose the status semantics.
- **`TodBookingOrderViewModel`** — hook to observe/override booking state (pickup/drop-off resolution, `OrderInformation`) before an order is placed.
- **`TodOrderActivity.sendOrderRequest` / `stopActiveOrder`** — hook to observe/modify the outgoing order request or suppress order teardown.
- **`TodRideActivity.onNewRideIntent`** — hook to capture the `rideId` of whatever ride the UI opens.

All 15 reported classes are `kept=true` (descriptive on-disk names); every class anchor is a rotation-stable string literal or Android resource-name ref, verified unique app-wide (exactly one matching class file).

## Classes identified

| Logical class | Renamed? | Confidence | Identity evidence |
| --- | --- | --- | --- |
| `TodRidesProvider` | no | high | Singleton BroadcastReceiver rides-repository: registers GCM topic "tod_ride" and local broadcasts com.moovit.tod_rides_provider.action.* (book/cancel_ride/lo… |
| `TodRideActivity` | no | high | Live active-ride screen (map + TodRideBottomSheet). Handles new-ride intents (rideId), cancel-ride dialog, rating, TOD support validator and Lottie prefetch.… |
| `TodOrderActivity` | no | high | Order/checkout screen: builds & sends the TOD order request, disables pay button while in-flight, keeps current order valid until expiry, stops active order.… |
| `TodBookingOrderViewModel` | no | high | Booking-flow state machine. Uses SavedStateHandle keys pickup_location/drop_off_location/pickup_loading/drop_off_loading/order_info/USER_CONTEXT; loads user … |
| `TodRide` | no | high | Central active-ride aggregate (Parcelable, implements odg). Fields: rideId, orderTime, TodRideStatus, TodRideJourney, TodRideVehicle, price, provider id/name… |
| `TodRideJourney` | no | high | Ride journey model: origin/destination LocationDescriptors, pickup & drop-off points, walking times, map bounds. Anchored on unique toString prefix TodRideJo… |
| `TodRideStatus` | no | high | Ride lifecycle status enum FUTURE/ACTIVE/CANCELLED/COMPLETED/PASSENGER_NOT_SHOWN/DECLINED, each with icon/text/color resource ids + priority; persisted via l… |
| `TodJourneyStatus` | no | high | Live vehicle-progress enum HEADING/ARRIVING/ARRIVED x PICKUP/DROP_OFF, driving the ride bottom-sheet state views; each value maps to a tod_passenger_ride_rea… |
| `TodOrderAssignment` | no | high | One driver/vehicle assignment within a TodOrder: assignmentId, TodRideJourney, provider image + provider map image. Anchored on its ctor validation string pr… |
| `TodRideVehicleColorBar` | no | high | Vehicle-identification color bar (find-my-ride color action) with mainColor. Anchored on unique toString prefix TodRideVehicleColorBar{mainColor=. |
| `TodLocation` | no | high | Chosen booking location: snapshotId + LocationDescriptor. Anchored on unique toString prefix TodLocation(snapshotId=. |
| `TodBookingPickupInformation` | no | high | Per-zone pickup rules: providerId, pickup shapes/stops, hasServiceArea, isPickupConfirmationRequired, pickupExplanationUrl. Anchored on unique toString prefi… |
| `TodBookingDropOffInformation` | no | high | Per-zone drop-off rules: drop-off shapes/stops, restrictions, dropOffExplanationUrl. Anchored on unique toString prefix TodBookingOrderDropOffInformation[dro… |
| `TodZoneShape` | no | high | TOD service-zone boundary polygon: shapeId + polygon point list. Anchored on unique toString prefix TodZoneShape{shapeId=. |
| `TodCancelFeeDialogInfo` | no | high | Cancel-fee confirmation dialog payload: image, title, message, options list, closeButtonText. Anchored on unique toString prefix TodCancelFeeDialogInfo(image=. |

