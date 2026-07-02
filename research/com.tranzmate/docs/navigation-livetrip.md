# Live navigation & trip tracking

Moovit (`com.tranzmate`), confirmed against **version_code 1785** (versionName 5.194.0.1785). Classes are referenced by their **logical** name; the obfuscated name for this version is in [`maps/com.tranzmate/1785.json`](../../../maps/com.tranzmate/1785.json) and the regex anchors in [`signatures/com.tranzmate/signatures.yaml`](../../../signatures/com.tranzmate/signatures.yaml).

## Moovit live navigation & trip-tracking subsystem

Moovit ships **two parallel navigation trees**. The one exercised by the live turn-by-turn engine is the **legacy `com.moovit.navigation.*`** tree (this subsystem). A newer, mostly-dormant `com.moovit.core.navigation.model.*` tree carries name-twins (`NavigationArrivalState`, core `NavigationLeg`→`r1a`, core `NavigationGeofence`→`l1a`, `MVArrivalState`) — those twins share validation/toString strings with the legacy models, which is why legacy `ArrivalState` and legacy `NavigationLeg` could NOT be uniquely anchored and were deliberately dropped. Everything reported below is the legacy tree actually driven by `NavigationService`.

### Architecture / key flow
- **`NavigationService`** (`com.moovit.navigation.NavigationService`, extends `com.moovit.MoovitLooperService`, implements `mp3`) is the foreground service that owns all active navigations. It is command-driven via Intents whose actions are `com.moovit.navigation_service.action.{start,stop,stop_all,resume}_navigation` and `...location_permission_changed`. The dispatch entry point is the `declared-synchronized a(ILandroid/content/Intent;)V` method (logs `"Handle intent with action: %s"`). It keeps a `HashMap` of navigable-id → `NavigationState`, persists them to a store keyed `"NAVIGATION_STATE_STORE"` ("Storing the current navigable states"), and holds a `navigation_log_manager`. Extras: `com.moovit.navigation_service.navigable_extra`, `...navigable_id_extra`, `...start_foreground_extra`, `...close_navigable_reason_extra`.
- **`NavigationState`** wraps a `Navigable` + an "accurateNavigatorState" (`h3a`) + the last `NavigationProgressEvent`; it is Parcelable and serialized by an `om`/`pm` coder pair for the persistent store.
- **`Navigator`** (obfuscated `com.moovit.navigation.i`, abstract, extends `android.content.ContextWrapper`, log tag `"Navigator"`) is the base navigation state machine: it interpolates progress along a `NavigationPath`, generates `NavigationProgressEvent`s, computes `ArrivalState` transitions (analytics reasons `navigation_travelling/arriving_soon/arrival_imminent/disembark/arrived`, `arrive_to_dest`), schedules expiry alarms ("Navigable %s will expire at %s"), and fires arrival via `l(NavigationProgressEvent)` (logs `"onNavigableArrivedToDestination: navigableId=%s"`).
- **`LocationBasedNavigator`** (obfuscated `com.moovit.navigation.a`, final, extends `Navigator`/`i`, log tag `"LocationBasedNavigator"`) is the concrete GPS-driven navigator. It consumes `LocationRequest` + `ActivityRecognitionResult`, and its `p(Landroid/location/Location;)V` method is the per-fix update loop (logs `"onLocationUpdate: %s activity: %s"`, `"Current path changed from %s to %s"`, `"Current FG geofence for path %s: %s"`, emits `"Navigation deviated"` / return-to-path).

