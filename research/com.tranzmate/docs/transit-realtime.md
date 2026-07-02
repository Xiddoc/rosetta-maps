# Transit entities & real-time arrivals

Moovit (`com.tranzmate`), confirmed against **version_code 1785** (versionName 5.194.0.1785). Classes are referenced by their **logical** name; the obfuscated name for this version is in [`maps/com.tranzmate/1785.json`](../../../maps/com.tranzmate/1785.json) and the regex anchors in [`signatures/com.tranzmate/signatures.yaml`](../../../signatures/com.tranzmate/signatures.yaml).

## Transit entities & real-time arrivals (Moovit `com.tranzmate` 5.194.0.1785 / vc 1785)

This subsystem is the transit **data model**, the **metro-entity loading pipeline** that materialises it, the **real-time stop-arrivals** feature, and **service alerts**.

### 1. Core transit data model — `com.moovit.transit`
Immutable `Parcelable` value objects, most with kept class names but obfuscated field/method tokens. They also implement a Moovit-internal marker interface `Lu46;` (an "entity ref"-able type; obfuscated) and use a custom coder pair (obfuscated `Lrda;`/`Lsda;` = reader/writer, and per-class package coders like `com.moovit.transit.e`) for the app's own binary/pref serialization on top of Parcelable.
- **TransitStop** — the stop entity: `id`, `name`, `location` (LocationDescriptor), `mainTransitTypeRef`, `lineRefs`, `nearByLinesRefs`, `platforms`, `pathways`, `amenities`, `mapImages`. Central node for arrivals.
- **TransitLine** / **TransitLineGroup** — a line belongs to a group; group carries `agencyRef`, `lineNumber`, `imageRefSet`, `innerImageIds` and the member `lines`. Validation guards ("Transit line group may not be null", "Line id … does not exist in attached group id …") are the stable anchors.
- **TransitPattern** — ordered `stopRefSequence` + `stopNames` (must be equal length — the anchor). The stop-sequence backbone used by StopArrivals to lay out the pattern.
- **TransitFrequency** — headway model: `windows` + `intervals` (equal-length invariant is the anchor).
- **LocationDescriptor** — a geocoded location/place ref (`type`, `id`, coordinates); throws "Unable to set null coordinates when location type is …". Used pervasively as the stop/place locator.
- **TripId** — `serverId`-based trip identity (`TripId[…]` toString).
- (TransitAgency, TransitType, Schedule are present and relevant but have **no rotation-stable, class-unique anchor** — their strings are generic field-name/serialization keys shared with Thrift `MV*` structs — so they are intentionally omitted rather than anchored on a fragile field letter.)

### 2. Metro-entity loading pipeline — `com.moovit.metroentities`
The model above is fetched/resolved here.
- **MetroEntityType** (enum) — the catalog of loadable entity kinds: TRANSIT_STOP, TRANSIT_LINE, TRANSIT_LINE_GROUP, TRANSIT_PATTERN, TRANSIT_FREQUENCIES, SHAPE, SHAPE_SEGMENT, BICYCLE_STOP. Drives request planning; `TRANSIT_FREQUENCIES` (plural) distinguishes it from the legacy GTFS `com.moovit.data.gtfs.metroentitiy.MetroEntityType`.
- **MetroEntitiesRepository** (obfuscated to `com.moovit.metroentities.c`, abstract; the readable name leaks via inner classes `MetroEntitiesRepository$submit*`) — the loader. Key static methods:
  - `c(RequestContext, metroId, …)` → single-page fetch, logs `"fetch: metroId="`.
  - `d(Context, metroId, …, HashSetHashMap, HashSetHashMap)` → the multi-pass **resolver loop** that resolves entity refs across pages (`"initiator=%s, performing resolving pass:%s"`, `"initiator=%s, remaining:%s"`, "Unable to resolve all metro entities: …"). Reads config via `CONFIGURATION`.
  Wire/pref keys seen: `metro_id`, `metro_entities`, `page_size`, `pages_count`, `ids_count`, `max_parallelism`.

### 3. Real-time stop arrivals — `com.moovit.app.stoparrivals`
- **StopArrivalsViewModel** (obfuscated to `com.moovit.app.stoparrivals.d`, super `Lh60;` = base ViewModel; name leaks via `StopArrivalsViewModel$refresh$2`, `$fetchLineArrivals$1`, `$fetchPatternStops$1`, `$refreshArrivals$1`, `$fetchSyncEntities$1`) — orchestrates a refresh that fans out coroutine deferreds (supportedAgencies, conf, serviceAlerts, lineArrivals, syncEntities) and exposes StateFlows keyed `stopArrivals` / `selectedArrivals` (SavedStateHandle keys — the stable anchor). The refresh body is static method `a(d, ServerId, List, Continuation)`; it assembles `CONFIGURATION` + `METRO_CONTEXT` + `requestContext` then produces the arrival list.
- **StopArrival** — one real-time arrival row: `line`, `arrival` (time), `tripIndex`, `serviceAlert`, `isVehicleSupported`, `isAgencyVomSupported`.
- **StopArrivalServiceAlert** — per-arrival alert badge: `status` + `alertId`.
- **TripsUpdateResult** — a realtime tick for a stop: `stop`, `stopArrivals`, `vehicleIdToPosition` (live vehicle positions), `shapeIdToSegments`.
- **TripsSelectionUpdate** — UI trip-selection delta: `adapterPosition`, `prevArrival`, `currArrival`, `analyticKey`.

