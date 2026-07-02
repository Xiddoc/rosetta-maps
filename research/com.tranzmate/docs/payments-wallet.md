# Payments & wallet

Moovit (`com.tranzmate`), confirmed against **version_code 1785** (versionName 5.194.0.1785). Classes are referenced by their **logical** name; the obfuscated name for this version is in [`maps/com.tranzmate/1785.json`](../../../maps/com.tranzmate/1785.json) and the regex anchors in [`signatures/com.tranzmate/signatures.yaml`](../../../signatures/com.tranzmate/signatures.yaml).

## Moovit Payments & Wallet subsystem (com.tranzmate 5.194.0.1785 / vc 1785)

R8 is *partially* applied: package paths and many top-level types (Activities, ViewModels, Fragments, Thrift `MV*` structs, model data-classes) keep their names, but **methods/fields are renamed to short tokens even inside kept classes**, and a few central logic classes are fully renamed to short tokens (`iva`, `com.moovit.payment.contacts.c`). Synthetic/lambda classes leak original names (e.g. `PaymentContextContactsRepository$fetchContacts$1`) which is how the renamed outer classes were recovered.

### Core state holder — PaymentAccountManager (`iva`, default package)
Process-wide singleton (`iva.a()`, `volatile iva l`). Owns the connected **payment account** and its auth. Persists to SharedPreferences via keys `account_id`, `account_type`, `last_connected_account_type`, `account_auth_type`, `account_auth_required`, `default_payment_gateway_type`, `last_purchase_pref` (log tag `PaymentAccountManager`, worker pool `m-pa`). `setPaymentAccount(...)` (in synthetic `no5`) writes prefs, stores `AuthenticationInfo`, then broadcasts `com.moovit.payment.account.action.created`; `invalidate(action)` (method `h`) fires account-changed broadcasts; `notifyPurchase(time)` (method `j`) records the last-purchase timestamp; account deletion lives in synthetic `g96`. **Prime hook point** for reading/forcing the logged-in payment account, auth state, and default gateway.

### Contacts repository — PaymentContextContactsRepository (`com.moovit.payment.contacts.c`)
Per-payment-context contacts repo; constructor takes the payment-context id string, runs on its own `CoroutineScope`, uses server domain string `contacts`, and loads `CONFIGURATION` app-data. Suspend/instance methods: add contact (`b`), fetch contacts (`e`, logs `fetchContacts[…]`), resend invitation link (`f`, logs `resendInvitationLink[…]`), remove, and fetch-contact-profile. Validation `Contact or Instruction must be set!`. Hook `fetchContacts`/add to observe or tamper with payment-contact operations (family/linked payers).

### Data models
`PaymentAccount` (kept) is the central object: accountId, AccountType, payment-account *contexts*, PersonalDetails, **paymentMethods**, profiles, certificates, badge, PaymentAccountSettings, account products, smart cards. `PaymentAccountContact` and `PaymentAccountProfile` (kept data classes) model a contact and a rider profile (profile + status + linked text). Payment methods are a sealed hierarchy under `com.moovit.payment.account.paymentmethod.PaymentMethod` (abstract, id + default flag + status) with concretes `CreditCardPaymentMethod`, `BalancePaymentMethod` (wraps `BalancePreview` = icon/caption/`CurrencyAmount`), Bank/External. Note: `PaymentMethod`, `CreditCardToken`, `BalancePreview` were **not** signed — their only string literals (`paymentMethodId`, `preview`, `balance`) are not class-unique, so no rotation-stable anchor exists (kept the classes out rather than emit a shaky anchor).

### Wallet & invoices ViewModels (kept; base class renamed to `h60`)
`MyWalletViewModel` (widget), `WalletItemsViewModel` (list; requires `setCategory()` first, loads `WALLET_UI_CONFIGURATION`, keyed by `viewmodel_category`), `WalletItemsActionViewModel` (action widget, folds in `PaymentAccount`), and `PaymentAccountUpcomingPaymentViewModel` (invoices/upcoming payments; `fetchAccountInvoices`). Each exposes a private **`calculateUiState(...)`** reducer whose full method-descriptor survives as a string literal in smali (a stable, class-unique anchor). Hook `calculateUiState` to inspect/override wallet & invoice UI state.

