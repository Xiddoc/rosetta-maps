# Home & dashboard suggestions

Moovit (`com.tranzmate`), confirmed against **version_code 1785** (versionName 5.194.0.1785). Classes are referenced by their **logical** name; the obfuscated name for this version is in [`maps/com.tranzmate/1785.json`](../../../maps/com.tranzmate/1785.json) and the regex anchors in [`signatures/com.tranzmate/signatures.yaml`](../../../signatures/com.tranzmate/signatures.yaml).

## Moovit Home & Dashboard Suggestions subsystem

The home screen is `com.moovit.app.home.HomeActivity` (kept), a tabbed shell whose tabs are the `HomeTab` enum (DASHBOARD, NEARBY, LINES, EXPLORE, DASHBOARD_MAP, TRIP_PLANNER, CHAT_BOT, UNIFIED_WALLET, FAIRTIQ, …). `HomeTabUi` (kept enum) wraps each tab with its analytics event (`dashboard_clicked`, `map_view_clicked`, `station_tab_tap`, …). The "default tab" is rendered from `DefaultTabViewModel` computing a `DefaultTabUiState` from a list of `DashboardSection`.

### Dashboard sections
`DashboardSection` (kept enum) enumerates the section kinds shown on the dashboard: NAVIGABLE, TAXI, TOPUP, COMMUNITY, FAVORITE_LOCATIONS, FAVORITE_STATIONS, ITINERARY_HISTORY, LOCATION_SERVICES_ALERT, PROMOTION, WEB_PAGES, MOT. Concrete section views include `LocationServicesStateSection` (the "location_services_bar" alert row that reacts to GPS/permission state, logging "Change state: from=%s, to=%s"), `PackageSection` (subscription-package promo card, keyed on pref `first_time_section_impression_timestamp`, firing `package_section_impression`/`package_section_clicked`), `IntercitySection` and `ContentCardPromotionSection` (Braze-style content cards; no stable string anchor, omitted). The favorite Home/Work rows are `HomeFavoriteItemFragment` (`fav_home_clicked`, `home_favorite`) and `WorkFavoriteItemFragment` (`fav_work_clicked`, `work_favorite`), both in the `dashboard_favorites_section`.

### Suggestion engine (the core of this subsystem)
The suggestions carousel is driven by `SuggestionsSectionFragment` (kept) + `SuggestionsSectionViewModel` (kept, on-disk name preserved but it has **no globally-unique single-line string anchor** — its only distinctive literals `latest_itinerary_controller_service` and `SMART_COMPONENT_INLINE_BANNER` are shared with many classes, so it is intentionally omitted from the signatures rather than anchored shakily). The VM registers a `dda` observer over an `UpdateType` (REFRESH / AD_LOADED / AD_LOAD_FAILED) flow; REFRESH triggers `loadAllCards`, AD_LOADED/AD_LOAD_FAILED toggle the auto-swipe gate. `SuggestionsSectionFragment.stopAutoSwipe()` stops the timed auto-advance of the pager.

Cards come from a set of **suggestion-card providers**. There are two provider shapes:
- **`ywd` providers** that synchronously expose a card descriptor `zwd(type:String, …)` and asynchronously `loadCards`: `LatestItinerarySuggestionCardProvider` (type `suggestion_latest_route`), `FrequentLinesCardsProvider` (`suggestion_frequent_lines`), `TripNotificationsSuggestionCardProvider` (`suggestion_trip_notifications`).
- **`v17` providers** (and the abstract `FavoriteSuggestionCardsProvider` base, letter `c`, subclassed by Custom/Home/Work): `FavoriteRouteSuggestionCardsProvider` (`suggestion_favorite_route`), `RecentSearchSuggestionCardsProvider` (`suggestion_recent_trip` / `suggestion_recent_trip_matched`), `ReturnTripSuggestionCardsProvider` (`suggestion_return_trip`), `CustomFavoriteSuggestionCardsProvider` (`suggestion_custom_favorite`), `HomeSuggestionCardsProvider` (`suggestion_home`), `WorkSuggestionCardsProvider` (`suggestion_work`), `FavoriteStopSuggestionCardsProvider` (`suggestion_favorite_station`), `NearbyStopSuggestionCardProvider` (`suggestion_nearby_station`).

