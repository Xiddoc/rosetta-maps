# Instagram Map / Friend Map — live location sharing

The Friend Map lets you share live location with chosen friends and see theirs
on a map, with place pins and presence clusters. Data/API/repository classes
under `com.instagram.friendmap.data.*` keep real names; the map **Fragment**
layer is renamed into `X/` but each class preserves its name in a
`__redex_internal_original_name` field (e.g. `FriendMapFragment → X.T0K`,
`MapLocationManager → X.ju1`). GraphQL `xdt_*` doc names are the strongest
anchors and are captured in the map + `signatures.yaml`.

## Map screen & location collection

- **`FriendMapFragment`** (renamed `X.T0K`, dex classes15) is the map host: a
  `ViewPager2`-based fragment overlaying a native map with place pins, friend
  presence clusters, and a like-animation overlay. It holds a
  `FriendMapLaunchConfig` and tags its sub-controllers `mapViewController`,
  `placesOverlayController`, `mapCoordinator`, `mapNavigator`,
  `presenceHScrollPager`. Module name `"friend_map"` / `"ig_friendmap"`; cluster
  ids `friend_map_saved_place_cluster`, `friend_map_unified_cluster`.
- **`MapLocationManager`** (renamed `X.ju1`, dex classes17) is the location
  collector/publisher. A single-shot path gates on
  `LocationPluginImpl.isLocationPermitted(ctx, session, "MEDIA_MAP")` then
  `getLastLocation(...)`. A continuous path starts updates with **interval
  10000 ms, fastest 500 ms, displacement 10 m**. **Hook point** for live location
  collection (anchored via its `__redex_internal_original_name = "MapLocationManager"`).
- The actual map surface is `IgRasterMapView` / `IgStaticMapView`
  (`com.instagram.maps.*`) — native-map wrappers with no string literals (named
  but not signature-anchored). Fused location comes from `GPSLocationLibraryImpl`
  (`com.instagram.gpslocation.impl`, Google Play Services
  `LocationServices`/`GoogleApiAvailability`).

## Publish & fetch (core data flow)

- **`FriendMapPresenceApiImpl`** (`…data.presence`) **publishes** your location
  (`UpdateLastActiveLocationMutation` / `xdt_update_last_active_location`) and
  **fetches all friends' locations** (`xdt_get_all_presence_points`). It is
  aggregated by `FriendMapPresenceRepository`.
- **`FriendMapMediaRepository`** (`…data.media`) fetches location-tagged media
  highlights (`xdt_friend_location_highlights`).
- **`FriendMapReactionsApiImpl`** (`…data.reactions`) handles map reactions
  (`xdt_friend_map_reactions_update_last_seen`).

## Privacy / audience controls

- **`FriendMapSettingsApiImpl`** (`…data.settings`) is the master on/off +
  audience-mode setter: `UpdateFriendMapSettingsMutation` /
  `xdt_update_friend_map_settings`; also the location-picker disclosure
  (`xig_set_location_picker_dialog_as_seen`).
- **`FriendMapAudienceApiImpl`** (`…data.audience`) manages the allow-list:
  `xdt_update_presence_audience_list_members` / `xdt_get_presence_audience_list_members`.
- **`FriendMapLocationSharingApiImpl`** (`…data.locationsharing`) is the pairwise
  consent layer: send/remove/clean-up sharing requests
  (`xdt_location_sharing_request_mutation`,
  `xdt_remove_location_sharing_request_mutation`,
  `xdt_remove_obsolete_location_sharing_requests_mutation`), all keyed on
  `target_user_id`.
- **`FriendMapEntrypointApiImpl`** (`…data.entrypoint`) gates the entry on the
  user's sharing status (op `"GetUserSharingInfo"`).

## Entry points

- **`FriendMapUrlHandlerActivity`** (`com.instagram.urlhandlers.friendmap`,
  manifest-declared) routes deep links `friends_map`,
  `friend_map_audience_settings`, `friend_map_custom_places`.
- Numerous bottom-sheet fragments (settings, reactions, hide-places,
  multi-device, updates, presence-reply, floaty-cluster) are confirmed by their
  `__redex_internal_original_name` fields but not individually signed.

## Collect → publish flow (summary)

`FriendMapFragment` hosts `IgRasterMapView` → `MapLocationManager` gates on
`LocationPluginImpl.isLocationPermitted(…, "MEDIA_MAP")`, gets a fused location
(10 s / 500 ms / 10 m request) → `FriendMapPresenceApiImpl` publishes via
`xdt_update_last_active_location` and fetches friends via
`xdt_get_all_presence_points`. Privacy is governed by `FriendMapSettingsApiImpl`,
`FriendMapAudienceApiImpl`, and `FriendMapLocationSharingApiImpl`.
