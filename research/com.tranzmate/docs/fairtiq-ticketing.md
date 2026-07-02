# Fairtiq check-in/out ticketing

Moovit (`com.tranzmate`), confirmed against **version_code 1785** (versionName 5.194.0.1785). Classes are referenced by their **logical** name; the obfuscated name for this version is in [`maps/com.tranzmate/1785.json`](../../../maps/com.tranzmate/1785.json) and the regex anchors in [`signatures/com.tranzmate/signatures.yaml`](../../../signatures/com.tranzmate/signatures.yaml).

## Fairtiq check-in/out ticketing subsystem

Moovit integrates the **FAIRTIQ SDK** (`com.fairtiq.sdk.api.*`) for GPS/BLE "be-in / be-out" open-loop transit ticketing: the user checks in at a station, the SDK tracks the journey via location, and either the user or the SDK's automatic *be-out* detection checks out. Moovit wraps this in two managers plus a Kotlin-Flow state machine and a small set of Parcelable models.

### Two-layer manager design
- **FairtiqManager** (`com.moovit.fairtiq.b`, singleton via companion `n`) is the **direct SDK wrapper** — the lowest layer that talks to the FAIRTIQ SDK. It owns the SDK client, the `User`, OIDC authentication (`authenticateWithOpenIdConnect` with a `SubjectToken`/`IdPHint`), check-in (`performCheckIn`), check-out (`performCheckOut`), be-out handling, and a merged state flow (`stateFlow`) built from five `MutableStateFlow`s (authenticator token availability, auth state, tracker state, be-out state) reduced by `mapState`. Log tag is `"FairtiqManager"`; it persists to SharedPreferences file **`FAIRTIQ_PREFERENCES"`**.
- **FairtiqTicketingManager** (`com.moovit.ticketing.fairtiq.d`, singleton via companion `m`) is the **app/ticketing-facing layer**. It registers the SDK-provided **FairtiqAuthenticator** onto FairtiqManager (`setAuthenticator()`), exposes a resolved ticketing-state flow, fetches discount info for the confirmation summary (`fetchDiscountInfo` → CONFIGURATION appdata + a payment-summary request), tracks the intro-completed flag, and holds the current `FairtiqAdditionalOptions` (class level + discount). Log tag `"FairtiqTicketingManager"`; SharedPreferences file **`FAIRTIQ_TICKETING_PREFERENCES"`** with boolean key `IS_INTRO_FINISHED`. Its authenticator's `provideAuthToken` reads a **Firebase** ID token (`iva.a().c.d()`), i.e. Moovit federates its Firebase identity into FAIRTIQ via OIDC.

### Auth flow
Firebase ID token → FairtiqAuthenticator.provideAuthToken (inner class of FairtiqTicketingManager) → SDK `UnauthorizedContext.authenticateWithOpenIdConnect(SubjectToken(idToken, ID_TOKEN, IdPHint(idpHint)), …)` in FairtiqManager. Availability is exposed as a `Flow<Boolean>` (`fairtiqAuthenticator$1$availability`).

