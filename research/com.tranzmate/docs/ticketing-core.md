# Ticketing core (storage & purchase)

Moovit (`com.tranzmate`), confirmed against **version_code 1785** (versionName 5.194.0.1785). Classes are referenced by their **logical** name; the obfuscated name for this version is in [`maps/com.tranzmate/1785.json`](../../../maps/com.tranzmate/1785.json) and the regex anchors in [`signatures/com.tranzmate/signatures.yaml`](../../../signatures/com.tranzmate/signatures.yaml).

## Moovit Ticketing Core (storage & purchase) — subsystem map

The generic ticketing engine lives under `com.moovit.ticketing.*` and is R8 **partially** obfuscated: package paths and most model/Activity/ViewModel class names are **kept**, but the central `Ticket` model class and most internal helpers are renamed to short tokens, and all field/method names rotate. This subsystem covers the ticket wallet (persistent storage), the purchase flow (fare/cart/confirmation), vouchers, and rewards.

### Wallet storage (the on-disk ticket store)
Two singleton stores back the wallet, both persisted via an obfuscated name-keyed store class `scd` (a "persisted store"):
`Lscd;->r(Landroid/content/Context; Ljava/lang/String; <writer-coder> <reader-coder>)Lscd;`.
- **UserWalletStore** — active wallet. Persisted under the name **`"ticketing_user_wallet_store"`**. Holds `moovitServerTickets` (List of the Ticket model), `validations`, `storedValues`, `agencyMessagesByKey` (Map), and `quickPurchaseInfo` (QuickPurchaseInfo). Static accessor loads/caches the store into a `volatile scd` field and logs `iu9.G("UserWalletStore", ... "Unable to initialize ticketing user wallet store!")` on failure.
- **HistoryUserWalletStore** — past tickets. Persisted under **`"ticketing_history_user_wallet_store"`**; holds only `moovitServerTickets` (history list).

Each persistable model exposes a static Coder (`khe`/`vbf`/`mi3`/`bnb`/`z`/`li4` instances constructed with `(Class, id, versionCode)`) used by `lla.u(parcel, this, CODER)` in `writeToParcel` — this Coder is the serialization descriptor for both Parcel and the persisted store.

### Ticket model & identity
The core **Ticket** class is `com.moovit.ticketing.ticket.a` (renamed; implements interface `odg`). It aggregates: `TicketId`, ticketId string, `Ticket$Status`, name, `TicketAgency`, `CurrencyAmount` price, several long timestamps, `PassengerInfo`, `Ticket$Alert`, `TicketMultipleActivationsInfo`, attribution `Image`, and boolean flags. It is **not emitted as a signature** — every candidate anchor (its validation strings like `"ticketStatus"`, and its kept-type constructor signature) also appears in its Parcelable/coder serializers (`vbf`, `c56`, `the`, `providers/mobeepass/a`), so no class-unique anchor exists. Its identity keys are still recoverable from **TicketId** (providerId `ServerId` + agencyKey + ticketId, optional payload Map) and **TicketRef** (TicketId + `ParcelableMemRef` to the Ticket).
- **Ticket$Status** — kept enum: ACTIVE, VALID_AUTO_ACTIVATE, VALID, VALID_AUTO_MANAGED, NOT_YET_VALID, ISSUING_IN_PROGRESS, EXPIRED, CANCELED, each with an int `priority` (2000..7000) surfaced via the model's `getPriority()`.
- **TicketAgency** — agencyKey/agencyName + logo/background `Image` + `DbEntityRef<TransitAgency>`.