**Anchoring note / dropped providers:** every provider’s type-key string leaks into its sibling `<Provider>$loadCards$2` coroutine class (a separate .smali file, sometimes also into `zwd` or the matching compact Fragment), so the type-key is only globally-unique for the four providers whose `loadCards` lives in the shared base (`a`/`d`/`j` extend base `c`) or that carry a second unique literal (`h` via `suggestion_recent_trip_matched`, `notifications/b` via the `TripNotificationsSuggestionCard` log tag). The providers `FavoriteRouteSuggestionCardsProvider` (b), `LatestItinerarySuggestionCardProvider` (g), `ReturnTripSuggestionCardsProvider` (i), `FavoriteStopSuggestionCardsProvider` (station/a), `NearbyStopSuggestionCardProvider` (station/b) and `FrequentLinesCardsProvider` (line/a) are **real and identified** but have no single-line rotation-stable anchor unique to the class file, so they are documented here but omitted from the verified signatures.

### Card fragments / compact cards
Each card type has an expanded fragment and often a "compact" card. Notable logic holders: `AdSuggestionFragment` (`suggestions_data_type_ad`) + `AdSuggestionViewModel` (letter `c`; log tag `AdSuggestionViewModel`, `loadAdWithTimeOut` with a timeout race), `StopSuggestionFragment` (`suggestions_data_type_station`, anchor leaks so omitted), `LatestItineraryCompactCardViewModel` (holds a required `itinerary`, subscribes to realtime), `TripNotificationCompactCardViewModel` (holds required `line`+`notification`, fetches transit-line arrivals, can cancel the notification).

### Homepage2 (map-centric home)
`Homepage2Fragment` + `Homepage2ViewModel` render the newer map-first home with a bottom sheet of compact cards; `HomeChipsFragment`/`HomeChipsViewModel` render the favorite-location chips; `TransitStopBottomSheetDialog`/`TransitStopBottomSheetViewModel` show a tapped stop’s arrivals. These Kotlin VMs/fragments carry only view-binding tags or common config keys (`CONFIGURATION`, `METRO_CONTEXT`) that are not globally unique, so they are described but not signatured.

### Hook points (Frida/Xposed)
- **Force / observe suggestion refresh:** hook `SuggestionsSectionViewModel.loadAllCards` (name preserved) or feed `UpdateType.REFRESH` into its observer.
- **Intercept produced cards per source:** hook the individual providers’ `loadCards` — e.g. `HomeSuggestionCardsProvider`, `WorkSuggestionCardsProvider`, `CustomFavoriteSuggestionCardsProvider`, `RecentSearchSuggestionCardsProvider`, `TripNotificationsSuggestionCardProvider`. Their card type key is the `suggestion_*` string.
- **Stop the auto-swipe carousel:** `SuggestionsSectionFragment.stopAutoSwipe()`.
- **Ad-card timing:** `AdSuggestionViewModel.loadAdWithTimeOut` (letter class `ads.c`).
- **Dashboard section gating:** enumerate/patch via `DashboardSection` and `LocationServicesStateSection`/`PackageSection` view classes.
- **Home tab selection & analytics:** `HomeActivity` (`extra_tab`/`extra_tab_position` intent extras) and `HomeTabUi`.

### Serialization / formats
No custom on-disk format here; cards are in-memory `zwd` descriptors. Persistence is via SharedPreferences keys (e.g. `PackageSection`’s `first_time_section_impression_timestamp`, `had_subscription`). Server data arrives through the app’s Thrift/`MV*` request layer (metro-entities, transit-stop arrivals) invoked from the ViewModels.