### 4. Service alerts — `com.moovit.servicealerts`
- **StopServiceAlertDigest** / **LineServiceAlertDigest** — compact per-stop / per-line alert summaries: `affectedStop`/`affectedLine` (kept `ServiceAlertAffectedStop`/`ServiceAlertAffectedLine`), a `status` (`ServiceStatus` → `ServiceStatusCategory`: CRITICAL/MODIFIED/INFO/REGULAR/UNKNOWN), and `alertIds` (guarded "alertIds may not be empty!"). Anchored on the declared field of the kept affected-entity type (name letter left as `[a-z]` so the anchor tolerates field rotation). (ServiceAlert, ServiceStatus, and the affected-entity classes are present but share their field-name strings with the Thrift `MV*Alert*` structs, so they lack a class-unique string anchor and are omitted.)

### Good Frida/Xposed hook points
- **MetroEntitiesRepository** static `c` (fetch, `"fetch: metroId="`) and static `d` (resolve pass, `"initiator=%s, performing resolving pass:%s"`) — observe/inject the raw transit entities (stops/lines/patterns/frequencies) as they load; the choke point for the whole model.
- **StopArrivalsViewModel** static `a` (anchor `"requestContext"`) — hook the return to inspect or synthesize the live `StopArrival` list for a stop.
- **StopArrival** / **TripsUpdateResult** constructors — read live arrival times and `vehicleIdToPosition` per tick.
- **StopServiceAlertDigest** / **LineServiceAlertDigest** constructors — observe which alerts/status apply to a given stop or line.

### Serialization notes
All model classes are Android `Parcelable` AND carry an app-specific coder (static `Lrda;`/`Lsda;` reader/writer fields, plus `u46`-based entity-ref indirection) for the metro-entities binary format that MetroEntitiesRepository reads. Enum ordinals are used on the wire, so anchor on the string members, not order.

## Classes identified

| Logical class | Renamed? | Confidence | Identity evidence |
| --- | --- | --- | --- |
| `TransitStop` | no | high | Kept class name; final Parcelable implementing Lu46;/Lt46;; toString 'TransitStop{id=' with fields id,name,location,mainTransitTypeRef,lineRefs,nearByLinesRe… |
| `TransitLine` | no | high | Kept name; Parcelable implementing Lu46;; guard string 'Transit line group may not be null' and 'destination' field — a line belonging to a TransitLineGroup. |
| `TransitLineGroup` | no | high | Kept final Parcelable implementing Lu46;; fields agencyRef,lineNumber,imageRefSet,innerImageIds,lines and integrity guard 'Line id … does not exist in attach… |
| `TransitPattern` | no | high | Kept Parcelable implementing Lu46;; fields stopRefSequence + stopNames with equal-length invariant 'stop sequence & names must be with the same size' — the o… |
| `TransitFrequency` | no | high | Kept class; headway model with 'windows' + 'intervals' lists, toString 'TransitFrequency … frequency id=', equal-length invariant 'windows & intervals must b… |
| `LocationDescriptor` | no | high | Kept Parcelable; nested LocationType/SourceType enums; toString 'LocationDescriptor[type=…]'; guard 'Unable to set null coordinates when location type is …' … |
| `TripId` | no | high | Kept class; serverId-based trip identity, toString 'TripId[…]'. |
| `StopArrival` | no | high | Kept final Parcelable; data-class toString 'StopArrival(line=…, arrival=…, tripIndex=…, serviceAlert=…, isVehicleSupported=…, isAgencyVomSupported=…)' — one … |
| `StopArrivalServiceAlert` | no | high | Kept final Parcelable; data-class toString 'StopArrivalServiceAlert(status=…, alertId=…)' — the alert badge attached to a StopArrival. |
| `TripsUpdateResult` | no | high | Kept final Parcelable; data-class toString 'TripsUpdateResult(stop=…, stopArrivals=…, vehicleIdToPosition=…, shapeIdToSegments=…)' — a realtime update tick (… |
| `TripsSelectionUpdate` | no | high | Kept final Parcelable; data-class toString 'TripsSelectionUpdate(adapterPosition=…, prevArrival=…, currArrival=…, analyticKey=…)' — UI trip-selection delta i… |
| `StopArrivalsViewModel` | yes | high | Outer class renamed to 'd' (super Lh60; base ViewModel) but leaks via inner classes StopArrivalsViewModel$refresh$2, $fetchLineArrivals$1, $fetchPatternStops… |
| `MetroEntitiesRepository` | yes | high | Abstract outer class renamed to 'c'; leaks via inner classes MetroEntitiesRepository$submitSinglePageRequest$1 etc. (reference Lcom/moovit/metroentities/c;) … |
| `MetroEntityType` | no | high | Kept enum listing loadable entity kinds TRANSIT_STOP/TRANSIT_LINE/TRANSIT_LINE_GROUP/TRANSIT_PATTERN/TRANSIT_FREQUENCIES/SHAPE/SHAPE_SEGMENT/BICYCLE_STOP plu… |
| `StopServiceAlertDigest` | no | high | Kept Parcelable; holds a kept ServiceAlertAffectedStop + ServiceStatus + alertIds ('alertIds may not be empty!'). Anchored on the declared field of type Serv… |
| `LineServiceAlertDigest` | no | high | Kept Parcelable; holds a kept ServiceAlertAffectedLine + ServiceStatus + alertIds ('alertIds may not be empty!'). Anchored on the declared field of type Serv… |