### Purchase flow
`PurchaseTicketActivity` (extends `AbstractPaymentGatewayActivity`) is the entry point; it reads a `PurchaseTicketIntent`/`purchaseIntent` extra (`"ticket_purchase_intent_se"`), tracks UTM params, and drives a chain of `PurchaseStep` (abstract: contextId + analyticKey; subclasses for fare selection, day selection, cart, stored-value, mobeepass, web/intercity). Fares are modelled by **TicketFare** (id, providerId, name, price/fullPrice `CurrencyAmount`, quantityLimit, `TicketAgency`, `PurchaseVerificationType`, providerData) built into a **CartInfo**/**CartItem** cart. **PurchaseCartConfirmationActivity** (extends `AbstractPaymentGatewayActivity`) is the final confirm-and-buy screen — analytics `"ticketing_cart"`, `"cart_confirmation_view"`, `"purchase_clicked"`, an abandon-cart dialog, and a full-wallet guard (`"The wallet is full - can not add an additional item!"`). (Note: CartInfo/CartItem/PurchaseStep mirror thrift structs `MVPurchaseCartInfo`/`MVPurchaseCart*` and share all their strings, so they have no class-unique anchor and are not emitted.)

### Vouchers
`VoucherManagementActivity` + **VouchersManagementViewModel** (extends AndroidViewModel base `h60`) manage a **VoucherWallet** (`data class`, list of **ReservedVoucher**{code, title, descriptionHtml, expirationTime}). The VM guards on `"Voucher management is not active"`, exposes reserve/apply flows (analytics `voucher_management_apply_clicked`, `voucher_management_screen_impression`; add dialog tag `ADD_MANAGEMENT_VOUCHER_DIALOG`), and its synthetic flow classes carry `"Failed to reserve voucher."` / `"Failed to calculate voucher wallet ui state!"`.

### Rewards
**VelociaViewModel** (extends `h60`) powers the Velocia rewards screen (`VelociaActivity`): loads a Velocia webview URL, computes a home-menu item + full-screen UiState, guards `"Velocia is not supported"`, and emits `home_menu_item_velocia_rewards_impression`.

### Notable Frida/Xposed hook points
- **UserWalletStore.getStore(Context)** (static loader, anchored by `"ticketing_user_wallet_store"`) — single best hook to read/tamper the entire active wallet (tickets, validations, stored values). **HistoryUserWalletStore.getStore(Context)** for past tickets. The two store-name strings also identify the on-disk files.
- **Ticket model `com.moovit.ticketing.ticket.a` constructor / `getPriority()`** — observe every ticket materialised from server/store (renamed class; reach it via UserWalletStore's `moovitServerTickets`).
- **TicketFare / TicketAgency / VoucherWallet / ReservedVoucher `writeToParcel` / constructors** — observe fare, agency and voucher data as it crosses process/persistence boundaries.
- **PurchaseTicketActivity** (entry) and **PurchaseCartConfirmationActivity** (final purchase; hook the purchase action behind `"purchase_clicked"`) — intercept/observe the buy flow.
- **VouchersManagementViewModel** (reserve/apply voucher) and **VelociaViewModel** (rewards) — hook to observe or override entitlement/reward state.
- **Ticket$Status** — map ticket status/priority values.

## Classes identified

| Logical class | Renamed? | Confidence | Identity evidence |
| --- | --- | --- | --- |
| `UserWalletStore` | no | high | Kept class name; Parcelable holder of moovitServerTickets/validations/storedValues/agencyMessagesByKey/quickPurchaseInfo; static singleton persisted via scd.… |
| `HistoryUserWalletStore` | no | high | Kept class name; Parcelable holder of a history moovitServerTickets list; static singleton persisted via scd.r(context, "ticketing_history_user_wallet_store"… |
| `TicketAgency` | no | high | Kept class name; Parcelable model with agencyKey/agencyName + logo/background Image + DbEntityRef<TransitAgency>; distinctive toString prefix "TicketAgency{a… |
| `TicketFare` | no | high | Kept class name; purchasable fare model (id, providerId ServerId, name, price/fullPrice CurrencyAmount, quantityLimit, TicketAgency, PurchaseVerificationType… |
| `VoucherWallet` | no | high | Kept class name; Kotlin data/Parcelable class wrapping an ArrayList of ReservedVoucher; distinctive toString "VoucherWallet(reservedVouchers=". Anchor is the… |
| `ReservedVoucher` | no | high | Kept class name; Kotlin data/Parcelable class with code/title/descriptionHtml/expirationTime; distinctive toString "ReservedVoucher(code=". Anchor is the toS… |
| `Ticket.Status` | no | high | Kept inner enum name (leaks that the outer 'Ticket' model was renamed); Parcelable enum with values ACTIVE/VALID_AUTO_ACTIVATE/VALID/VALID_AUTO_MANAGED/NOT_Y… |
| `VelociaViewModel` | no | high | Kept class name; AndroidViewModel (obfuscated base h60, rotates) driving the Velocia rewards screen: loads Velocia webview URL + required data, computes menu… |
| `VouchersManagementViewModel` | no | high | Kept class name; AndroidViewModel (obfuscated base h60) managing the VoucherWallet: fetch wallet, reserve/apply voucher, payment-account flow; in-class guard… |
| `VoucherManagementActivity` | no | high | Kept class name; voucher management screen; shows the add-voucher dialog (fragment tag "ADD_MANAGEMENT_VOUCHER_DIALOG"), reads initialCode extra, emits vouch… |
| `PurchaseCartConfirmationActivity` | no | high | Kept class name; final cart confirm-and-buy screen (extends AbstractPaymentGatewayActivity); analytics ticketing_cart/cart_confirmation_view/purchase_clicked… |
| `PurchaseTicketActivity` | no | high | Kept class name; entry point of the ticket purchase flow (extends AbstractPaymentGatewayActivity); reads a PurchaseTicketIntent from the "ticket_purchase_int… |

