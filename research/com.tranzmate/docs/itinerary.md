# Itinerary model & legs

Moovit (`com.tranzmate`), confirmed against **version_code 1785** (versionName 5.194.0.1785). Classes are referenced by their **logical** name; the obfuscated name for this version is in [`maps/com.tranzmate/1785.json`](../../../maps/com.tranzmate/1785.json) and the regex anchors in [`signatures/com.tranzmate/signatures.yaml`](../../../signatures/com.tranzmate/signatures.yaml).

## Itinerary model & legs — Moovit (com.tranzmate 5.194.0.1785 / vc 1785)

### What the subsystem is
An **itinerary** is Moovit's resolved trip-plan result. The domain model lives under
`com/moovit/itinerary/model` (class names are **kept**), the Thrift↔model translation
in the root `defpackage` (fully renamed), and the modern UI-model in
`com/moovit/app/itinerary2`.

Core model shape (`Itinerary`):
- `a: String` — itinerary id/guid
- `b: ItineraryMetadata` — metadata (see below)
- `c: List<Leg>` — the ordered legs (guaranteed non-empty; ctor throws `"legs may not be empty!"`)
- `d: Polylon` — lazily-built combined polyline (`U0()` unions every leg's `U0()`)
- `getStartTime()` = first leg's start, `getEndTime()` = last leg's end.

`ItineraryMetadata` is a 14-field Parcelable: `b:ServerId` (section id), `c:int` groupType
(0 NONE / 1 NO_GROUPING / 2 LINE_GROUPING / 3 STOP_GROUPING), `d` groupKey,
`e:CurrencyAmount` fare, `f/g/h/i:boolean` hasNext/hasPrev/relevantForRealtime/isAccessible,
`j:EmissionLevel`, `k` serverContext, `l` preferredId, `m` isCancelled, `n:List<ItineraryTag>`.

### The Leg model
`com.moovit.itinerary.model.leg.Leg` is the common **interface** (extends Parcelable) with:
`getType()I`, `getStartTime()`, `getEndTime()`, `getOrigin()`, `F1()` (= destination
LocationDescriptor), `U0()` (= Polyline shape), and `p1(xs7)` — a **visitor dispatch**
(each concrete leg calls one method on the `xs7` visitor, e.g. WalkLeg→`.G`, TransitLineLeg→`.z0`).
`Leg.getType()` codes observed: WalkLeg=1, TransitLineLeg=2, WaitToTransitLineLeg=3,
CarpoolLeg=7, PathwayWalkLeg=8, MultiTransitLinesLeg=9, BicycleRentalLeg=12 (others:
TaxiLeg/WaitToTaxiLeg/Bicycle/Car/Dockless*/Event/WaitToMultiTransitLines).

NOTE: these `getType()` codes are a **different namespace** from the Parcelable-codec
"type tag" registry built in `ItineraryProtocol`'s static block (`bkb` builder →
`kca a`), where each leg is registered as `(tag, LegClass, writer, reader)` with tags
1,2,3,4,5,7,8,9,10,11,12,13,14,15,16,18,19. The codec registry (field `w07.a`) is what
drives Parcel (de)serialization of a heterogeneous leg list; the per-class writer/reader
pairs are static fields on each leg (`WalkLeg.j`/`WalkLeg.k`, `TransitLineLeg.l`/`.m`, …).

### Serialization formats
Two wire forms:
1. **Parcelable** — every model/leg has a `CREATOR` plus static codec objects
   (`zc`/`ad`/`o0c`/`u8b`/`bdg`/`m9`…); `writeToParcel` delegates to `lla.u(parcel,this,codec)`.
2. **Thrift** — server type is `com.tranzmate.moovit.protocol.tripplanner.MVTripPlanItinerary`
   (+ `MVTripPlanLeg`, `MVLineLeg`, `MVWaitToLineLeg`, `MVBicycleRentalLeg`, …).

### Key flows
- **Decode (server → app):** `ItineraryProtocol.decodeItinerary` (`w07.d(String, r89, zp2,
  MVTripPlanItinerary, w89) : Itinerary`) builds `ItineraryMetadata` via `w07.e(...)` and maps
  `MVTripPlanItinerary.legs` → `List<Leg>` (per-leg builders `w07.m`=TransitLineLeg,
  `w07.q`=WaitToTransitLineLeg, `w07.h`=MultiTransitLinesLeg, `w07.p`=WaitToMultiTransitLinesLeg…).
  On failure it logs tag `"ItineraryProtocol"` and fires analytics `ITINERARY_LOAD_FAILED`.
  `w07.o(...)` decodes a whole `MVTripPlanSectionedResponse` into `TripPlanResult`
  (itineraries, banners, match-counts).
- **Encode (app → server):** `w07.u(Itinerary) : MVTripPlanItinerary` (used when the app
  re-sends an itinerary, e.g. navigation/share).
- **Bridge / enrich:** `ItineraryBridgeImpl` (renamed `com.moovit.app.itinerary2.d`,
  `decodeItinerary` suspend fn on a coroutine dispatcher) wraps `w07.H`+`w07.d`, then calls
  `ItineraryLegLocationResolver` (`f17.a(Itinerary)`) which walks the legs (via the `p1`
  visitor) and reverse-geocodes/fills each `LocationDescriptor`'s image on the `"IRGH"`
  background executor.
