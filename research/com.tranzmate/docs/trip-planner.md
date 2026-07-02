# Trip planning

Moovit (`com.tranzmate`), confirmed against **version_code 1785** (versionName 5.194.0.1785). Classes are referenced by their **logical** name; the obfuscated name for this version is in [`maps/com.tranzmate/1785.json`](../../../maps/com.tranzmate/1785.json) and the regex anchors in [`signatures/com.tranzmate/signatures.yaml`](../../../signatures/com.tranzmate/signatures.yaml).

## Moovit Trip Planning subsystem (com.tranzmate 5.194.0.1785 / vc 1785)

### What it does
Trip planning turns an origin + destination (+ optional intermediate stop and a route
sequence) plus time/preferences into a set of itineraries, by POSTing a Thrift
`MVTripPlanRequest` to the server and streaming back sectioned results. There are two
generations of code living side-by-side:

- **Legacy UI** under `com.moovit.app.tripplanner` (`TripPlannerActivity` +
  `TripPlannerResultsFragment`) and the older `com.moovit.app.suggestedroutes.*`.
- **New Compose/Kotlin feature** under `com.moovit.feature.tripplan.*` (MVVM: `TripPlanActivity`
  → `TripPlanViewModel`, plus preferences / itineraries / schedule sub-screens) backed by
  repositories/data-sources under `com.moovit.data.tripplan.*` and use-cases under
  `com.moovit.domain.tripplan.*`.