### Payment gateway / clearing flow — PaymentGatewayFragment (kept; base `rk9`)
Central orchestrator of tokenization/clearing. Keeps the in-progress tokenizer under bundle key `activeTokenizer` (saved/restored across config changes) and routes `onActivityResult` to it. Implements a visitor over gateway / payment-method types — distinct methods take `GooglePayGateway` (`s0`), `CashGateway` (`J0`), `PaymentMethodGateway` (`M0`), `CreditCardPaymentMethod` (`W0`), `BankPaymentMethod` (`b0`), `ExternalPaymentMethod` (`f0`), `BalancePaymentMethod` (`l`). `z1()` emits analytics `payment_method_add_clicked` and launches the add-payment-method flow. The actual tokenizers live in `com.moovit.payment.gateway.*` (kept names): `GooglePayGateway$GooglePayTokenizer` (Google Pay, requestCode 3834, analytics `google_pay`), `ClearanceProviderGateway$ClearanceProviderTokenizer` (CreditGuard/clearance provider, requestCode 3835), `PaymentMethodCvvTokenizer` (CVV re-entry, fragment tag `payment_extra_info_cvv`), `CashGateway`. These tokenizer subclasses were not signed individually — their strings (`google_pay`, `clearanceProviderType`, `payment_extra_info_cvv`, `paymentDataRequest`) also appear in Thrift structs / sibling fragments, so they are not class-unique; hook them via their kept FQCNs instead.

### Serialization / wire formats
Models implement a custom versioned Parcel codec, not stock Parcelable: static descriptor fields `new z(Class, v, code)` / `m9(...)` / `do9(...)` plus `lla.u(parcel, this, DESC)` on write (the field names rotate but the pattern is stable). The **wire format is Thrift**: `com.tranzmate.moovit.protocol.payments.MV*` (e.g. `MVAddPaymentMethodInfo`, `MVPaymentMethodCardInfo`, `MVCardType`, `MVGooglePayInstructions`). `CreditCardToken.a(...)` maps a `CreditCardPreview` into `MVPaymentMethodCardInfo`/`MVAddPaymentMethodInfo` — a good hook to observe card metadata (last-4/expiry/type) leaving the app.

### Best Frida/Xposed hook points
- `PaymentAccountManager` (`iva`) `invalidate`/`notifyPurchase` + the `no5`/`g96` setters/deleter — observe/force account & auth state.
- `PaymentContextContactsRepository` (`c`) `fetchContacts`/add — payment-contact ops.
- `PaymentGatewayFragment` `activeTokenizer` + `z1()` + the per-type visitor methods — intercept the whole clearing/tokenization flow.
- Wallet/invoice `calculateUiState` reducers — read or rewrite wallet & upcoming-payment UI state.

## Classes identified

| Logical class | Renamed? | Confidence | Identity evidence |
| --- | --- | --- | --- |
| `PaymentAccountManager` | yes | high | Singleton (static a()Liva; + volatile iva l). Log tag "PaymentAccountManager" used in invalidate/notifyPurchase (this class) and in setPaymentAccount/delete … |
| `PaymentContextContactsRepository` | yes | high | Outer class renamed to c, but its lambda/suspend synthetics keep the original name (com.moovit.payment.contacts.PaymentContextContactsRepository$add$2, $fetc… |
| `PaymentAccount` | no | high | Kept class name. Constructor validates fields via b56.v with literal names accountId, accountType, paymentAccountContexts, personalDetails, paymentMethods, p… |
| `PaymentAccountContact` | no | high | Kept Kotlin data class (id, PaymentAccountContactPersonalInfo, PaymentAccountContactStatus, PaymentAccountContactAdditionalInfo). Generated toString literal … |
| `PaymentAccountProfile` | no | high | Kept model. Constructor validates fields profile, status, linkedText via b56.v; "linkedText" is class-unique globally. Rider profile within a PaymentAccount. |
| `MyWalletViewModel` | no | high | Kept ViewModel (base class renamed to h60). Listens to active/future wallet-update broadcasts (activeWalletUpdatesReceiver, futureWalletUpdatesReceiver) and … |
| `WalletItemsActionViewModel` | no | high | Kept ViewModel (base h60) for the wallet action widget; folds AppDataParts + PaymentAccount into a UiState. calculateUiState descriptor literal (with AppData… |
| `WalletItemsViewModel` | no | high | Kept ViewModel (base h60) backing the wallet items list; requires setCategory() before use (guard string "Must call setCategory() first." appears twice), key… |
| `PaymentAccountUpcomingPaymentViewModel` | no | high | Kept ViewModel (base h60) for account invoices / upcoming payments; has fetchAccountInvoices + invoicesFlow/profileFlow synthetics and a calculateUiState red… |
| `PaymentGatewayFragment` | no | high | Kept Fragment (base renamed rk9) orchestrating the tokenization/clearing flow. Holds the in-progress tokenizer under bundle key "activeTokenizer" (saved/rest… |