### Check-in / check-out / be-out
- **Check-in:** `FairtiqManager.performCheckIn(ClassLevel, String, String)` (obf method `f`) launches `FairtiqManager$performCheckIn$1`. Class level + a required station/leg id.
- **Check-out (user):** `FairtiqManager.performCheckOut()` (obf `g`) and, at the ticketing layer, `FairtiqTicketingManager.performCheckOut` (obf method `d`, which calls the SDK checkout `this.i.g()` then resets options to `FairtiqAdditionalOptions(SECOND, null)`).
- **Be-out (automatic):** a `BeOutServiceListener` (anonymous `tt4`) handles `BeOutTransition` → updates a be-out `MutableStateFlow` (`NotPlanned` vs `Planned(at, abort)`), and for `Performed`/`Scheduled` transitions posts a local notification on `MoovitNotificationChannel.RIDE_SHARING` (string tag `"Fairtiq"`, string resources `fairtiq_gps_be_out_*`). Push-driven be-out arrives via FCM: `FairtiqManager.handleNotification(RemoteMessage)` (obf `e`) parses a `BeOutNotificationPayload` (returns false if the FCM message isn't a be-out payload). `closeElsewhereTracker()` (obf `c`) tears down a tracker that's running on another device/session ("tracking elsewhere").

### Journey UI + state machine
- **FairtiqJourneyViewModel** (kept) is the journey screen's state machine. It combines FairtiqTicketingManager's resolved state (`FairtiqTicketingState`), the saved-state `chosenStationId`, additional-options flow, payment-account flow, and CONFIGURATION into a `JourneyUiState` via the method-reference lambda **`calculateUiState(FairtiqTicketingState, String, FairtiqAdditionalOptions, PaymentAccount, Configuration) → JourneyUiState`**. It listens for payment-account updates through a `BroadcastReceiver` (`FairtiqJourneyViewModel$paymentAccountUpdatesReceiver$1`).
- **FairtiqAdditionalOptionsViewModel** (kept) backs the class-level / discount selection screen; saved-state key `selectedOptions`, log tag `FairtiqAdditionalOptionsViewModel`, `setDiscountInfo: discountInfo=` log.

### Models / serialization (all Parcelable data classes, kept names)
- **FairtiqTicket** {fareTypeDisplayName:String?, classLevel:FairtiqClassLevel?, token:FairtiqTicketToken}
- **FairtiqStation** {id:String, name:String}
- **FairtiqTracker** {checkinStationName:String?, startTime:Long?, ticket:FairtiqTicket?, isOutOfCommunity:boolean} — the active-journey snapshot.
- **FairtiqAdditionalOptions** {classLevel:FairtiqClassLevel, discountInfo:DiscountInfo?}
- **FairtiqClassLevel** enum {FIRST, SECOND} — Parcelable-by-name.
- **FairtiqReason** — abstract, `Comparable`, sealed base for "why check-in is unavailable/blocked": subclasses `LocationServiceNotAvailable`, `LocationServiceInsufficientAccuracyPermission`, `TrackingElsewhere`, `UnableToDisplayTicket`, `AirplaneModeEnabled`, `ServerFailure`, `Connectivity`, `NoNearbyStation`, `LoadingStations`, `GeneralReason` (each carries an int priority + a `FairtiqReasonResolution`). Resolutions: `LocationNotAvailableResolution`, `TrackingElsewhereResolution`, `UpgradeVersionResolution`.
- **FairtiqTicketToken.FairtiqTicketBarcodeToken** {data:String, format:BarcodeMoovit BarcodeFormat} — the scannable proof-of-ticket.

### Good Frida/Xposed hook points
- **FairtiqManager.performCheckIn** (descriptor `(Lcom/fairtiq/sdk/api/domains/user/ClassLevel;Ljava/lang/String;Ljava/lang/String;)V`) — observe/spoof check-in station + class level.
- **FairtiqManager.performCheckOut** `()V` — force/trace checkout.
- **FairtiqManager.handleNotification** `(RemoteMessage)Z` — intercept be-out FCM handling; return value gates whether Moovit treats the push as a be-out.
- **FairtiqManager.closeElsewhereTracker** `()V` — trace "tracking elsewhere" teardown.
- **FairtiqTicketingManager.setAdditionalOptions** `(FairtiqAdditionalOptions)V` — single funnel for every class-level/discount change (logs `setAdditionalOptions: classLevel=…`).
- **FairtiqTicketingManager.performCheckOut** `()V` — app-level checkout entry that also resets options.
- **FairtiqJourneyViewModel.calculateUiState** — reduce point where all inputs converge into the journey UI state.

### Obfuscation notes
The two managers are renamed to single letters (`b`, `d`) but their coroutine/broadcast **inner classes leak the original names** (`FairtiqManager$performCheckIn$1`, `FairtiqTicketingManager$performCheckOut$1`, `…$paymentAccountUpdatesReceiver$1`, `…$stateFlow$1`) — those references are the rotation-stable identity + method-anchor evidence. Managers were anchored on their SharedPreferences file-name strings; models/ViewModels retain kept names and were anchored on `toString()` / method-reference / log literals. The SDK-state sealed classes (FairtiqState/FairtiqAuthState/FairtiqBeOutState/FairtiqAuthenticator, referenced in the `mapState(...)` descriptor string) live under `defpackage` with fully rotated names and no in-class string anchors, so they were left out.

## Classes identified

| Logical class | Renamed? | Confidence | Identity evidence |
| --- | --- | --- | --- |
| `FairtiqManager` | yes | high | Direct FAIRTIQ SDK wrapper: imports com.fairtiq.sdk.api.* (ClassLevel, SubjectToken, User, UnauthorizedContext, BeOut*); log tag "FairtiqManager"; SharedPref… |
| `FairtiqTicketingManager` | yes | high | App/ticketing-facing manager over FairtiqManager: registers the authenticator via setAuthenticator() (log tag "FairtiqManager") and holds com.moovit.fairtiq.… |
| `FairtiqJourneyViewModel` | no | high | Kept class name; AndroidViewModel (super h60). Combines FairtiqTicketingManager state, saved-state chosenStationId, additional-options flow, payment-account … |
| `FairtiqAdditionalOptionsViewModel` | no | high | Kept class name; AndroidViewModel (super h60) for the class-level/discount selection screen. Saved-state key "selectedOptions", log tag "FairtiqAdditionalOpt… |
| `FairtiqTicket` | no | high | Kept-name Parcelable data class {fareTypeDisplayName:String?, classLevel:FairtiqClassLevel?, token:FairtiqTicketToken}; toString literal "FairtiqTicket(fareT… |
| `FairtiqStation` | no | high | Kept-name Parcelable data class {id:String, name:String}; toString literal "FairtiqStation(id=" is unique. |
| `FairtiqTracker` | no | high | Kept-name Parcelable data class = active-journey snapshot {checkinStationName:String?, startTime:Long?, ticket:FairtiqTicket?, isOutOfCommunity:boolean}; toS… |
| `FairtiqAdditionalOptions` | no | high | Kept-name Parcelable data class {classLevel:FairtiqClassLevel, discountInfo:DiscountInfo?}; the options carried by FairtiqTicketingManager.setAdditionalOptio… |
| `FairtiqClassLevel` | no | high | Kept-name Parcelable enum {FIRST, SECOND} (fare class level), Parcelable-by-name (writeToParcel writes name()). Anchored on the .class enum line which carrie… |
| `FairtiqReason` | no | high | Kept-name abstract sealed base (implements Comparable<FairtiqReason>, Parcelable) for reasons a check-in is blocked/unavailable; fields {int priority, Fairti… |
| `FairtiqTicketBarcodeToken` | no | high | Kept-name nested Parcelable data class implementing the FairtiqTicketToken sealed interface; the scannable proof-of-ticket {data:String, format:BarcodeFormat… |

