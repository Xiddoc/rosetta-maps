# User account & profile

Moovit (`com.tranzmate`), confirmed against **version_code 1785** (versionName 5.194.0.1785). Classes are referenced by their **logical** name; the obfuscated name for this version is in [`maps/com.tranzmate/1785.json`](../../../maps/com.tranzmate/1785.json) and the regex anchors in [`signatures/com.tranzmate/signatures.yaml`](../../../signatures/com.tranzmate/signatures.yaml).

## Moovit — User account & profile subsystem

Moovit's user-account layer is exposed through Android's `getSystemService` registry on `MoovitAppApplication`. `getSystemService("user_account_manager_service")` returns the app component keyed `"USER_ACCOUNT"` — the **UserAccountManager** (`juf`). That manager owns three `UserAccountDataProvider`s, one per `UserAccountDataProvider$ProviderType` value (FAVORITES / NOTIFICATIONS / PROMOTIONS):

- `UserAccountManager.a()` → **FavoritesManager** (`awf`, `getType()→FAVORITES`), also reachable via `getSystemService("user_favorites_manager_service")`.
- `UserAccountManager.b()` → **UserNotificationsManager** (`pwf`, `getType()→NOTIFICATIONS`), also via `getSystemService("user_notifications_manager_service")`.
- **UserPromotionsManager** (`xwf`, `getType()→PROMOTIONS`).

Each provider refreshes from the server and fires a completion broadcast, e.g. `com.moovit.useraccount.manager.notifications.user_notifications_update_success/_failure` and `com.moovit.useraccount.manager.promotions.user_promotions_update_success/_failure`. Notifications/promotions persist to `user_notifications.dat` etc.

### Favorites
`FavoritesManager` (`awf`) provides add/remove for favorite line/stop/location/route (param strings `line`, `stop`, `location`, `favoriteRouteId`). Actual on-disk persistence + version migration lives in `lw4` (a `qh3` component): it reads/writes per-metro `.dat` files — `favorite_home_%s.dat`, `favorite_work_%s.dat`, `favorite_stops_vtwo_%s.dat`, `favorite_lines_vtwo_%s.dat`, `favorites_routes_%s.dat`, `favorites_locations_%s.dat` — and runs upgraders logged as `FavoriteStopsMigrator`, `FavoriteLocationsMigrator`, `FavoriteRoutesMigrator`, `FavoriteLineGroupsMigrator`. Favorite domain models are kept-name Parcelables (`Favorite` base + `FavoriteLocation`/`FavoriteStop`/`FavoriteRoute`/`FavoriteLineGroup`, `FavoriteSource` enum) using reflective CODERs; they serialize via bracketed toString forms like `[[NAME,…][LOCATION,…][SOURCE,…]]`.

### Payment account identity (overlaps user identity)
`PaymentAccountManager` (`iva`, tag `PaymentAccountManager`, service key `payment_account_manager`) holds the connected payment/identity account and its prefs (`account_id`, `account_type`, `account_auth_required`, `account_auth_type`, `last_connected_account_type`, `default_payment_gateway_type`, `last_purchase_pref`). It broadcasts `com.moovit.payment.account.action.created/updated/deleted` on account lifecycle changes and calls `invalidate` / `notifyPurchase`.

Account/device authentication is a separate cluster:
- **PaymentAccountAuthManager** (`v37`, tag `PaymentAccountAuthManager`) reads/writes the auth token blob `payment_account_auth_info_v2.dat` via `setAuthInfo`/`getAuthInfo`.
- **AccountAuthGetTokenTask** (`ec`) fetches/refreshes the network access token (`getNetworkAccessToken attempt #%d …`, caches + validates tokens).
- `pac` (abstract) injects `Authorization` / `Access-Token` headers into requests and reacts to `CLIENT_ACCOUNT_ACCESS_TOKEN_INVALID`, `CLIENT_ACCOUNT_REFRESH_TOKEN_INVALID`, `CLIENT_DEVICE_ACCESS_TOKEN_INVALID` (uses both `PaymentAccountAuthManager` and `DeviceAuthManager` tags).

### Connect / login / logout
Social/account connect uses the kept-name enum `ConnectProvider` (FACEBOOK / GOOGLE / MOOVIT). Logout is driven from account screens (analytics `logout_confirmed_clicked` / `logout_canceled_clicked` in `ExternalPaymentAccountActivity`) and clears state through `PaymentAccountManager.invalidate` and the `UserAccountManager` providers. Profile ad-targeting data is carried by the kept-name model `UserAdsTargetingData` (`userTags` + `customUserProperties`).