### Key data model (all in `com.moovit.tripplanner`, class NAMES kept, fields renamed)
`TripPlannerLocations` (origin `a`, destination `b`, `TripPlannerRouteSequence c`),
`TripPlannerParams` (abstract, same triple), `TripPlannerTime` (Type = DEPART/ARRIVE/LAST + epoch),
`TripPlannerPersonalPrefs` (accessible boolean + max-walking-minutes short),
`TripPlannerSortType` (NO_CLIENT_SORTING/PRICE/DURATION/EMISSION/LEAST_WALKING/LEAST_TRANSFERS/
EARLIEST_DEPARTURE/EARLIEST_ARRIVAL — carries the client-side `Comparator<Itinerary>`),
`TripPlannerRouteType`, `TripPlannerAlgorithmType` (FILTER/PREFERRED), `TripPlannerTransportType`.
These are Parcelable + custom coder (`li4`/`lla` codec helpers); most have no in-class string
literals so they are hard to anchor and were largely not signed (low map value: names already kept).
The new feature layer re-models input as `TripPlanArgs` (nav arg) and `MutableTripPlanParams`
(builder that resolves to an immutable params object; throws the distinctive
"resolveTripPlanRoute called while origin/destination is null" / "MutableTripPlanParams.toImmutable
called while routeType is null").

### Network flow (the important part)
- **Trip plan search:** `DefaultFullTripPlansRepository.performFullTripPlanSearch` builds an
  `MVTripPlanRequest` (via helper `n8f.b(...)`) and POSTs to endpoint **`V4/TripPlanner2/Search`**
  (Thrift). The suspend lambda `DefaultFullTripPlansRepository$performFullTripPlanSearch$1` is where
  the request is assembled and the endpoint constant lives — best hook point for observing/modifying
  outgoing trip-plan searches. Results are streamed; the collector `com.moovit.data.tripplan.full.b`
  logs "Received trip plan: isUpdated=…, response=…" as each (partial) response arrives — hook here
  to observe/inspect incoming itinerary batches. Resolved config for the results list is
  `TripPlanConfig` (list of `TripPlanSection`: id/type/sortType/text/maxItemsToDisplay/branding).
- **Time suggestions / schedule:** `DefaultTripPlanScheduleRemoteDataSource`
  (`com.moovit.data.tripplan.schedule.remote.a`, uses a ktor `io.ktor.client`) calls endpoint
  **`V4/TripPlanner2/TripPlanTimeSuggestion`** and parses `MVTripPlanTimeSuggestionResponse`
  (method `fetchSchedule`). Other Thrift structs in `com.tranzmate.moovit.protocol.tripplanner`
  (kept names): `MVGetTripPlanInformationRequest`, `MVSingleTripPlanResponse`,
  `MVTripPlanSectionedResponse`, `MVCarpoolTripPlanRequest`, `MVTripPlanSuggestionRequest/Response`.

### ViewModels / controllers (Kotlin, renamed to short tokens; identity via leaked synthetic names)
- `TripPlanViewModel` = `com.moovit.feature.tripplan.c` (extends ViewModel base `f6g`). Nav args
  `trip_plan_args`/`trip_plan_uri`/`ui_input`; methods (from synthetics) `setOrigin`,
  `setDestination`, `setIntermediateLocation`, `addToFavorites(IfNeeded)`,
  `performGeocodingIfNeeded`, `performNormalization`, `resolveUiInputArgs`,
  `updateCurrentLocationIdNeeded`. Hook `setOrigin`/`setDestination` to observe user input; hook the
  uiState flow to observe planning state. Logs "Failed to add auto favorite".
- `TripPlanPreferencesViewModel` = `com.moovit.feature.tripplan.preferences.f` — persists prefs keys
  `trip_plan_widget_sort` / `trip_plan_widget_fit`; reads `com.moovit.data.tripplan.preferences.b`.
- `ItinerariesNoGroupingViewModel` = `com.moovit.feature.tripplan.nogroup.b` — renders itineraries
  for a `(ITINERARIES_REQUEST_ID_KEY, TRIP_PLAN_SECTION_ID_KEY)` pair.
- `TripPlanBridgeImpl` = `com.moovit.app.tripplanner.d` (implements bridge iface `d4f`) — bridges
  trip-plan results into `ItineraryActivity2` / `StepByStepActivity`, reads result extras
  `search_metro_id` / `search_result`, exposes feature gates (advanced time picker, compare-on-map,
  trip insights) and `setLatestItinerary`. NOTE: no in-class-unique string literal, so it is NOT
  signed here (would require anchoring on a rotated token) — reach it via its synthetics
  `TripPlanBridgeImpl$setLatestItinerary$1` etc.

### Persistence
- `DefaultLatestItineraryRepository` = `com.moovit.data.tripplan.latest.a` — remembers the last
  chosen itinerary (method `saveLatestItineraryId`; logs "Failed to save latest itinerary:
  itineraryId="). Backed by `DefaultLatestItineraryLocalDataSource`
  (`com.moovit.data.tripplan.latest.local.a`, DataStore keys `latest_itinerary_request_id` /
  `latest_itinerary_itinerary_id`).

### Good Frida/Xposed hook points
1. `DefaultFullTripPlansRepository$performFullTripPlanSearch$1` — intercept outgoing trip-plan
   searches (endpoint `V4/TripPlanner2/Search`, `MVTripPlanRequest`).
2. `DefaultFullTripPlansRepository`'s response collector (`…full.b`) — observe incoming itinerary
   responses ("Received trip plan").
3. `DefaultTripPlanScheduleRemoteDataSource` — time-suggestion / schedule network.
4. `TripPlanViewModel.setOrigin/setDestination` — capture/modify user O/D input.
5. `MutableTripPlanParams` (toImmutable/resolveTripPlanRoute) — inspect final params (routeType,
   time, prefs) just before request build.
6. `DefaultLatestItineraryRepository.saveLatestItineraryId` — observe itinerary selection.

### Anchoring notes
Obfuscation is R8-partial: package paths kept; Thrift `MV*` and Activity/Fragment/model names kept
but Kotlin managers/VMs/data-sources renamed to short tokens (a/b/c/d/f). All signatures anchor on
rotation-stable string literals reached by the class — server endpoint paths
(`V4/TripPlanner2/…`), DataStore/pref keys, nav-arg keys, Thrift toString prefixes, and unique
error/log messages — never on renamed tokens. Renamed Kotlin classes were identified from the
leaked synthetic/lambda class names (e.g. `…$performFullTripPlanSearch$1`, `…$setOrigin$1`,
`…$saveLatestItineraryId$1`) whose `this$0` field points at the real (renamed) outer class.
Methods/fields are renamed to tokens with no stable per-member anchor, so member entries are omitted
(class resolution is the value); logical method names above come from the synthetics.

## Classes identified

| Logical class | Renamed? | Confidence | Identity evidence |
| --- | --- | --- | --- |
| `DefaultFullTripPlansRepository$performFullTripPlanSearch$1` | no | high | Suspend lambda of DefaultFullTripPlansRepository.performFullTripPlanSearch; contains the trip-plan search server endpoint const-string "V4/TripPlanner2/Searc… |
| `DefaultTripPlanScheduleRemoteDataSource` | yes | high | Remote data source for trip-plan schedule/time suggestions: synthetic DefaultTripPlanScheduleRemoteDataSource$fetchSchedule$1 has this$0:Lcom/moovit/data/tri… |
| `DefaultFullTripPlansRepositoryReceiveTripPlanCollector` | yes | medium | Flow collector (implements kb5 = FlowCollector) belonging to DefaultFullTripPlansRepository.getFullTripPlan: logs const-string "Received trip plan: isUpdated… |
| `MVTripPlanRequest` | no | high | Thrift-generated wire struct for the trip-plan search request; field metadata const-strings tripPlanPref/timeUtc/timeType/routeTypes/fromLocation/toLocation/… |
| `TripPlanViewModel` | yes | high | Extends ViewModel base f6g; every TripPlanViewModel$* synthetic (setOrigin$1, setDestination$1, resolveUiInputArgs$2, addToFavorites$1, ...) has this$0:Lcom/… |
| `TripPlanPreferencesViewModel` | yes | high | Extends ViewModel base f6g; synthetics TripPlanPreferencesViewModel$uiState$2 / $special$$inlined$flatMapLatest$1 belong to it. Persists preference keys cons… |
| `ItinerariesNoGroupingViewModel` | yes | high | Extends ViewModel base f6g; synthetics ItinerariesNoGroupingViewModel$uiState$1/$2 belong to it. Reads a trip-plan section's itineraries by (ITINERARIES_REQU… |
| `MutableTripPlanParams` | yes | high | Mutable builder for the new-feature trip-plan params: contains its own distinctive error const-strings "MutableTripPlanParams.toImmutable called while routeT… |
| `DefaultLatestItineraryRepository` | yes | high | Synthetic DefaultLatestItineraryRepository$saveLatestItineraryId$1 belongs here; holds latest chosen ItineraryId (AtomicReference), delegates to DefaultLates… |
| `DefaultLatestItineraryLocalDataSource` | yes | high | Local (DataStore) persistence for the latest itinerary: preference-key const-strings "latest_itinerary_request_id" and "latest_itinerary_itinerary_id". Synth… |
| `TripPlannerActivity` | no | high | Abstract base Activity for the legacy trip planner: declares fragment tags trip_plan_locations/options/map/results/search_button_fragment_tag, extras extra_t… |
| `TripPlannerResultsFragment` | no | high | Legacy results fragment; holds SearchParams (searchId/locations/options) and a saved-instance key const-string "latestSearchParams" (appears twice, globally … |
| `TripPlanArgs` | no | high | Navigation/argument model for the new trip-plan feature (originLocation/destinationLocation/intermediate/...); data-class toString prefix const-string "TripP… |
| `TripPlanConfig` | no | high | Parcelable config describing how a resolved trip plan is laid out: holds a list of TripPlanSection. data-class toString prefix const-string "TripPlanConfig(s… |
| `TripPlanSection` | no | high | Parcelable section of a trip-plan result list (id/type/sortType/text/maxItemsToDisplay/collapseByGroupKey/branding). data-class toString prefix const-string … |