- **UI model:** `ItineraryViewModel` (com.moovit.app.itinerary2, kept) stores the current
  itinerary in a `SavedStateHandle` under key `"current_itinerary"` (and `"is_favorite"`),
  exposes `itineraryRequiredData`/`itineraryUiState` flows (`d()`/`e()`), and
  `f()`=save, `g(Itinerary)`=set, `h(int)`=load similar. Synthetic classes leak the method
  names (`ItineraryViewModel$saveItinerary$1`, `$setItinerary$1`, `$similarItinerary$1`,
  `$resolveItinerary$2`, `$loadSimilarItinerary$2`, `$checkTripInsightsAvailability$1`, …).

### Good Frida/Xposed hook points
- **`ItineraryProtocol.decodeItinerary` (`w07.d`)** — single choke point to observe/modify
  every itinerary parsed from the server (return value is the fully-built `Itinerary`).
- **`ItineraryProtocol.u`** — observe/modify itineraries serialized back to Thrift.
- **`Itinerary.<init>`** — fires on every itinerary instantiation (decode + parcel restore).
- **`Leg.getType` / `Leg.getStartTime` / `Leg.U0`** — per-leg classification and geometry.
- **`ItineraryViewModel.g(Itinerary)` / `.f()`** — UI-level "current itinerary" set/save.
- **`ItineraryLegLocationResolver.a` (`f17.a`)** / `.b` — post-decode location enrichment.

### Anchoring notes
Most leg model names are **kept**, so the highest-value mappings here are the *renamed*
converters (`ItineraryProtocol`=`w07`, `ItineraryLegLocationResolver`=`f17`) and the
per-member field/method tokens (all renamed to short tokens even inside kept classes; e.g.
`Itinerary` fields a/b/c/d and methods `U0`/`a`/`d`). Legs that share identical constructor
key-strings could not be string-disambiguated and were dropped: `WalkLeg`↔`BicycleLeg`
(identical `startTime/endTime/origin/destination/shape/instructions`), the four `Dockless*Leg`
(identical `…/info/serviceId`), `TaxiLeg`↔`WaitToTaxiLeg` (`providerId` shared), `CarLeg`,
`EventLeg` (`"event"` hits 58 files), `WaitToMultiTransitLinesLeg` (no strings). `WalkLeg`,
`ItineraryMetadata` and `ItineraryViewModel` are included with a **kept-name `.class`
anchor** (rotation-stable only while R8 keeps the name) because they carry no in-class-unique
string literal but are central to the subsystem.

## Classes identified

| Logical class | Renamed? | Confidence | Identity evidence |
| --- | --- | --- | --- |
| `Itinerary` | no | high | Parcelable holding id(String a), ItineraryMetadata(b), List<Leg>(c) and a lazily-built combined Polylon(d); ctor validates args and throws "legs may not be e… |
| `ItineraryMetadata` | no | medium | 14-field Parcelable itinerary metadata: ServerId section id(b), groupType int(c: NONE/NO_GROUPING/LINE_GROUPING/STOP_GROUPING), groupKey(d), CurrencyAmount f… |
| `Leg` | no | high | Common leg interface (extends Parcelable) implemented by all concrete legs; declares getType()I, getStartTime/getEndTime (Time), getOrigin/F1 (LocationDescri… |
| `WalkLeg` | no | medium | Implements Leg; getType()=1; fields startTime/endTime, origin/destination LocationDescriptor, Polyline shape, List<TurnInstruction> instructions, two TripPla… |
| `TransitLineLeg` | no | high | Implements Leg; getType()=2; holds DbEntityRef<TransitLine> lineRef, List<DbEntityRef<TransitStop>> stopRefs (unmodifiable, >=2 enforced), Polyline shape, Cu… |
| `WaitToTransitLineLeg` | no | high | Implements Leg; getType()=3; the 'wait for a transit line at a stop' leg. Ctor takes static+realtime start/end Times, lineRef, waitAt/departOn TransitStop re… |
| `MultiTransitLinesLeg` | no | high | Implements Leg; getType()=9; ctor takes a List of TransitLineLeg alternatives (unique key-string "lineLegs"), a primaryAlternativeIndex and a destination Sto… |
| `BicycleRentalLeg` | no | high | Implements Leg; getType()=12; docked bike-share leg. Ctor holds origin/destination bicycle stops + originNearbyBicycleStops/destinationNearbyBicycleStops lis… |
| `CarpoolLeg` | no | high | Implements Leg; getType()=7; carpool/ride-share leg. Ctor key-strings origin/destination/provider/carpoolType/image/driverInfo, with "driverInfo" unique to t… |
| `PathwayWalkLeg` | no | medium | Implements Leg; getType()=8; indoor pathway walk leg. Ctor takes startTime/endTime plus a stop reference; key-string "stopRef" is (verified) unique to this c… |
| `ItineraryProtocol` | yes | high | Abstract static converter between Thrift MVTripPlan* types and the itinerary model. Imports every Leg subtype and MV* tripplanner type; static block builds a… |
| `ItineraryLegLocationResolver` | yes | medium | Post-decode itinerary enricher constructed by ItineraryBridgeImpl (new f17(context)). a(Itinerary) iterates the legs via the Leg.p1 visitor; b(LocationDescri… |
| `ItineraryViewModel` | no | medium | AndroidViewModel-style UI model for the itinerary2 screen (super h60). Stores the current itinerary in a SavedStateHandle (jnc b) under keys "current_itinera… |