### Good Frida / Xposed hook points
- **UserAccountManager (`juf`) constructor / a()/b()** — observe or swap the favorites/notifications providers, or intercept account-manager creation.
- **FavoritesManager (`awf`)** — hook add/remove-favorite methods to log or force favorites.
- **`lw4`** — hook the `.dat` read/write to dump or spoof persisted favorites; hook migrators to trace upgrades.
- **UserNotificationsManager (`pwf`) / UserPromotionsManager (`xwf`)** update methods (`"Updating user notifications"` / `"Updating user promotions"`) — intercept server sync results.
- **PaymentAccountManager (`iva`).invalidate / .notifyPurchase** — detect logout/account-change and purchase events; the created/updated/deleted broadcasts are cheap external observation points.
- **PaymentAccountAuthManager (`v37`).setAuthInfo** and **AccountAuthGetTokenTask (`ec`)** — capture or replace auth tokens; `pac` header injection is the choke point for outbound authenticated requests.

### Notes on obfuscation / verification
The tree is R8 partially-obfuscated: managers/providers are renamed to default-package short tokens (`juf`, `awf`, `lw4`, `pwf`, `xwf`, `iva`, `v37`, `pac`, `ec`) → `kept:false`; the Parcelable domain/profile models keep their names (confirmed genuinely kept via reflective-CODER `const-class` self-references) → `kept:true`. Every class anchor below is a `const-string` literal (rename-immune) verified to occur the stated number of times in the target file AND to match exactly one class file across all 8 smali dirs. Method anchors are in-class-unique const-strings marking hook-point methods.

## Classes identified

| Logical class | Renamed? | Confidence | Identity evidence |
| --- | --- | --- | --- |
| `UserAccountManager` | yes | high | Component returned by MoovitAppApplication.getSystemService("user_account_manager_service") = this.e.d("USER_ACCOUNT"), cast to juf. juf.a() returns the FAVO… |
| `FavoritesManager` | yes | high | UserAccountDataProvider whose getType() returns UserAccountDataProvider$ProviderType.FAVORITES; returned by UserAccountManager.a() / getSystemService("user_f… |
| `FavoritesLocalStore` | yes | medium | qh3 component that persists favorites to per-metro .dat files (favorite_home_%s.dat, favorite_stops_vtwo_%s.dat, favorites_routes_%s.dat, etc.) and runs vers… |
| `UserNotificationsManager` | yes | high | UserAccountDataProvider getType()->NOTIFICATIONS; returned by UserAccountManager.b(). Leaks tag "UserNotificationsManager", broadcasts com.moovit.useraccount… |
| `UserPromotionsManager` | yes | high | UserAccountDataProvider getType()->PROMOTIONS. Leaks tag "UserPromotionsManager", broadcast com.moovit.useraccount.manager.promotions.user_promotions_update_… |
| `PaymentAccountManager` | yes | high | Holds the connected payment/identity account: tag "PaymentAccountManager", service key "payment_account_manager", prefs account_id/account_type/account_auth_… |
| `PaymentAccountAuthManager` | yes | high | Tag "PaymentAccountAuthManager"; reads/writes the auth token blob "payment_account_auth_info_v2.dat" (globally unique) via setAuthInfo/getAuthInfo ("setAuthI… |
| `AccountAuthGetTokenTask` | yes | high | Log tag "AccountAuthGetTokenTask" (repeated 6x, globally unique) names the class; body validates cached tokens and calls getNetworkAccessToken with retry ("g… |
| `AccountAuthHeadersProvider` | yes | medium | Abstract type that injects Authorization / Access-Token request headers and handles auth-error codes CLIENT_ACCOUNT_ACCESS_TOKEN_INVALID / CLIENT_ACCOUNT_REF… |
| `UserAdsTargetingData` | no | high | Kept-name Parcelable profile model (userTags + customUserProperties maps) with reflective CODER (const-class self-reference confirms it is genuinely kept). t… |
| `FavoriteLocation` | no | high | Kept-name Parcelable extending Favorite (reflective CODER const-class self-ref confirms kept). Serializes as [[NAME,…][LOCATION,…][SOURCE,…]]; anchor "][LOCA… |