### Geofencing / arrival model
`NavigationPath` (ServerId + polyline + `GeofencePath` + `pathLengthMeters`/`pathTimeSeconds`) → `GeofencePath` → ordered `NavigationGeofence`s, each carrying `GeofenceMetadata` (arrivalState, distToDest, timeToDest, expirationFromEtaSeconds, nextStopIndex). Arrival is a 5-state ladder `TRAVELLING < ARRIVING_SOON < ARRIVAL_IMMINENT < DISEMBARK < ARRIVED` (legacy `ArrivalState` enum, `getFromBooleanStates`). Progress is broadcast as **`NavigationProgressEvent`** (action `com.moovit.navigation_event.action.navigation_progress`); lifecycle as `NavigationStartEvent` / `NavigationStopEvent` (carries `NavigationStopReason`) / `NavigationDeviationEvent` / `NavigableUpdateEvent`, all wrapped in `NavigationEvent` (`com.moovit.navigation_event.event_obj`). A `t1a` `ServiceConnection` fan-outs these action strings (why the raw action strings aren't class-unique for Start/Update events).

### Resume-trip
Independent of the live navigator: **`ResumeTripNotificationWorker`** (a `CoroutineWorker`) reads app-data parts (CONFIGURATION, HISTORY, LATEST_ITINERARY_CONTROLLER, plus `NAVIGATION_STATE_STORE`) and schedules an alarm; **`ResumeTripBroadcastReceiver`** fires on the alarm (`com.moovit.resumetrip.action.publish_notification`) and on dismissal (`...notification_dismissed`), building the "resume your trip" notification (`ResumeTripActivity` is the tap target). Actions: `com.moovit.resumetrip.action.publish_notification`, `...notification_dismissed`, `com.moovit.resumetrip.notification_clear`.

### Trip notifications (line-arrival alerts)
`TripNotification` (Parcelable data class: stopId/lineId/activationTime/expirationTime) is the model for the "notify me when this line comes" feature. Its `TripNotificationsEntryPointHelper` and `TripNotificationCancelViewModel` MAIN classes are fully obfuscated/inlined (only their `$1` lambda inner-classes survive on disk), so only the `TripNotification` model is anchorable.

### Serialization formats
Navigation models use Moovit's custom stream coders (`t3g`/`r3g` writer/reader pairs — legacy classes `c`/`d` for `NavigationLeg`, `e`/`f` for `NavigationPath`) and `xba`/`li4` for enums, NOT Parcel-only. The persisted `NAVIGATION_STATE_STORE` uses the `NavigationState` `om`/`pm` coder. Geofences are converted from Thrift `MVGeofence`/`MVShape` in the legacy helper class `g`.

### Best Frida / Xposed hook points
- **`NavigationService.a(ILandroid/content/Intent;)V`** — single choke point for every start/stop/resume command; hook to observe or inject navigation control.
- **`LocationBasedNavigator.p(Landroid/location/Location;)V`** — every GPS fix that drives navigation; hook to spoof/inspect location-based progress, deviation, and geofence advance (pairs well with `MockLocation`/`MockLocationsMode`).
- **`Navigator.l(Lcom/moovit/navigation/event/NavigationProgressEvent;)V`** — arrival-to-destination trigger; hook to detect/force "arrived".
- **`NavigationProgressEvent`** ctor / `NavigationStopEvent` — passive tap of live ETA / stops-to-dest / arrivalState without touching the navigators.
- **`ResumeTripBroadcastReceiver.onReceive`** and **`ResumeTripNotificationWorker`** — hook to observe or suppress resume-trip scheduling.

All obfuscated tokens (`i`, `a`, method names `a`/`l`/`p`, field names) rotate between builds; the reported anchors are rotation-stable const-strings only.

## Classes identified

| Logical class | Renamed? | Confidence | Identity evidence |
| --- | --- | --- | --- |
| `NavigationService` | no | high | Foreground navigation service (extends MoovitLooperService, implements mp3). Holds HashMap of navigable-id -> NavigationState, persists to 'NAVIGATION_STATE_… |
| `NavigationState` | no | high | Parcelable state holder wrapping a Navigable + accurate-navigator-state (h3a) + last NavigationProgressEvent; null-checks its ctor args with messages 'naviga… |
| `Navigator` | yes | high | Abstract navigation state machine (extends ContextWrapper), log tag 'Navigator'. Interpolates progress along NavigationPath, computes ArrivalState transition… |
| `LocationBasedNavigator` | yes | high | Concrete GPS-driven navigator (final, extends Navigator/i), log tag 'LocationBasedNavigator'. Consumes LocationRequest + ActivityRecognitionResult; per-fix l… |
| `NavigationProgressEvent` | no | high | Live-progress broadcast payload (action com.moovit.navigation_event.action.navigation_progress). Unique toString format 'NavigationProgressEvent[pathIndex=%d… |
| `NavigationStopEvent` | no | high | Navigation-stopped lifecycle event (action com.moovit.navigation_event.action.navigation_stop) carrying a NavigationStopReason; unique toString prefix 'Navig… |
| `NavigationDeviationEvent` | no | high | Off-route deviation event (action com.moovit.navigation_event.action.navigation_deviation) carrying legIndex + location; unique toString prefix 'NavigationDe… |
| `GeofenceMetadata` | no | high | Per-geofence arrival metadata (arrivalState, distToDest, timeToDest, expirationFromEtaSeconds, nextStopIndex); unique toString prefix 'GeofenceMetadata[arriv… |
| `NavigationGeofence` | no | high | Comparable geofence node (legIndex/pathIndex/inLegIndex + Geofence + GeofenceMetadata); guards cross-leg/cross-path comparison and has unique toString prefix… |
| `NavigationPath` | no | high | Navigation path model: ServerId + polyline + ShapeReliability + stopIds + GeofencePath + pathLengthMeters + pathTimeSeconds. Serialized by legacy stream code… |
| `ResumeTripNotificationWorker` | no | high | CoroutineWorker that reads app-data parts (CONFIGURATION, HISTORY, LATEST_ITINERARY_CONTROLLER, NAVIGATION_STATE_STORE) and schedules the resume-trip alarm/n… |
| `ResumeTripBroadcastReceiver` | no | high | BroadcastReceiver firing on the resume-trip alarm (com.moovit.resumetrip.action.publish_notification) and dismissal (...notification_dismissed); builds the r… |
| `TripNotification` | no | high | Parcelable data class for line-arrival alerts: stopId/lineId/activationTime/expirationTime; unique toString prefix 'TripNotification(stopId='. Its EntryPoint… |