## Classes identified

| Logical class | Renamed? | Confidence | Identity evidence |
| --- | --- | --- | --- |
| `HomeActivity` | no | high | On-disk name kept: `.class public Lcom/moovit/app/home/HomeActivity;` extending MoovitAppActivity. Reads intent extras `extra_tab`/`extra_tab_position` to se… |
| `HomeTabUi` | no | high | Kept enum `.class public final enum Lcom/moovit/app/home/tab/HomeTabUi;`. Each tab constant carries its analytics event: `dashboard_clicked`, `map_view_click… |
| `DashboardSection` | no | high | Kept enum `.class public final enum Lcom/moovit/app/home/dashboard/DashboardSection;` whose <clinit> defines the dashboard section kinds: NAVIGABLE, TAXI, TO… |
| `LocationServicesStateSection` | no | high | Kept name; log tag `LocationServicesStateSection` + `Change state: from=%s, to=%s`; renders the `location_services_bar` dashboard alert row reacting to locat… |
| `PackageSection` | no | high | Kept name `.class public final Lcom/moovit/app/home/dashboard/PackageSection;`; subscription-package promo dashboard section persisting pref `first_time_sect… |
| `HomeFavoriteItemFragment` | no | high | Kept name; dashboard favorites row for the Home location — analytics `fav_home_clicked`, `edit_home_clicked`, `remove_home_clicked` in `dashboard_favorites_s… |
| `WorkFavoriteItemFragment` | no | high | Kept name; dashboard favorites row for the Work location — analytics `fav_work_clicked`, `edit_work_clicked`, `remove_work_clicked` in `dashboard_favorites_s… |
| `SuggestionsSectionFragment` | no | high | Kept name `.class public final Lcom/moovit/app/home/dashboard/suggestions/SuggestionsSectionFragment;`; hosts the suggestions ViewPager+indicator, references… |
| `AdSuggestionFragment` | no | high | Kept name; the ad card in the suggestions carousel (`suggestions_data_type_ad`), log tag `AdSuggestionFragment`. |
| `AdSuggestionViewModel` | yes | high | Renamed to letter `c` under the ads package. Its own log tag is `AdSuggestionViewModel`; drives ad loading with a timeout race, logging `loadAdWithTimeOut: a… |
| `CustomFavoriteSuggestionCardsProvider` | yes | high | Renamed to letter `a`; extends the abstract FavoriteSuggestionCardsProvider base (letter `c`). Card type key `suggestion_custom_favorite`; synthetic CustomFa… |
| `HomeSuggestionCardsProvider` | yes | high | Renamed to letter `d`; extends FavoriteSuggestionCardsProvider base `c`. Card type key `suggestion_home`; synthetic HomeSuggestionCardsProvider$getFavoriteLo… |
| `WorkSuggestionCardsProvider` | yes | high | Renamed to letter `j`; extends FavoriteSuggestionCardsProvider base `c`. Card type key `suggestion_work`; synthetic WorkSuggestionCardsProvider$getFavoriteLo… |
| `RecentSearchSuggestionCardsProvider` | yes | high | Renamed to letter `h`; extends provider base v17. Two card type keys: `suggestion_recent_trip` and `suggestion_recent_trip_matched` (the latter is globally u… |
| `TripNotificationsSuggestionCardProvider` | yes | high | Renamed to letter `b`; implements the ywd provider interface and builds a zwd descriptor with type `suggestion_trip_notifications`. Its log tag `TripNotifica… |
| `LatestItineraryCompactCardViewModel` | no | high | Kept name `.class public final Lcom/moovit/app/home/dashboard/suggestions/itinerary/LatestItineraryCompactCardViewModel;` extending AndroidViewModel h60. Req… |
| `TripNotificationCompactCardViewModel` | no | high | Kept name extending AndroidViewModel h60. Requires `line` and `notification` (`Line is required.` / `Notification is required.`), fetches transit-line arriva… |

